"""All analyses reported in the manuscript.

1. Headline cases: today's costs; learning (current demand); transition (learning + 4% finance + demand levers),
   with the corporate and government accounts at October 2026 and 2025 pump prices.
2. Pump prices: the price at which the renewable system only breaks even, and the price at which it also replaces
   the pre-royalty operating surplus of oil and gas extraction and refining.
3. Cost levers applied cumulatively from today's costs.
4. Exports: the supply curve of exportable drop-in fuel and the export volume and margin at given export prices.
5. Stress tests and forced design options, with their accounts.
6. Monte Carlo over the transition case (1,000 draws).
7. Price exposure (2025 average -> October 2026).
Writes outputs/results.json, levers.json, exports.json, robustness.csv/json, monte_carlo.csv,
monte_carlo_summary.json.
"""
import copy
import csv
import json
from pathlib import Path

import numpy as np

import economy as E
import fiscal as fi
import employment_fiscal as ef
import optimise as o
import scenarios as sc
from lifecycle import sampled_lifecycle
from grid_harvester import fleet_sizing

OUT = Path(__file__).resolve().parent / "outputs"
RNG = np.random.default_rng(20261014)
PERIODS = ("oct2026", "avg2025")


def brief(s):
    keys = ("objective_bn", "total_cost_bn", "energy_cost_bn", "supply_cost_bn", "vehicle_premium_bn", "fossil_cost_bn",
            "electricity_delivered_twh", "generation_twh", "wind_by_tier_twh", "capacity_gw", "kelp_total_km2", "kelp_dry_mt",
            "kelp_wet_mt", "kelp_share_pct", "kelp_fuel_twh", "kelp_hc_twh", "kelp_jet_twh", "kelp_cost_bn", "kelp_farm_cost_bn",
            "kelp_refinery_cost_bn", "fuels_twh", "fertiliser_mt", "fertiliser_value_bn", "fertiliser_energy_avoided_pj", "co2_mt",
            "build", "end_use_twh", "heat_twh_th", "kelp_by_zone_km2", "kelp_by_zone_band_km2", "kelp_by_route_km2",
            "kelp_by_nutrient_method_km2", "kelp_by_preprocess_km2", "kelp_by_band_km2", "fossil_co2_mt", "demand_twh",
            "demand_total_twh", "electrolyser_gw", "electricity_vehicles_rail_twh", "electricity_for_efuels_twh",
            "electricity_for_dac_twh", "electricity_for_heat_storage_twh", "electricity_refineries_twh", "lifecycle",
            "marginal_cad_mwh", "kelp_fleet_fuel_twh", "kite_saved_twh", "wind_assist_twh_saved", "bio_methanol_from_CH4_twh",
            "kelp_refinery_heat_twh", "upwelling_pipes", "forest_residue_modt", "agri_residue_modt", "capital_return_bn",
            "export_twh", "export_revenue_bn", "dropin_supply_twh", "lake_dry_kt", "lake_dry_kt_by", "lake_p_removed_t", "lake_p_removed_t_by",
            "lake_fuel_twh", "lake_share_pct", "lake_vessels", "lake_cutters", "lake_fertiliser_kt", "fertiliser_total_mt",
            "lake_p_removed_t_by_biomass", "lake_dry_kt_by_biomass", "ers", "offroad_twh", "lake_p_removed_t_by_lake_biomass",
            "lake_grid_km2", "lake_grid_km2_by", "lake_harvesters", "lake_grid_units")
    out = {k: s[k] for k in keys}
    out["cost_items_bn"] = {k: v[0] for k, v in s["cost_items_bn"].items()}
    return out


def harvesters(s, standing_kg_m2=8.0, hours=4000):
    """Grid Harvester engineering fleet: biomass-throughput and area-pass screens."""
    return fleet_sizing(s.get("kelp_by_zone_km2", {}), s.get("kelp_wet_mt", 0.0),
                        hours_per_year=hours, standing_kg_m2=standing_kg_m2)


def fiscal_block(s):
    out = {}
    for per in PERIODS:
        for py in ("avg2025", "h1_2026"):
            out[f"{per}|{py}"] = fi.accounts(s, per, py)
        m_oil = fi.price_needed(s, per, "avg2025", "oil")
        m_oil26 = fi.price_needed(s, per, "h1_2026", "oil")
        m_be = fi.price_needed(s, per, target="breakeven")
        out[f"{per}|price"] = dict(mult_oil_2025=m_oil, mult_oil_h1_2026=m_oil26, mult_breakeven=m_be,
                                   pump_oil_2025=fi.pump_price(m_oil, per), pump_oil_h1_2026=fi.pump_price(m_oil26, per),
                                   pump_breakeven=fi.pump_price(m_be, per), pump_now=fi.pump_price(1.0, per))
    return out


CASES = {"today": lambda: sc.today(), "central": lambda: sc.build_case(demand=False), "transition": lambda: sc.build_case(),
         "eb": lambda: sc.build_case(demand=False, overrides={"eb_only": True})}
CEN = lambda **kw: sc.build_case(demand=False, **kw)   # central case: learning, 4% finance, full 2025 demand (827 TWh)


def headline():
    R = {}
    S = {k: o.solve(f()) for k, f in CASES.items()}
    for k, s in S.items():
        R[k] = brief(s)
        R[k]["harvesters"] = harvesters(s)
        R[k]["fiscal"] = fiscal_block(s)
    for k, f in CASES.items():
        lo = o.solve(o.merge(f(), {"veh": {"car": 0, "van": 0, "truck": 0, "lng_truck": 0, "ed95_truck": 0, "e100_car": 0}}))
        hi = o.solve(o.merge(f(), {"veh": {"car": 4800, "van": 8000, "truck": 95000, "lng_truck": 63000, "ed95_truck": 21000}}))
        R[k]["vehicle_premium_range_total_bn"] = [lo["total_cost_bn"], hi["total_cost_bn"]]
        R[k]["vehicle_premium_range_bn"] = [lo["vehicle_premium_bn"], hi["vehicle_premium_bn"]]
        R[k]["ebit_oct2026_vehicle_range_bn"] = [fi.accounts(lo)["ebit_bn"], fi.accounts(hi)["ebit_bn"]]
    # price exposure: commodity-linked inputs are waste lipids, canola oil and grain ethanol
    low = S["central"]; p = CASES["central"]()
    f = low["fuels_twh"]
    traded = (f["HEFA_waste_lipids"] * p["hefa"]["cost"] + f["canola_HVO"] * p["canola"]["cost"]
              + f["grain_ethanol_existing"] * p["crop_etoh"]["cost"]) / 1000
    fs = low["fossil_cost_bn"]
    shock = fs["oct2026"] / fs["avg2025"] - 1
    R["exposure"] = dict(fossil_2025_bn=fs["avg2025"], fossil_oct2026_bn=fs["oct2026"], fossil_swing_bn=fs["oct2026"] - fs["avg2025"],
                         fossil_swing_pct=shock * 100, lowcarbon_commodity_linked_bn=traded, lowcarbon_swing_bn=traded * shock,
                         lowcarbon_swing_pct=traded * shock / low["total_cost_bn"] * 100)
    R["prices"] = {per: E.segment_prices(per) for per in PERIODS}
    R["pump_now"] = {per: fi.pump_price(1.0, per) for per in PERIODS}
    R["retail"] = E.RETAIL
    R["oil"] = {py: E.oil_pie(py) for py in ("avg2025", "h1_2026")}
    R["demand_gl"] = E.VOL_GL
    R["employment_fiscal"] = ef.employment_and_tax(S["central"])
    json.dump(R["employment_fiscal"], open(OUT / "employment_fiscal.json", "w"), indent=1, default=float)
    json.dump(R, open(OUT / "results.json", "w"), indent=1, default=float)
    return R, S


def _acct(s):
    a = fi.accounts(s, "oct2026", "avg2025")
    return dict(ebit=a["ebit_bn"], coverage=a["pie_coverage"], rent=a["rent_bn"], mult_oil=fi.price_needed(s, "oct2026"),
                mult_oil_2025=fi.price_needed(s, "avg2025"))


