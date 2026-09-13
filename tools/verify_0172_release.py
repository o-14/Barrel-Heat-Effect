"""Compare the complete subtle-refraction trial with the preserved 0.17.1 mod."""
from pathlib import Path
import argparse
import hashlib
import json
import zipfile

from package_release import DATA, MANIFEST

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline', type=Path, required=True)
parser.add_argument('--release', type=Path, required=True)
args = parser.parse_args()
with zipfile.ZipFile(args.baseline) as before, zipfile.ZipFile(args.release) as after:
    assert before.testzip() is None and after.testzip() is None
    assert len(after.namelist()) == len(set(after.namelist())) == 13
    assert set(after.namelist()) == set(MANIFEST)
    added = set(after.namelist())-set(before.namelist())
    assert added == {'Textures/GunHeatHaze/Soft0172_n.dds'}
    assert not set(before.namelist())-set(after.namelist())
    changed = {n for n in before.namelist() if before.read(n) != after.read(n)}
    assert changed == {'Meshes/GunHeatHaze/GunHeatBarrelRefractionCard.nif'}, changed
    files = []
    for name in after.namelist():
        data = after.read(name)
        assert data == (DATA/name).read_bytes()
        files.append(dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                          status='added' if name in added else 'changed' if name in changed else 'unchanged'))
report = dict(archive=args.release.name, bytes=args.release.stat().st_size,
              sha256=hashlib.sha256(args.release.read_bytes()).hexdigest(),
              baseline=args.baseline.name, unchanged_files=11, files=files)
Path('docs/subtle-0.17.2/release-verification.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
