"""Transition analysis: why liquid biofuels, including kelp, are needed while the fleet turns over.

The least-cost programme (optimise.py) solves a mature, annual end state. It cannot see that the vehicles on the road
today keep burning liquid fuel until they are retired. This module adds a year-by-year screening account, 2025-2050:

1. Fleet turnover. For each segment a vintage stock model with Weibull survival converts a sales share of electric
   vehicles (or machines) into the electric share of stock energy. Electric sales shares rise along logistic paths to
   the end-state electric shares that the least-cost programme selects (results.json, central case).
2. Liquid demand. Each year, the energy not yet electrified must be met by liquid (or gaseous) fuel: fossil, or drop-in
   and blended biofuels.
3. Biofuel supply ramps. Existing biofuels, new forest and farm residue fuels, lake biomass, electrofuels and kelp are
   built up along stated ramps to the volumes of the programme's supply sets. Ethanol is limited by the gasoline blend
   wall (E10) unless flexible-fuel vehicles take E85; hydrotreated HTL, HEFA/HVO and Fischer-Tropsch fuels are drop-in
   diesel and jet-range fuels (jet use subject to ASTM qualification).
4. Emissions. Well-to-wheel factors are those of the lifecycle module (lifecycle in results.json).
5. Heavy vehicles. Battery mass needed to replace a day of diesel work, for three heavy machines.

All ramps, lifetimes and machine duty cycles are screening assumptions listed in ASSUME and reported in the
Supporting Information; they are not forecasts.
"""
import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
YEARS = np.arange(2025, 2051)

ASSUME = {
    # fleet: mean service life (years), Weibull shape, current electric share of new sales, year electric sales
    # reach 95% of the end-state share in the central / fast / slow electrification paths
    "segments": {
        "ldv":      dict(life=16.0, shape=4.0, sales_now=0.094, t95={"central": 2040, "fast": 2035, "slow": 2050}, stock_now=0.028),
        "hdv":      dict(life=14.0, shape=3.5, sales_now=0.01,  t95={"central": 2042, "fast": 2037, "slow": 2050}, stock_now=0.002),
        "rail":     dict(life=30.0, shape=4.0, sales_now=0.02,  t95={"central": 2045, "fast": 2040, "slow": 2050}, stock_now=0.0),
        "farm":     dict(life=20.0, shape=3.5, sales_now=0.01,  t95={"central": 2045, "fast": 2040, "slow": 2050}, stock_now=0.0),
        "mine":     dict(life=15.0, shape=3.5, sales_now=0.03,  t95={"central": 2042, "fast": 2037, "slow": 2050}, stock_now=0.0),
        "con":      dict(life=18.0, shape=3.5, sales_now=0.02,  t95={"central": 2045, "fast": 2040, "slow": 2050}, stock_now=0.0),
    },
    # biofuel supply ramps (TWh/a of fossil energy replaced): start year, year at full volume
    "ramp_existing": (2027, 2027), "ramp_residues": (2029, 2040), "ramp_lake": (2029, 2035),
    "ramp_efuels": (2030, 2045),
    "kelp_start": 2030, "kelp_build_km2_a": 4000.0, "kelp_learning_year": 2036, "kelp_design_to_learned": 2 / 3,
    "e10_energy_share": 0.067,       # ethanol energy share of E10
    "e85_energy_share": 0.62,        # annual-average ethanol energy share of E85 (summer ~E83, winter ~E51-E70)
    "grain_ethanol_twh": 12.0,       # existing grain ethanol within the 35 TWh of existing biofuels
    "kelp_eh_ethanol_share": 3.762 / (3.762 + 3.344),   # ethanol share of route EH fuel energy (biorefinery.py)
    "conversion_levels": {"low": 0.25, "central": 0.50, "high": 0.75},   # share of gasoline cars converted by 2035
    "conversion_ramp": (2027, 2035),
    "ffv_share_now": 0.02,           # flexible-fuel share of the light-duty ICE stock today (screening assumption)
    # heavy machines: daily diesel use (L), diesel kWh/L, engine and electric drivetrain efficiencies, pack kWh/kg,
    # winter capacity margin
    "diesel_kwh_l": 10.0, "eta_diesel": 0.40, "eta_electric": 0.90, "pack_kwh_kg": (0.14, 0.18), "winter_margin": 1.3,
    "machines": {
        "Long-haul tractor-trailer, 800 km day": dict(litres_day=280.0),
        "Combine harvester, 14 h harvest day": dict(litres_day=700.0),
        "220-t mining haul truck, 12 h shift": dict(litres_day=1800.0),
    },
}


