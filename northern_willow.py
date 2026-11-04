"""North-Canada UNHEATED high-tunnel willow HTL screening model (research hypothesis).

IMPORTANT: this is NOT a cadastral site inventory, an Arctic yield observation, or a GHG/LCA model.
All assumed disturbed-land caps and yield ranges are planning scenarios, NOT mapped available land.
No intact tundra, wetlands, permafrost, Indigenous lands or agricultural land is presumed available.
No benefit for kelp biostimulant is asserted by default. No electricity or heat is used to warm crops.
The refinery DOES use electricity and process heat and is priced as cold-climate wind + storage/firming.
Revenue from selling biofuel is NOT presumed; isolated diesel comparator assessed separately.
"""
from dataclasses import dataclass, asdict
from typing import Dict
from math import inf

@dataclass(frozen=True)
class Region:
    name: str
    # These are SCENARIO BUDGETS of disturbed, nonagricultural brownfield surface, not measured eligible areas.
    land_cap_ha: float
    cover_fraction: float  # structures only over this fraction of gross site, with access and spacing
    yield_odt_covered_ha: float  # annualised coppice, not first-year crop
    structure_cad_m2: float  # installed and wind/snow/foundation uplift; sensitivity assumptions, not vendor quotes
    onsite_diesel_cad_mwh: float  # hypothetical delivered avoided-diesel comparator, NOT a local observation
    local_fuel_cap_gwh: float  # hypothetical diesel liquid demand, NOT a local official fuel balance
    wind_lcoe_cad_mwh: float  # wind, storage, firming, icing, offgrid distribution composite
    ice_availability: float  # availability multiplier, included in wind-energy price assumption

REGIONS: Dict[str, Region] = {
    'N Alberta': Region('Northern Alberta', 1000, 0.65, 8.0, 12, 300, 80, 150, .90),
    'N Saskatchewan': Region('Northern Saskatchewan', 750, 0.65, 7.5, 13, 320, 60, 160, .88),
    'N Manitoba': Region('Northern Manitoba', 750, 0.65, 7.0, 14, 330, 60, 175, .86),
    'Yukon': Region('Yukon', 250, 0.60, 5.0, 25, 480, 35, 230, .80),
    'NWT': Region('Northwest Territories', 200, 0.60, 4.0, 30, 560, 35, 260, .78),
    'Nunavut': Region('Nunavut', 50, 0.55, 2.0, 42, 680, 12, 330, .72),
}
# plant dry wood HHV 19 MJ/kg; assumed upgraded transport liquid output uses dry mass of biocrude.
# Biocrude 0.30 t per odt, HHV 38 MJ/kg; 80% upgrade energy efficiency => 2.533 MWh/t wood.
BIODRY_BIOCRUDE_FRACTION = 0.30  # willow pilot 39.7%, conservative < observed single lab trial
BIOCRUDE_HHV_MJ_KG = 38
UPGRADING_ENERGY_EFFICIENCY = .80
CRF = lambda r,n: r*(1+r)**n/((1+r)**n-1)

DEFAULT = dict(covered_yield_mult=1., structure_mult=1., biocrude_mass_fraction=BIODRY_BIOCRUDE_FRACTION,
    upgrading_efficiency=UPGRADING_ENERGY_EFFICIENCY, capex_life_years=12, wacc=.07, poly_cover_life_years=4,
    poly_replacement_cad_m2=2.0, establishment_cad_covered_ha=3000,
    farming_annual_cad_covered_ha=3500, dry_transport_cad_odt=65,
    htl_upgrading_cad_odt=420, forest_nutrient_cad_odt=55,
    ht_process_electric_mwh_odt=.75, ht_process_heat_mwh_odt=1.2,
    wind_heat_input_efficiency=.90, # electricity-> process heat excluding reactor heat recovery already in heat figure
    other_operating_cad_odt=45, kelp_treatment=False, kelp_fert_transport_cad_odt=35, kelp_dry_equiv_kg_per_odt=25,
    # Dry kelp additive/treated recovered nutrients are not guaranteed to enhance crop yields.
    kelp_biostimulant_yield_uplift=0.,
    land_cap_mult=1.,
    # Positive wind CF and nearby turbines do NOT imply hourly firm supply.
)

