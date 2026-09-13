"""Verify only the overlap key and compatible DLL change in the complete package."""
from pathlib import Path
import argparse,configparser,hashlib,json,zipfile
from package_release import DATA,MANIFEST

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline',type=Path,required=True)
parser.add_argument('--release',type=Path,required=True)
args=parser.parse_args()
expected={'F4SE/Plugins/GunHeat.dll','F4SE/Plugins/GunHeat.ini',
          'MCM/Config/GunHeat/config.json','MCM/Config/GunHeat/settings.ini'}
with zipfile.ZipFile(args.baseline) as old,zipfile.ZipFile(args.release) as new:
    assert old.testzip() is None and new.testzip() is None
    assert len(new.namelist())==len(set(new.namelist()))==13
    assert set(new.namelist())==set(old.namelist())==set(MANIFEST)
    changed={name for name in old.namelist() if old.read(name)!=new.read(name)}
    assert changed==expected,changed
    for name in expected-{'F4SE/Plugins/GunHeat.dll'}:
        assert old.read(name).decode().replace('uPuffMaxOverlap','iPuffMaxOverlap')==new.read(name).decode()
    files=[]
    for name in new.namelist():
        data=new.read(name); assert data==(DATA/name).read_bytes()
        files.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                          status='changed' if name in changed else 'unchanged'))
report=dict(archive=args.release.name,bytes=args.release.stat().st_size,
            sha256=hashlib.sha256(args.release.read_bytes()).hexdigest(),baseline=args.baseline.name,
            unchanged_files=9,changed_files=sorted(changed),files=files)
Path('docs/overlap-0.17.4/release-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