def survival(age, life, shape):
    """Weibull survival with mean service life `life`."""
    import math
    lam = life / math.gamma(1 + 1 / shape)
    return np.exp(-(np.asarray(age, float) / lam) ** shape)


def sales_path(end_share, now, t95, years=YEARS):
    """Logistic electric sales share from `now` in 2025 to 95% of `end_share` in year t95."""
    if end_share <= now:
        return np.full(len(years), end_share)
    f0 = now / end_share
    a0, a1 = np.log(f0 / (1 - f0)), np.log(0.95 / 0.05)
    k = (a1 - a0) / (t95 - 2025); t50 = 2025 - a0 / k
    return end_share / (1 + np.exp(-k * (years - t50)))


def stock_share(sales, life, shape, stock_now):
    """Cohort model of a constant-size stock: each year survivors age one year, retirements are replaced by new
    units of which the share `sales[i]` is electric. Returns the electric share of the stock by year."""
    ages = np.arange(0, 60)
    S = survival(ages, life, shape)
    p = np.r_[S[1:] / np.maximum(S[:-1], 1e-12), 0.0]            # probability of surviving from age a to a+1
    n = S / S.sum()                                              # steady-state age distribution
    young = ages < 5
    e = np.where(young, n * stock_now / n[young].sum(), 0.0)      # today's electric units are recent
    out = [e.sum()]
    for i in range(1, len(YEARS)):
        n_new = np.r_[0.0, (n * p)[:-1]]; e_new = np.r_[0.0, (e * p)[:-1]]
        add = 1.0 - n_new.sum()
        n_new[0] = add; e_new[0] = add * sales[i]
        n, e = n_new, e_new
        out.append(e.sum() / n.sum())
    return np.array(out)


def ramp(target, start, full):
    return np.array([0.0 if y < start else target * min(1.0, (y - start + 1) / (full - start + 1)) for y in YEARS])


def load():
    R = json.load(open(OUT / "results.json"))["central"]
    S = {c["case"]: c for c in json.load(open(OUT / "self_reliance.json"))["cases"]}
    return R, S


def end_state_shares(R):
    d, u = R["demand_twh"], R["end_use_twh"]
    off = {"farm": 30.0 / 75.05555555555556, "mine": 27.8 / 75.05555555555556, "con": 17.3 / 75.05555555555556}
    dem = {"ldv": d["ldv_gasoline"] + d["ldv_diesel"], "hdv": d["hdv"], "rail": d["rail"],
           "farm": d["offroad"] * off["farm"], "mine": d["offroad"] * off["mine"], "con": d["offroad"] * off["con"],
           "aviation": d["aviation"], "shipping": d["shipping"]}
    on_wire = 0.90
    el = {"ldv": 1.0, "hdv": (u["hdv|bet"] + on_wire * u["hdv|ers"]) / d["hdv"], "rail": u["rail|el"] / d["rail"],
          "farm": u["offroad|farm_el"] / dem["farm"], "mine": u["offroad|mine_el"] / dem["mine"],
          "con": u["offroad|con_el"] / dem["con"], "aviation": 0.0, "shipping": 0.0}
    return dem, el


def fleet(R, path="central"):
    dem, el = end_state_shares(R)
    share = {}
    for seg, a in ASSUME["segments"].items():
        sales = sales_path(el[seg], a["sales_now"], a["t95"][path])
        share[seg] = stock_share(sales, a["life"], a["shape"], a["stock_now"])
    share["aviation"] = np.zeros(len(YEARS)); share["shipping"] = np.zeros(len(YEARS))
    liquid = {s: dem[s] * (1 - share[s]) for s in dem}
    gasoline = R["demand_twh"]["ldv_gasoline"] * (1 - share["ldv"])
    return dem, el, share, liquid, gasoline