def tech(region: Region, **over):
    p={**DEFAULT,**over}
    y = region.yield_odt_covered_ha*p['covered_yield_mult']
    if p['kelp_treatment']:
        y *= (1 + p['kelp_biostimulant_yield_uplift'])
    fuel_mwh_odt = p['biocrude_mass_fraction']*1000*BIOCRUDE_HHV_MJ_KG/3600*p['upgrading_efficiency']
    cover_m2_gross_ha = region.cover_fraction*10000
    annual_structure=region.structure_cad_m2*p['structure_mult']*cover_m2_gross_ha*CRF(p['wacc'],p['capex_life_years'])
    annual_poly=p['poly_replacement_cad_m2']*cover_m2_gross_ha/p['poly_cover_life_years']
    annual_establishment=p['establishment_cad_covered_ha']*region.cover_fraction*CRF(p['wacc'],8)
    per_covered_odt=(p['farming_annual_cad_covered_ha']/y + p['dry_transport_cad_odt'] +
        p['htl_upgrading_cad_odt'] + p['forest_nutrient_cad_odt']+p['other_operating_cad_odt'] +
        region.wind_lcoe_cad_mwh*(p['ht_process_electric_mwh_odt']+p['ht_process_heat_mwh_odt']/p['wind_heat_input_efficiency']))
    if p['kelp_treatment']: per_covered_odt += p['kelp_fert_transport_cad_odt']
    odt_per_gross_ha = y*region.cover_fraction
    fuel_mwh_per_gross_ha = odt_per_gross_ha*fuel_mwh_odt
    annual_cost_per_gross_ha = annual_structure+annual_poly+annual_establishment+odt_per_gross_ha*per_covered_odt
    return dict(name=region.name, ha_gross_cap=region.land_cap_ha*p['land_cap_mult'],
        ha_covered_cap=region.land_cap_ha*p['land_cap_mult']*region.cover_fraction,
        annual_odt_gross_ha=odt_per_gross_ha, annual_fuel_mwh_gross_ha=fuel_mwh_per_gross_ha,
        annual_cost_cad_gross_ha=annual_cost_per_gross_ha, lcof_cad_mwh=annual_cost_per_gross_ha/fuel_mwh_per_gross_ha,
        potential_gwh=fuel_mwh_per_gross_ha*region.land_cap_ha*p['land_cap_mult']/1000,
        sample_local_diesel_gwh=region.local_fuel_cap_gwh,
        example_delivered_diesel_cad_mwh=region.onsite_diesel_cad_mwh,
        capex_cad_gross_ha=region.structure_cad_m2*p['structure_mult']*cover_m2_gross_ha,
        local_wind_energy_mwh_gross_ha=odt_per_gross_ha*(p['ht_process_electric_mwh_odt']+p['ht_process_heat_mwh_odt']/p['wind_heat_input_efficiency']),
        fuel_mwh_odt=fuel_mwh_odt,
        kelp_amended=bool(p['kelp_treatment']), energy_balance_wood_mwh_odt=19*1000/3600,
        normalized_cost_cad_per_litre_diesel_eq=(annual_cost_per_gross_ha/fuel_mwh_per_gross_ha)*.0100,
    )

def run_screen(**over):
    data=[tech(r,**over) for r in REGIONS.values()]
    for d in data:
        # islanded-region diesel service at assumed delivered prices; 0 means uneconomic, not technologically impossible
        d['economic_local_gwh']=(min(d['potential_gwh'],d['sample_local_diesel_gwh'])
          if d['lcof_cad_mwh'] <= d['example_delivered_diesel_cad_mwh'] else 0.)
        d['economic_local_ha_gross']=(d['economic_local_gwh']*1000/d['annual_fuel_mwh_gross_ha'])
    return dict(regions=data,total_technical_gwh=sum(d['potential_gwh'] for d in data),
       total_economic_gwh=sum(d['economic_local_gwh'] for d in data),
       total_land_scenario_ha=sum(d['ha_gross_cap'] for d in data),
       params={**DEFAULT, **over})

if __name__=='__main__':
 import json
 for name,over in [('base',{}),('optimistic',dict(covered_yield_mult=2.,structure_mult=.50,biocrude_mass_fraction=.397,upgrading_efficiency=.85)),
                  ('kelp_unproven_25pct',dict(kelp_treatment=True,kelp_biostimulant_yield_uplift=.25))]:
  r=run_screen(**over)
  print(name, round(r['total_technical_gwh'],1),round(r['total_economic_gwh'],1),
        [(v['name'],round(v['lcof_cad_mwh']),round(v['economic_local_gwh'],2)) for v in r['regions']])
