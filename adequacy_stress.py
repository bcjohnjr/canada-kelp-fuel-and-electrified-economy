"""Multi-day winter adequacy stress tests for the central 2050 system.

The national model balances energy annually. This screen asks what it takes to keep vehicles, rail and refineries
supplied through cold, low-wind periods of 3, 7 and 14 days. Flexible loads (electrolysers, direct air capture,
wind-charged heat storage) stop; battery-electric vehicle demand rises in winter and peaks above its average.
Supply during the lull is wind and solar at reduced capacity factors, SMR output, and an assumed share of Canada's
weekly hydro energy reshaped from exports and reservoir storage. Any remaining power gap is met by fossil-free
peaking turbines burning renewable methane produced by the system (or by equivalent long-duration storage), and their
capital and fuel are costed. All values are screening assumptions listed in PARAMS.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"

PARAMS = {
    "ev_winter_factor": 1.25, "peak_factor": 1.35, "pv_cf_lull": 0.03,
    "wind_cf_lull": [0.05, 0.10, 0.15], "durations_days": [3, 7, 14],
    "hydro_weekly_twh": 0.60 * 625.7 / 52.18,          # 60% hydro share of 625.7 TWh national generation, per week
    "hydro_reshape_share": [0.0, 0.10, 0.25],           # share of weekly hydro energy that can be redirected to transport
    "turbine_capex_cad_kw": 1400.0, "turbine_fom_cad_kw_yr": 25.0, "turbine_life": 30, "rate": 0.04,
    "turbine_efficiency": 0.38,
    "events_per_year": 1.0,                             # one design event a year for fuel cost
    "smr_availability_winter": 0.95,
}


def crf(r, n):
    return r * (1 + r) ** n / ((1 + r) ** n - 1)


def stress(s, P=PARAMS):
    ev = s["electricity_vehicles_rail_twh"]
    ref = s["electricity_refineries_twh"] + s.get("lake_refinery_el_twh", 0.0)
    load_avg = (ev * P["ev_winter_factor"] + ref) / 8.76
    load_peak = (ev * P["ev_winter_factor"] * P["peak_factor"] + ref) / 8.76
    wind = s["capacity_gw"]["Onshore wind"]; pv = s["capacity_gw"]["PV"]; smr = s["capacity_gw"].get("SMR", 0.0)
    methane_value = s["marginal_cad_mwh"]["methane"]
    firm_budget = s["cost_items_bn"]["Firming and balancing"][0]
    rows = []
    for cf in P["wind_cf_lull"]:
        sup = wind * cf + pv * P["pv_cf_lull"] + smr * P["smr_availability_winter"]
        for days in P["durations_days"]:
            for hs in P["hydro_reshape_share"]:
                h = days * 24
                hydro_gw = hs * P["hydro_weekly_twh"] * 1000 / 168          # average GW from reshaped hydro
                gap_avg = max(load_avg - sup - hydro_gw, 0.0)
                gap_peak = max(load_peak - sup - hydro_gw, 0.0)
                energy_twh = gap_avg * h / 1000
                turbine_bn = gap_peak * 1e6 * (P["turbine_capex_cad_kw"] * crf(P["rate"], P["turbine_life"]) + P["turbine_fom_cad_kw_yr"]) / 1e9
                fuel_bn = energy_twh * 1e6 / P["turbine_efficiency"] * methane_value * P["events_per_year"] / 1e9
                rows.append(dict(wind_cf=cf, days=days, hydro_share=hs, lull_supply_gw=sup, hydro_gw=hydro_gw, load_avg_gw=load_avg,
                                 load_peak_gw=load_peak, gap_avg_gw=gap_avg, gap_peak_gw=gap_peak, gap_energy_twh=energy_twh,
                                 methane_twh=energy_twh / P["turbine_efficiency"], turbine_bn=turbine_bn, fuel_bn=fuel_bn,
                                 backup_bn=turbine_bn + fuel_bn, extra_over_firming_budget_bn=max(turbine_bn + fuel_bn - firm_budget, 0.0)))
    design = next(r for r in rows if r["wind_cf"] == 0.10 and r["days"] == 7 and r["hydro_share"] == 0.10)
    worst = max(rows, key=lambda r: r["backup_bn"])
    return dict(params=P, firming_budget_bn=firm_budget, methane_value_cad_mwh=methane_value, rows=rows, design=design, worst=worst,
                # bracket: the backup either replaces part of the existing firming budget or is entirely additional
                design_cost_bracket_bn=[s["total_cost_bn"] + design["extra_over_firming_budget_bn"], s["total_cost_bn"] + design["backup_bn"]],
                worst_cost_bracket_bn=[s["total_cost_bn"] + worst["extra_over_firming_budget_bn"], s["total_cost_bn"] + worst["backup_bn"]])


def integrated(cases=(("7 days, wind CF 0.10, 10% hydro", 0.10, 7, 0.10), ("14 days, wind CF 0.10, 10% hydro", 0.10, 14, 0.10),
                       ("14 days, wind CF 0.05, no hydro (worst)", 0.05, 14, 0.0)), iterations=3):
    """Adds the winter methane reserve and backup turbines to the national LP and re-optimizes production (iterating
    because the backup need depends on the re-optimized capacities)."""
    import optimise as O, scenarios as SC
    base = O.solve(SC.build_case(demand=False))
    out = []
    for label, cf, days, hs in cases:
        s = base; hist = []
        for _ in range(iterations):
            row = next(r for r in stress(s)["rows"] if r["wind_cf"] == cf and r["days"] == days and r["hydro_share"] == hs)
            p = SC.build_case(demand=False)
            p["winter_reserve"].update(methane_twh=row["methane_twh"], turbine_gw=row["gap_peak_gw"])
            s = O.solve(p); hist.append(s["total_cost_bn"])
        f = s["fuels_twh"]
        out.append(dict(case=label, wind_cf=cf, days=days, hydro_share=hs, turbine_gw=row["gap_peak_gw"], methane_reserve_twh=row["methane_twh"],
                        total_cost_bn=s["total_cost_bn"], extra_vs_annual_bn=s["total_cost_bn"] - base["total_cost_bn"],
                        extra_pct=100 * (s["total_cost_bn"] - base["total_cost_bn"]) / base["total_cost_bn"],
                        waste_biomethane_twh=f["waste_biomethane"], e_methane_twh=f["e_methane"], kelp_km2=s["kelp_total_km2"],
                        kelp_dry_mt=s["kelp_dry_mt"], kelp_fuel_twh=s["kelp_fuel_twh"], reduction_pct=s["lifecycle"]["reduction_pct"],
                        lowcarbon_wtw_mt=s["lifecycle"]["lowcarbon_wtw_mtco2e"], electricity_twh=s["electricity_delivered_twh"],
                        wind_twh=s["generation_twh"]["Onshore wind"], iterations=hist,
                        reserve_cost_item_bn=s["cost_items_bn"]["Winter reserve (backup turbines, methane storage)"][0]))
    return dict(annual_only_bn=base["total_cost_bn"], annual_only_kelp_km2=base["kelp_total_km2"], annual_only_kelp_dry_mt=base["kelp_dry_mt"],
                annual_only_reduction_pct=base["lifecycle"]["reduction_pct"], annual_only_electricity_twh=base["electricity_delivered_twh"], cases=out)


if __name__ == "__main__":
    s = json.load(open(OUT / "central_smr.json"))
    R = stress(s)
    R["integrated"] = integrated()
    for c in R["integrated"]["cases"]:
        print(c["case"], round(c["total_cost_bn"], 2), round(c["extra_vs_annual_bn"], 2), round(c["methane_reserve_twh"], 1),
              round(c["turbine_gw"], 1), [round(x, 3) for x in c["iterations"]])
    json.dump(R, open(OUT / "adequacy_stress.json", "w"), indent=1)
    for k in ("design", "worst"):
        print(k, {a: round(b, 2) for a, b in R[k].items()})
    print("firming budget", round(R["firming_budget_bn"], 2), "design", [round(v, 2) for v in R["design_cost_bracket_bn"]],
          "worst", [round(v, 2) for v in R["worst_cost_bracket_bn"]])
