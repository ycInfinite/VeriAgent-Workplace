"""Bounded read-only SSH chunk retrieval for the two registered adapters."""
import concurrent.futures
import getpass
import hashlib
import json
from pathlib import Path
import shlex
import time
import paramiko
from remote_session import PinnedKey

ROOT = Path(__file__).resolve().parents[1]
REMOTE = '/root/autodl-tmp/veriagent-workplace-sft-20261010/'
PIN = 'SHA256:liZ36vNCsNcNdXeWs4f+g5ZIhPM/ZihP834vxs8Ulqc'


def main():
    folder = ROOT/'evidence/preference29-20261016'
    manifest = json.loads((folder/'adapters.json').read_text())
    receipt = folder/'adapter_download.json'
    assert not receipt.exists()
    secret = getpass.getpass('SSH password (not logged): ')
    start = time.time()
    records = []
    for rel, spec in manifest.items():
        assert rel.startswith(('experiments/PREF29-CHOSEN-SFT-20261016-001/adapter/',
                               'experiments/PREF29-DPO-20261016-001/adapter/'))
        dest = (ROOT/rel).resolve()
        assert dest.is_relative_to(ROOT)
        if dest.exists() and hashlib.file_digest(dest.open('rb'), 'sha256').hexdigest() == spec['sha256']:
            records.append({'path': rel, 'status': 'existing_sha256_verified'})
            continue
        assert not dest.exists(), 'Preserve incomplete previous copy before recovery'
        block = 1024*1024
        total_blocks = (spec['bytes']+block-1)//block
        width = (total_blocks+3)//4
        chunks = [(i, min(width, total_blocks-i)) for i in range(0, total_blocks, width)]
        def fetch(item):
            offset, count = item
            part = dest.with_name(dest.name+'.chunk'+str(offset)+'.part')
            assert not part.exists()
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(PinnedKey(PIN))
            try:
                client.connect('connect.westb.seetacloud.com', port=33142, username='root',
                               password=secret, look_for_keys=False, allow_agent=False,
                               timeout=20, auth_timeout=20, banner_timeout=20)
                transport = client.get_transport()
                channel = transport.open_session(window_size=16*1024*1024, max_packet_size=65536)
                channel.settimeout(120)
                channel.exec_command('dd if='+shlex.quote(REMOTE+rel)+' bs=1048576 skip='+str(offset)+
                                     ' count='+str(count)+' status=none')
                received = 0
                with part.open('xb') as f:
                    while True:
                        buf = channel.recv(1024*1024)
                        if not buf:
                            break
                        f.write(buf)
                        received += len(buf)
                assert channel.recv_exit_status() == 0
                assert received == min(count*block, spec['bytes']-offset*block)
                return offset, part
            finally:
                client.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            parts = sorted(pool.map(fetch, chunks))
        dest.parent.mkdir(parents=True, exist_ok=True)
        combined = dest.with_name(dest.name+'.verified-download.part')
        with combined.open('xb') as out:
            for _, part in parts:
                with part.open('rb') as f:
                    while buf := f.read(1024*1024):
                        out.write(buf)
        with combined.open('rb') as f:
            actual = hashlib.file_digest(f, 'sha256').hexdigest()
        assert actual == spec['sha256'] and combined.stat().st_size == spec['bytes']
        combined.rename(dest)
        records.append({'path': rel, 'status': 'four_chunk_full_SHA256_verified', 'sha256': actual,
                        'bytes': spec['bytes'], 'partial_chunks_retained': True})
        print(json.dumps(records[-1]), flush=True)
    secret = None
    receipt.write_text(json.dumps({'status': 'ALL_SIX_ADAPTER_FILES_SHA256_VERIFIED', 'files': records,
                                  'started_epoch': start, 'ended_epoch': time.time()}, indent=2), encoding='utf-8')
    print(json.dumps({'status': 'ALL_SIX_ADAPTER_FILES_SHA256_VERIFIED'}), flush=True)


if __name__ == '__main__':
    main()
