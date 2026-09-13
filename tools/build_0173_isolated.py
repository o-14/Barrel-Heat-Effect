"""Build the defaults-only DLL in this worktree, with game deployment disabled."""
from pathlib import Path
from local_paths import required_path
import subprocess
import build_gunheat_clean_env as clean

ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'GunHeatPlugin/build-codex'
BUILD.mkdir(parents=True,exist_ok=True)
environment=clean.developer_environment()
cmake=Path(required_path('CMAKE_EXE'))
commands=[('defaults-configure.log',[str(cmake),'-S',str(ROOT/'GunHeatPlugin'),'-B',str(BUILD),'-G','Ninja',
    '-DCMAKE_BUILD_TYPE=Release','-DCOPY_BUILD=OFF',
    '-DVCPKG_INSTALLATION_ROOT=' + str(required_path('VCPKG_ROOT')),
    '-DVCPKG_INSTALLED_DIR=' + str(required_path('VCPKG_INSTALLED_DIR')),
    '-DVCPKG_MANIFEST_INSTALL=OFF','-DVCPKG_TARGET_TRIPLET=x64-windows-static-md',
    '-DCommonLibF4Path=' + str(required_path('COMMONLIBF4_DIR')),
    '-DCMAKE_MAKE_PROGRAM='+str(clean.NINJA)]),
    ('defaults-build.log',[str(clean.NINJA),'-C',str(BUILD),'-j','4','GunHeat.dll'])]
for log_name,command in commands:
    with (BUILD/log_name).open('w') as log:
        result=subprocess.run(command,env=environment,stdout=log,stderr=subprocess.STDOUT)
    if result.returncode:
        print((BUILD/log_name).read_text()[-18000:])
        raise SystemExit(result.returncode)
    print(log_name+': passed',flush=True)
print('Isolated Release DLL built; no game deployment.',flush=True)
