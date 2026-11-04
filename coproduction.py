"""Marine co-production on the national kelp farms: Grid Harvester fleet and energy, shellfish co-culture, salmon
co-location (integrated multi-trophic aquaculture), solar utility drones, multifunction ROVs and battery-electric
service rafts.

These accounts sit OUTSIDE the transport-energy linear programme: no food revenue, nitrogen credit or robot saving is
used to lower the cost of transport energy. They test whether the marine platform the fuel system builds can also carry
food production and robotic farm care, and at what margin. All parameters are screening assumptions listed in PARAMS;
the shellfish, ROV and salmon blocks reuse the parameters of the marine screen and the salmon/laser model supplied with
the earlier Canadian study.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"

PARAMS = {
    "grid_harvester": {"cycle_m2": 14400.0, "cycle_mj": 33.9, "conventional_cycle_mj": 90.9, "unit_capex_cad_m": 6.0,
                       "missed_area_pct_grid": 0.62, "missed_area_pct_conventional": 1.49},
    # shellfish co-culture: one 1 km2 block (8 ha mussel longlines + 4 ha oyster trays) per site, inside the kelp lease
    "shellfish": {"km2_kelp_per_site": 25.0, "nearshore_band": "0-50",
                  "chemistry_pass": {"pac": 0.50, "atl": 0.80},          # share of sites passing DO >= 5 mg/L and Omega_ar >= 1.5
                  "mussel_t_site": 48.0, "oyster_t_site": 24.0, "sales_cad_site": 280800.0,
                  "nonharvest_opex_cad_site": 247200.0, "manual_harvest_cad_site": 21600.0,
                  "robot_variable_cad_site": 4080.0, "robot_fixed_cad_site": 57568.47, "shared_kelp_lease_saving_cad_site": 60000.0},
    # salmon: reference 50,000 t/yr block (parameters of the earlier salmon and laser-delousing model, road freight); Atlantic open-net pens in kelp leases,
    # British Columbia closed containment (open-net pens prohibited in BC coastal waters from 30 June 2029)
    "salmon": {"block_t": 50000.0, "price_cad_kg": [6.0, 8.0, 10.0], "revenue_cad_m_at_6": 300.0, "feed_cad_m": 105.0,
               "pen_cad_m": 35.46, "hatchery_cad_m": 37.5, "robots": 1544, "robot_cad_m": 25.20, "other_cad_m": 60.0,
               "freight_cad_m": 9.36, "laser_capex_cad": 15000.0, "laser_years": 5, "laser_om_cad": 1500.0, "rate": 0.08,
               "closed_containment_premium_cad_kg": [1.0, 2.0, 3.0], "n_released_t": 690.0, "kelp_n_fraction": 0.02,
               "edible_t": 35000.0, "edible_protein_t": 7000.0},
    # utility drones: solar-charged underwater drones for spot inspection and reseeding (2 per km2), shared ROVs at
    # shellfish sites for kelp care, battery-electric service rafts
    "drones": {"per_km2": 2.0, "kwh_day": 0.4, "capex_cad": 12000.0, "life": 6, "om_cad": 800.0, "rate": 0.06,
               "bare_spot_share": 0.05, "detection": 0.85, "reseed_cad_km2": 250000.0,
               "rov_break_even_diver_days": 47.5, "raft_km2": 400.0, "raft_kwh_day": 600.0},
}


def crf(r, n):
    return r * (1 + r) ** n / ((1 + r) ** n - 1)


def grid_harvester(s, fleet):
    p = PARAMS["grid_harvester"]
    area_pass = fleet["area_pass_km2_per_year"]
    cycles = area_pass * 1e6 / p["cycle_m2"]
    return dict(units=fleet["engineering_units"], area_pass_km2=area_pass,
                energy_gwh=cycles * p["cycle_mj"] / 3.6e6, conventional_energy_gwh=cycles * p["conventional_cycle_mj"] / 3.6e6,
                saving_gwh=cycles * (p["conventional_cycle_mj"] - p["cycle_mj"]) / 3.6e6,
                capex_cad_bn=fleet["engineering_units"] * p["unit_capex_cad_m"] / 1e3,
                missed_area_km2=area_pass * p["missed_area_pct_grid"] / 100,
                missed_area_conventional_km2=area_pass * p["missed_area_pct_conventional"] / 100)


def shellfish(s):
    p = PARAMS["shellfish"]
    zb = s["kelp_by_zone_band_km2"]
    out = {}
    for reg in ("pac", "atl"):
        near = sum(v for k, v in zb.items() if k.startswith(reg) and k.endswith("|0-50"))
        sites = near / p["km2_kelp_per_site"]
        ok = sites * p["chemistry_pass"][reg]
        manual = p["sales_cad_site"] - p["nonharvest_opex_cad_site"] - p["manual_harvest_cad_site"]
        robot = p["sales_cad_site"] - p["nonharvest_opex_cad_site"] - p["robot_variable_cad_site"] - p["robot_fixed_cad_site"]
        out[reg] = dict(nearshore_kelp_km2=near, candidate_sites=sites, operable_sites=ok,
                        mussel_t=ok * p["mussel_t_site"], oyster_t=ok * p["oyster_t_site"],
                        margin_manual_cad_m=ok * manual / 1e6, margin_robot_cad_m=ok * robot / 1e6,
                        margin_robot_shared_lease_cad_m=ok * (robot + p["shared_kelp_lease_saving_cad_site"]) / 1e6,
                        margin_manual_shared_lease_cad_m=ok * (manual + p["shared_kelp_lease_saving_cad_site"]) / 1e6)
    return out


def salmon(s):
    p = PARAMS["salmon"]
    lam = p["laser_capex_cad"] * crf(p["rate"], p["laser_years"]) + p["laser_om_cad"]
    laser_m = p["robots"] * lam / 1e6
    cost = p["feed_cad_m"] + p["pen_cad_m"] + p["hatchery_cad_m"] + p["robot_cad_m"] + p["other_cad_m"] + p["freight_cad_m"] + laser_m
    rows = []
    for price in p["price_cad_kg"]:
        rev = p["block_t"] * price / 1e3
        rows.append(dict(region="Atlantic, open-net pens in kelp lease", price_cad_kg=price, revenue_cad_m=rev, cost_cad_m=cost,
                         net_cad_m=rev - cost, net_cad_kg=(rev - cost) / p["block_t"] * 1e3))
        for prem in p["closed_containment_premium_cad_kg"]:
            c2 = cost + prem * p["block_t"] / 1e3
            rows.append(dict(region=f"British Columbia, closed containment (+CAD {prem:.0f}/kg)", price_cad_kg=price,
                             revenue_cad_m=rev, cost_cad_m=c2, net_cad_m=rev - c2, net_cad_kg=(rev - c2) / p["block_t"] * 1e3))
    kelp_n = s["kelp_dry_mt"] * 1e6 * p["kelp_n_fraction"]
    be_atl = cost / p["block_t"] * 1e3
    return dict(rows=rows, laser_cad_m=laser_m, cost_cad_m=cost, breakeven_price_atlantic_cad_kg=be_atl,
                breakeven_price_bc_cad_kg={str(k): be_atl + k for k in p["closed_containment_premium_cad_kg"]},
                n_released_t=p["n_released_t"], kelp_n_uptake_t=kelp_n, n_share_of_kelp_need_pct=100 * p["n_released_t"] / kelp_n,
                robots=p["robots"], edible_t=p["edible_t"], protein_t=p["edible_protein_t"])


def drones(s, sh):
    p = PARAMS["drones"]
    area = s["kelp_total_km2"]
    n = area * p["per_km2"]
    el_gwh = n * p["kwh_day"] * 365 / 1e6
    ann = n * (p["capex_cad"] * crf(p["rate"], p["life"]) + p["om_cad"]) / 1e6
    repair_km2 = area * p["bare_spot_share"] * p["detection"]
    rafts = area / p["raft_km2"]
    return dict(drones=n, pv_charging_gwh=el_gwh, annual_cost_cad_m=ann, cost_cad_per_km2=ann * 1e6 / area,
                spot_repair_km2=repair_km2, reseeding_cad_m=repair_km2 * p["reseed_cad_km2"] / 1e6,
                rov_sites=sh["pac"]["operable_sites"] + sh["atl"]["operable_sites"], rov_break_even_diver_days=p["rov_break_even_diver_days"],
                service_rafts=rafts, raft_gwh=rafts * p["raft_kwh_day"] * 300 / 1e6)


def run(s):
    from grid_harvester import fleet_sizing
    fleet = fleet_sizing(s["kelp_by_zone_km2"], s["kelp_wet_mt"])
    gh = grid_harvester(s, fleet)
    sh = shellfish(s)
    sa = salmon(s)
    dr = drones(s, sh)
    return dict(params=PARAMS, grid_harvester=gh, shellfish=sh, salmon=sa, drones=dr,
                kelp_km2={"pac": sum(v for k, v in s["kelp_by_zone_km2"].items() if k.startswith("pac")),
                          "atl": sum(v for k, v in s["kelp_by_zone_km2"].items() if not k.startswith("pac"))})


if __name__ == "__main__":
    s = json.load(open(OUT / "central_smr.json"))
    R = run(s)
    json.dump(R, open(OUT / "coproduction.json", "w"), indent=1, default=float)
    print(json.dumps({k: R[k] for k in ("grid_harvester", "shellfish", "drones")}, indent=1, default=float))
    for r in R["salmon"]["rows"]: print(r)
    print({k: R["salmon"][k] for k in ("laser_cad_m", "cost_cad_m", "breakeven_price_atlantic_cad_kg", "n_share_of_kelp_need_pct")})
