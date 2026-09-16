"""Start the official interactive TUI. No prompt injection, pipe, queue or batch mode."""
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != 'linux' or not sys.stdin.isatty() or not sys.stdout.isatty():
        raise RuntimeError('Use the personal remote Linux terminal interactively; do not pipe prompts')
    destination = ROOT/'.cache/interactive-client'
    receipt = json.loads((destination/'installation.json').read_text())
    key = getpass.getpass('Token Plan key (hidden; process environment only): ')
    if not key.startswith('sk-sp-') or any(c.isspace() for c in key):
        raise ValueError('Expected a Token Plan key without whitespace; credential suppressed')
    env = os.environ.copy()
    env['QWEN_HOME'] = receipt['client_home']
    env['OPENAI_API_KEY'] = key
    env['BAILIAN_TOKEN_PLAN_API_KEY'] = key
    env['OPENAI_BASE_URL'] = 'https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1'
    env['OPENAI_MODEL'] = 'qwen3.8-max'
    env['QWEN_CODE_DISABLE_CRON'] = '1'
    env['QWEN_CODE_DISABLE_WORKFLOWS'] = '1'
    env['PATH'] = str(Path(receipt['node']).parent)+os.pathsep+env.get('PATH','')
    key = None
    transcript = destination/('client-events-'+uuid.uuid4().hex+'.jsonl')
    # The inspected 0.23.4 registry keeps MCP tools available under whole-tool
    # denies for built-ins. Keep files, shell, web, subagents and schedules absent.
    excluded = ['read_file','zoom_image','write_file','edit','notebook_edit','glob','grep_search',
                'run_shell_command','list_directory','read_mcp_resource','web_fetch','web_search',
                'todo_write','save_memory','lsp','cron_create','cron_list','cron_delete','loop_wakeup',
                'create_sub_session','monitor','agent','skill','send_message','computer_use','code_mode']
    command = [receipt['node'], receipt['qwen_cli'], '--bare', '--auth-type','openai',
               '--openai-base-url',env['OPENAI_BASE_URL'],'--model','qwen3.8-max',
               '--mcp-config',str(destination/'mcp.json'),'--allowed-mcp-server-names','workplace',
               '--approval-mode','default','--max-session-turns','6','--max-tool-calls','8',
               '--openai-logging=false','--telemetry=false','--json-file',str(transcript),
               '--system-prompt','You are helping the user debug one public Workplace task. '
               'Use only the workplace MCP tools. Begin with get_task, ground identifiers in '
               'the task and actual observations, and finish once with finish_task. '
               'Never invent tool observations or claim training eligibility. '
               'Wait for the user to initiate the task.','--exclude-tools',*excluded]
    print('Official interactive client. You must type the task yourself; no automated prompt will be sent.',flush=True)
    process = subprocess.Popen(command,cwd=receipt['workspace'],env=env)
    env.pop('OPENAI_API_KEY',None)
    env.pop('BAILIAN_TOKEN_PLAN_API_KEY',None)
    try:
        process.wait(timeout=1800)
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        print('Interactive session ended at the 30-minute process bound.')
    print('Client exited. Preserve tool logs and client transcript for review; no SFT approval is implied.')


if __name__ == '__main__':
    main()