def factors(R):
    lc = R["lifecycle"]; f = R["fuels_twh"]; p = lc["parts_mtco2e"]
    fossil = lc["fossil_wtw_mtco2e"] / R["demand_total_twh"]
    kelp = p["Kelp fuels"] / (f["kelp HTL diesel/jet"] + f["kelp biomethane (net of fleet)"])
    resid = p["Residue and lake fuels"] / (f["forest_residue_HTL"] + f["agri_residue_FT"] + f["lake HTL diesel/jet"] + f["lake biomethane (net of fleet)"])
    crop = p["Crop and waste biofuels"] / (f["waste_biomethane"] + f["HEFA_waste_lipids"] + f["canola_HVO"] + f["grain_ethanol_existing"])
    efuel = p["Electrofuels"] / f["eFT_liquids"]
    electric = p["Direct electric transport"] / (R["demand_total_twh"] - R["dropin_supply_twh"]) if R.get("dropin_supply_twh") else 0.0045
    return dict(fossil=fossil, kelp=kelp, residues=resid, lake=resid, existing=crop, efuels=efuel, electric=electric)


def supplies(R, S, kelp_case="Electric or biofuel only"):
    cen = S["All routes (central case)"]; kc = S[kelp_case]
    ex = S["Electric or biofuel only"]["existing_biofuels_twh"]          # 35 TWh of existing biofuel feedstocks
    out = {
        "existing": ramp(ex, *ASSUME["ramp_existing"]),
        "residues": ramp(cen["residues_twh"], *ASSUME["ramp_residues"]),
        "lake": ramp(cen["lake_fuel_twh"], *ASSUME["ramp_lake"]),
        "efuels": ramp(cen["efuels_twh"], *ASSUME["ramp_efuels"]),
    }
    twh_per_km2 = kc["kelp_hc_twh"] / kc["kelp_km2"]
    area = np.array([0.0 if y < ASSUME["kelp_start"] else min(kc["kelp_km2"], ASSUME["kelp_build_km2_a"] * (y - ASSUME["kelp_start"] + 1)) for y in YEARS])
    yld = np.where(YEARS < ASSUME["kelp_learning_year"], ASSUME["kelp_design_to_learned"], 1.0)
    out["kelp"] = area * twh_per_km2 * yld
    out["kelp_area_km2"] = area
    return out


SCEN = {
    "Electrification only": [],
    "+ existing biofuels, residues, lake biomass": ["existing", "residues", "lake"],
    "+ … and electrofuels (no kelp)": ["existing", "residues", "lake", "efuels"],
    "+ … and kelp (no electrofuels)": ["existing", "residues", "lake", "kelp"],
    "+ … kelp and electrofuels": ["existing", "residues", "lake", "kelp", "efuels"],
}


def ethanol_cap(gasoline, ffv, conv):
    """Ethanol the gasoline fleet can take: E10 in ordinary cars, E85 (annual-average ethanol energy share) in
    flexible-fuel and converted cars."""
    f85 = np.minimum(1.0, ffv + conv)
    return gasoline * ((1 - f85) * ASSUME["e10_energy_share"] + f85 * ASSUME["e85_energy_share"])


def conversion_path(level, start=2027, full=2035):
    """Share of the gasoline combustion stock converted to E85 with an aftermarket kit."""
    return np.array([0.0 if y < start else level * min(1.0, (y - start + 1) / (full - start + 1)) for y in YEARS])


