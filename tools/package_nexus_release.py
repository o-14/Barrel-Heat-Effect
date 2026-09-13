"""Package the Nexus edition from the published DLL/assets, without rebuilding anything.

Usage: python -B tools/package_nexus_release.py --baseline <BarrelHeatEffect-1.0.0.zip>
Uses package_release.py's explicit manifest and exclusive-create install packager.
It never calls the private source-archive builder. Existing archives are never overwritten.
"""
from pathlib import Path
import argparse, hashlib, json, zipfile
import package_release as release

ROOT = Path(__file__).resolve().parents[1]
INI = 'F4SE/Plugins/BarrelHeatEffect.ini'

def ordered_settings(data):
    section = None
    result = []
    for line in data.decode('utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith((';', '#')):
            continue
        if line.startswith('['):
            section = line
        else:
            assert '=' in line, line
            key, value = line.split('=', 1)
            result.append((section, key, value))
    return result

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--baseline', required=True, type=Path)
    parser.add_argument('--baseline-sha256', required=True)
    parser.add_argument('--output-dir', type=Path)
    args = parser.parse_args()
    if args.output_dir:
        release.DIST = args.output_dir
    baseline_digest = args.baseline_sha256.lower()
    assert hashlib.sha256(args.baseline.read_bytes()).hexdigest() == baseline_digest
    output = release.DIST / 'BarrelHeatEffect-1.0.0_Nexus.zip'
    stage = release.DIST / 'nexus-1.0.0-install-staging'
    assert not output.exists() and not stage.exists(), 'Preserve existing output; choose a new packaging run.'
    excluded = [name for name in release.MANIFEST if name.endswith('.psc')]
    assert len(excluded) == 3
    manifest = [name for name in release.MANIFEST if name not in excluded]
    overrides = {
        INI: ROOT / 'packaging/nexus/BarrelHeatEffect.ini',
        'README.txt': ROOT / 'packaging/nexus/README.txt',
        'COPYRIGHT.md': ROOT / 'packaging/nexus/COPYRIGHT.md',
    }
    with zipfile.ZipFile(args.baseline) as baseline:
        assert baseline.testzip() is None
        assert set(baseline.namelist()) == set(release.MANIFEST + release.EXTRAS)
        old_ini = baseline.read(INI)
        new_ini = overrides[INI].read_bytes()
        settings = ordered_settings(old_ini)
        assert len(settings) == 45 and ordered_settings(new_ini) == settings
        energy = lambda data: [s.strip() for s in data.decode().splitlines() if s.strip().startswith(';sEnergyAmmoFormIDs=')]
        assert energy(new_ini) == energy(old_ini)
        for name in manifest + release.EXTRAS:
            path = stage / ('Data' if name in manifest else 'packaging') / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(overrides[name].read_bytes() if name in overrides else baseline.read(name))
    release.DATA = stage / 'Data'
    release.PACKAGING = stage / 'packaging'
    release.MANIFEST = manifest
    archive = release.build_install_archive('1.0.0_Nexus', args.baseline, {INI})
    rows = []
    with zipfile.ZipFile(archive) as current, zipfile.ZipFile(args.baseline) as baseline:
        assert current.testzip() is None
        assert len(current.namelist()) == 17
        assert set(current.namelist()) == set(manifest + release.EXTRAS)
        for name in current.namelist():
            data = current.read(name)
            identical = data == baseline.read(name)
            assert identical or name in overrides, name
            rows.append({'path': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(), 'identical_to_1_0_0': identical})
        assert ordered_settings(current.read(INI)) == settings
    report = {
        'package': archive.name,
        'dll_version': '1.0.0 (unchanged published DLL; no rebuild)',
        'baseline': args.baseline.name,
        'baseline_sha256': baseline_digest,
        'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'bytes': archive.stat().st_size,
        'entries': rows,
        'omitted_from_new_archive_only': excluded,
        'changed_files': list(overrides),
        'unchanged_ordered_ini_entries': len(settings),
        'commented_energy_override_unchanged': True,
        'game_test': 'Not performed; package-only edit, with unchanged runtime binaries/assets and settings.'
    }
    out = ROOT / 'docs/nexus-1.0.0'
    out.mkdir(exist_ok=True)
    (out / 'package-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'entries'}, indent=2))

if __name__ == '__main__':
    main()
