"""Verify exact remote evidence members and extract only inside this project."""
import argparse,hashlib,json,tarfile
from common import ROOT


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',required=True);p.add_argument('--manifest',required=True);a=p.parse_args()
    archive=(ROOT/a.archive).resolve();manifest=(ROOT/a.manifest).resolve()
    assert archive.is_relative_to(ROOT) and manifest.is_relative_to(ROOT)
    meta=json.loads(manifest.read_text(encoding='utf-8'))
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==meta['archive_sha256']
    with tarfile.open(archive,'r:gz') as t:
        assert {m.name for m in t.getmembers()}==set(meta['files'])
        for m in t.getmembers():
            assert m.isfile() and not m.issym()
            data=t.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==meta['files'][m.name]['sha256']
            target=(ROOT/m.name if m.name.startswith('experiments/S1-EXPAND-ACQUIRE-20261016-001/') else archive.parent/'remote_operations'/m.name).resolve()
            assert target.is_relative_to(ROOT)
            if target.exists():assert target.read_bytes()==data,'Existing immutable evidence differs'
            else:target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    print(json.dumps({'status':'ARCHIVE_AND_MEMBERS_VERIFIED','files':len(meta['files'])}))


if __name__=='__main__':main()
