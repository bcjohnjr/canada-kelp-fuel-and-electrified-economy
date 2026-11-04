"""Independent species-specific Canadian biomass sensitivity; reproducible.

Correa et al. (Aquac Res 2016, DOI 10.1111/are.12529): Chilean
Macrocystis pilot, 41.3 kg wet per metre of line per year at 4 m
spacing. At 100% packing this is 103.25 t wet/ha/a or 15.4875 t
DM/ha/a IF 15% harvested dry matter (an explicit transfer assumption).
Partial line occupancy, transfer to Canada and offshore structure are NOT
validated, and no ecological yield benefit is credited to sea-otter habitat.

Sæther et al. J Appl Phycol (2024) DOI 10.1007/s10811-024-03213-1
review reports 75-200 t wet/ha for Saccharina latissima, explicitly warns
cross-study comparisons confounded by planting density and configuration.
7.5% DM is an exploratory parameter, not a universal measured rate.

Wet-fraction modelling is optional and leaves historical benchmarks intact.
"""
import csv,json
from pathlib import Path
import optimise as o
import scenarios as sc

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'outputs'
CHILE_WET_KG_LINE=41.3
LINE_SPACING_M=4.0
DRY_FRACTION_PAC=0.15
DRY_FRACTION_ATL=0.075
CHILE_DRY=(CHILE_WET_KG_LINE*(10000/LINE_SPACING_M)/1000)*DRY_FRACTION_PAC
CASES=[
 ('V4 benchmark (shared 12% DM)',12.0,12.0,9.0,None,None),
 ('Chile analogue: Pacific shelf, Atlantic midpoint',CHILE_DRY,8.0,9.375,.15,.075),
 ('Chile analogue: Pacific shelf, Atlantic low',CHILE_DRY,8.0,5.625,.15,.075),
 ('Chile analogue: Pacific shelf, Atlantic high',CHILE_DRY,8.0,15.0,.15,.075),
 ('50% Pacific line occupancy, Atlantic midpoint',CHILE_DRY*.5,CHILE_DRY*.5,9.375,.15,.075),
 ('All-Pacific-zone yield transfer, Atlantic midpoint',CHILE_DRY,CHILE_DRY,9.375,.15,.075),
 ('All-Pacific-zone yield transfer, Atlantic high',CHILE_DRY,CHILE_DRY,15.0,.15,.075),
 ('17.6 dry t/ha exploratory, NOT verified by supplied LCA',17.6,17.6,15.0,.15,.075),
]

def yields(pac_sh,pac_other,atl):
 vals={}
 for zone in o.ZONES:
  if zone=='pac_shelf': vals[zone]=pac_sh
  elif zone.startswith('pac'):vals[zone]=pac_other
  else:vals[zone]=atl*sc.YIELD_SCALE.get(zone.split('_')[0],1.)
 return vals

def extract(sol):
 return dict(cost_cad_bn=sol['total_cost_bn'], kelp_area_km2=sol['kelp_total_km2'],
             kelp_dry_mt=sol['kelp_dry_mt'],kelp_wet_mt=sol['kelp_wet_mt'],
             new_electricity_twh=sol['electricity_delivered_twh'],
             biogenic_export_twh=sol['export_twh'],export_revenue_cad_bn=sol['export_revenue_bn'],
             eFT_twh=sol['fuels_twh']['eFT_liquids'],
             kelp_area_by_zone=sol['kelp_by_zone_km2'],
             domestic_biogenic_twh=sol['dropin_supply_twh']-sol['fuels_twh']['eFT_liquids'])

def main():
 rows=[]
 for name,pac_sh,pac_other,atl,dm_p,dm_a in CASES:
  overrides=dict(zone_yield=yields(pac_sh,pac_other,atl),farm={})
  if dm_p:overrides['farm']={'dm_pacific':dm_p,'dm_atlantic':dm_a}
  prm=sc.build_case(demand=False, overrides=overrides)
  prm['export']={'price':0.0,'cap_twh':0.0,'logistics':8.0,'bio_only':True}
  b=o.solve(prm)
  raw_b=extract(b)
  ef0=raw_b['eFT_twh']; bio0=raw_b['domestic_biogenic_twh']
  exp={'price':400.0,'cap_twh':500.0,'logistics':8.0,'bio_only':True,
       'baseline_biogenic_dropin_twh':bio0,'max_domestic_eft_twh':ef0}
  p2=sc.build_case(demand=False, overrides={**overrides,'export':exp})
  sol=o.solve(p2); raw_exp=extract(sol)
  assert raw_exp['biogenic_export_twh'] <= max(0,raw_exp['domestic_biogenic_twh']-bio0)+1e-5
  assert raw_exp['eFT_twh'] <= ef0+1e-5
  r={'case':name,'pac_shelf_dry_t_ha_yr':pac_sh,'pac_slope_deep_dry_t_ha_yr':pac_other,
     'atlantic_open_water_dry_t_ha_yr':atl,
     'pacific_dry_fraction':dm_p or .12,'atlantic_dry_fraction':dm_a or .12,
     'baseline_cost_cad_bn':raw_b['cost_cad_bn'],
     'baseline_kelparea_km2':raw_b['kelp_area_km2'],
     'baseline_dry_mt':raw_b['kelp_dry_mt'],
     'baseline_wet_mt':raw_b['kelp_wet_mt'],
     'baseline_new_electricity_twh':raw_b['new_electricity_twh'],
     'export_price_cad_mwh':400.0,
     'additional_biogenic_exports_twh':raw_exp['biogenic_export_twh'],
     'export_farm_area_km2':raw_exp['kelp_area_km2'],
     'export_dry_mt':raw_exp['kelp_dry_mt'],
     'export_wet_mt':raw_exp['kelp_wet_mt'],
     'export_new_electricity_twh':raw_exp['new_electricity_twh'],
     'export_total_cost_before_sales_cad_bn':raw_exp['cost_cad_bn'],
     'no_export_kelparea_by_zone':raw_b['kelp_area_by_zone'],
     'export_kelparea_by_zone':raw_exp['kelp_area_by_zone']}
  rows.append(r)
  print(name,'cost',round(r['baseline_cost_cad_bn'],3),'area',round(r['baseline_kelparea_km2']), 'export',round(r['additional_biogenic_exports_twh'],2),'export area',round(r['export_farm_area_km2']),flush=True)
 OUT.mkdir(exist_ok=True)
 odata={'sources':{
    'Correa giant kelp pilot':'https://doi.org/10.1111/are.12529',
    'Saether sugar kelp review':'https://doi.org/10.1007/s10811-024-03213-1'},
    'chile_reported_unit':'41.3 wet kg per metre of line per year, 4 m apart (NOT 41.3 wet tonnes per hectare)',
    'chile_implied_wet_t_ha_yr':103.25,
    'chile_implied_dry_t_ha_yr_at_assumed_15pct_dm':CHILE_DRY,
    'limits':'Chilean pilot to BC transfer is conditional; 100% line packing and 15% dry fraction are design assumptions; applying coastal yield to slope/deep is not validated; Atlantic 7.5% DM and 75–200 wet t/ha range are heterogeneous studies, not site guarantees; otter houses not quantified; chemistry, seasonal storm losses and actual farm construction/policy exclusion not independently validated.',
    'rows':rows}
 (OUT/'species_yield_sensitivity.json').write_text(json.dumps(odata,indent=2))
 cols=[k for k in rows[0] if not k.endswith('_by_zone')]
 with (OUT/'species_yield_sensitivity.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows([{k:r[k] for k in cols} for r in rows])
 return odata

if __name__=='__main__':main()
