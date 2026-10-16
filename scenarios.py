"""Scenario construction: today's costs, learning, finance and demand levers (applied cumulatively)."""
import copy
import optimise as o

CRF = o.CRF


def cheaper_capital(prm, r_new=0.04, r_old=0.07, life=25):
    """Re-price the capital share of each cost line at a lower cost of capital."""
    f = CRF(r_new, life) / CRF(r_old, life)
    sc = lambda v, cs: v * (1 - cs + cs * f)
    for t in prm["wind"]["tiers"]:
        t["lcoe"] = sc(t["lcoe"], 0.85)
    prm["pv"]["lcoe"] = sc(prm["pv"]["lcoe"], 0.85)
    prm["new_hydro"]["lcoe"] = sc(prm["new_hydro"]["lcoe"], 0.90)
    for k, cs in (("wind", 0.7), ("pv_shift", 0.8), ("network_direct", 0.8), ("network_flex", 0.8), ("flex_pv", 0.8),
                  ("flex_wind", 0.8), ("pv_day", 0.7)):
        prm["adder"][k] = sc(prm["adder"][k], cs)
    prm["heat"]["tes_cost"] = sc(prm["heat"]["tes_cost"], 0.85)
    prm["heat"]["bio_boiler_cost"] = sc(prm["heat"]["bio_boiler_cost"], 0.75)
    for k in ("eft", "emeoh", "enh3", "ech4", "atj"):
        prm[k]["cost"] = sc(prm[k]["cost"], 0.7)
    prm["dac"]["cost"] = sc(prm["dac"]["cost"], 0.6)
    for k in ("waste_ch4",):
        prm[k]["cost"] = sc(prm[k]["cost"], 0.5)
    for k in ("hefa", "canola", "crop_etoh"):
        prm[k]["cost"] = sc(prm[k]["cost"], 0.15)
    prm["forest"]["conv"] = sc(prm["forest"]["conv"], 0.7)
    prm["agres"]["conv"] = sc(prm["agres"]["conv"], 0.7)
    prm["farm"]["base_cad_t"] = sc(prm["farm"]["base_cad_t"], 0.6)
    prm["farm"]["rate"] = r_new
    prm["refinery_cost_mult"] = sc(prm["refinery_cost_mult"], 0.7)
    prm["veh"]["r"] = r_new
    prm["wacc"] = r_new
    return prm


YIELD_LEARN = {"pac_shelf": 12.0, "pac_slope": 12.0, "pac_deep": 12.0, "atl_shelf": 9.0, "atl_slope": 9.0, "atl_deep": 9.0,
               "gsl_shelf": 7.5, "gsl_slope": 7.5, "lab_shelf": 6.0, "lab_slope": 6.0, "hb_shelf": 3.75, "hb_slope": 3.75}
YIELD_SCALE = {"gsl": 5 / 6, "lab": 4 / 6, "hb": 2.5 / 6}       # seasonal-ice zones relative to the Atlantic yield

LEVERS = [
    ("farm", "Cheaper farming: biomass CAD 520 → 340 per dry t at reference yield",
     lambda p: p["farm"].update(base_cad_t=340.0)),
    ("yield", "Higher yield: 8 → 12 (Pacific) and 6 → 9 (Atlantic) t dry ha⁻¹ yr⁻¹",
     lambda p: p.update(zone_yield=dict(YIELD_LEARN))),
    ("deep", "Cheaper deep-water structures: factor 1.45 → 1.2; depth cycling CAD 1.6M → 0.8M km⁻²",
     lambda p: p["farm"].update(deep_factor=1.2, slope_factor=1.1, depth_cycle_capex_km2=0.8e6)),
    ("conversion", "Better conversion: whole-kelp HTL 0.193 → 0.23, residue 0.25 → 0.30, all alginate fermented",
     lambda p: p["proc"].update(htl_biocrude_whole=0.23, htl_biocrude_resid=0.30, alginate_use=1.0)),
    ("refcapex", "Biorefinery cost −30% (nth-of-a-kind plants)",
     lambda p: p.update(refinery_cost_mult=p["refinery_cost_mult"] * 0.7)),
    ("efuels", "Electrofuel synthesis and electrolysers −25%; DAC −25%",
     lambda p: [p[k].update(cost=p[k]["cost"] * 0.75) for k in ("eft", "emeoh", "enh3", "ech4", "dac")]),
    ("capital", "Cheaper capital: 4% instead of 7%", lambda p: cheaper_capital(p)),
    ("demand", "Less fuel: aviation −20%, shipping −10%, off-road −15% (no oil-sands mining fleet), wind-assisted ships up to 15%",
     lambda p: p.update(demand_mult={"aviation": 0.80, "shipping": 0.90, "offroad": 0.85}, wind_assist_share=0.15)),
]
LEARNING_KEYS = ("farm", "yield", "deep", "conversion", "refcapex", "efuels")


def build_case(learning=True, capital=True, demand=True, overrides=None, r=0.04):
    p = o.base_params()
    for key, _, fn in LEVERS:
        if key in LEARNING_KEYS and not learning:
            continue
        if key == "capital":
            if capital:
                cheaper_capital(p, r_new=r)
            continue
        if key == "demand" and not demand:
            continue
        fn(p)
    for k, v in (overrides or {}).items():
        p[k] = {**p[k], **v} if isinstance(v, dict) and isinstance(p.get(k), dict) else copy.deepcopy(v)
    return p


def today():
    return build_case(learning=False, capital=False, demand=False)