def account(R, S, path="central", kelp_case="Electric or biofuel only", ffv_policy=False, conv_level=None):
    dem, el, share, liquid, gasoline = fleet(R, path)
    F = factors(R); sup = supplies(R, S, kelp_case)
    L = sum(liquid.values()); elec = sum(dem.values()) - L
    G = gasoline; N = L - G                     # gasoline pool and diesel/jet/other pool
    ffv = np.full(len(YEARS), ASSUME["ffv_share_now"])
    if ffv_policy:   # every new light-duty ICE vehicle flexible-fuel capable from 2028
        ldv = ASSUME["segments"]["ldv"]
        ffv = stock_share(np.where(YEARS >= 2028, 1.0, ASSUME["ffv_share_now"]), ldv["life"], ldv["shape"], ASSUME["ffv_share_now"])
    conv = conversion_path(conv_level) if conv_level else np.zeros(len(YEARS))
    ecap = ethanol_cap(G, ffv, conv)
    eh_eth = ASSUME["kelp_eh_ethanol_share"]
    res = {}
    for name, keys in SCEN.items():
        used = {}; roomN = N.copy(); roomE = ecap.copy()
        for k in keys:
            q = sup[k].copy()
            if k == "existing":                       # 12 TWh grain ethanol to the gasoline pool, the rest drop-in
                eth = np.minimum(np.minimum(q, ASSUME["grain_ethanol_twh"]), roomE); roomE -= eth
                dro = np.minimum(np.maximum(q - ASSUME["grain_ethanol_twh"], 0), roomN); roomN -= dro
                used[k] = eth + dro; used["ethanol_grain"] = eth
            elif k == "kelp" and conv_level:          # kelp ethanol (route EH) wherever converted cars can take it
                eth = np.minimum(eh_eth * q, roomE); roomE -= eth
                hc = np.minimum(q - eth, roomN); roomN -= hc
                used[k] = eth + hc; used["kelp_ethanol"] = eth
            else:
                d = np.minimum(q, roomN); roomN -= d; used[k] = d
        fossil = roomN + (G - (ecap - roomE))      # unfilled diesel/jet pool plus gasoline not displaced by ethanol
        em = fossil * F["fossil"] + elec * F["electric"] + sum(used[k] * F[k] for k in used if k in F)
        y = (YEARS >= 2027)
        res[name] = dict(fossil_twh=fossil.tolist(), used_twh={k: v.tolist() for k, v in used.items()}, emissions_mt=em.tolist(),
                         cumulative_2027_2050_mt=float(em[y].sum()))
    base = res["Electrification only"]["cumulative_2027_2050_mt"]
    for v in res.values():
        v["avoided_vs_electrification_only_mt"] = base - v["cumulative_2027_2050_mt"]
    return dict(path=path, liquid_twh=L.tolist(), electric_twh=elec.tolist(), gasoline_ice_twh=G.tolist(), dropin_pool_twh=N.tolist(),
                liquid_by_segment={k: v.tolist() for k, v in liquid.items()}, stock_electric_share={k: v.tolist() for k, v in share.items()},
                ethanol_cap_twh=ecap.tolist(), converted_share=conv.tolist(), supply_twh={k: v.tolist() for k, v in sup.items()},
                factors=F, scenarios=res)


def machines():
    A = ASSUME; out = []
    for name, m in A["machines"].items():
        diesel_kwh = m["litres_day"] * A["diesel_kwh_l"]
        work = diesel_kwh * A["eta_diesel"]
        batt = work / A["eta_electric"] * A["winter_margin"]
        mass = [batt / d / 1000 for d in A["pack_kwh_kg"][::-1]]
        diesel_mass = m["litres_day"] * 0.835 / 1000
        out.append(dict(machine=name, diesel_l_day=m["litres_day"], battery_kwh=batt, battery_t=mass, diesel_t=diesel_mass,
                        mass_ratio=[x / diesel_mass for x in mass]))
    return out


def ethanol_kelp(S):
    """Ethanol that kelp could supply through the ethanol + residue-HTL route (EH) on the electric-or-biofuel area."""
    b = json.load(open(OUT / "biorefinery_per_dry_tonne.json"))["routes"]["EH"]
    kc = S["Electric or biofuel only"]
    return dict(kelp_km2=kc["kelp_km2"], kelp_dry_mt=kc["kelp_dry_mt"],
                ethanol_twh=kc["kelp_dry_mt"] * 1e6 * b["ethanol_gj"] / 3.6e6, hc_twh=kc["kelp_dry_mt"] * 1e6 * b["hc_gj"] / 3.6e6)


