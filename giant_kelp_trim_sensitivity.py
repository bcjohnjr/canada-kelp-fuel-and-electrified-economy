"""Canada supplemental screen: Chile observed crop vs hypothetical Grid Harvester pruning.

Sources: Camus et al. Reviews in Aquaculture (2018) 10 543-559 doi:10.1111/raq.12185
observed BEST crop 124 wet t/ha under their pilot configuration; not an established
annual multi-cut yield in British Columbia. In their shallow suspended culture,
mowing did not lead to re-growth. Separate wild giant-kelp partial harvest work
supports regrowth in other configurations (Borras-Chavez et al. 2012).

SCENARIOS ARE NOT EXPERIMENTAL EVIDENCE FOR ENGINEERED TRIMMING.
Other-Pacific 8 dry t/ha and Atlantic 9.375 are held at previous screened values.
Additionality restrictions are identical to species_yield_sensitivity.py.
"""
import csv,json
from pathlib import Path
import optimise as o, scenarios as sc
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'outputs'
CHILE_OBS_WET=124.0 # Camus et al. best observed Quenac crop in five months, ~1m lines
# Unobserved Canadian engineering prices. At 1 m spacing Camus had 99 ~100m lines/ha.
# Charge incremental 1m vs illustrative 4m rope inventory ONLY in Pacific shelf zones.
REF_M_HA=2500.0
DENSE_M_HA=9900.0
ROPE_RATE=0.07
ROPE_LIFE=5
ROPE_OM=0.03

def rope_cost_per_dry_t(pac_yield, occupancy, cost_cad_m):
 ann=cost_cad_m*(DENSE_M_HA-REF_M_HA)*occupancy*(ROPE_RATE*(1+ROPE_RATE)**ROPE_LIFE/((1+ROPE_RATE)**ROPE_LIFE-1)+ROPE_OM)
 return ann/pac_yield
# Scenario, dry fraction, usable area, net cut yield gain, extra trim CAD/dry t, rope CAD/m, research status.
CASES=[
 ('Observed high crop / 50% usable farm area',.12,.5,1.,0,.5,'partial packing'),
 ('Observed high crop / 75% usable farm area',.12,.75,1.,0,.5,'partial packing'),
 ('Observed high crop / full transfer',.12,1.,1.,0,.5,'upper transfer'),
 ('Trim retains 40%, no regrowth',.12,1.,.6,15,.5,'trimming failure'),
 ('Trim plus unproven second cut: +30% net',.12,1.,1.3,30,.5,'exploratory success'),
 ('Trim plus unproven second cut: +60% net',.12,1.,1.6,50,.5,'exploratory optimistic'),
 ('Observed high crop / 15% dry matter assumption',.15,1.,1.,0,.5,'dry-matter upper bracket'),
 ('Observed crop / full transfer / high line cost',.12,1.,1.,0,2.,'dense-line cost stress'),
]
def run():
 rows=[]
 for name,dm,occupancy,gain,extra,rope_cad_m,kind in CASES:
  pac=CHILE_OBS_WET*dm*occupancy*gain
  yy={}
  for zone in o.ZONES:
   if zone=='pac_shelf': yy[zone]=pac
   elif zone.startswith('pac'): yy[zone]=8.
   else: yy[zone]=9.375*sc.YIELD_SCALE.get(zone.split('_')[0],1.0)
  dense_surcharge=rope_cost_per_dry_t(pac, occupancy,rope_cad_m)
  only_shelf={'pac_shelf':dense_surcharge+extra}
  base=sc.build_case(demand=False,overrides={'zone_yield':yy,'farm':{'dm_pacific':dm,'dm_atlantic':.075},'zone_extra_farm_cost_cad_t':only_shelf})
  # Costed additional cutting/maintenance: explicitly assumed penalty per dry t.
  base['export']={'price':0.,'cap_twh':0.,'logistics':8.,'bio_only':True}
  sol=o.solve(base)
  eft=sol['fuels_twh']['eFT_liquids'];bio=sol['dropin_supply_twh']-eft
  xp=sc.build_case(demand=False,overrides={'zone_yield':yy,'farm':{'dm_pacific':dm,'dm_atlantic':.075},'zone_extra_farm_cost_cad_t':only_shelf})
  xp['export']={'price':400.,'cap_twh':500.,'logistics':8.,'bio_only':True,
                'baseline_biogenic_dropin_twh':bio,'max_domestic_eft_twh':eft}
  ex=o.solve(xp)
  assert ex['fuels_twh']['eFT_liquids'] <= eft+1e-5
  assert ex['export_twh'] <= max(0.,ex['dropin_supply_twh']-ex['fuels_twh']['eFT_liquids']-bio)+1e-5
  row=dict(case=name,scenario_class=kind,wet_t_ha_one_cropping=CHILE_OBS_WET,
           assumed_dry_fraction=dm,usable_farm_fraction=occupancy,
           annual_net_yield_multiplier_vs_one_cropping=gain,
           pac_shelf_dry_t_ha_year=pac,
           additional_harvest_cost_cad_per_dry_tonne=extra,
           additional_dense_line_cost_cad_per_dry_tonne=dense_surcharge,
           rope_capex_cad_per_metres=rope_cad_m,
           total_shelf_only_surcharge_cad_per_dry_tonne=dense_surcharge+extra,
           no_export_cost_cad_bn=sol['total_cost_bn'],no_export_kelp_area_km2=sol['kelp_total_km2'],
           no_export_electricity_twh=sol['electricity_delivered_twh'],
           additional_biogenic_exports_cad400_twh=ex['export_twh'],
           export_case_kelp_area_km2=ex['kelp_total_km2'],
           export_case_electricity_twh=ex['electricity_delivered_twh'])
  rows.append(row)
  print(name,round(pac,2),round(row['no_export_cost_cad_bn'],3),round(row['additional_biogenic_exports_cad400_twh'],1),flush=True)
 OUT.mkdir(exist_ok=True)
 with (OUT/'giant_kelp_trim_sensitivity.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 (OUT/'giant_kelp_trim_sensitivity.json').write_text(json.dumps({'research_basis':{
  'observed_high_crop':'Camus et al. (2018) maximum reported 124 WMT/ha in best Chilean production cycle',
  'no_regrowth_in_shallow_suspension':'Camus et al. (2018), p. 555: mowing trials did not regrow',
  'wild_partial_frond_regrowth':'Borras-Chavez et al. (2012) doi:10.1007/s10811-012-9829-x',
  'sources':['https://doi.org/10.1111/raq.12185','https://doi.org/10.1007/s10811-012-9829-x'],
  'scope':'Pilot best-crop wet density is a source-derived observation, but dry fractions, gross-area occupancy, Canadian transfer, multi-cut factors, added costs and full suitability are model assumptions. Nothing shows a +30% or +60% yield increase in the Grid Harvester, or that deep-ocean nutrient supply sustains the output.',
  'zone_specific_costs':'Incremental dense-line capex: 9,900 minus 2,500 m/ha times 0.5 CAD/m (2.0 cost stress); 5-year life, 7% capital rate, 3% annual O&M. Added only to pac_shelf. Trim costs 15-50 CAD/dry tonne added only on pac_shelf; all else unchanged.',
  'additionality':'Matched same-scenario no-export solution reserves biogenic fuel and caps domestic synthetic eFT in export case'},'rows':rows},indent=2))
 return rows
if __name__=='__main__':run()
