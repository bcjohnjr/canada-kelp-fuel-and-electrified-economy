"""Machine-readable provenance of the principal model inputs: value, unit, source, date, conversion, range and type.

Type: observed (published statistic or measurement), derived (calculated from observed values), project (published
project or policy value), assumption (screening value chosen by the authors). Values are read from the model code
where possible so the table cannot drift from the inputs actually used.
"""
import csv
from pathlib import Path

import economy as E
import optimise as O
import scenarios as SC
import smr_canada_cascade as SMR
import coproduction as CP

OUT = Path(__file__).resolve().parent / "outputs"


def rows():
    p = O.base_params(); c = SC.build_case(demand=False); d = E.demand()
    sm = p["smr"]; M = SMR.PARAMS
    R = []
    add = lambda *a: R.append(dict(zip(("group", "parameter", "value", "unit", "type", "source", "source_date", "conversion", "range_or_uncertainty"), a)))
    # demand
    add("demand", "motor gasoline sales to end users", E.VOL_GL["gasoline"], "GL/yr", "observed", "Statistics Canada, End use of refined petroleum products, 2025 (The Daily)", "2026-10-27", "34.0 MJ/L", "±1% (survey revision)")
    add("demand", "diesel fuel oil sales to end users", E.VOL_GL["diesel_total"], "GL/yr", "observed", "Statistics Canada, End use of refined petroleum products, 2025", "2026-10-27", "38.6 MJ/L", "±1%")
    add("demand", "aviation turbo fuel sales", E.VOL_GL["jet"], "GL/yr", "observed", "Statistics Canada, End use of refined petroleum products, 2025", "2026-10-27", "34.7 MJ/L; includes international flights fuelled in Canada", "±1%")
    add("demand", "net road diesel", E.VOL_GL["road_diesel"], "GL/yr", "observed", "Statistics Canada, Motor vehicle fuel sales, 2025", "2026-10-02", "38.6 MJ/L; 10% light-duty", "±2%")
    add("demand", "rail diesel", E.VOL_GL["rail_diesel"], "GL/yr", "observed", "NRCan Comprehensive Energy Use Database, transportation 2023", "2025", "88.0 PJ", "±3%")
    add("demand", "marine fuel", 62.3, "PJ/yr", "observed", "NRCan Comprehensive Energy Use Database, transportation 2023", "2025", "27.3 PJ heavy fuel oil, rest diesel", "±5%")
    add("demand", "off-road machinery diesel", E.VOL_GL["offroad_diesel"], "GL/yr", "derived", "diesel total less road, rail, marine and stationary uses", "2026", "agriculture, mining, construction, forestry", "±15%")
    for k, v in d.items():
        add("demand", f"modelled demand: {k}", round(v, 2), "TWh/yr", "derived", "economy.demand()", "2026", "volume × energy content", "follows volumes")
    # electricity and heat
    for i, t in enumerate(p["wind"]["tiers"]):
        add("electricity", f"onshore wind tier {i + 1} LCOE (7%, today)", t["lcoe"], "CAD/MWh", "assumption", "national model; Canadian wind auctions and NREL ATB", "2026", f"CF {t['cf']}, cap {t['cap_gw']} GW", "MC ±20%")
    add("electricity", "solar PV LCOE (7%, today)", p["pv"]["lcoe"], "CAD/MWh", "assumption", "national model", "2026", f"CF {p['pv']['cf']}", "MC ±20%")
    add("electricity", "BC Hydro 2024 call for power average price", 74, "CAD/MWh", "observed", "BCUC decision, 25 Aug 2025", "2025-08-25", "", "")
    add("heat", "heat-pump COP (150 °C lift)", p["heat"]["hp_cop"], "-", "assumption", "Arpagaus et al. 2018 (Energy 152)", "2018", "max 60% of a pool", "2.0–3.0")
    add("heat", "wind-charged thermal storage cost", p["heat"]["tes_cost"], "CAD/MWh_th", "assumption", "national model", "2026", "efficiency 0.95", "±30%")
    add("heat", "ethanol distillation heat", p["ethanol_heat"]["mwh_th_per_mwh"], "MWh_th/MWh ethanol", "derived", "RFA 2024 using Argonne GREET 2022: 26,083 Btu/gal", "2024", "7.25 MJ/L ÷ 21.1 MJ/L", "±15%")
    add("heat", "ethanol co-located with an inland SMR site", sm["ethanol_colocated_share"], "share", "assumption", "Chatham (ON) and Belle Plaine (SK) distilleries relative to national capacity", "2026", "", "0–1 tested")
    # SMR
    add("smr", "module capital", sm["capex_bn"], "CAD bn per 300 MWe", "project", "OPG Darlington New Nuclear: CAD 20.9 bn for four BWRX-300", "2025", "later units", "3.5 (fleet) – 6.1 (first unit)")
    add("smr", "clean electricity ITC", 0.15, "share of capital", "project", "Income Tax Act clean electricity ITC; property available for use before 2035", "2024", "0 after 2034 under current law", "0 or 0.15")
    add("smr", "fixed O&M", sm["fom_cad_kw_yr"], "CAD/kW-yr", "assumption", "NREL ATB 2024 nuclear (converted)", "2024", "USD→CAD 1.40", "±25%")
    add("smr", "fuel, variable O&M, waste", sm["var_cad_mwh"], "CAD/MWh", "assumption", "NREL ATB 2024 nuclear", "2024", "12 fuel+VOM, 3 waste", "±25%")
    add("smr", "steam extraction penalty, 150 °C", sm["steam_loss"], "MWh_e/MWh_th", "derived", "second-law estimate, 35 °C condenser", "2026", "", "0.15–0.23")
    add("smr", "maximum steam per module", 200, "MWth", "assumption", "GE Vernova BWRX-300 (870 MWth) with turbine minimum load", "2026", "0.667 MWh_th per MWh_e gross", "150–300")
    add("smr", "availability", sm["cf"], "-", "assumption", "", "2026", "", "0.85–0.93")
    add("smr", "site common infrastructure", "0.8 / 1.6 / 2.4", "CAD bn per new site", "project", "OPG Darlington budget: CAD 1.6 bn common infrastructure within CAD 20.9 bn", "2025", "per site of up to two modules", "0–2.4 tested")
    add("smr", "steam pipeline capital", "4.0 (150 °C) / 2.5 (80 °C)", "CAD M per km", "assumption", "screening value for large-diameter steam and hot-water lines", "2026", "1% O&M", "±50%")
    add("smr", "heat load factors", "0.90 process steam / 0.85 kelp refinery / 0.45 greenhouse", "share of operating hours", "assumption", "seasonal greenhouse heating; continuous process steam", "2026", "", "−20% tested")
    add("smr", "capacity value", M["ccgt"]["capacity_value_cad_kw_yr"], "CAD/kW-yr", "assumption", "near the cost of new entry of a peaking turbine (CAD 1,400/kW, 30 yr, 4–7%, + CAD 25/kW-yr = 106–138)", "2026", "", "0–120 tested")
    add("adequacy", "backup turbine capital", 1400, "CAD/kW", "assumption", "open-cycle turbine on renewable methane", "2026", "30 yr, CAD 25/kW-yr fixed O&M", "±30%")
    add("adequacy", "methane storage cost", 3.0, "CAD/MWh-yr held", "assumption", "underground gas storage capacity charge", "2026", "", "1–10")
    add("smr", "carbon price path", "95/115/130/140", "CAD/t (2026/2030/2035/2040)", "project", "GLJ, Canada’s carbon pricing reset (May 2026)", "2026-05-28", "", "realisation 50–100% tested")
    add("smr", "gas CO2 factor", M["gas_co2_t_per_gj"], "t/GJ", "observed", "ECCC offset system emission factors: 1,919 g/m3", "2026", "38.3 MJ/m3", "")
    add("smr", "CCGT heat rate", M["ccgt"]["heat_rate_gj_mwh"], "GJ/MWh", "assumption", "", "2026", "", "6.5–7.5")
    add("smr", "fossil-free grid power value after switch", M["decarbonised_grid"]["power_cad_mwh"], "CAD/MWh", "derived", "national model el_direct shadow price less network adder", "2026", "", "")
    # kelp
    for z, y in SC.YIELD_LEARN.items():
        add("kelp", f"learning-target yield {z}", y, "t dry/ha/yr", "assumption", "learning target; fuel designs 10–20 (Greene et al. 2020; ARPA-E MARINER)", "2020", "", "MC 3–15")
    add("kelp", "design yield Pacific / Atlantic", "8 / 6", "t dry/ha/yr", "assumption", "between commercial and fuel-design values", "2026", "", "")
    add("kelp", "demonstrated commercial yield (Faroe Islands)", "0.9–1.4", "t dry/ha/yr", "observed", "Bak et al. 2018, Algal Res. 33:36", "2018", "", "")
    add("kelp", "farm base cost (today / learning)", f"{p['farm']['base_cad_t']:.0f} / {c['farm']['base_cad_t']:.0f}", "CAD/t dry at reference yield", "assumption", "national model", "2026", "", "MC")
    add("kelp", "whole-kelp HTL biocrude yield (today)", p["proc"]["htl_biocrude_whole"], "t/t dry", "observed", "Anastasakis & Ross 2011; Elliott et al. 2015", "2011–2015", "", "0.15–0.25")
    add("kelp", "farmable share of zone area", "0.05–0.25", "share", "assumption", "marine GIS with exclusions and conserved areas", "2026", "", "")
    # co-production
    for grp, vals in CP.PARAMS.items():
        for k, v in vals.items():
            add("coproduction:" + grp, k, v, "", "assumption", "marine screen and salmon/laser model supplied with the study", "2026", "", "screening")
    return R


if __name__ == "__main__":
    R = rows()
    with open(OUT / "input_provenance.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(R[0].keys())); w.writeheader(); w.writerows(R)
    print(len(R), "rows written to outputs/input_provenance.csv")