def main():
    R, S = load()
    res = {"assumptions": ASSUME, "years": YEARS.tolist()}
    for path in ("central", "fast", "slow"):
        res[path] = account(R, S, path)
    res["central_strict_kelp"] = account(R, S, "central", kelp_case="Electrification, seaweed and existing biofuels only")
    res["central_ffv_policy"] = account(R, S, "central", ffv_policy=True)
    res["machines"] = machines()
    res["kelp_ethanol"] = ethanol_kelp(S)
    c = res["central"]; y = YEARS
    i30, i35, i40, i50 = (int(np.where(y == t)[0][0]) for t in (2030, 2035, 2040, 2050))
    sc = c["scenarios"]
    nonkelp = np.array(c["supply_twh"]["existing"]) + np.array(c["supply_twh"]["residues"]) + np.array(c["supply_twh"]["lake"])
    res["summary"] = dict(
        liquid_twh={str(t): c["liquid_twh"][i] for t, i in ((2030, i30), (2035, i35), (2040, i40), (2050, i50))},
        endstate_liquid_twh=c["liquid_twh"][-1],
        nonkelp_biofuel_2040_twh=float(nonkelp[i40]),
        liquid_minus_nonkelp_min_twh=float(np.min(np.array(c["liquid_twh"]) - nonkelp)),
        cumulative_mt={k: v["cumulative_2027_2050_mt"] for k, v in sc.items()},
        avoided_mt={k: v["avoided_vs_electrification_only_mt"] for k, v in sc.items()},
        kelp_added_avoided_mt=sc["+ … and kelp (no electrofuels)"]["avoided_vs_electrification_only_mt"] - sc["+ existing biofuels, residues, lake biomass"]["avoided_vs_electrification_only_mt"],
        kelp_added_with_efuels_mt=sc["+ … kelp and electrofuels"]["avoided_vs_electrification_only_mt"] - sc["+ … and electrofuels (no kelp)"]["avoided_vs_electrification_only_mt"],
        kelp_twh_2040=c["supply_twh"]["kelp"][i40], kelp_used_2040=sc["+ … and kelp (no electrofuels)"]["used_twh"]["kelp"][i40],
        kelp_area_2040=c["supply_twh"]["kelp_area_km2"][i40],
        by_path={p: dict(kelp_added_avoided_mt=res[p]["scenarios"]["+ … and kelp (no electrofuels)"]["avoided_vs_electrification_only_mt"] - res[p]["scenarios"]["+ existing biofuels, residues, lake biomass"]["avoided_vs_electrification_only_mt"],
                         liquid_2035=res[p]["liquid_twh"][i35]) for p in ("central", "fast", "slow")},
        strict_kelp_added_avoided_mt=res["central_strict_kelp"]["scenarios"]["+ … and kelp (no electrofuels)"]["avoided_vs_electrification_only_mt"] - res["central_strict_kelp"]["scenarios"]["+ existing biofuels, residues, lake biomass"]["avoided_vs_electrification_only_mt"],
        ethanol_cap_2030={"E10 only": c["ethanol_cap_twh"][i30], "FFV policy": res["central_ffv_policy"]["ethanol_cap_twh"][i30]},
        ethanol_cap_2035={"E10 only": c["ethanol_cap_twh"][i35], "FFV policy": res["central_ffv_policy"]["ethanol_cap_twh"][i35]},
    )
    for lvl, v in ASSUME["conversion_levels"].items():
        res[f"central_conversion_{lvl}"] = account(R, S, "central", conv_level=v)
    cc = res["central_conversion_central"]
    hk = "+ … and kelp (no electrofuels)"; nk = "+ existing biofuels, residues, lake biomass"
    res["summary"]["conversion"] = dict(
        ethanol_cap={str(t): cc["ethanol_cap_twh"][int(np.where(y == t)[0][0])] for t in (2030, 2035, 2040)},
        kelp_ethanol_used={str(t): cc["scenarios"][hk]["used_twh"].get("kelp_ethanol", [0] * len(y))[int(np.where(y == t)[0][0])] for t in (2035, 2040, 2045)},
        kelp_added_avoided_mt={lvl: res[f"central_conversion_{lvl}"]["scenarios"][hk]["avoided_vs_electrification_only_mt"] - res[f"central_conversion_{lvl}"]["scenarios"][nk]["avoided_vs_electrification_only_mt"] for lvl in ASSUME["conversion_levels"]},
        all_avoided_mt={lvl: res[f"central_conversion_{lvl}"]["scenarios"]["+ … kelp and electrofuels"]["avoided_vs_electrification_only_mt"] for lvl in ASSUME["conversion_levels"]},
        cumulative_mt={k: v["cumulative_2027_2050_mt"] for k, v in cc["scenarios"].items()},
        # added ethanol market opened by conversion (beyond E10), 2027-2050, and the emissions it could avoid if filled
        # with low-carbon ethanol at the kelp factor; conditional on that ethanol being produced
        added_ethanol_twh_2027_2050={lvl: float(sum(np.array(res[f"central_conversion_{lvl}"]["ethanol_cap_twh"])[y >= 2027]
                                                    - np.array(res["central"]["ethanol_cap_twh"])[y >= 2027])) for lvl in ASSUME["conversion_levels"]},
        potential_avoided_if_filled_mt={lvl: float(sum((np.array(res[f"central_conversion_{lvl}"]["ethanol_cap_twh"])[y >= 2027]
                                                        - np.array(res["central"]["ethanol_cap_twh"])[y >= 2027]))
                                                   * (res["central"]["factors"]["fossil"] - res["central"]["factors"]["kelp"]))
                                        for lvl in ASSUME["conversion_levels"]})
    json.dump(res, open(OUT / "transition.json", "w"), indent=1, default=float)
    print(json.dumps(res["summary"], indent=1, default=float))
    print(json.dumps(res["machines"], indent=1, default=float))
    print(json.dumps(res["kelp_ethanol"], indent=1, default=float), json.dumps(c["factors"], default=float))




