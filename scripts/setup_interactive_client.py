"""Install official pinned CLI/SDK into project cache and prepare a human session.

No model requests, keys, global settings, GPU operations or automated prompts.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
NODE_VERSION = '24.19.0'
QWEN_VERSION = '0.23.4'
QWEN_INTEGRITY = 'sha512-qrM7Lwp9S6LfIx8Mh9sAr4aBPyUa9W0k72uOQJPsJ6Z8ClAzoEQzkdLD1TrchioJicgSckM1PLyendibyXHElA=='


def run(command, env=None):
    return subprocess.run(command, check=True, capture_output=True, text=True,
                          env=env, timeout=600).stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--install', action='store_true')
    parser.add_argument('--node', type=Path)
    args = parser.parse_args()
    cache = ROOT/'.cache'
    cache.mkdir(exist_ok=True)
    node_sha = None
    if args.install:
        if platform.system() != 'Linux' or platform.machine() not in ('x86_64','AMD64'):
            raise ValueError('Automatic runtime install is limited to the prepared Linux x64 host')
        name = f'node-v{NODE_VERSION}-linux-x64'
        archive = cache/(name+'.tar.xz')
        url = f'https://nodejs.org/dist/v{NODE_VERSION}/'
        sums = urllib.request.urlopen(url+'SHASUMS256.txt', timeout=30).read().decode()
        node_sha = next(line.split()[0] for line in sums.splitlines() if line.endswith(archive.name))
        if not archive.exists():
            with urllib.request.urlopen(url+archive.name, timeout=60) as response, archive.open('xb') as target:
                while data := response.read(1024*1024):
                    target.write(data)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != node_sha:
            raise ValueError('Node archive checksum mismatch; retained for diagnosis')
        if not (cache/name/'bin/node').is_file():
            with tarfile.open(archive) as source:
                source.extractall(cache, filter='data')
        node = cache/name/'bin/node'
        env = os.environ.copy()
        env['PATH'] = str(node.parent) + os.pathsep + env.get('PATH','')
        print('Installing pinned official Qwen Code; no provider key used', flush=True)
        run([str(node), str(cache/name/'lib/node_modules/npm/bin/npm-cli.js'), 'install',
             '--prefix', str(cache/'qwen-code'), '--cache', str(cache/'npm'),
             '--no-audit','--no-fund','--registry=https://registry.npmjs.org',
             '--fetch-retries=0','--fetch-timeout=30000',f'@qwen-code/qwen-code@{QWEN_VERSION}'], env)
        print('Installing isolated MCP SDK', flush=True)
        run([sys.executable,'-m','pip','install','--target',str(cache/'interactive-python'),
             '-r',str(ROOT/'requirements-interactive.pinned.txt'), '--disable-pip-version-check',
             '--no-warn-script-location','--retries','0','--timeout','30'])
    else:
        if args.node is None:
            raise ValueError('Specify an existing node executable, or use --install on Linux')
        node = args.node.resolve()
    cli = cache/'qwen-code/node_modules/@qwen-code/qwen-code/cli.js'
    if run([str(node),'--version']) != 'v'+NODE_VERSION:
        raise ValueError('Unexpected Node version')
    if run([str(node),str(cli),'--version']) != QWEN_VERSION:
        raise ValueError('Unexpected Qwen Code version')
    lock = json.loads((cache/'qwen-code/package-lock.json').read_text())
    if lock['packages']['node_modules/@qwen-code/qwen-code']['integrity'] != QWEN_INTEGRITY:
        raise ValueError('Qwen Code registry package integrity differs from the checked version')
    destination = cache/'interactive-client'
    client_home = destination/'client-home'
    workspace = destination/'workspace'
    client_home.mkdir(parents=True,exist_ok=True)
    workspace.mkdir(parents=True,exist_ok=True)
    settings = json.loads((ROOT/'configs/qwen_code_token_plan.example.json').read_text(encoding='utf-8'))
    settings['telemetry'] = {'enabled':False,'logPrompts':False}
    settings['mcpServers'] = {'workplace':{
        'command':sys.executable, 'args':[str(ROOT/'scripts/serve_workplace_interactive.py'),'--task-id','707'],
        'cwd':str(ROOT),'trust':False, 'timeout':60000,
        'env':{'PYTHONIOENCODING':'utf-8','BAILIAN_TOKEN_PLAN_API_KEY':'','OPENAI_API_KEY':''}}}
    settings_path = client_home/'settings.json'
    previous = destination/'installation.json'
    previous_receipt = json.loads(previous.read_text()) if previous.exists() else {}
    if settings_path.exists():
        existing = json.loads(settings_path.read_text())
        # The official CLI adds a schema-version marker on first use. Preserve it;
        # it is not a user preference or a credential. Other changes still fail closed.
        if '$version' in existing:
            settings['$version'] = existing['$version']
    if settings_path.exists() and json.loads(settings_path.read_text()) != settings:
        old = settings_path.read_bytes()
        old_hash = hashlib.sha256(old).hexdigest()
        if old_hash != previous_receipt.get('settings_sha256'):
            raise FileExistsError('Client settings changed since our receipt; review rather than overwrite')
        backup = client_home/('settings.before-'+old_hash[:12]+'.json')
        if not backup.exists():
            backup.write_bytes(old)
    settings_path.write_text(json.dumps(settings,indent=2),encoding='utf-8')
    (destination/'mcp.json').write_text(json.dumps({'mcpServers':settings['mcpServers']},indent=2),encoding='utf-8')
    if node_sha is None and previous_receipt.get('node') == str(node):
        node_sha = previous_receipt.get('node_archive_sha256')
    receipt = {'node':str(node),'node_version':NODE_VERSION,'node_archive_sha256':node_sha,
               'qwen_cli':str(cli),'qwen_version':QWEN_VERSION,'qwen_integrity':QWEN_INTEGRITY,
               'python':sys.executable,'sdk_version':'1.30.0','workspace':str(workspace),
               'client_home':str(client_home),'provider_requests':0,'credentials_persisted':False,
               'settings_sha256':hashlib.sha256(settings_path.read_bytes()).hexdigest()}
    (destination/'installation.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
