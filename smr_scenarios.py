"""SMR cogeneration and regional heat-pool scenarios on the national transport-energy model.

Central case: current federal law (the 15% clean-electricity ITC applies only to property available for use before
2035, so modules in the 2050 system receive no credit). The LP optimum is a continuous relaxation; whole-module results
come from enumerating fixed module counts in each regional fleet.
"""
import copy
import itertools
import json

import numpy as np

import optimise as O
import scenarios as sc

MOD = 0.3   # GW per module
SITE_COMMON_BN = 1.6     # common infrastructure per new site (Darlington: CAD 1.6 bn), sites of up to two modules
PER_SITE = 2


def site_cost_bn(n_atl, n_inl, itc=0.0, common=SITE_COMMON_BN, r=0.04, life=40):
    """Annualized common-infrastructure cost of the new sites a whole-module fleet needs (CAD bn per year)."""
    sites = -(-n_atl // PER_SITE) + -(-n_inl // PER_SITE)
    return sites * common * (1 - itc) * r * (1 + r) ** life / ((1 + r) ** life - 1)


def S(smr=None, fleets=None, **ov):
    p = sc.build_case(demand=False, overrides=ov)
    if smr: p["smr"].update(smr)
    for k, v in (fleets or {}).items(): p["smr"]["fleets"][k].update(v)
    return p


def fixed(n_atl, n_inl, **kw):
    fl = {"atl": dict(min_gw=n_atl * MOD, cap_gw=n_atl * MOD), "inl": dict(min_gw=n_inl * MOD, cap_gw=n_inl * MOD)}
    fl.update(kw.pop("fleets", {}))
    return S(fleets=fl, **kw)


def fl(v):
    return float(v) if isinstance(v, (np.floating, np.integer)) else v


def row(label, r, base=None):
    k = r["kelp_km2"]
    reg = lambda pre: sum(v for z, v in k.items() if z.startswith(pre))
    f = r["smr"]["by_fleet"]
    d = dict(case=label, total_cost_bn=r["total_cost_bn"], delta_bn=(r["total_cost_bn"] - base) if base is not None else 0.0,
             smr_gw=r["smr"]["gw"], smr_modules=r["smr"]["modules"], smr_lcoe=r["smr"]["lcoe_cad_mwh"],
             atl_gw=f["atl"]["gw"], inl_gw=f["inl"]["gw"], pac_gw=f["pac"]["gw"], hb_gw=f["hb"]["gw"],
             steam_atl_twh=f["atl"]["steam_twh"], steam_inl_twh=f["inl"]["steam_twh"], steam_pac_twh=f["pac"]["steam_twh"],
             steam_hb_twh=f["hb"]["steam_twh"], smr_steam_twh=r["smr"]["steam_twh"],
             smr_net_twh=r["smr"]["direct_twh"] + r["smr"]["flex_twh"],
             kelp_km2=r["kelp_total_km2"], kelp_pacific_km2=reg("pac"), kelp_atlantic_km2=reg("atl") + reg("gsl") + reg("lab"),
             kelp_hb_km2=reg("hb"), wind_twh=r["generation_twh"]["Onshore wind"], pv_twh=r["generation_twh"]["PV"],
             heat=r["heat_by_pool_twh_th"], ethanol_heat_twh=r["ethanol_distillation_heat_twh_th"],
             reduction_pct=r["lifecycle"]["reduction_pct"])
    return json.loads(json.dumps(d, default=fl))


def best_integer(max_atl=4, max_inl=3, common=SITE_COMMON_BN, **kw):
    grid = []
    itc = kw.get("smr", {}).get("itc", 0.0)
    for a, b in itertools.product(range(max_atl + 1), range(max_inl + 1)):
        r = O.solve(fixed(a, b, **copy.deepcopy(kw)))
        sc_ = site_cost_bn(a, b, itc, common)
        grid.append(dict(atl=a, inl=b, modules=a + b, cost_lp=r["total_cost_bn"], site_cost_bn=sc_, cost=r["total_cost_bn"] + sc_,
                         steam_atl=float(r["smr"]["by_fleet"]["atl"]["steam_twh"]), steam_inl=float(r["smr"]["by_fleet"]["inl"]["steam_twh"])))
    best = min(grid, key=lambda g: g["cost"])
    return best, grid


def breakeven(builder, ref_cost, lo=0.1, hi=8.0, n=24, extra=0.0):
    """Largest module capital cost (CAD bn) at which the configuration (plus a fixed site cost) costs no more than the reference."""
    for _ in range(n):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if O.solve(builder(m))["total_cost_bn"] + extra <= ref_cost + 1e-7 else (lo, m)
    return lo


def run():
    out = []
    base = O.solve(S(smr=dict(enabled=False)))
    b0 = base["total_cost_bn"]
    out.append(row("No SMR (wind, solar and hydro only)", base, b0))
    cases = [
        ("Central: current law (no ITC after 2034), CAD 4.4 bn/module, 4%", S()),
        ("ITC extended beyond 2034 (15%)", S(smr=dict(itc=0.15))),
        ("CAD 3.5 bn/module (fleet learning)", S(smr=dict(capex_bn=3.5))),
        ("CAD 3.5 bn/module and ITC extended", S(smr=dict(capex_bn=3.5, itc=0.15))),
        ("CAD 6.1 bn/module (first of a kind)", S(smr=dict(capex_bn=6.1))),
        ("Financed at 7%", S(smr=dict(r=0.07))),
        ("Financed at 3% (public)", S(smr=dict(r=0.03))),
        ("All distilleries beside a module (co-location 100%)", S(smr=dict(ethanol_colocated_share=1.0))),
        ("All distilleries beside a module, ITC extended", S(smr=dict(ethanol_colocated_share=1.0, itc=0.15))),
        ("No distillery co-location (0%), ITC extended", S(smr=dict(ethanol_colocated_share=0.0, itc=0.15))),
        ("Forced fleet 10 modules (4 Atlantic, 6 inland)", S(fleets={"atl": dict(min_gw=1.2), "inl": dict(min_gw=1.8)})),
        ("Forced fleet 20 modules (8 Atlantic, 12 inland)", S(fleets={"atl": dict(min_gw=2.4), "inl": dict(min_gw=3.6)})),
        ("Forced fleet 40 modules (10 Atlantic, 30 inland)", S(fleets={"atl": dict(min_gw=3.0), "inl": dict(min_gw=9.0)})),
        ("BC fleet allowed (SMR steam for Pacific refineries), ITC extended", S(smr=dict(itc=0.15), fleets={"pac": dict(cap_gw=3.0)})),
        ("BC fleet allowed, CAD 3.5 bn/module and ITC", S(smr=dict(itc=0.15, capex_bn=3.5), fleets={"pac": dict(cap_gw=3.0)})),
        ("Electric boilers only (no storage, no heat pumps)", S(eb_only=True)),
    ]
    res = {}
    SITES_OF = {"Forced fleet 10 modules (4 Atlantic, 6 inland)": (4, 6), "Forced fleet 20 modules (8 Atlantic, 12 inland)": (8, 12),
                "Forced fleet 40 modules (10 Atlantic, 30 inland)": (10, 30)}
    for lab, p in cases:
        r = O.solve(p); res[lab] = r; rw = row(lab, r, b0)
        if lab in SITES_OF:
            rw["site_cost_bn"] = site_cost_bn(*SITES_OF[lab]); rw["total_with_sites_bn"] = rw["total_cost_bn"] + rw["site_cost_bn"]
            rw["delta_with_sites_bn"] = rw["total_with_sites_bn"] - b0
        out.append(rw)
    for lab, p in (("Transition (demand levers), no SMR", sc.build_case(overrides={"smr": {**O.base_params()["smr"], "enabled": False}})),
                   ("Transition (demand levers), SMR option", sc.build_case()),
                   ("Today's costs, 7%, no SMR", sc.build_case(learning=False, capital=False, demand=False,
                                                              overrides={"smr": {**O.base_params()["smr"], "enabled": False}})),
                   ("Today's costs, 7%, SMR option", sc.build_case(learning=False, capital=False, demand=False))):
        out.append(row(lab, O.solve(p)))
    # whole modules
    integer = {}
    for lab, kw, common in (("current_law", {}, SITE_COMMON_BN), ("itc_extended", dict(smr=dict(itc=0.15)), SITE_COMMON_BN),
                            ("capex_3p5", dict(smr=dict(capex_bn=3.5)), SITE_COMMON_BN),
                            ("capex_3p5_itc", dict(smr=dict(capex_bn=3.5, itc=0.15)), SITE_COMMON_BN),
                            ("itc_extended_no_site_cost", dict(smr=dict(itc=0.15)), 0.0),
                            ("capex_3p5_itc_site_0p8", dict(smr=dict(capex_bn=3.5, itc=0.15)), 0.8)):
        best, grid = best_integer(common=common, **kw)
        relax = O.solve(S(**copy.deepcopy(kw)))
        integer[lab] = dict(best=best, grid=grid, relaxed_cost=relax["total_cost_bn"], relaxed_modules=float(relax["smr"]["modules"]),
                            relaxed_atl=float(relax["smr"]["by_fleet"]["atl"]["modules"]), relaxed_inl=float(relax["smr"]["by_fleet"]["inl"]["modules"]),
                            saving_best_bn=b0 - best["cost"], saving_relaxed_bn=b0 - relax["total_cost_bn"])
    # capital-cost sweep (relaxed and whole-module optimum), with and without the ITC
    sweep = []
    for itc in (0.0, 0.15):
        for cap in (2.0, 2.5, 3.0, 3.5, 4.0, 4.4, 5.0, 6.1):
            r = O.solve(S(smr=dict(capex_bn=cap, itc=itc)))
            sweep.append(dict(itc=itc, capex_bn=cap, lcoe=r["smr"]["lcoe_cad_mwh"], gw=float(r["smr"]["gw"]),
                              atl_gw=float(r["smr"]["by_fleet"]["atl"]["gw"]), inl_gw=float(r["smr"]["by_fleet"]["inl"]["gw"]),
                              steam=float(r["smr"]["steam_twh"]), cost=r["total_cost_bn"], saving_vs_nosmr=b0 - r["total_cost_bn"]))
    # break-even capital (no ITC unless stated)
    be = {   # module capital at break-even, with CAD 1.6 bn common infrastructure per site of up to two modules
        "one_atlantic_module": breakeven(lambda m: fixed(1, 0, smr=dict(capex_bn=m)), b0, extra=site_cost_bn(1, 0)),
        "two_atlantic_modules": breakeven(lambda m: fixed(2, 0, smr=dict(capex_bn=m)), b0, extra=site_cost_bn(2, 0)),
        "two_atlantic_modules_itc": breakeven(lambda m: fixed(2, 0, smr=dict(capex_bn=m, itc=0.15)), b0, extra=site_cost_bn(2, 0, 0.15)),
        "one_atlantic_module_no_site_cost": breakeven(lambda m: fixed(1, 0, smr=dict(capex_bn=m)), b0),
        "10_modules": breakeven(lambda m: S(smr=dict(capex_bn=m), fleets={"atl": dict(min_gw=1.2), "inl": dict(min_gw=1.8)}), b0,
                                extra=site_cost_bn(4, 6)),
        "40_modules": breakeven(lambda m: S(smr=dict(capex_bn=m), fleets={"atl": dict(min_gw=3.0), "inl": dict(min_gw=9.0)}), b0,
                                extra=site_cost_bn(10, 30)),
    }
    # forced northern and Gulf kelp, without and with nuclear steam in that region
    forced = []
    for reg in ("gsl", "lab", "hb"):
        for lab, kw in (("no SMR", dict(smr=dict(enabled=False))), ("SMR option (current law)", {}),
                        ("SMR CAD 3.5 bn with ITC, Hudson Bay fleet allowed", dict(smr=dict(capex_bn=3.5, itc=0.15), fleets={"hb": dict(cap_gw=1.2)}))):
            ref = O.solve(S(**copy.deepcopy(kw)))["total_cost_bn"]
            q = O.solve(S(kelp_min_km2={reg: 2000.0}, **copy.deepcopy(kw)))
            forced.append(dict(region=reg, smr=lab, extra_cost_bn=q["total_cost_bn"] - ref, total_cost_bn=q["total_cost_bn"],
                               smr_steam_twh=float(q["smr"]["steam_twh"]), hb_steam_twh=float(q["smr"]["by_fleet"]["hb"]["steam_twh"])))
    return dict(rows=out, integer=integer, sweep=sweep, breakeven_capex_bn=be, forced=forced, no_smr=base,
                central=res["Central: current law (no ITC after 2034), CAD 4.4 bn/module, 4%"],
                itc=res["ITC extended beyond 2034 (15%)"])


if __name__ == "__main__":
    R = run()
    for r in R["rows"]:
        print(f'{r["case"][:62]:62s} {r["total_cost_bn"]:7.3f} {r["delta_bn"]:+7.3f} atl {r["atl_gw"]:4.2f} inl {r["inl_gw"]:4.2f} '
              f'pac {r["pac_gw"]:4.2f} steam {r["smr_steam_twh"]:5.2f}  kelp P{r["kelp_pacific_km2"]:6.0f} A{r["kelp_atlantic_km2"]:6.0f}')
    for k, v in R["integer"].items():
        print(k, v["best"], round(v["relaxed_modules"], 2), round(v["saving_relaxed_bn"], 4), round(v["saving_best_bn"], 4))
    print({k: round(v, 2) for k, v in R["breakeven_capex_bn"].items()})
    for f in R["forced"]: print(f)
    json.dump({k: R[k] for k in ("rows", "integer", "sweep", "breakeven_capex_bn", "forced")}, open("outputs/smr_scenarios.json", "w"),
              indent=1, default=fl)
    json.dump(R["central"], open("outputs/central_smr.json", "w"), indent=1, default=fl)
    json.dump(R["itc"], open("outputs/central_smr_itc_extended.json", "w"), indent=1, default=fl)
    json.dump(R["no_smr"], open("outputs/central_no_smr.json", "w"), indent=1, default=fl)
