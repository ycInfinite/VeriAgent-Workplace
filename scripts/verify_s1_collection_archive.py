"""Verify and preserve the exact Oct16 inference evidence; never overwrite history."""
import hashlib
import json
import tarfile
from common import ROOT


def main():
    folder = ROOT/'evidence/s1-failure-execution-20261016'
    archive = folder/'raw.tar.gz'
    meta = json.loads((folder/'raw_manifest.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == meta['archive_sha256']
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        assert len(members) == len(meta['files'])
        assert {m.name for m in members} == set(meta['files'])
        for member in members:
            assert member.isfile() and not member.issym()
            data = tar.extractfile(member).read()
            assert len(data) == meta['files'][member.name]['bytes']
            assert hashlib.sha256(data).hexdigest() == meta['files'][member.name]['sha256']
            base = ROOT if member.name.startswith('experiments/S1-FAILURE-ACQUIRE-20261012-001/') else folder/'remote_operations'
            target = (base/member.name).resolve()
            assert target.is_relative_to(base.resolve())
            if target.exists():
                assert target.read_bytes() == data, 'Immutable evidence differs'
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
    result = {'status': 'ARCHIVE_AND_ALL_MEMBERS_VERIFIED', 'members': len(members), 'archive_sha256': meta['archive_sha256']}
    with (folder/'local_integrity.json').open('x', encoding='utf-8', newline='\n') as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
