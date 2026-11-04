"""Reproducible counterfactual-controlled marine biofuel export sensitivity.

Three guardrails for reported 'additional biogenic export':
  1. export volume <= marine/lake and conventional biogenic drop-in output;
  2. export volume <= biogenic output - no-export biogenic output, for the
     same dry yield, domestic supply policy, and techno-economic parameters;
  3. domestic electricity-derived Fischer-Tropsch liquid output cannot rise
     above the matched no-export counterfactual.
This is additionality accounting within the *model*, NOT fuel certification.
Prices are hypothetical exogenous CAD/MWh, not observed aviation-fuel contracts.
"""
import csv, json
from pathlib import Path
import scenarios as sc
import optimise as o

OUT=Path(__file__).resolve().parent/'outputs'
PRICE=(0,330,400,500)
YIELDS=(1.4,3.0,5.0,8.0,12.0,15.0,20.0)

def regional_yield(pac):
    return {zone: (pac if zone.startswith('pac') else pac * 0.75 * sc.YIELD_SCALE.get(zone.split('_')[0], 1.0))
            for zone in o.ZONES}

def evaluate():
    rows=[]
    for y in YIELDS:
        for system in ('least_cost','electric_or_biofuel'):
            eb = system == 'electric_or_biofuel'
            baseline_params={'zone_yield':regional_yield(y),
              'export':{'price':0.,'cap_twh':0.,'logistics':8.,'bio_only':True},'eb_only':eb}
            try:
                base=o.solve(sc.build_case(demand=False,overrides=baseline_params))
            except RuntimeError as e:
                for p in PRICE:
                    rows.append(dict(pacific_yield_t_dry_ha=y,atlantic_yield_t_dry_ha=round(y*.75,4),
                         system=system, export_price_cad_mwh=p,feasible=False,error=str(e)))
                continue
            ef_baseline=base['fuels_twh']['eFT_liquids']
            bio_baseline=base['dropin_supply_twh'] - ef_baseline
            for p in PRICE:
                ex={'price':float(p),'cap_twh':500.0,'logistics':8.0,'bio_only':True,
                    'baseline_biogenic_dropin_twh':bio_baseline,
                    'max_domestic_eft_twh':ef_baseline}
                overrides={'zone_yield':regional_yield(y),'export':ex,'eb_only':eb}
                try:
                    s=o.solve(sc.build_case(demand=False,overrides=overrides))
                    bnow=s['dropin_supply_twh']-s['fuels_twh']['eFT_liquids']
                    eps=1e-5
                    assert s['export_twh'] <= max(0,bnow-bio_baseline)+eps, (y,p,system,'additionality')
                    assert s['fuels_twh']['eFT_liquids'] <= ef_baseline+eps, (y,p,system,'eFT')
                    rows.append(dict(pacific_yield_t_dry_ha=y,atlantic_yield_t_dry_ha=round(y*.75,4),
                      system=system,export_price_cad_mwh=p,feasible=True,
                      baseline_domestic_biogenic_dropin_twh=bio_baseline,
                      baseline_domestic_eft_twh=ef_baseline,
                      no_export_domestic_cost_bn=base['total_cost_bn'],
                      total_cost_bn=s['total_cost_bn'],kelp_area_km2=s['kelp_total_km2'],
                      kelp_dry_mt=s['kelp_dry_mt'],new_electricity_twh=s.get('electricity_delivered_twh'),
                      actual_biogenic_dropin_twh=bnow,
                      export_twh=s['export_twh'],export_revenue_bn=s['export_revenue_bn'],
                      efuels_twh=s['fuels_twh']['eFT_liquids']))
                except RuntimeError as e:
                    rows.append(dict(pacific_yield_t_dry_ha=y,atlantic_yield_t_dry_ha=round(y*.75,4),
                      system=system,export_price_cad_mwh=p,feasible=False,error=str(e)))
    payload={'definitions':{
      'yield':'Pacific dry tonnes per gross farm hectare per year; Atlantic 75%, with additional ice-zone reductions',
      'prices':'Assumed CAD/MWh exogenous test prices, not observed contracts or forecasts',
      'counterfactual':'For each yield and domestic policy, recompute no-export optimum; then reserve its biogenic liquid output and cap electricity-derived FT liquids at its no-export level',
      'additionality':'Export <= additional biogenic drop-in output relative to no-export optimum AND export <= actual biogenic drop-in output. Domestic eFT cannot grow relative to no-export baseline. This prevents synthetic eFT from backfilling exported biofuel through domestic substitution.',
      'limits':'Aggregate annual fuel streams, not chain-of-custody or certification; net export economics do not represent realized commercial trade or aircraft fuel qualification',
      'learning':'Learning-target conversion, farm costs and finance apply equally to all export and no-export cases',
      '15_20_yields':'High yield tiers are unvalidated commercial stretch cases, not current BC observations',
      'spatial':'Zone averages and site constraints are not species-by-pixel forecasts'}, 'rows':rows}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'kelp_productivity_export_sensitivity.json').write_text(json.dumps(payload,indent=2))
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with (OUT/'kelp_productivity_export_sensitivity.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(rows)
    print('YIELD POLICY PRICE EXPORT_TWH ELECTROFUEL_TWH KELP_AREA_KM2')
    for r in rows:
        if r['export_price_cad_mwh'] in (400,500):
            print(r['pacific_yield_t_dry_ha'],r['system'],r['export_price_cad_mwh'],
                  round(r.get('export_twh',0),3),round(r.get('efuels_twh',0),3),round(r.get('kelp_area_km2',0)))
    return payload

if __name__=='__main__': evaluate()