def figure():
    import matplotlib.pyplot as plt
    from figstyle import C, INK2, MUTED, MM, save, record, dump_source, vgrid
    T = json.load(open(OUT / "transition.json")); y = np.array(T["years"]); c = T["central"]
    fig, axs = plt.subplots(2, 2, figsize=(180 * MM, 120 * MM)); axs = axs.ravel()
    ax = axs[0]
    segs = [("ldv", "Cars and light trucks", C["blue"]), ("hdv", "Trucks and buses", C["orange"]),
            ("farm", "Farm machinery", C["green"]), ("mine", "Mining machinery", C["yellow"]),
            ("con", "Construction and forestry", C["magenta"]), ("rail", "Rail", C["violet"]),
            ("aviation", "Aviation", C["aqua"]), ("shipping", "Shipping", MUTED)]
    ax.stackplot(y, [c["liquid_by_segment"][k] for k, _, _ in segs], colors=[col for _, _, col in segs],
                 labels=[lab for _, lab, _ in segs], alpha=0.85, lw=0)
    for p, ls in (("fast", "--"), ("slow", ":")):
        ax.plot(y, T[p]["liquid_twh"], color="#0b0b0b", lw=0.9, ls=ls, label=f"Total, {p} electrification")
    ax.set_xlim(2025, 2050); ax.set_ylim(0, 1250); ax.set_ylabel("Liquid and gaseous fuel demand (TWh/a)")
    ax.legend(fontsize=5.2, ncol=2, loc="upper right"); ax.set_title("A  Fuel still needed while the fleet turns over"); vgrid(ax)
    record("Fig10", "A_liquid_demand", ["year"] + [lab for _, lab, _ in segs] + ["total fast", "total slow"],
           [[int(y[i])] + [c["liquid_by_segment"][k][i] for k, _, _ in segs] + [T["fast"]["liquid_twh"][i], T["slow"]["liquid_twh"][i]] for i in range(len(y))])
    ax = axs[1]
    sc = c["scenarios"]["+ … kelp and electrofuels"]; u = sc["used_twh"]
    parts = [("existing", "Existing biofuels", C["yellow"]), ("residues", "Forest and farm residues", C["green"]),
             ("lake", "Lake biomass", C["aqua"]), ("kelp", "Kelp", C["blue"]), ("efuels", "Electrofuels", C["violet"])]
    ax.stackplot(y, [u[k] for k, _, _ in parts] + [sc["fossil_twh"]], colors=[col for _, _, col in parts] + ["#d9d8d4"],
                 labels=[lab for _, lab, _ in parts] + ["Fossil fuel remaining"], lw=0)
    ax.set_xlim(2025, 2050); ax.set_ylim(0, 1100); ax.set_ylabel("Fuel supplied (TWh/a)")
    ax.legend(fontsize=5.2, loc="upper right", ncol=2); ax.set_title("B  Who supplies it (all biofuel routes)"); vgrid(ax)
    record("Fig10", "B_supply", ["year"] + [lab for _, lab, _ in parts] + ["fossil remaining"],
           [[int(y[i])] + [u[k][i] for k, _, _ in parts] + [sc["fossil_twh"][i]] for i in range(len(y))])
    ax = axs[2]
    lines = [("Electrification only", "#0b0b0b", "-"), ("+ existing biofuels, residues, lake biomass", C["green"], "-"),
             ("+ … and electrofuels (no kelp)", C["violet"], "--"), ("+ … and kelp (no electrofuels)", C["blue"], "-"),
             ("+ … kelp and electrofuels", C["orange"], "-")]
    rows = []
    for name, col, ls in lines:
        e = c["scenarios"][name]["emissions_mt"]
        ax.plot(y, e, color=col, ls=ls, lw=1.1, label=f"{name} ({c['scenarios'][name]['cumulative_2027_2050_mt']:,.0f} Mt)")
        rows.append([name] + list(e))
    ax.set_xlim(2025, 2050); ax.set_ylim(0, 290); ax.set_ylabel("Transport well-to-wheel emissions (Mt CO₂e/a)")
    ax.legend(fontsize=5.0, loc="lower left", title="cumulative 2027–2050", title_fontsize=5.0); ax.set_title("C  Emissions on the way"); vgrid(ax)
    record("Fig10", "C_emissions", ["scenario"] + [int(v) for v in y], rows)
    ax = axs[3]
    M = T["machines"]
    names = [m["machine"].replace(", ", "\n") for m in M]
    lo = [m["battery_t"][0] for m in M]; hi = [m["battery_t"][1] for m in M]; dm = [m["diesel_t"] for m in M]
    xx = np.arange(len(M))
    ax.bar(xx - 0.18, dm, width=0.34, color=C["yellow"], label="Diesel for the same day's work")
    ax.bar(xx + 0.18, hi, width=0.34, color=C["blue"], alpha=0.35, label="Battery, 0.14 kWh/kg pack")
    ax.bar(xx + 0.18, lo, width=0.34, color=C["blue"], label="Battery, 0.18 kWh/kg pack")
    for i, m in enumerate(M):
        ax.text(xx[i] + 0.18, hi[i] * 1.15, f"{m['battery_kwh']:,.0f} kWh", ha="center", fontsize=5.4, color=INK2)
    ax.set_yscale("log"); ax.set_ylim(0.1, 300); ax.set_xticks(xx); ax.set_xticklabels(names, fontsize=5.6)
    ax.set_ylabel("Mass carried for one working day (t)"); ax.legend(fontsize=5.2, loc="upper left")
    ax.set_title("D  Energy carried by heavy machines")
    record("Fig10", "D_heavy_machines", ["machine", "diesel L/day", "battery kWh", "battery t (0.18 kWh/kg)", "battery t (0.14 kWh/kg)", "diesel t"],
           [[m["machine"], m["diesel_l_day"], m["battery_kwh"], m["battery_t"][0], m["battery_t"][1], m["diesel_t"]] for m in M])
    fig.tight_layout(w_pad=1.6, h_pad=1.6)
    save(fig, "Fig10_transition"); dump_source("Fig10")



if __name__ == "__main__":
    main()
    figure()
