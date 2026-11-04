"""Run six-region northern unheated willow screening and optional national LP inclusion.
Figures + data from this exact script. Not a predictive forecast or verified land inventory.
"""
import csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from northern_willow import REGIONS,run_screen
from optimise import solve
from scenarios import build_case

O=Path(__file__).resolve().parent/'outputs';O.mkdir(exist_ok=True)
F=Path(__file__).resolve().parent/'paper_figures';F.mkdir(exist_ok=True)
SC={
  'Baseline (unheated)': {},
  'Kelp additive; zero proven uplift': {'kelp_treatment':True},
  'Hypothetical +25% kelp boost': {'kelp_treatment':True,'kelp_biostimulant_yield_uplift':.25},
  'High productivity + 50% structure': {'covered_yield_mult':2,'structure_mult':.5,'biocrude_mass_fraction':.397,'upgrading_efficiency':.85},
  'Extreme research-only 3x + 85% structure saving': {'covered_yield_mult':3,'structure_mult':.15,'biocrude_mass_fraction':.397,'upgrading_efficiency':.85},
}
rows=[];sc={}
for label,settings in SC.items():
 r=run_screen(**settings);sc[label]=r
 for item in r['regions']:
  rows.append({'scenario':label, 'jurisdiction':item['name'], 'land_scenario_gross_ha':item['ha_gross_cap'],
      'covered_ha':item['ha_covered_cap'], 'annual_dry_t_ha_gross':item['annual_odt_gross_ha'],
      'annual_liquid_MWh_gross_ha':item['annual_fuel_mwh_gross_ha'], 'hypothetical_max_fuel_GWh_a':item['potential_gwh'],
      'assumed_delivered_diesel_CAD_MWh':item['example_delivered_diesel_cad_mwh'],
      'modelled_full_cost_CAD_MWh':item['lcof_cad_mwh'],
      'cost_CAD_per_L_diesel_equivalent':item['normalized_cost_cad_per_litre_diesel_eq'],
      'competitive_local_diesel_GWh':item['economic_local_gwh'],
      'wind_and_HTL_el_MWh_gross_ha':item['local_wind_energy_mwh_gross_ha']})
with (O/'northern_willow_scenarios.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
p=build_case(demand=False)
bas=solve(p)
p['northern_willow']['enabled']=True
integ=solve(p)
summary={
 'assumptions':'unverified brownfield land caps, no intact tundra/peat/permafrost conversion, no heating of greenhouses, willow maturity required',
 'scenarios':sc,
 'national_central_baseline':dict(annual_cost_cad_bn=bas['total_cost_bn'],kelp_area_km2=bas['kelp_total_km2']),
 'national_central_with_willow':dict(annual_cost_cad_bn=integ['total_cost_bn'],willow_fuel_twh=integ['northern_willow_fuel_twh'],willow_area_km2=integ['northern_willow_area_total_km2'])}
(O/'northern_willow_scenarios.json').write_text(json.dumps(summary,indent=2,default=float))
N=list(REGIONS); ticks=[REGIONS[k].name.replace('Northern ','N. ').replace('Northwest Territories','NWT') for k in N]
fig,ax=plt.subplots(figsize=(12.5,5.9))
x=np.arange(len(N));wd=.35
baseline=sc['Baseline (unheated)']['regions'];opt=sc['High productivity + 50% structure']['regions']
ax.bar(x-wd/2,[d['lcof_cad_mwh'] for d in baseline],wd,label='Baseline: unheated tunnels')
ax.bar(x+wd/2,[d['lcof_cad_mwh'] for d in opt],wd,label='Hypothetical 2× yield; 50% capex')
ax.scatter(x,[d['example_delivered_diesel_cad_mwh'] for d in baseline],marker='D',s=70,label='Assumed delivered diesel price')
ax.set_xticks(x,ticks,rotation=18,ha='right');ax.set_ylabel('Modelled levelized fuel cost (CAD/MWh)')
ax.set_title('Northern unheated willow-to-HTL: screening economics, not projected production')
ax.set_yscale('log');ax.legend(loc='upper left');ax.grid(axis='y',alpha=.22)
fig.text(.02,.015,'No greenhouse heating; dedicated cold-climate wind/process heat costed. Land and diesel-price caps are illustrative, not surveyed.',fontsize=8)
fig.tight_layout(rect=(0,.045,1,1))
for suf in ('png','pdf'): fig.savefig(F/('FigS8_northern_willow_cost_screen.'+suf),dpi=240,bbox_inches='tight')
plt.close(fig)
print('Central baseline',bas['total_cost_bn'],'with willow',integ['total_cost_bn'],'selected TWh',integ['northern_willow_fuel_twh'])
for k,v in sc.items(): print(k,'technical GWh',round(v['total_technical_gwh'],2),'economic GWh',round(v['total_economic_gwh'],2))
