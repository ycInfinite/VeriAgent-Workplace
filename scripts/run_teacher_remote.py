"""Non-echoing SSH terminal bridge for the already deployed bounded teacher run.

No credential arguments, files, local environment variables, raw exception output,
or retries. The API key travels only through SSH stdin after remote getpass is ready.
"""
import argparse
import getpass
import json
import re
import shlex
import sys
import time
import warnings

import paramiko
from remote_session import PinnedKey


def hidden(prompt):
    if not sys.stdin.isatty():
        raise RuntimeError('A real non-echoing terminal is required')
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        return getpass.getpass(prompt)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--pin', required=True)
    parser.add_argument('--run-id', required=True)
    args = parser.parse_args()
    if not re.fullmatch(r'TEACHER-ACQUIRE-\d{8}-\d{3}', args.run_id):
        raise ValueError('Invalid immutable run ID')
    client = paramiko.SSHClient(); client.set_missing_host_key_policy(PinnedKey(args.pin))
    password = hidden('SSH password (hidden): ')
    client.connect(args.host, port=args.port, username='root', password=password,
        look_for_keys=False, allow_agent=False, timeout=20, auth_timeout=20, banner_timeout=30)
    password = None
    client.get_transport().set_keepalive(20)
    command = ('cd /root/autodl-tmp/veriagent-workplace-sft-20260910 && '
               '.venv/bin/python scripts/collect_teacher_probe.py --run-id '
               + shlex.quote(args.run_id) + ' --prompt-key')
    started = time.monotonic(); key_sent = False; buffer = ''
    marker = 'Ordinary Bailian API key (hidden; remote process only): '
    try:
        stdin, stdout, stderr = client.exec_command(command, get_pty=True, timeout=1950)
        channel = stdout.channel
        while not channel.exit_status_ready() or channel.recv_ready():
            if channel.recv_ready():
                buffer += channel.recv(65536).decode(errors='replace')
                if not key_sent and marker in buffer:
                    before, buffer = buffer.split(marker, 1)
                    for line in before.splitlines():
                        if line.startswith('{'):
                            print(line, flush=True)
                    secret = hidden('Ordinary Bailian API key (hidden; forwarded to remote process): ')
                    if not secret or any(c.isspace() for c in secret):
                        raise ValueError('Empty key or whitespace')
                    stdin.write(secret + '\n'); stdin.flush()
                    secret = None; key_sent = True
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    # Collector stdout is bounded JSON metadata; discard PTY noise.
                    if line.startswith('{'):
                        print(line.rstrip('\r'), flush=True)
            if not key_sent and time.monotonic()-started > 180:
                raise TimeoutError('Remote preflight did not reach hidden input')
            if time.monotonic()-started > 1950:
                raise TimeoutError('Remote collection bridge deadline')
            time.sleep(.05)
        code = channel.recv_exit_status()
        print(json.dumps({'remote_exit_code': code, 'key_sent_via_non_echoing_stdin': key_sent,
                          'credentials_persisted': False}), flush=True)
        return code
    finally:
        client.close()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({'status': 'REMOTE_BRIDGE_STOPPED', 'error_type': type(exc).__name__,
                          'details': 'Suppressed to avoid credential disclosure; no automatic retry'}), flush=True)
        raise SystemExit(1)
