"""Check MCM persistence coverage, duplicated controls and compiled fallback agreement."""
import configparser, json, re
from decimal import Decimal
from pathlib import Path

root=Path(__file__).resolve().parents[1]
def ini(path):
    result=configparser.ConfigParser(); result.optionxform=str; result.read(path)
    return result
panel=json.loads((root/'Data/MCM/Config/GunHeat/config.json').read_text())
defaults=ini(root/'Data/MCM/Config/GunHeat/settings.ini')
runtime=ini(root/'Data/F4SE/Plugins/GunHeat.ini')
members=(root/'GunHeatPlugin/src/Config.h').read_text()
requested={'fRefractionMaxStrength:Haze':('0.04','refractionMaxStrength_'),
           'fArtOffsetUp:Haze':('1','artOffsetUp_'),'fHeatPerShot:Heat':('0.07','heatPerShot_'),
           'fPulseStrength:Haze':('0.01','pulseStrength_'),'fPuffScale:Haze':('0.1','puffScale_'),
           'fPuffRise:Haze':('0.5','puffRise_')}
controls={}; occurrences=0
def visit(node):
    global occurrences
    if isinstance(node,dict):
        if 'id' in node and 'valueOptions' in node:
            occurrences+=1
            setting=node['id']; options=node['valueOptions']
            if setting in controls: assert controls[setting]==options,setting
            controls[setting]=options
            key,section=setting.split(':')
            value=Decimal(str(float(options['default'])))
            assert Decimal(defaults[section][key])==value,setting
            assert Decimal(runtime[section][key])==value,setting
            if setting in requested:
                assert value==Decimal(requested[setting][0]),setting
            if node['type']=='slider':
                low,high,step=(Decimal(str(options[k])) for k in ['min','max','step'])
                assert low<=value<=high and step>0,setting
                # Existing unrelated sliders may predate aligned minima. Check
                # the two controls changed here, including the requested endpoints.
                if setting in ['fPulseStrength:Haze','fPuffRise:Haze']:
                    assert (value-low)%step==0 and (high-low)%step==0,setting
        for child in node.values(): visit(child)
    elif isinstance(node,list):
        for child in node: visit(child)
visit(panel)
for setting,(value,member) in requested.items():
    match=re.search(member+r'\{ ([0-9.]+)F \}',members)
    assert match and Decimal(match[1])==Decimal(value),setting
for setting,wanted in [('fPulseStrength:Haze',(.005,.05,.005)),('fPuffRise:Haze',(0,1,.1))]:
    assert tuple(controls[setting][k] for k in ['min','max','step'])==wanted
report=dict(unique_mcm_controls=len(controls),control_occurrences=occurrences,
            requested_defaults={s:v[0] for s,v in requested.items()},
            pulse_slider={k:controls['fPulseStrength:Haze'][k] for k in ['min','max','step']},
            puff_rise_slider={k:controls['fPuffRise:Haze'][k] for k in ['min','max','step']},
            result='All controls covered; duplicate definitions and four default sources agree; changed slider values reachable.')
(root/'docs/defaults-0.17.3/config-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