def levers():
    p = sc.today()
    s0 = o.solve(p)
    out = [dict(key="today", label="Today's costs (7%, current demand)", cost=s0["total_cost_bn"], kelp_km2=s0["kelp_total_km2"],
                kelp_share=s0["kelp_share_pct"], electricity_twh=s0["electricity_delivered_twh"], fossil=s0["fossil_cost_bn"], **_acct(s0))]
    single = {}
    for key, label, fn in sc.LEVERS:
        q = copy.deepcopy(sc.today())
        sc.cheaper_capital(q) if key == "capital" else fn(q)
        ss = o.solve(q)
        single[key] = dict(label=label, cost=ss["total_cost_bn"], saving=s0["total_cost_bn"] - ss["total_cost_bn"], **_acct(ss))
    for key, label, fn in sc.LEVERS:
        sc.cheaper_capital(p) if key == "capital" else fn(p)
        s = o.solve(p)
        out.append(dict(key=key, label=label, cost=s["total_cost_bn"], step_saving=out[-1]["cost"] - s["total_cost_bn"],
                        kelp_km2=s["kelp_total_km2"], kelp_share=s["kelp_share_pct"], electricity_twh=s["electricity_delivered_twh"],
                        fossil=s["fossil_cost_bn"], **_acct(s)))
    res = dict(cumulative=out, single=single)
    json.dump(res, open(OUT / "levers.json", "w"), indent=1, default=float)
    return res


EXPORT_PRICES = (180, 250, 300, 330, 350, 375, 400, 450, 500, 600)
EXPORT_VOLUMES = (0, 25, 50, 75, 100, 150, 200, 300, 400, 500)


def exports():
    """Supply curve (forced export volumes at zero price) and the profit-maximising export volume at given prices."""
    base = o.solve(CEN())
    curve = []
    for X in EXPORT_VOLUMES:
        s = o.solve(CEN(overrides={"export": {"price": 0.0, "cap_twh": X, "min_twh": X, "logistics": 8.0}}))
        curve.append(dict(volume_twh=X, added_cost_bn=s["objective_bn"] - base["objective_bn"],
                          marginal_cad_mwh=s["marginal_cad_mwh"]["dropin"] + 8.0, kelp_km2=s["kelp_total_km2"],
                          efuels_twh=s["fuels_twh"]["eFT_liquids"], wind_twh=s["generation_twh"]["Onshore wind"]))
    for i in range(1, len(curve)):
        a, b = curve[i - 1], curve[i]
        b["average_increment_cad_mwh"] = (b["added_cost_bn"] - a["added_cost_bn"]) * 1000 / (b["volume_twh"] - a["volume_twh"])
    at_price = []
    for P in EXPORT_PRICES:
        s = o.solve(CEN(overrides={"export": {"price": float(P), "cap_twh": 500.0, "logistics": 8.0}}))
        a = fi.accounts(s, "oct2026", "avg2025")
        at_price.append(dict(price_cad_mwh=P, price_usd_t=P / E.FX["oct2026"] * 12.0, volume_twh=s["export_twh"],
                             revenue_bn=s["export_revenue_bn"], ebit_bn=a["ebit_bn"], coverage=a["pie_coverage"],
                             added_ebit_bn=a["ebit_bn"] - fi.accounts(base)["ebit_bn"], kelp_km2=s["kelp_total_km2"],
                             efuels_twh=s["fuels_twh"]["eFT_liquids"], wind_twh=s["generation_twh"]["Onshore wind"]))
    oil_twh = (E.OIL_EXPORTS_2025["crude_mbd"] + E.OIL_EXPORTS_2025["products_mbd"]) * 1e6 * 365 * 1.61 / 1e6
    res = dict(supply_curve=curve, at_price=at_price, oil_export_energy_twh=oil_twh,
               reference_prices_cad_mwh=dict(fossil_jet_oct2026=E.segment_prices("oct2026")["aviation"]["p"],
                                             fossil_jet_2025=E.segment_prices("avg2025")["aviation"]["p"],
                                             saf_europe_jul2026=2600 * E.FX["oct2026"] / 12.0,
                                             saf_europe_mar2026_peak=3500 * E.FX["oct2026"] / 12.0))
    json.dump(res, open(OUT / "exports.json", "w"), indent=1, default=float)
    return res


def tri(a, m, b):
    return _TRI(a, m, b)


_TRI = lambda a, m, b: RNG.triangular(a, m, b)
TRI_MODES = {"draw": lambda a, m, b: RNG.triangular(a, m, b), "mean": lambda a, m, b: (a + m + b) / 3.0,
             "mode": lambda a, m, b: m}


def mc_params(demand_levers=True, mode="draw"):
    global _TRI
    _TRI = TRI_MODES[mode]
    r = tri(0.03, 0.04, 0.07)
    p = o.base_params()
    yp = tri(4.0, 12.0, 15.0)
    ya = yp * tri(0.6, 0.75, 0.9)
    p["zone_yield"] = {z: (yp if z.startswith("pac") else ya * sc.YIELD_SCALE.get(z.split("_")[0], 1.0)) for z in o.ZONES}
    p["farm"].update(base_cad_t=tri(240, 340, 950), deep_factor=tri(1.1, 1.2, 1.8), slope_factor=tri(1.0, 1.1, 1.3),
                     depth_cycle_capex_km2=tri(0.5e6, 0.8e6, 3.2e6))
    p["proc"].update(htl_biocrude_whole=tri(0.15, 0.21, 0.27), htl_biocrude_resid=tri(0.20, 0.28, 0.32),
                     alginate_use=tri(0.5, 0.9, 1.0), ad_ch4_nm3_kgvs=tri(0.18, 0.24, 0.30))
    p["refinery_cost_mult"] = 0.7 * tri(0.8, 1.0, 1.4)
    wm = tri(0.85, 1.0, 1.25)
    for t in p["wind"]["tiers"]:
        t["lcoe"] *= wm
    p["pv"]["lcoe"] *= tri(0.85, 1.0, 1.2)
    am = tri(0.7, 1.0, 1.8)
    for k in ("wind", "pv_day", "pv_shift", "network_direct", "network_flex", "flex_wind", "flex_pv"):
        p["adder"][k] *= am
    efm = tri(0.6, 0.75, 1.1)
    for k in ("eft", "emeoh", "enh3", "ech4"):
        p[k]["cost"] *= efm
    p["dac"]["cost"] *= tri(0.5, 0.75, 1.2)
    rm = tri(0.5, 1.0, 1.2)
    p["forest"].update(cap_modt=20.0 * rm, cost_odt=tri(70, 95, 140), conv=tri(55, 75, 110))
    p["agres"].update(cap_modt=15.0 * tri(0.5, 1.0, 1.2), cost_odt=tri(65, 85, 120), conv=tri(70, 95, 140))
    p["hefa"]["cost"] *= tri(0.8, 1.0, 1.3); p["canola"]["cost"] *= tri(0.8, 1.0, 1.3)
    p["heat"]["tes_cost"] = tri(14, 20, 35)
    fm = tri(0.7, 1.0, 1.3)
    p["fert"]["price"] = {k: v * fm for k, v in p["fert"]["price"].items()}
    if demand_levers:
        p["demand_mult"] = {"aviation": tri(0.70, 0.80, 0.95), "shipping": tri(0.85, 0.90, 1.0), "offroad": tri(0.80, 0.85, 1.0)}
        p["wind_assist_share"] = tri(0.08, 0.15, 0.20)
    p["lakes"] = dict(enabled=True, cleanup_cad_kg_p=0.0, force=False, p_capture_max=tri(0.05, 0.15, 0.25),
                      scum_dw_gm2=tri(15.0, 40.0, 120.0), bloom_hours=tri(500.0, 900.0, 1400.0),
                      algae_biocrude=tri(0.22, 0.30, 0.38), milfoil_biocrude=tri(0.15, 0.20, 0.25),
                      grid_g_max=tri(5.0, 10.0, 20.0), grid_share_max=tri(0.005, 0.02, 0.03), grid_biocrude=tri(0.15, 0.22, 0.28),
                      unit_capex=tri(4.0e6, 6.0e6, 12.0e6))
    p["area_share"] = {z: tri(0.025, 0.10, 0.10) if not z.endswith("deep") else tri(0.0625, 0.25, 0.25) for z in p["area_share"]}
    p["veh"].update(car=tri(0, 1500, 4800), van=tri(0, 3200, 8000), truck=tri(0, 48000, 95000),
                    lng_truck=tri(0, 39000, 63000), ed95_truck=tri(0, 12600, 21000), e100_car=tri(0, 420, 840),
                    ers_truck=tri(25000, 45000, 90000))
    p["hwy1"].update(aadtt=tri(1500.0, 2500.0, 3500.0), capex_m_km=tri(2.46, 3.6, 4.83))
    sc.cheaper_capital(p, r_new=r)
    if mode == "draw" and RNG.random() < 0.10:
        p["allow_kelp"] = False
    return p, dict(wacc=r, yield_pacific_t_ha=yp, yield_atlantic_t_ha=ya, farm_cad_t=p["farm"]["base_cad_t"], adder_mult=am,
                   wind_mult=wm, efuel_mult=efm, residue_mult=rm)


