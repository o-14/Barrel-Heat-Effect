"""Verify the full defaults update preserves the accepted asset, scripts and ESP."""
import argparse, configparser, hashlib, json, zipfile
from pathlib import Path
from package_release import DATA,MANIFEST

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--baseline',type=Path,required=True)
parser.add_argument('--release',type=Path,required=True)
args=parser.parse_args()
expected={'F4SE/Plugins/GunHeat.dll','F4SE/Plugins/GunHeat.ini',
          'MCM/Config/GunHeat/config.json','MCM/Config/GunHeat/settings.ini'}
requested={'Haze.fRefractionMaxStrength','Haze.fArtOffsetUp','Heat.fHeatPerShot',
           'Haze.fPulseStrength','Haze.fPuffScale','Haze.fPuffRise'}
with zipfile.ZipFile(args.baseline) as old,zipfile.ZipFile(args.release) as new:
    assert old.testzip() is None and new.testzip() is None
    assert len(new.namelist())==len(set(new.namelist()))==13
    assert set(new.namelist())==set(old.namelist())==set(MANIFEST)
    changed={n for n in old.namelist() if old.read(n)!=new.read(n)}
    assert changed==expected,changed
    for filename in ['F4SE/Plugins/GunHeat.ini','MCM/Config/GunHeat/settings.ini']:
        maps=[]
        for archive in [old,new]:
            cp=configparser.ConfigParser(); cp.optionxform=str; cp.read_string(archive.read(filename).decode())
            maps.append({section+'.'+k:v for section in cp.sections() for k,v in cp[section].items()})
        assert set(maps[0])==set(maps[1])
        actual={key for key in maps[0] if maps[0][key]!=maps[1][key]}
        assert actual==requested,(filename,actual)
    files=[]
    for name in new.namelist():
        data=new.read(name)
        assert data==(DATA/name).read_bytes()
        files.append(dict(path=name,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                          status='changed' if name in changed else 'unchanged'))
report=dict(archive=args.release.name,bytes=args.release.stat().st_size,
            sha256=hashlib.sha256(args.release.read_bytes()).hexdigest(),baseline=args.baseline.name,
            unchanged_files=9,changed_files=sorted(changed),files=files)
Path('docs/defaults-0.17.3/release-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='files'},indent=2))
