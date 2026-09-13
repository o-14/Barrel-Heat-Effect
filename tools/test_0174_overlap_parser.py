"""Compile and exercise the production overlap reader without requiring Fallout 4."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
import build_gunheat_clean_env as clean

root=Path(__file__).resolve().parents[1]
source=(root/'GunHeatPlugin/src/Config.cpp').read_text()
build=root/'GunHeatPlugin/build-codex'; build.mkdir(parents=True,exist_ok=True)
def definition(signature):
    start=source.index(signature); opening=source.index('{',start); depth=0
    for i in range(opening,len(source)):
        if source[i]=='{': depth+=1
        if source[i]=='}':
            depth-=1
            if depth==0: return source[start:i+1]
    raise AssertionError('Unclosed function')
trim=definition('std::string Trim(')
parse_uint=definition('std::uint32_t ParseUInt(')
start=source.index('if (section == "Haze" && (key == "iPuffMaxOverlap"')
end=source.index('\n\t\t} else if (section == "Haze" && key == "bDriveScroll")',start)
branch=source[start:end]+'\n}'
declaration=re.search(r'bool canonicalPuffOverlapSeen = false;',source)
assert declaration and source.index('void Config::ParseFile(')<declaration.start()<source.index('while (std::getline(file, line))')
harness=r'''
#include <algorithm>
#include <cassert>
#include <charconv>
#include <cctype>
#include <cstdint>
#include <initializer_list>
#include <iostream>
#include <string>
#include <string_view>
#include <unordered_map>
#include <utility>
'''+trim+'\n'+parse_uint+r'''
struct Reader {
    std::uint32_t puffMaxOverlap_{6};
    std::unordered_map<std::string,float> floats_;
    void file(std::initializer_list<std::pair<std::string_view,std::string_view>> rows,
              std::string_view section="Haze") {
        '''+declaration.group()+r'''
        for (auto [key,value]:rows) {
            '''+branch+r'''
        }
    }
    void expect(std::uint32_t count) const {
        assert(puffMaxOverlap_==count);
        if (!floats_.empty()) {
            assert(floats_.at("Haze.iPuffMaxOverlap")==count);
            assert(floats_.at("Haze.uPuffMaxOverlap")==count);
        }
    }
};
int main() {
    Reader empty; empty.file({}); empty.expect(6);
    Reader canonical; canonical.file({{"iPuffMaxOverlap","8"}}); canonical.expect(8);
    Reader legacy; legacy.file({{"uPuffMaxOverlap","11"}}); legacy.expect(11);
    Reader orderA; orderA.file({{"uPuffMaxOverlap","14"},{"iPuffMaxOverlap","9"}}); orderA.expect(9);
    Reader orderB; orderB.file({{"iPuffMaxOverlap","9"},{"uPuffMaxOverlap","14"}}); orderB.expect(9);
    Reader overlay; overlay.file({{"iPuffMaxOverlap","6"}});
    overlay.file({{"uPuffMaxOverlap","12"}}); overlay.expect(12);
    overlay.file({{"iPuffMaxOverlap","8"}}); overlay.expect(8);
    overlay.file({{"uPuffMaxOverlap","16"},{"iPuffMaxOverlap","7"}}); overlay.expect(7);
    Reader duplicates; duplicates.file({{"iPuffMaxOverlap","9"},{"iPuffMaxOverlap","7"}}); duplicates.expect(7);
    Reader bounds; bounds.file({{"iPuffMaxOverlap","0"}}); bounds.expect(1);
    bounds.file({{"iPuffMaxOverlap","999"}}); bounds.expect(24);
    for (auto value:{"-3","8.5","8junk","4294967296","","nan"}) {
        Reader invalid; invalid.file({{"iPuffMaxOverlap",value}}); invalid.expect(6);
    }
    Reader whitespace; whitespace.file({{"iPuffMaxOverlap"," 8 "}}); whitespace.expect(8);
    Reader unrelated; unrelated.file({{"anotherKey","12"}}); unrelated.expect(6);
    unrelated.file({{"iPuffMaxOverlap","12"}},"Other"); unrelated.expect(6);
    std::cout << "Production overlap parser: keys, precedence, file overrides, bounds, invalid values and lookup aliases passed.\n";
}
'''
test_source=build/'overlap-parser-test.cpp'; test_source.write_text(harness)
env=clean.developer_environment(); compiler=shutil.which('cl.exe',path=env['Path']); assert compiler
exe=build/'overlap-parser-test.exe'
subprocess.run([compiler,'/nologo','/std:c++latest','/EHsc','/W4','/WX',str(test_source),
                '/Fo'+str(build/'overlap-parser-test.obj'),'/Fe'+str(exe)],cwd=build,env=env,check=True)
result=subprocess.run([str(exe)],capture_output=True,text=True,check=True)
out=root/'docs/overlap-0.17.4'; out.mkdir(parents=True,exist_ok=True)
report=dict(production_source_sha256=hashlib.sha256(source.encode()).hexdigest(),
            tested='Extracted unchanged Trim, ParseUInt and overlap branch from production Config.cpp',
            result=result.stdout.strip(),limitation='Isolated parser execution, not an in-game MCM round trip.')
(out/'parser-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(result.stdout,end='')