def monte_carlo(n=1000, demand_levers=True, tag="", eb=False):
    rows = []
    for i in range(n):
        p, info = mc_params(demand_levers)
        p["eb_only"] = eb
        try:
            s = o.solve(p)
        except RuntimeError:
            rows.append(dict(draw=i, **info, kelp_allowed=p["allow_kelp"], infeasible=True))
            continue
        lc, fl, red = sampled_lifecycle(s, RNG)
        a26 = fi.accounts(s, "oct2026", "avg2025"); a25 = fi.accounts(s, "avg2025", "avg2025")
        rows.append(dict(draw=i, **info, kelp_allowed=p["allow_kelp"], cost_bn=s["total_cost_bn"],
                         vehicle_premium_bn=s["vehicle_premium_bn"], fossil_oct2026_bn=s["fossil_cost_bn"]["oct2026"],
                         fossil_2025_bn=s["fossil_cost_bn"]["avg2025"], kelp_km2=s["kelp_total_km2"], kelp_share_pct=s["kelp_share_pct"],
                         electricity_twh=s["electricity_delivered_twh"], efuels_twh=s["fuels_twh"]["eFT_liquids"],
                         ebit_oct2026_bn=a26["ebit_bn"], coverage_oct2026=a26["pie_coverage"], rent_oct2026_bn=a26["rent_bn"],
                         ebit_2025_bn=a25["ebit_bn"], coverage_2025=a25["pie_coverage"],
                         mult_oil_oct2026=fi.price_needed(s, "oct2026"), mult_breakeven_oct2026=fi.price_needed(s, "oct2026", target="breakeven"),
                         mult_oil_2025=fi.price_needed(s, "avg2025"), mult_breakeven_2025=fi.price_needed(s, "avg2025", target="breakeven"),
                         gov_resource_oct2026_bn=a26["gov_resource_bn"], profit_oct2026_bn=a26["operating_profit_bn"],
                         allocable_coverage_oct2026=a26["allocable_coverage"], coverage_capture0_oct2026=fi.accounts(s, capture=0.0)["pie_coverage"],
                         coverage_capture50_oct2026=fi.accounts(s, capture=0.5)["pie_coverage"],
                         lake_p_removed_t=s["lake_p_removed_t"], lake_fuel_twh=s["lake_fuel_twh"],
                         lowcarbon_lifecycle_mtco2e=lc, fossil_lifecycle_mtco2e=fl, lifecycle_reduction_pct=red))
    fields = list(next(r for r in rows if not r.get("infeasible"))) + ["infeasible"]
    with open(OUT / f"monte_carlo{tag}.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, restval=""); w.writeheader(); w.writerows(rows)
    n_inf = sum(1 for r in rows if r.get("infeasible"))
    rows = [r for r in rows if not r.get("infeasible")]
    A = lambda k: np.array([float(r[k]) for r in rows])
    pc = lambda v: np.percentile(v, [5, 50, 95]).tolist()
    cov = A("coverage_oct2026"); m26 = A("mult_oil_oct2026"); be26 = A("mult_breakeven_oct2026")
    summ = dict(n=n, n_infeasible=n_inf, cost_p5_p50_p95=pc(A("cost_bn")), fossil_oct2026_p50=float(np.median(A("fossil_oct2026_bn"))),
                fossil_2025_p50=float(np.median(A("fossil_2025_bn"))),
                ebit_oct2026_p5_p50_p95=pc(A("ebit_oct2026_bn")), coverage_oct2026_p5_p50_p95=pc(cov),
                n_coverage_ge_1_oct2026=int(np.sum(cov >= 1.0)), n_coverage_ge_1_2025=int(np.sum(A("coverage_2025") >= 1.0)),
                mult_oil_oct2026_p5_p50_p95=pc(m26), mult_breakeven_oct2026_p5_p50_p95=pc(be26),
                mult_oil_2025_p5_p50_p95=pc(A("mult_oil_2025")), mult_breakeven_2025_p5_p50_p95=pc(A("mult_breakeven_2025")),
                n_breakeven_below_oct2026_prices=int(np.sum(be26 <= 1.0)),
                n_breakeven_below_2025_prices=int(np.sum(A("mult_breakeven_2025") <= 1.0)),
                n_oil_replaced_within_10pct_of_oct2026=int(np.sum(m26 <= 1.10)),
                pump_oil_oct2026_p50=fi.pump_price(float(np.median(m26)), "oct2026"),
                pump_breakeven_oct2026_p50=fi.pump_price(float(np.median(be26)), "oct2026"),
                gov_resource_oct2026_p50=float(np.median(A("gov_resource_oct2026_bn"))),
                profit_oct2026_p50=float(np.median(A("profit_oct2026_bn"))),
                kelp_km2_p5_p50_p95=pc(A("kelp_km2")), kelp_share_p5_p50_p95=pc(A("kelp_share_pct")),
                electricity_twh_p5_p50_p95=pc(A("electricity_twh")),
                lifecycle_reduction_pct_p5_p50_p95=pc(A("lifecycle_reduction_pct")),
                n_kelp_disabled=int(sum(1 for r in rows if not r["kelp_allowed"])),
                n_kelp_zero_or_negligible=int(np.sum(A("kelp_km2") <= 1)),
                kelp_unconditional_median_km2=float(np.median(A("kelp_km2"))),
                n_kelp_used=int(np.sum(A("kelp_km2") > 1)),
                median_kelp_used_draws_km2=float(np.median(A("kelp_km2")[A("kelp_km2") > 1])),
                median_kelp_share_used_draws=float(np.median(A("kelp_share_pct")[A("kelp_km2") > 1])),
                coverage_capture0_p5_p50_p95=pc(A("coverage_capture0_oct2026")), coverage_capture50_p5_p50_p95=pc(A("coverage_capture50_oct2026")),
                lake_p_removed_t_p5_p50_p95=pc(A("lake_p_removed_t")), lake_fuel_twh_p5_p50_p95=pc(A("lake_fuel_twh")))
    json.dump(summ, open(OUT / f"monte_carlo_summary{tag}.json", "w"), indent=1)
    return summ


ZK = tuple(o.ZONES)
OBSERVED_YIELD = 1.4     # t dry/ha/yr, upper end of commercial offshore harvests (Faroe Islands, Bak et al. 2018)


def yields_at(v):
    """All zones at a given ice-free yield; seasonal-ice zones scaled by their growing season."""
    return {z: v * sc.YIELD_SCALE.get(z.split("_")[0], 1.0) for z in ZK}


STRESS = [
    ("No kelp", {"allow_kelp": False}),
    ("No kelp and wind limited to 100 GW", {"allow_kelp": False, "wind": "cap:1.0,0.2667,0.0"}),
    ("Kelp yield at observed commercial level (1.4 t ha⁻¹ yr⁻¹)", {"zone_yield": yields_at(OBSERVED_YIELD)}),
    ("Kelp yield 4 t ha⁻¹ yr⁻¹", {"zone_yield": yields_at(4.0)}),
    ("Kelp yield 6 t ha⁻¹ yr⁻¹", {"zone_yield": yields_at(6.0)}),
    ("Whole-kelp HTL yield 0.15", {"proc": {"htl_biocrude_whole": 0.15}}),
    ("Candidate marine area 25%", "area:0.25"),
    ("Candidate marine area 5%", "area:0.05"),
    ("No depth cycling (natural nutrients or pumps)", {"nutrient_methods": ("natural", "solar_pipe", "wave_pump", "wave_pump_xl")}),
    ("No fertiliser credit", {"fert": {"price": {"n": 0.0, "p": 0.0, "k": 0.0}}}),
    ("Integration and network adders ×2", "adders:2.0"),
    ("Wind limited to 60 GW (best sites only)", {"wind": "cap:1.0,0.0,0.0"}),
    ("Wind cost +25%", "windcost:1.25"),
    ("Forest and farm residues halved", {"forest": {"cap_modt": 10.0}, "agres": {"cap_modt": 7.5}}),
    ("No food-crop fuels (canola, grain ethanol)", {"canola": {"cap": 0.0}, "crop_etoh": {"cap": 0.0}}),
    ("Finance at 7%", "finance:0.07"),
    ("Vehicle premia high", {"veh": {"car": 4800, "van": 8000, "truck": 95000, "lng_truck": 63000, "ed95_truck": 21000}}),
    ("Domestic aviation only", {"scope": "domestic"}),
    ("Lower aviation, shipping and off-road demand (transition case)", {"demand_mult": {"aviation": 0.80, "shipping": 0.90, "offroad": 0.85}, "wind_assist_share": 0.15}),
    ("No lake harvest", {"lakes": {"enabled": False}}),
    ("Lake bloom harvest capped at 5% of the P load", {"lakes": {"enabled": True, "p_capture_max": 0.05}}),
    ("Combined adverse (7%, no kelp, residues halved, adders ×2, wind +25%, high vehicle premia)", "combined:1"),
]
OPTIONS_FORCED = [
    ("Ethanol route at every kelp refinery", {"refinery_routes": ("EH",)}),
    ("Offshore pressing before shipping", {"preprocess": ("press",)}),
    ("Pumped upwelling only", {"nutrient_methods": ("natural", "solar_pipe")}),
    ("No electrofuels", {"allow_efuels": False}),
    ("LNG and CNG vehicles allowed (with liquefaction and conversion)", {"allow_methane_vehicles": True}),
    ("Electrify heavy equipment where possible (drop-in rule relaxed)", {"liquid_required": False}),
    ("Electric or biofuel only (no electrofuels; no methane, methanol or ammonia vehicles)", {"eb_only": True}),
    ("No electrified Trans-Canada Highway", {"hwy1": {"enabled": False}}),
    ("Trans-Canada Highway plus the Windsor-Montréal corridor (Highways 401 and 20, 1,300 km)", {"hwy1": {"extra_km": 1300.0, "extra_aadtt": 8000.0}}),
]


def _case(spec):
    if isinstance(spec, dict):
        spec = dict(spec)
        w = spec.pop("wind", None)
        p = CEN(overrides=spec)
        if isinstance(w, str):
            caps = [float(v) for v in w.split(":")[1].split(",")]
            for t, c in zip(p["wind"]["tiers"], caps):
                t["cap_gw"] *= c
        return p
    kind, v = spec.split(":"); v = float(v)
    p = CEN()
    if kind == "area":
        p["area_share"] = {k: min(x, v) if not k.endswith("deep") else v for k, x in p["area_share"].items()}
    elif kind == "adders":
        for k in ("wind", "pv_day", "pv_shift", "network_direct", "network_flex", "flex_wind", "flex_pv"):
            p["adder"][k] *= v
    elif kind == "windcost":
        for t in p["wind"]["tiers"]:
            t["lcoe"] *= v
    elif kind == "finance":
        p = CEN(capital=False)
    elif kind == "combined":
        p = combined_adverse(CEN(capital=False))
    return p


def combined_adverse(p):
    """Correlated stresses applied together: 7% finance (caller), no kelp, residues halved, integration and network
    adders doubled, wind cost +25% and high vehicle premia."""
    p["allow_kelp"] = False
    p["forest"]["cap_modt"] *= 0.5
    p["agres"]["cap_modt"] *= 0.5
    for k in ("wind", "pv_day", "pv_shift", "network_direct", "network_flex", "flex_wind", "flex_pv"):
        p["adder"][k] *= 2.0
    for t in p["wind"]["tiers"]:
        t["lcoe"] *= 1.25
    p["veh"].update(car=4800, van=8000, truck=95000, lng_truck=63000, ed95_truck=21000)
    return p


def robustness():
    central = o.solve(CEN())
    ca = fi.accounts(central)
    rows = []
    for group, lst in (("stress", STRESS), ("option", OPTIONS_FORCED)):
        for label, spec in lst:
            try:
                s = o.solve(_case(spec))
            except RuntimeError:
                rows.append(dict(group=group, case=label, infeasible=True))
                continue
            a = fi.accounts(s)
            rows.append(dict(group=group, case=label, cost_bn=s["total_cost_bn"], delta_bn=s["total_cost_bn"] - central["total_cost_bn"],
                             vehicle_premium_bn=s["vehicle_premium_bn"], fossil_oct2026_bn=s["fossil_cost_bn"]["oct2026"],
                             fossil_2025_bn=s["fossil_cost_bn"]["avg2025"], kelp_km2=s["kelp_total_km2"], kelp_share_pct=s["kelp_share_pct"],
                             electricity_twh=s["electricity_delivered_twh"], wind_gw=s["capacity_gw"]["Onshore wind"],
                             electrolyser_gw=s["electrolyser_gw"], dac_mt=s["co2_mt"]["DAC"], efuels_twh=s["fuels_twh"]["eFT_liquids"],
                             ebit_oct2026_bn=a["ebit_bn"], delta_ebit_bn=a["ebit_bn"] - ca["ebit_bn"], coverage_oct2026=a["pie_coverage"],
                             mult_oil_oct2026=fi.price_needed(s, "oct2026"), mult_oil_2025=fi.price_needed(s, "avg2025"),
                             lifecycle_reduction_pct=s["lifecycle"]["reduction_pct"]))
    fields = list(rows[0]) + ["infeasible"]
    with open(OUT / "robustness.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, restval=""); w.writeheader(); w.writerows(rows)
    json.dump(dict(central_bn=central["total_cost_bn"], central_ebit_bn=ca["ebit_bn"], central_coverage=ca["pie_coverage"], cases=rows),
              open(OUT / "robustness.json", "w"), indent=1, default=float)
    return rows


# ------------------------------------------------------------------ diagnostic analyses
CAPTURES = (0.0, 0.25, 0.5, 0.75, 1.0)


def capture_table(S):
    """Share of the oil-and-gas surplus replaced when only part of the positive economic rent is collected."""
    out = {}
    for k in ("central", "transition", "eb"):
        s = S[k]
        e = fi.efficiency_surplus(s)
        rows = []
        for c in CAPTURES:
            a = fi.accounts(s, capture=c)
            rows.append(dict(capture=c, ebit_bn=a["ebit_bn"], coverage=a["pie_coverage"], user_saving_bn=a["user_saving_bn"]))
        a1 = fi.accounts(s)
        out[k] = dict(rows=rows, decomposition=fi.decomposition(s), rent_bn=a1["rent_full_bn"], capital_return_bn=a1["capital_return_bn"],
                      allocable_surplus_bn=a1["allocable_surplus_bn"], **e,
                      liquid_rent_bn=a1["rent_full_bn"] - e["efficiency_surplus_bn"])
    return out


def export_ceiling(build, lo=0.0, hi=3000.0, tol=1.0):
    """Largest forced export volume (TWh/yr) for which the model is feasible under its resource bounds."""
    def ok(X):
        try:
            return o.solve(build(X))
        except RuntimeError:
            return None
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if ok(mid) is not None:
            lo = mid
        else:
            hi = mid
    s = ok(lo)
    return dict(ceiling_twh=lo, cost_bn=s["total_cost_bn"], electricity_twh=s["electricity_delivered_twh"],
                wind_twh=s["generation_twh"]["Onshore wind"], wind_gw=s["capacity_gw"]["Onshore wind"],
                pv_gw=s["capacity_gw"]["PV"], kelp_km2=s["kelp_total_km2"], dac_mt=s["co2_mt"]["DAC"],
                efuels_twh=s["fuels_twh"]["eFT_liquids"])


def exports_extended():
    oil_twh = (E.OIL_EXPORTS_2025["crude_mbd"] + E.OIL_EXPORTS_2025["products_mbd"]) * 1e6 * 365 * 1.61 / 1e6
    ex = lambda dem: (lambda X: sc.build_case(demand=dem, overrides={"export": {"price": 0.0, "cap_twh": X, "min_twh": X, "logistics": 8.0}}))
    res = {"oil_export_energy_twh": oil_twh}
    for k, dem in (("transition", True), ("central", False)):
        c = export_ceiling(ex(dem))
        c["share_of_oil_exports"] = c["ceiling_twh"] / oil_twh
        res[k] = c
    curve = []
    for X in (600, 700, 750):
        try:
            s = o.solve(ex(False)(X))
            curve.append(dict(volume_twh=X, cost_bn=s["total_cost_bn"], electricity_twh=s["electricity_delivered_twh"],
                              wind_twh=s["generation_twh"]["Onshore wind"], kelp_km2=s["kelp_total_km2"], dac_mt=s["co2_mt"]["DAC"],
                              marginal_cad_mwh=s["marginal_cad_mwh"]["dropin"] + 8.0))
        except RuntimeError:
            curve.append(dict(volume_twh=X, infeasible=True))
    res["beyond_500"] = curve
    json.dump(res, open(OUT / "export_ceiling.json", "w"), indent=1, default=float)
    return res


def combined():
    out = {}
    for k, dem in (("transition", True), ("central", False)):
        s = o.solve(combined_adverse(sc.build_case(capital=False, demand=dem)))
        a = fi.accounts(s)
        out[k] = dict(cost_bn=s["total_cost_bn"], coverage=a["pie_coverage"], ebit_bn=a["ebit_bn"],
                      coverage_capture0=fi.accounts(s, capture=0.0)["pie_coverage"],
                      mult_oil=fi.price_needed(s, "oct2026"), mult_breakeven=fi.price_needed(s, "oct2026", target="breakeven"),
                      electricity_twh=s["electricity_delivered_twh"], dac_mt=s["co2_mt"]["DAC"], efuels_twh=s["fuels_twh"]["eFT_liquids"])
    return out


def mc_skew():
    """Deterministic runs with every sampled parameter at its triangular mean and at its mode."""
    out = {}
    for k, dem in (("transition", True), ("central", False)):
        for mode in ("mean", "mode"):
            p, info = mc_params(dem, mode=mode)
            s = o.solve(p)
            a = fi.accounts(s)
            out[f"{k}|{mode}"] = dict(cost_bn=s["total_cost_bn"], coverage=a["pie_coverage"], mult_oil=fi.price_needed(s, "oct2026"),
                                      **{kk: float(v) for kk, v in info.items()})
    global _TRI
    _TRI = TRI_MODES["draw"]
    return out


def emissions_bridge(s):
    """Reconcile the model's fossil comparator with the 2024 National Inventory economic-sector transport total."""
    d = s["demand_twh"]
    comb = sum(E.CO2_T_PER_MWH[k] * d[k] for k in d)
    wtw = s["lifecycle"]["fossil_wtw_mtco2e"]
    intl = (1 - E.JET_DOMESTIC_SHARE) * d["aviation"] * E.CO2_T_PER_MWH["aviation"]
    offroad = d["offroad"] * E.CO2_T_PER_MWH["offroad"]
    eth = 0.075 * 21.2 / 34.0 * d["ldv_gasoline"] * E.CO2_T_PER_MWH["ldv_gasoline"]
    bd = 0.04 * sum(d[k] for k in ("ldv_diesel", "hdv", "rail", "offroad", "shipping")) * E.CO2_T_PER_MWH["hdv"]
    nir = E.TRANSPORT_EMISSIONS_2024_MT
    rows = [("Model fossil comparator, well to wheel", wtw),
            ("less upstream (well-to-tank) emissions", -(wtw - comb)),
            ("= combustion CO2 of fuel sold", comb),
            ("less international aviation (reported as a memo item)", -intl),
            ("less off-road machinery (inventory: agriculture, construction, mining, oil and gas)", -offroad),
            ("less biogenic CO2 of ethanol blends (7.5% by volume, estimate)", -eth),
            ("less biogenic CO2 of biodiesel and renewable diesel blends (4% of energy, estimate)", -bd)]
    rest = comb - intl - offroad - eth - bd
    rows += [("= fossil CO2 comparable with inventory transport", rest),
             ("Inventory economic-sector transport, 2024 (CO2e, incl. CH4 and N2O)", nir),
             ("Residual (inventory boundary and methods, CH4 and N2O, rounding)", nir - rest)]
    return [dict(item=a, mt=b) for a, b in rows]


def adequacy(s, wind_cf_lull=0.10, pv_cf_lull=0.03, ev_winter=1.25, peak_factor=1.35, hours=168):
    """Screening check of a seven-day cold, low-wind period: flexible loads (electrolysis, direct air capture, heat
    storage) stop; vehicle, rail and refinery loads continue. Reports the gap that reservoir hydropower, imports or
    storage would have to fill."""
    ev = s["electricity_vehicles_rail_twh"]
    ref = s["electricity_refineries_twh"] + s.get("lake_refinery_el_twh", 0.0)
    load_avg = (ev * ev_winter + ref) / 8.76
    load_peak = (ev * ev_winter * peak_factor + ref) / 8.76
    wind_gw = s["capacity_gw"]["Onshore wind"]; pv_gw = s["capacity_gw"]["PV"]
    hyd = s["generation_twh"]["Hydro (redirected exports)"] / 8.76 + s["generation_twh"]["New hydro"] / 8.76
    sup = wind_gw * wind_cf_lull + pv_gw * pv_cf_lull + hyd
    gap_avg = max(load_avg - sup, 0.0)
    firm_bn = s["cost_items_bn"]["Firming and balancing"][0]
    return dict(direct_load_annual_twh=ev + ref, load_avg_gw=load_avg, load_peak_gw=load_peak, wind_gw=wind_gw, pv_gw=pv_gw,
                lull_supply_gw=sup, gap_avg_gw=gap_avg, gap_peak_gw=max(load_peak - sup, 0.0), gap_energy_twh=gap_avg * hours / 1000,
                hydro_weekly_twh=0.60 * 625.7 / 52.18, gap_share_of_weekly_hydro=gap_avg * hours / 1000 / (0.60 * 625.7 / 52.18),
                flexible_load_gw_shed=(s["electricity_for_efuels_twh"] + s["electricity_for_dac_twh"] + s["electricity_for_heat_storage_twh"]) / 8.76,
                firming_budget_bn=firm_bn, firming_capital_share=0.70, firming_asset_life_yr=25,
                firm_capacity_affordable_gw=firm_bn * 0.70 * 1e9 / (3000 * CRF_(0.04, 25)) / 1e6)


def CRF_(r, n):
    return r * (1 + r) ** n / ((1 + r) ** n - 1)


def lakes_analysis(S):
    import lakes as lk
    T = lk.table()
    out = {"inputs": T}
    base = S["central"]
    out["central"] = dict(dry_kt=base["lake_dry_kt"], by=base["lake_dry_kt_by"], p_removed_t=base["lake_p_removed_t"],
                             p_by=base["lake_p_removed_t_by"], n_removed_t=base["lake_n_removed_t"], fuel_twh=base["lake_fuel_twh"],
                             share_pct=base["lake_share_pct"], vessels=base["lake_vessels"], cutters=base["lake_cutters"],
                             harvest_cost_bn=base["lake_harvest_cost_bn"], refinery_cost_bn=base["lake_refinery_cost_bn"],
                             fertiliser_kt=base["lake_fertiliser_kt"], p_by_lake_biomass=base["lake_p_removed_t_by_lake_biomass"],
                             p_by_biomass=base["lake_p_removed_t_by_biomass"], dry_by_biomass=base["lake_dry_kt_by_biomass"],
                             grid_km2=base["lake_grid_km2"], grid_km2_by=base["lake_grid_km2_by"], harvesters=base["lake_harvesters"],
                             grid_units=base["lake_grid_units"])
    # clean-up payment per kg of P removed: how much more P the least-cost system takes from the lakes
    curve = []
    for pay in (0.0, 25.0, 50.0, 100.0, 200.0):
        q = o.solve(CEN(overrides={"lakes": {"enabled": True, "cleanup_cad_kg_p": pay}}))
        curve.append(dict(payment_cad_kg_p=pay, p_removed_t=q["lake_p_removed_t"], p_by=q["lake_p_removed_t_by"],
                          grid_km2=q["lake_grid_km2"], dry_kt=q["lake_dry_kt"], fuel_twh=q["lake_fuel_twh"],
                          payment_bn=q["lake_cleanup_payment_bn"], harvesters=q["lake_harvesters"],
                          cost_bn=q["total_cost_bn"] + q["lake_cleanup_payment_bn"]))
    out["payment_curve"] = curve
    out["all_lakes"] = [dict(key=k, name=L.name, area_km2=L.area_km2, eutrophic_km2=L.eutrophic_km2, tp_mgl=L.tp_mgl,
                             trophic=L.trophic, p_load_t=L.p_load_t, p_removed_t=base["lake_p_removed_t_by"].get(k, 0.0),
                             grid_km2=base["lake_grid_km2_by"].get(k, 0.0),
                             grid_t_ha=(lk.grid_yield(lk.LakeParams(), L)["t_ha"] if L.eutrophic_km2 > 0 and L.tp_mgl >= 0.02 else 0.0),
                             grid_cad_t=(lk.grid_cost(lk.LakeParams(), L)["cad_t"] if L.eutrophic_km2 > 0 and L.tp_mgl >= 0.02 else None))
                        for k, L in lk.LAKES.items()]
    off = o.solve(CEN(overrides={"lakes": {"enabled": False}}))
    out["central"]["system_saving_bn"] = off["total_cost_bn"] - base["total_cost_bn"]
    out["central"]["coverage_without_lakes"] = fi.accounts(off)["pie_coverage"]
    # Lake St. Clair drains to western Lake Erie: credit its removal to the Canadian Lake Erie target
    pb = dict(base["lake_p_removed_t_by"])
    erie_credit = pb.get("erie", 0.0) + pb.pop("stclair", 0.0)
    pb["erie"] = erie_credit
    out["response"] = lk.response(pb)
    # stand-alone economics per dry tonne and per kg P at three fuel values (CAD per MWh of drop-in fuel)
    c = lk.LakeParams(); conv = lk.conversion(c, CEN()["proc"]); fert = o.base_params()["fert"]["price"]
    econ = []
    for r in lk.supply(c):
        rt = "H"
        cv = lk.conversion(c, CEN()["proc"], r["grid_p"])["grid|H"] if r["biomass"] == "grid" else conv[f"{r['biomass']}|{rt}"]
        cost = r["port_cad_t"] + cv["cost_cad"] * CEN()["refinery_cost_mult"]
        el_cost = cv["el_mwh"] * 80.0 + cv["heat_mwh_th"] * 40.0
        fert_v = cv["fert_n_kg"] * fert["n"] + cv["fert_p_kg"] * fert["p"] + cv["fert_k_kg"] * fert["k"]
        ch4_v = max(cv["ch4_gj"] - r["fleet_gj_t"], 0) / 3.6 * 75.0
        for label, v in (("fossil diesel pre-tax, 2025", E.segment_prices("avg2025")["hdv"]["p"]),
                         ("fossil diesel pre-tax, Oct 2026", E.segment_prices("oct2026")["hdv"]["p"]),
                         ("marginal renewable drop-in (central case)", base["marginal_cad_mwh"]["dropin"])):
            net = cost + el_cost - cv["hc_gj"] / 3.6 * v - fert_v - ch4_v
            econ.append(dict(lake=r["lake"], biomass=r["biomass"], fuel_value=label, fuel_cad_mwh=v, cost_cad_t=cost + el_cost,
                             net_cost_cad_t=net, net_cad_per_kg_p=net / r["p_kg_t"], fuel_mwh_t=cv["hc_gj"] / 3.6))
    out["economics"] = econ
    # ranges of harvestable P (low and high parameter sets)
    rng = {}
    for nm, kw in (("low", dict(p_capture_max=0.05, scum_dw_gm2=15.0, bloom_hours=500.0, bed_share_max=0.25, cattail_yield_t_ha=10.0,
                                cattail_share_max=0.25, grid_g_max=5.0, grid_share_max=0.005)),
                   ("central", {}), ("high", dict(p_capture_max=0.25, scum_dw_gm2=120.0, bloom_hours=1400.0, bed_share_max=0.5,
                                                  cattail_yield_t_ha=20.0, grid_g_max=20.0, grid_share_max=0.03))):
        cc = lk.LakeParams(**kw)
        sup = lk.supply(cc)
        rng[nm] = dict(dry_kt=sum(r["cap_t"] for r in sup) / 1e3, p_t=sum(r["cap_t"] * r["p_kg_t"] for r in sup) / 1e3,
                       winnipeg_p_t=sum(r["cap_t"] * r["p_kg_t"] for r in sup if r["lake"] == "winnipeg") / 1e3,
                       erie_stclair_p_t=sum(r["cap_t"] * r["p_kg_t"] for r in sup if r["lake"] in ("erie", "stclair")) / 1e3)
    out["ranges"] = rng
    # nutrients recovered by the whole system (kelp + lakes) against domestic fertiliser use caps
    out["fertiliser_balance"] = dict(kelp_mt=base["fertiliser_mt"], lakes_kt=base["lake_fertiliser_kt"],
                                     total_mt=base["fertiliser_total_mt"], domestic_cap_mt=o.base_params()["fert"]["cap_mt"])
    json.dump(out, open(OUT / "lakes.json", "w"), indent=1, default=float)
    return out


def diagnostics():
    S = {k: o.solve(f()) for k, f in CASES.items()}
    R = dict(capture=capture_table(S), combined=combined(), mc_skew=mc_skew(),
             emissions_bridge={k: emissions_bridge(S[k]) for k in ("central", "transition")},
             adequacy={k: adequacy(S[k]) for k in ("central", "transition", "eb")},
             cer_net_zero=dict(demand_growth_2021_2050=1.20, generation_2021_twh=625.7))
    json.dump(R, open(OUT / "diagnostics.json", "w"), indent=1, default=float)
    return R, S


# ------------------------------------------------------------------ self-reliance and national emissions
STRICT = {"allow_efuels": False, "eb_only": True, "forest": {"cap_modt": 0.0}, "agres": {"cap_modt": 0.0}}
SELF_CASES = [("All routes (central case)", {}),
              ("No electrofuels", {"allow_efuels": False}),
              ("Electric or biofuel only", {"eb_only": True}),
              ("Electrification, seaweed and existing biofuels only", STRICT),
              ("… and no lake biomass", {**STRICT, "lakes": {"enabled": False}})]


def _self_row(label, s):
    a = fi.accounts(s)
    return dict(case=label, cost_bn=s["total_cost_bn"], kelp_km2=s["kelp_total_km2"], kelp_dry_mt=s["kelp_dry_mt"],
                kelp_share_pct=s["kelp_share_pct"], kelp_hc_twh=s["kelp_hc_twh"], lake_fuel_twh=s["lake_fuel_twh"],
                electricity_twh=s["electricity_delivered_twh"], wind_gw=s["capacity_gw"]["Onshore wind"],
                efuels_twh=s["fuels_twh"]["eFT_liquids"], residues_twh=s["fuels_twh"]["forest_residue_HTL"] + s["fuels_twh"]["agri_residue_FT"],
                existing_biofuels_twh=sum(s["fuels_twh"][k] for k in ("HEFA_waste_lipids", "canola_HVO", "grain_ethanol_existing", "waste_biomethane")),
                coverage=a["pie_coverage"], coverage_capture0=fi.accounts(s, capture=0.0)["pie_coverage"],
                mult_breakeven=fi.price_needed(s, "oct2026", target="breakeven"), mult_oil=fi.price_needed(s, "oct2026"),
                lifecycle_reduction_pct=s["lifecycle"]["reduction_pct"], harvesters=harvesters(s)["engineering_units"], harvesters_area_basis=harvesters(s)["area_duty_units"],
                harvesters_biomass_basis=harvesters(s)["biomass_throughput_units"],
                kelp_refineries=s["kelp_dry_mt"] / 0.5)


def self_reliance(n_mc=1000):
    rows = []
    for label, ov in SELF_CASES:
        try:
            rows.append(_self_row(label, o.solve(CEN(overrides=copy.deepcopy(ov)))))
        except RuntimeError:
            rows.append(dict(case=label, infeasible=True))
    try:
        rows.append(_self_row("Electrification, seaweed and existing biofuels, transition demand",
                              o.solve(sc.build_case(overrides=copy.deepcopy(STRICT)))))
    except RuntimeError:
        rows.append(dict(case="Electrification, seaweed and existing biofuels, transition demand", infeasible=True))
    # area actually available to kelp at the farm-area caps
    p = CEN(); kelp_max = sum(sum(z.area_km2.values()) * p["area_share"][k] for k, z in o.ZONES.items())
    # lowest kelp yield (multiple of the learned yields) at which the strict case is feasible
    def feas(f):
        q = CEN(overrides=copy.deepcopy(STRICT)); q["zone_yield"] = {k: v * f for k, v in q["zone_yield"].items()}
        try:
            o.solve(q); return True
        except RuntimeError:
            return False
    lo, hi = 0.5, 1.0
    for _ in range(12):
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if feas(mid) else (mid, hi)
    ymin = hi
    # Monte Carlo: share of draws in which the strict case is feasible
    rng_state = RNG.bit_generator.state
    ok, cov = 0, []
    for i in range(n_mc):
        q, info = mc_params(False)
        q["allow_efuels"] = False; q["eb_only"] = True; q["forest"]["cap_modt"] = 0.0; q["agres"]["cap_modt"] = 0.0
        q["allow_kelp"] = True
        try:
            ss = o.solve(q); ok += 1; cov.append(fi.accounts(ss)["pie_coverage"])
        except RuntimeError:
            pass
    RNG.bit_generator.state = rng_state
    res = dict(cases=rows, kelp_area_available_km2=kelp_max, strict_min_yield_factor=ymin,
               strict_min_yield_pacific=12.0 * ymin, strict_min_yield_atlantic=9.0 * ymin,
               kelp_area_available_by_zone_km2={k: sum(z.area_km2.values()) * p["area_share"][k] for k, z in o.ZONES.items()},
               mc_strict_feasible=ok, mc_n=n_mc, mc_strict_coverage_p50=float(np.median(cov)) if cov else None)
    json.dump(res, open(OUT / "self_reliance.json", "w"), indent=1, default=float)
    return res


def territorial(s):
    """Emissions released in Canada (NIR boundary) by a solved renewable system."""
    import emissions as em
    from lifecycle import domestic_fuels
    f = domestic_fuels(s)
    bio = sum(v for k, v in f.items() if k not in ("eFT_liquids", "e_methanol", "e_ammonia", "e_methane"))
    intl_jet = (1 - E.JET_DOMESTIC_SHARE) * s["demand_twh"]["aviation"]
    ch4 = max(s["kelp_ch4_gross_twh"], 0) + max(s.get("lake_ch4_gross_twh", 0), 0) + f.get("waste_biomethane", 0)
    efuel = sum(f.get(k, 0) for k in ("eFT_liquids", "e_methanol", "e_ammonia", "e_methane"))
    return em.territorial_addition(max(bio + efuel - intl_jet, 0.0), ch4)


# ------------------------------------------------------------------ electric-or-biofuel end uses, Trans-Canada Highway, siting
SEG_LABEL = {"ldv_gasoline": "Cars and light trucks", "ldv_diesel": "Diesel pick-ups and vans", "hdv": "Heavy trucks and buses",
             "rail": "Rail", "offroad|farm": "Farm machinery", "offroad|mine": "Mining equipment",
             "offroad|con": "Construction, forestry machinery", "aviation": "Aviation (jets)", "shipping": "Domestic shipping"}


def end_use_table(s):
    """Fossil energy replaced by segment and how it is served (TWh of fossil fuel replaced)."""
    import optimise as oo
    eu = s["end_use_twh"]; d = s["demand_twh"]
    rows = []
    for key, label in SEG_LABEL.items():
        if key.startswith("offroad|"):
            k = key.split("|")[1]
            el = eu.get(f"offroad|{k}_el", 0.0); liq = eu.get(f"offroad|{k}_liq", 0.0)
            rows.append(dict(segment=label, demand_twh=oo.OFFROAD[k]["share"] * d["offroad"], battery=el, catenary=0.0,
                             biofuel=liq, other=0.0, electricity_twh=el * oo.OPTIONS["offroad"][f"{k}_el"][1]))
            continue
        opts = oo.OPTIONS[key]
        bat = sum(v for kk, v in eu.items() if kk.startswith(key + "|") and opts[kk.split("|")[1]][0] == "el_direct" and not kk.endswith("|ers"))
        cat = eu.get(f"{key}|ers", 0.0)
        bio = sum(v for kk, v in eu.items() if kk.startswith(key + "|") and opts[kk.split("|")[1]][0] in ("dropin", "jet", "ethanol"))
        wa = s["wind_assist_twh_saved"] if key == "shipping" else 0.0
        oth = d[key] - bat - cat - bio - wa
        el = sum(v * opts[kk.split("|")[1]][1] for kk, v in eu.items() if kk.startswith(key + "|") and opts[kk.split("|")[1]][0] == "el_direct")
        rows.append(dict(segment=label, demand_twh=d[key], battery=bat, catenary=cat, biofuel=bio, other=max(oth, 0.0), wind_assist=wa,
                         electricity_twh=el))
    return rows


def hwy1_analysis():
    out = {}
    for nm, ov in (("central", {}), ("eb", {"eb_only": True})):
        base = o.solve(CEN(overrides=dict(ov)))
        off = o.solve(CEN(overrides={**ov, "hwy1": {"enabled": False}}))
        ext = o.solve(CEN(overrides={**ov, "hwy1": {"extra_km": 1300.0, "extra_aadtt": 8000.0}}))
        rows = []
        for lab, hv in (("AADTT 1,500", {"aadtt": 1500.0}), ("AADTT 3,500", {"aadtt": 3500.0}),
                        ("Catenary CAD 2.46 M/km", {"capex_m_km": 2.46}), ("Catenary CAD 4.83 M/km", {"capex_m_km": 4.83}),
                        ("Catenary CAD 9 M/km", {"capex_m_km": 9.0})):
            q = o.solve(CEN(overrides={**ov, "hwy1": hv}))
            rows.append(dict(case=lab, cost_bn=q["total_cost_bn"], saving_vs_no_ers_bn=off["total_cost_bn"] - q["total_cost_bn"],
                             ers_used_twh=q["ers"]["used_twh_diesel"], ers_cad_mwh=q["ers"]["cad_per_mwh_diesel"]))
        out[nm] = dict(ers=base["ers"], cost_bn=base["total_cost_bn"], cost_no_ers_bn=off["total_cost_bn"],
                       saving_bn=off["total_cost_bn"] - base["total_cost_bn"], kelp_km2=base["kelp_total_km2"],
                       kelp_km2_no_ers=off["kelp_total_km2"], dropin_twh=base["dropin_supply_twh"], dropin_twh_no_ers=off["dropin_supply_twh"],
                       marginal_dropin=base["marginal_cad_mwh"]["dropin"],
                       with_401=dict(cost_bn=ext["total_cost_bn"], ers=ext["ers"], kelp_km2=ext["kelp_total_km2"],
                                     saving_vs_hwy1_bn=base["total_cost_bn"] - ext["total_cost_bn"]),
                       sensitivity=rows, end_use=end_use_table(base), offroad_twh=base["offroad_twh"])
    json.dump(out, open(OUT / "highway1.json", "w"), indent=1, default=float)
    return out


def yield_taxonomy():
    """Demonstrated, design and learning-target kelp yields in the central and electric-or-biofuel cases."""
    sets = (("demonstrated (commercial, Faroe Islands)", yields_at(OBSERVED_YIELD)),
            ("design (8 Pacific, 6 Atlantic)", {z: o.ZONES[z].yield_t_ha for z in ZK}),
            ("learning target (12 Pacific, 9 Atlantic)", dict(sc.YIELD_LEARN)))
    out = []
    for nm, ov in (("central", {}), ("eb", {"eb_only": True}), ("strict", copy.deepcopy(STRICT))):
        for lab, y in sets:
            try:
                q = o.solve(CEN(overrides={**copy.deepcopy(ov), "zone_yield": y}))
                a = fi.accounts(q)
                out.append(dict(case=nm, yield_set=lab, cost_bn=q["total_cost_bn"], kelp_km2=q["kelp_total_km2"], kelp_dry_mt=q["kelp_dry_mt"],
                                kelp_share_pct=q["kelp_share_pct"], electricity_twh=q["electricity_delivered_twh"],
                                efuels_twh=q["fuels_twh"]["eFT_liquids"], mult_breakeven=fi.price_needed(q, "oct2026", target="breakeven"),
                                coverage=a["pie_coverage"], feasible=True))
            except RuntimeError:
                out.append(dict(case=nm, yield_set=lab, feasible=False))
    json.dump(out, open(OUT / "yield_taxonomy.json", "w"), indent=1, default=float)
    return out


REGION_NAME = {"pac": "British Columbia coast", "atl": "Scotian Shelf, Bay of Fundy and south Newfoundland",
               "gsl": "Gulf of St Lawrence", "lab": "Labrador and north-east Newfoundland", "hb": "Hudson Bay and James Bay"}


def siting(S):
    """Kelp farm siting by region in the central and electric-or-biofuel cases, biomass cost at the cheapest band of
    each region, and the extra cost of forcing 2,000 km2 of farms into each seasonal-ice region (Hudson Bay farms
    supply biorefineries at Churchill, Manitoba, and Moosonee, Ontario)."""
    import farm as fm
    fc = fm.FarmCost(**CEN()["farm"])
    out = {"available_km2": {}, "cheapest_biomass_cad_t": {}, "solutions": {}, "forced": []}
    p = CEN()
    for zk, z in o.ZONES.items():
        reg = zk.split("_")[0]
        out["available_km2"][reg] = out["available_km2"].get(reg, 0.0) + sum(z.area_km2.values()) * p["area_share"][zk]
        y = p["zone_yield"].get(zk)
        best = min(fm.farm_cost(zk, b, fc, m, yield_override=y)["total_cad_t"] for b in z.area_km2 for m in o.METHODS)
        out["cheapest_biomass_cad_t"][zk] = best
    for k in ("central", "eb"):
        bz = S[k]["kelp_by_zone_km2"]
        reg = {}
        for zk, v in bz.items():
            reg[zk.split("_")[0]] = reg.get(zk.split("_")[0], 0.0) + v
        out["solutions"][k] = dict(by_region_km2=reg, by_zone_band_km2=S[k]["kelp_by_zone_band_km2"], total_km2=S[k]["kelp_total_km2"])
    for k, ov in (("central", {}), ("eb", {"eb_only": True})):
        for reg in ("gsl", "lab", "hb"):
            try:
                q = o.solve(CEN(overrides={**ov, "kelp_min_km2": {reg: 2000.0}}))
                extra = q["total_cost_bn"] - S[k]["total_cost_bn"]
                dry = sum(v * 1e2 * (p["zone_yield"].get(z.split("|")[0]) or o.ZONES[z.split("|")[0]].yield_t_ha)
                          for z, v in q["kelp_by_zone_band_km2"].items() if z.startswith(reg + "_")) / 1e6
                out["forced"].append(dict(case=k, region=reg, extra_cost_bn=extra, dry_mt=dry,
                                          extra_cad_per_t=extra * 1e9 / (dry * 1e6) if dry > 0 else None))
            except RuntimeError:
                out["forced"].append(dict(case=k, region=reg, infeasible=True))
    json.dump(out, open(OUT / "siting.json", "w"), indent=1, default=float)
    return out


def national(S, key="central"):
    import emissions as em
    s = S[key]
    br = {r["item"]: r["mt"] for r in emissions_bridge(s)}
    off = -br["less off-road machinery (inventory: agriculture, construction, mining, oil and gas)"]
    t = territorial(s)
    lc = dict(fossil_wtw_mt=s["lifecycle"]["fossil_wtw_mtco2e"], renewable_wtw_mt=s["lifecycle"]["lowcarbon_wtw_mtco2e"],
              renewable_wtw_range_mt=s["lifecycle"]["lowcarbon_factor_sensitivity_mtco2e"], reduction_pct=s["lifecycle"]["reduction_pct"],
              parts_mt=s["lifecycle"]["parts_mtco2e"])
    r = em.ledger(off, t["total_mt"],
                  (E.OIL_EXPORTS_2025["crude_mbd"] + E.OIL_EXPORTS_2025["products_mbd"]) * 1e6 * 365 * 1.61 / 1e6, lc)
    r["territorial_parts_mt"] = t
    r["case"] = key
    json.dump(r, open(OUT / f"national_emissions{'' if key == 'central' else '_' + key}.json", "w"), indent=1, default=float)
    return r


if __name__ == "__main__":
    R, S = headline()
    for k in CASES:
        r = R[k]; f26 = r["fiscal"]["oct2026|avg2025"]; f25 = r["fiscal"]["avg2025|avg2025"]
        print(k, "cost", round(r["total_cost_bn"], 2), "veh", round(r["vehicle_premium_bn"], 2), "fossil", {a: round(b, 1) for a, b in r["fossil_cost_bn"].items()},
              "kelp", round(r["kelp_total_km2"]), round(r["kelp_share_pct"], 1), "el", round(r["electricity_delivered_twh"]), "LCA", round(r["lifecycle"]["reduction_pct"], 1))
        print("   Oct26: EBIT", round(f26["ebit_bn"], 1), "cov", round(f26["pie_coverage"], 3), "gov", round(f26["gov_resource_bn"], 1), "profit", round(f26["operating_profit_bn"], 1),
              "| 2025: EBIT", round(f25["ebit_bn"], 1), "cov", round(f25["pie_coverage"], 3))
        for per in PERIODS:
            pr = r["fiscal"][f"{per}|price"]
            print("   ", per, "mult oil", round(pr["mult_oil_2025"], 3), {a: round(b, 1) for a, b in pr["pump_oil_2025"].items()},
                  "breakeven", round(pr["mult_breakeven"], 3), {a: round(b, 1) for a, b in pr["pump_breakeven"].items()})
    print("exposure", {k: round(v, 2) for k, v in R["exposure"].items()})
    L = levers()
    for c in L["cumulative"]:
        print("lever", c["key"], round(c["cost"], 2), round(c.get("step_saving", 0), 2), round(c["kelp_km2"]), round(c["kelp_share"], 1), "cov", round(c["coverage"], 3))
    X = exports()
    for c in X["supply_curve"]:
        print("supply", c["volume_twh"], round(c["added_cost_bn"], 2), round(c["marginal_cad_mwh"]), round(c.get("average_increment_cad_mwh", 0)))
    for c in X["at_price"]:
        print("price", c["price_cad_mwh"], round(c["price_usd_t"]), "vol", round(c["volume_twh"]), "addEBIT", round(c["added_ebit_bn"], 2), "cov", round(c["coverage"], 3))
    rows = robustness()
    for r in [r for r in rows if not r.get("infeasible")]:
        print(f"{r['group']:7s} {r['case'][:58]:58s} {r['cost_bn']:6.1f} {r['delta_bn']:+6.1f} kelp {r['kelp_km2']:7.0f} el {r['electricity_twh']:5.0f} cov {r['coverage_oct2026']:.3f} m {r['mult_oil_oct2026']:.3f}")
    print(monte_carlo(demand_levers=False))
    print(monte_carlo(demand_levers=True, tag="_transition"))
    print(monte_carlo(demand_levers=False, tag="_eb", eb=True))
    RR, SS = diagnostics()
    print("capture", {k: [round(r["coverage"], 3) for r in v["rows"]] for k, v in RR["capture"].items()})
    print("eff surplus", {k: round(v["efficiency_surplus_bn"], 1) for k, v in RR["capture"].items()}, "liquid rent", {k: round(v["liquid_rent_bn"], 1) for k, v in RR["capture"].items()})
    print("combined", RR["combined"])
    print("skew", {k: (round(v["cost_bn"], 1), round(v["coverage"], 3)) for k, v in RR["mc_skew"].items()})
    for r in RR["emissions_bridge"]["central"]:
        print("bridge", r["item"], round(r["mt"], 1))
    print("adequacy", {k: {a: round(b, 2) for a, b in v.items()} for k, v in RR["adequacy"].items()})
    XE = exports_extended()
    print("export ceiling", XE)
    LK = lakes_analysis(SS)
    SR = self_reliance()
    for r in SR["cases"]:
        print("self", r["case"], {k: round(v, 3) for k, v in r.items() if isinstance(v, float)})
    print("strict min yield factor", SR["strict_min_yield_factor"], "mc feasible", SR["mc_strict_feasible"], SR["mc_strict_coverage_p50"], "kelp max", SR["kelp_area_available_km2"])
    NE = national(SS)
    H1 = hwy1_analysis()
    print("hwy1", {k: (round(v["cost_bn"], 2), round(v["saving_bn"], 2), round(v["kelp_km2"]), round(v["kelp_km2_no_ers"])) for k, v in H1.items()})
    YT = yield_taxonomy()
    print("yields", [(r["case"], r["yield_set"][:12], round(r.get("cost_bn", 0), 1), round(r.get("kelp_km2", 0))) for r in YT])
    SI = siting(SS)
    print("siting", SI["solutions"], SI["forced"])
    NEB = national(SS, "eb")
    print("national eb", [(round(r["mt"], 1), r["case"][:40]) for r in NEB["rows"]])
    NE = national(SS)
    print("national", [(round(r["mt"], 1), r["case"][:40]) for r in NE["rows"]], NE["share_below_2005_pct"])
    print("lakes", LK["central"], LK["response"], LK["ranges"])
