"""Audit MCM setting type registration, persistence defaults and tuned values."""
from pathlib import Path
from local_paths import required_path
from decimal import Decimal
import configparser,json,zipfile

root=Path(__file__).resolve().parents[1]
project=Path(required_path('BHE_PROJECT_ROOT'))
def controls(node):
    if isinstance(node,dict):
        if 'id' in node and 'valueOptions' in node: yield node
        for child in node.values(): yield from controls(child)
    elif isinstance(node,list):
        for child in node: yield from controls(child)
def type_errors(panel):
    prefixes={'ModSettingInt':'i','ModSettingFloat':'f','ModSettingBool':'b','ModSettingString':'sS'}
    return sorted({c['id'] for c in controls(panel) if c['valueOptions']['sourceType'] in prefixes
                   and c['id'][0] not in prefixes[c['valueOptions']['sourceType']]})
panel=json.loads((root/'Data/MCM/Config/BarrelHeatEffect/config.json').read_text())
assert not type_errors(panel)
with zipfile.ZipFile(project/'dist/GunHeatHaze-0.17.3-tuned-defaults.zip') as archive:
    old_panel=json.loads(archive.read('MCM/Config/GunHeat/config.json'))
assert type_errors(old_panel)==['uPuffMaxOverlap:Haze'], 'Regression fixture no longer detects the reported bug'
inis=[]
for rel in ['Data/F4SE/Plugins/BarrelHeatEffect.ini','Data/MCM/Config/BarrelHeatEffect/settings.ini']:
    cp=configparser.ConfigParser(); cp.optionxform=str; cp.read(root/rel); inis.append(cp)
seen={}
for control in controls(panel):
    key,section=control['id'].split(':'); opts=control['valueOptions']
    if control['id'] in seen: assert seen[control['id']]==opts
    seen[control['id']]=opts
    assert all(Decimal(cp[section][key])==Decimal(str(float(opts['default']))) for cp in inis)
overlap=seen['iPuffMaxOverlap:Haze']
assert overlap==dict(min=1,max=16,step=1,default=6,sourceType='ModSettingInt')
assert 'uPuffMaxOverlap:Haze' not in seen
for setting,value in {'fRefractionMaxStrength:Haze':.04,'fArtOffsetUp:Haze':1,
                      'fHeatPerShot:Heat':.07,'fPulseStrength:Haze':.01,
                      'fPuffScale:Haze':.1,'fPuffRise:Haze':.5}.items():
    assert seen[setting]['default']==value
assert tuple(seen['fPulseStrength:Haze'][k] for k in ['min','max','step'])==(.005,.05,.005)
assert tuple(seen['fPuffRise:Haze'][k] for k in ['min','max','step'])==(0,1,.1)
# Assert every unrelated control is unchanged, not just its numeric default. Settings deliberately
# retuned in a later release are listed here with the release that moved them, so this keeps
# guarding the overlap fix instead of failing on every future tuning change.
RETUNED_SINCE_0174={'fScrollTilesPerSecond:Haze':'0.20.2, 0.6 -> 0.7 tiles per second'}
old_controls=list(controls(old_panel)); new_controls=list(controls(panel))
assert len(old_controls)==len(new_controls)
for old,new in zip(old_controls,new_controls):
    if old['id']=='uPuffMaxOverlap:Haze': old['id']='iPuffMaxOverlap:Haze'
    assert old['id']==new['id']
    if old['id'] in RETUNED_SINCE_0174: assert old!=new, f"{old['id']} listed as retuned but unchanged"
    else: assert old==new
out=root/'docs/overlap-0.17.4'; out.mkdir(parents=True,exist_ok=True)
report=dict(unique_controls=len(seen),control_occurrences=len(new_controls),type_errors=[],
            retuned_since_0_17_4=RETUNED_SINCE_0174,
            old_fixture_errors=['uPuffMaxOverlap:Haze'],new_key='iPuffMaxOverlap:Haze',
            overlap_options=overlap,unrelated_controls_unchanged=True,
            result='Supported prefixes, matching defaults and old-bug regression check passed.')
(out/'mcm-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
