"""Diagnostic of within-zone marine-area caps for the 500 CAD/MWh biogenic export sensitivities."""
import json
from pathlib import Path
import scenarios as sc, optimise as o
from kelp_productivity_sensitivity import regional_yield

rows=[]
for y in (12,15,20):
 for kind in ('least_cost','electric_or_biofuel'):
  eb=kind=='electric_or_biofuel'
  bp={'zone_yield':regional_yield(y),'export':{'price':0.,'cap_twh':0.,'logistics':8.,'bio_only':True},'eb_only':eb}
  baseline=o.solve(sc.build_case(demand=False,overrides=bp))
  basebio=baseline['dropin_supply_twh']-baseline['fuels_twh']['eFT_liquids']
  overrides={'zone_yield':regional_yield(y),'export':{'price':500.,'cap_twh':500.,'logistics':8.,'bio_only':True,
          'baseline_biogenic_dropin_twh':basebio,'max_domestic_eft_twh':baseline['fuels_twh']['eFT_liquids']},'eb_only':eb}
  prm=sc.build_case(demand=False,overrides=overrides)
  s=o.solve(prm)
  binding=[]
  for zone,z in o.ZONES.items():
   for band,base_area in z.area_km2.items():
    cap=base_area*prm['area_share'][zone]
    used=s['kelp_by_zone_band_km2'].get(zone+'|'+band,0.)
    if cap>1 and used>max(1,cap*0.99):binding.append(dict(zone=zone,band=band,area_used_km2=round(used,2),cap_km2=round(cap,2),ratio_used_to_cap=round(used/cap,6)))
  rows.append(dict(yield_pacific=y,policy=kind,farm_km2=s['kelp_total_km2'],binding_zone_bands=binding,
                  sum_binding_area_km2=sum(t['area_used_km2'] for t in binding)))
print(json.dumps(rows,indent=2))
Path('outputs/binding_marine_area_500.json').write_text(json.dumps(rows,indent=2))
