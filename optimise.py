"""Least-cost renewable supply for all transport fuel sold in Canada, with native-kelp fuels and fuel exports.

Annual linear programme (scipy/HiGHS). Units: TWh/yr, km2, Mt, CAD 2026 (pre-tax); bn = CAD billion.
Demand: transport fuel sold in Canada in 2025 (economy.py), including fuel for international flights, off-road
  machinery, rail and domestic shipping.
End uses: battery-electric, catenary-electric trucks on an electrified Trans-Canada Highway corridor with a
  renewable-diesel/biodiesel engine for off-wire driving, drop-in liquid (renewable diesel, biodiesel, biojet), ethanol
  (E100, ED95), methane (only if methane vehicles are allowed; liquefaction and conversion costs are then charged),
  methanol, ammonia. Off-road machinery is split into farm, mining and construction and forestry equipment.
  The drop-in rule (central case): aircraft use drop-in jet; trucks without a liquid-fuel engine (battery-electric
  only) supply at most half of heavy-truck and bus demand; at most 20% of farm, 40% of mining (underground battery
  equipment, trolley-assisted haul trucks) and 15% of construction and forestry machinery energy is electric; at least
  60% of rail demand uses liquid fuel.
  The electric-or-biofuel policy (eb_only) removes electrofuels and methane, methanol and ammonia vehicles, so every
  vehicle, ship, aircraft and machine runs on electricity or on liquid biofuel.
Supply: new onshore wind (three resource tiers), PV, redirected hydro exports, new hydro; native-kelp farms (shelf,
  slope, deep water; natural nutrients, depth cycling or pumped upwelling), wet biorefineries (HTL diesel/jet,
  ethanol, biomethane, fertiliser) heated by wind-charged thermal storage, heat pumps, electric boilers or
  residue-fired boilers; forest-residue HTL, agricultural-residue Fischer-Tropsch, waste-lipid and canola HVO,
  existing grain ethanol, ethanol-to-jet, landfill and manure biomethane, electrofuels, biogenic CO2 and direct
  air capture. No fossil energy and no new nuclear capacity are used.
Exports: drop-in fuel may be exported at a given price (CAD/MWh) up to a given volume; the objective then
  maximises the margin earned on exports alongside the least-cost domestic supply.
Vehicle purchase premia at normal fleet replacement are part of the objective and reported separately.
"""
import copy
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
from scipy.optimize import linprog

import economy as E
from farm import ZONES, FarmCost, farm_cost, METHODS
from biorefinery import Feed, Proc, routes as refinery_routes
from preprocess import Pre, options as preprocess_options
from lifecycle import screening_lifecycle
from lakes import lake_systems, LakeParams, bloom_vessel, cutter as lake_cutter

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)
GJ2TWH = 1 / 3.6e6
CRF = lambda r, n: r * (1 + r) ** n / ((1 + r) ** n - 1)
demand = E.demand
FOSSIL = {per: {k: v["p"] for k, v in E.segment_prices(per).items()} for per in ("oct2026", "avg2025")}

# segment -> option: (carrier, MWh carrier per MWh fossil replaced, max share, delivery CAD/MWh carrier, liquid?)
OPTIONS = {
    "ldv_gasoline": {"bev": ("el_direct", 0.28, 1.0, 60, False), "liq": ("dropin", 1.0, 1.0, 24, True),
                     "e100": ("ethanol", 1.0, 1.0, 24, True)},
    "ldv_diesel": {"bev": ("el_direct", 0.33, 1.0, 60, False), "liq": ("dropin", 1.0, 1.0, 24, True)},
    "hdv": {"bet": ("el_direct", 0.53, 0.90, 50, False), "ers": ("el_direct", 0.38, 1.0, 0, True),
            "lng": ("methane", 1.15, 0.50, 45, False),
            "liq": ("dropin", 1.0, 1.0, 24, True), "ed95": ("ethanol", 1.05, 0.50, 32, True)},
    "rail": {"el": ("el_direct", 0.45, 0.40, 30, False), "liq": ("dropin", 1.0, 1.0, 10, True)},
    "offroad": {"farm_el": ("el_direct", 0.42, 1.0, 48, False), "farm_liq": ("dropin", 1.0, 1.0, 24, True),
                "mine_el": ("el_direct", 0.42, 1.0, 40, False), "mine_liq": ("dropin", 1.0, 1.0, 20, True),
                "con_el": ("el_direct", 0.45, 1.0, 48, False), "con_liq": ("dropin", 1.0, 1.0, 24, True),
                "cng": ("methane", 1.10, 0.30, 15, False)},
    "aviation": {"jet": ("jet", 1.0, 1.0, 8, True)},
    "shipping": {"meoh": ("methanol", 1.0, 1.0, 8, True), "nh3": ("ammonia", 1.05, 0.50, 13, True),
                 "lng": ("methane", 1.0, 0.40, 36, False), "liq": ("dropin", 1.0, 1.0, 8, True)},
}
METHANE_OPTS = (("hdv", "lng"), ("offroad", "cng"), ("shipping", "lng"))
NON_EB_OPTS = METHANE_OPTS + (("shipping", "meoh"), ("shipping", "nh3"))
# Off-road diesel by machine type (share of 7.0 GL; approximate split of NRCan end-use data for agriculture, mining
# including oil-sands and quarry fleets, and construction and forestry) and the electric share allowed.
OFFROAD = {"farm": dict(share=0.40, el_max=0.20, el_max_relaxed=0.40),
           "mine": dict(share=0.37, el_max=0.40, el_max_relaxed=0.70),
           "con": dict(share=0.23, el_max=0.15, el_max_relaxed=0.40)}

# Vehicle use for premium conversion: annual km and fossil fuel energy per km (kWh/km)
KM = {"car": 15000, "van": 20000, "truck": 70000}
KWH_KM = {"petrol_car": 0.105 * E.KWH_PER_L["gasoline"], "diesel_ldv": 0.12 * E.KWH_PER_L["diesel"],
          "truck": 0.35 * E.KWH_PER_L["diesel"]}

UNIT_CAPEX = {   # CAD 2026
    "Onshore wind (CAD/kW)": 2300, "PV (CAD/kW)": 1500, "New hydro (CAD/kW)": 9000,
    "Electrolysers (CAD/kW)": 1580, "E-fuel synthesis (CAD/kW fuel)": 1430, "DAC (CAD per t/yr)": 2380,
    "Kelp farm shelf (CAD/km2)": 3.2e6, "Kelp farm deep (CAD/km2)": 5.7e6, "Kelp biorefinery (CAD per t dw/yr)": 2600,
    "Residue biorefinery (CAD per MWh/yr of fuel)": 330, "Vessel (CAD each)": 95e6, "ATJ plant (CAD/kW jet)": 1430,
    "Charging and grid (CAD bn per TWh/yr of EV load)": 0.56, "Thermal storage + heaters (CAD per MWh_th/yr)": 225,
    "Lake Grid Harvester (CAD each)": 6.0e6, "Lake algae grid (CAD/km2)": 1.5e6,
    "Highway catenary (CAD per route-km, both directions)": 3.6e6,
}


def ers(prm):
    """Electrified Trans-Canada Highway: on-wire diesel-equivalent energy (TWh) and catenary cost per MWh of diesel replaced at
    full use. Infrastructure cost: CAD 3.6 M per route-km (both directions), range 2.5-4.8 (Kayser-Bril and
    Whitmore, HEC Montreal, Canada e-highway study of the A20-H401 corridor). Truck traffic: average annual daily heavy
    truck traffic over the route; energy 4.07 kWh of diesel per km (0.38 L/km); on-wire share of corridor km."""
    h = prm["hwy1"]
    if not h["enabled"]:
        return 0.0, 0.0, 0.0
    km = h["km"] + h.get("extra_km", 0.0)
    tkm = (h["km"] * h["aadtt"] + h.get("extra_km", 0.0) * h.get("extra_aadtt", 0.0)) * 365
    twh_d = tkm * h["kwh_d_km"] * h["on_wire"] / 1e9
    ann = km * h["capex_m_km"] * 1e6 * (CRF(prm["wacc"], h["life"]) + h["om"])
    return twh_d, ann / (twh_d * 1e6), km


def base_params():
    return dict(
        wind=dict(tiers=[dict(lcoe=65, cf=0.40, cap_gw=60), dict(lcoe=78, cf=0.36, cap_gw=150), dict(lcoe=92, cf=0.32, cap_gw=400)]),
        pv=dict(lcoe=80, cf=0.16, cap_gw=100),
        hydro_redirect=dict(cost=95, cap_twh=30),      # opportunity cost of electricity now exported to the US
        new_hydro=dict(lcoe=160, cf=0.55, cap_twh=40),
        adder=dict(wind=22, pv_day=12, pv_shift=70, network_direct=32, network_flex=10, flex_wind=8, flex_pv=20,
                   pv_day_share=0.25),
        heat=dict(hp_cop=2.5, hp_max_share=0.6, eboiler_eff=0.99, tes_eff=0.95, tes_cost=20.0,
                  bio_boiler_mwh_per_odt=4.25, bio_boiler_cost=14.0),
        eft=dict(el=2.40, cost=174, co2=0.30),
        emeoh=dict(el=1.90, cost=95, co2=0.25),
        enh3=dict(el=1.75, cost=80),
        ech4=dict(el=1.80, cost=87, co2=0.20),
        atj=dict(eff=0.925, cost=71),
        biomeoh=dict(ch4_per_meoh=1.5, cost=39),
        dac=dict(el=1.5, cost=476),
        bio_co2_other=dict(cap=20.0, cost=110),        # pulp mills and ethanol plants, Mt CO2/yr, CAD/t
        kelp_co2_capture=32.0,
        waste_ch4=dict(cap=25.0, cost=85, co2=0.20),    # landfill gas, manure, food waste
        hefa=dict(cap=8.0, cost=190),                   # used cooking oil, tallow, distillers corn oil
        canola=dict(cap=15.0, cost=185),                # existing canola oil, no cropland expansion
        crop_etoh=dict(cap=12.0, cost=135),             # existing grain ethanol (about 2 GL/yr)
        forest=dict(cap_modt=20.0, cost_odt=95, mwh_per_odt=2.6, conv=75),     # forest harvest residues -> HTL
        agres=dict(cap_modt=15.0, cost_odt=85, mwh_per_odt=2.2, conv=95),      # straw and stover -> FT
        allow_efuels=True,
        fert=dict(price={"n": 2.05, "p": 4.10, "k": 1.00}, cap_mt={"n": 2.5, "p": 0.30, "k": 0.40}, export_share=0.6),
        farm=asdict(FarmCost()),
        nutrient_methods=METHODS,
        area_share={"pac_shelf": 0.10, "pac_slope": 0.10, "pac_deep": 0.25, "atl_shelf": 0.10, "atl_slope": 0.10, "atl_deep": 0.25,
                    "gsl_shelf": 0.05, "gsl_slope": 0.05, "lab_shelf": 0.10, "lab_slope": 0.10, "hb_shelf": 0.10, "hb_slope": 0.10},
        zone_yield={},
        refinery_routes=("EH", "H", "A"),
        proc=asdict(Proc()),
        preprocess=("wet", "press"),
        fleet=dict(harvest_gj=0.35, mj_tkm_near=0.15, mj_tkm_far=0.12, kite_near=0.10, kite_far=0.15),
        liquid_required=True,
        allow_methane_vehicles=False,
        allow_kelp=True,
        scope="all",
        demand_mult={},
        wind_assist_share=0.08,
        veh=dict(car=1500, van=3200, truck=48000, lng_truck=39000, ed95_truck=12600, e100_car=420, ers_truck=45000,
                 r=0.07, life=15),
        refinery_cost_mult=1.0,
        wacc=0.07,
        export=dict(price=0.0, cap_twh=0.0, logistics=8.0),
        lakes=dict(enabled=True, cleanup_cad_kg_p=0.0, force=False),
        hwy1=dict(enabled=True, km=7821.0, aadtt=2500.0, kwh_d_km=4.07, on_wire=0.90, capex_m_km=3.6, om=0.015, life=30,
                  extra_km=0.0, extra_aadtt=0.0),
        eb_only=False,
        kelp_min_km2={},          # zone prefix (e.g. "hb") -> minimum farm area, for regional siting cases
    )


def vehicle_premium_per_mwh(prm):
    """CAD per MWh of fossil fuel replaced, by (segment, option)."""
    v = prm["veh"]
    f = CRF(v["r"], v["life"])
    pm = lambda prem, km, kwh_km: prem * f / km * (1000 / kwh_km)
    car_d = 0.6 * pm(v["car"], KM["car"], KWH_KM["diesel_ldv"]) + 0.4 * pm(v["van"], KM["van"], KWH_KM["diesel_ldv"])
    return {("ldv_gasoline", "bev"): pm(v["car"], KM["car"], KWH_KM["petrol_car"]),
            ("ldv_gasoline", "e100"): pm(v["e100_car"], KM["car"], KWH_KM["petrol_car"]),
            ("ldv_diesel", "bev"): car_d,
            ("hdv", "bet"): pm(v["truck"], KM["truck"], KWH_KM["truck"]),
            ("hdv", "lng"): pm(v["lng_truck"], KM["truck"], KWH_KM["truck"]),
            ("hdv", "ed95"): pm(v["ed95_truck"], KM["truck"], KWH_KM["truck"]),
            ("hdv", "ers"): pm(v.get("ers_truck", 45000), 90000, KWH_KM["truck"] * 1.09),
            ("offroad", "farm_el"): pm(v["truck"], KM["truck"], KWH_KM["truck"]),
            ("offroad", "mine_el"): pm(v["truck"], KM["truck"], KWH_KM["truck"]),
            ("offroad", "con_el"): pm(v["truck"], KM["truck"], KWH_KM["truck"]),
            ("offroad", "cng"): pm(v["lng_truck"], KM["truck"], KWH_KM["truck"])}


class LP:
    def __init__(self):
        self.names, self.cost, self.bounds, self.ub, self.eq = [], [], [], [], []

    def var(self, name, cost=0.0, lb=0.0, ub=None):
        self.names.append(name); self.cost.append(cost); self.bounds.append((lb, ub))
        return len(self.names) - 1

    def le(self, co, rhs, tag=None):
        self.ub.append((co, rhs, tag))

    def eqc(self, co, rhs, tag=None):
        self.eq.append((co, rhs, tag))

    def solve(self):
        from scipy.sparse import coo_matrix
        n = len(self.names)

        def mat(rows):
            r, c, v, b = [], [], [], np.zeros(len(rows))
            for i, (co, rhs, _) in enumerate(rows):
                for j, val in co.items():
                    r.append(i); c.append(j); v.append(val)
                b[i] = rhs
            return coo_matrix((v, (r, c)), shape=(len(rows), n)).tocsr(), b
        Au, bu = mat(self.ub); Ae, be = mat(self.eq)
        res = linprog(np.array(self.cost), A_ub=Au, b_ub=bu, A_eq=Ae, b_eq=be, bounds=self.bounds, method="highs")
        if res.status != 0:
            raise RuntimeError(res.message)
        duals = {}
        for i, (_, _, tag) in enumerate(self.ub):
            if tag: duals[tag] = -res.ineqlin.marginals[i]
        for i, (_, _, tag) in enumerate(self.eq):
            if tag: duals[tag] = -res.eqlin.marginals[i]
        return dict(zip(self.names, res.x)), res.fun, duals


def add(d, k, v):
    d[k] = d.get(k, 0.0) + v


def kelp_systems(prm):
    """Enumerate (zone, band, nutrient method, pre-processing, refinery route) systems."""
    fc = FarmCost(**prm["farm"])
    fl = prm["fleet"]
    pre_opts = preprocess_options(Pre(**{**prm.get("pre", {}), "dm_harvest": fc.dm_harvest}))
    feed = Feed()
    systems = []
    for zk, z in ZONES.items():
        y = prm["zone_yield"].get(zk)
        for band in z.area_km2:
            for m in prm["nutrient_methods"]:
                fcost = farm_cost(zk, band, fc, m, yield_override=y)
                if not np.isfinite(fcost["total_cad_t"]) or fcost["yield_t_ha"] <= 0:
                    continue
                t_km2 = fcost["yield_t_ha"] * 100
                km = z.mid_km[band]
                far = km > 100
                wet = 1 / fc.dm_harvest
                transit = wet * km * (fl["mj_tkm_far"] if far else fl["mj_tkm_near"]) * 1.6 / 1000
                kite = fl["kite_far"] if far else fl["kite_near"]
                for pk in prm["preprocess"]:
                    po = pre_opts[pk]
                    mass_ratio = po["mass_t"] / wet
                    transport_new = po["mass_t"] * max(km - 40, 0) * fc.transport_cad_t_wet_km
                    farm_cad = fcost["total_cad_t"] - fcost["transport_cad_t"] + transport_new + po["cost"]
                    pproc = Proc(**{**prm["proc"], **({} if po["ensile"] else {"ensile_sugar_loss": 0.0})})
                    pfeed = Feed(**{**asdict(feed), "mannitol": feed.mannitol * po["mannitol_keep"]})
                    rts = refinery_routes(pfeed, pproc)
                    for r in prm["refinery_routes"]:
                        rr = dict(rts[r])
                        for kk in ("hc_gj", "jet_gj", "ch4_gj"):
                            rr[kk] *= po["vs_keep"]
                        if r != "EH":
                            rr["co2_ferm_t"] *= po["vs_keep"]
                        ref_cost = (rr["cost_cad"] - (0.0 if po["ensile"] else pproc.cost_ensile)) * prm["refinery_cost_mult"]
                        systems.append(dict(
                            key=f"{zk}|{band}|{m}|{pk}|{r}", zone=zk, band=band, method=fcost["method"], pre=pk, route=r,
                            area_cap=z.area_km2[band] * prm["area_share"][zk], t_km2=t_km2,
                            farm_cad_t=farm_cad, refinery_cad_t=ref_cost,
                            fleet_gj_t=fl["harvest_gj"] + transit * mass_ratio * (1 - kite),
                            kite_saved_gj_t=transit * mass_ratio * kite,
                            ethanol_gj=rr["ethanol_gj"], hc_gj=rr["hc_gj"], jet_gj=rr["jet_gj"], ch4_gj=rr["ch4_gj"],
                            el_mwh=rr["el_mwh"], heat_mwh=rr["heat_mwh_th"], co2_t=rr["co2_ferm_t"],
                            fert=(rr["fert_n_kg"], rr["fert_p_kg"], rr["fert_k_kg"]), fert_energy_gj=rr["fert_energy_gj"],
                            fert_co2_t=rr["fert_co2_t"], units_km2=fcost["units_per_km2"],
                            deep_water_m3_t=fcost["deep_water_m3_per_t_dw"], wet_mass_t=po["mass_t"]))
    return systems


def solve(prm):
    d = demand(prm["scope"])
    for k, m in prm.get("demand_mult", {}).items():
        d[k] *= m
    lp = LP()
    a = prm["adder"]
    G = {}
    for i, t in enumerate(prm["wind"]["tiers"]):
        G[f"wind{i}_dir"] = lp.var(f"wind_t{i + 1}_direct", t["lcoe"] + a["wind"] + a["network_direct"])
        G[f"wind{i}_flex"] = lp.var(f"wind_t{i + 1}_flex", t["lcoe"] + a["flex_wind"] + a["network_flex"])
    G["pv_day"] = lp.var("pv_direct_day", prm["pv"]["lcoe"] + a["pv_day"] + a["network_direct"])
    G["pv_shift"] = lp.var("pv_direct_shifted", prm["pv"]["lcoe"] + a["pv_shift"] + a["network_direct"])
    G["pv_flex"] = lp.var("pv_flex", prm["pv"]["lcoe"] + a["flex_pv"] + a["network_flex"])
    G["hydro_redirect"] = lp.var("hydro_redirected_from_exports", prm["hydro_redirect"]["cost"] + a["network_direct"],
                                 0, prm["hydro_redirect"]["cap_twh"])
    G["new_hydro"] = lp.var("new_hydro", prm["new_hydro"]["lcoe"] + a["network_direct"], 0, prm["new_hydro"]["cap_twh"])
    h = prm["heat"]
    HS = {"tes": lp.var("heat_wind_thermal_storage", h["tes_cost"]), "hp": lp.var("heat_heat_pump"),
          "eb": lp.var("heat_electric_boiler"), "bio": lp.var("heat_residue_boiler", h["bio_boiler_cost"])}

    kelp = kelp_systems(prm)
    lakes = lake_systems(prm)
    systems = kelp + lakes
    K = {s["key"]: lp.var(("lake_Mt|" if s["key"].startswith("lake|") else "kelp_km2|") + s["key"],
                          s["t_km2"] * (s["farm_cad_t"] + s["refinery_cad_t"]) / 1e6) for s in systems}
    zb = {}
    for s in systems:
        zb.setdefault((s["zone"], s["band"]), []).append(s)
    for ss in zb.values():
        co = {K[s["key"]]: 1.0 for s in ss}
        lp.le(co, ss[0]["area_cap"])
        if ss[0].get("force"):
            lp.le({k: -v for k, v in co.items()}, -ss[0]["area_cap"])
    pg = {}
    for s_ in lakes:
        if s_.get("p_group"):
            pg.setdefault(s_["p_group"], []).append(s_)
    for ss in pg.values():
        lp.le({K[s_["key"]]: s_["p_removed_kg_t"] * 1e6 / 1e3 for s_ in ss}, ss[0]["p_group_cap_t"])

    F = {}
    F["eft"] = lp.var("eFT_liquids", prm["eft"]["cost"])
    F["emeoh"] = lp.var("e_methanol", prm["emeoh"]["cost"])
    F["enh3"] = lp.var("e_ammonia", prm["enh3"]["cost"])
    F["ech4"] = lp.var("e_methane", prm["ech4"]["cost"])
    F["atj"] = lp.var("ATJ_jet_from_ethanol", prm["atj"]["cost"])
    F["biomeoh"] = lp.var("bio_methanol_from_CH4", prm["biomeoh"]["cost"])
    F["waste_ch4"] = lp.var("waste_biomethane", prm["waste_ch4"]["cost"], 0, prm["waste_ch4"]["cap"])
    F["hefa"] = lp.var("HEFA_waste_lipids", prm["hefa"]["cost"], 0, prm["hefa"]["cap"])
    F["canola"] = lp.var("canola_HVO", prm["canola"]["cost"], 0, prm["canola"]["cap"])
    F["cetoh"] = lp.var("grain_ethanol_existing", prm["crop_etoh"]["cost"], 0, prm["crop_etoh"]["cap"])
    fo, ag = prm["forest"], prm["agres"]
    F["forest_odt"] = lp.var("forest_residue_Modt", fo["cost_odt"], 0, fo["cap_modt"])
    F["forest_htl"] = lp.var("forest_residue_HTL", fo["conv"])
    F["agres"] = lp.var("agri_residue_FT", ag["conv"] + ag["cost_odt"] / ag["mwh_per_odt"], 0, ag["cap_modt"] * ag["mwh_per_odt"])
    F["dac"] = lp.var("DAC_CO2_Mt", prm["dac"]["cost"])
    F["bco2"] = lp.var("other_biogenic_CO2_Mt", prm["bio_co2_other"]["cost"], 0, prm["bio_co2_other"]["cap"])
    F["kco2"] = lp.var("kelp_CO2_used_Mt", prm["kelp_co2_capture"])
    F["wind_assist"] = lp.var("wind_assist_saving", 71.0, 0, prm["wind_assist_share"] * d["shipping"])
    ex = prm["export"]
    F["export"] = lp.var("export_dropin", ex["logistics"] - ex["price"], ex.get("min_twh", 0.0), max(ex["cap_twh"], ex.get("min_twh", 0.0)))
    # forest residues: fuel (HTL) and boiler heat share the supply
    lp.le({F["forest_htl"]: 1 / fo["mwh_per_odt"], HS["bio"]: 1 / h["bio_boiler_mwh_per_odt"], F["forest_odt"]: -1.0}, 0.0)
    fert = {}
    for nut in ("n", "p", "k"):
        pr = prm["fert"]["price"][nut] * 1000
        fert[nut + "_dom"] = lp.var(f"fert_{nut}_domestic_Mt", -pr, 0, prm["fert"]["cap_mt"][nut])
        fert[nut + "_exp"] = lp.var(f"fert_{nut}_export_Mt", -pr * prm["fert"]["export_share"])

    vp = vehicle_premium_per_mwh(prm)
    ers_twh, ers_cad, _ = ers(prm)
    U = {}
    for sg, opts in OPTIONS.items():
        for o, (car, ratio, share, extra, liq) in opts.items():
            U[(sg, o)] = lp.var(f"use|{sg}|{o}", extra * ratio + vp.get((sg, o), 0.0) + (ers_cad if (sg, o) == ("hdv", "ers") else 0.0))
    eb = prm.get("eb_only", False)
    for sg, opts in OPTIONS.items():
        co = {U[(sg, o)]: 1.0 for o in opts}
        if sg == "shipping":
            co[F["wind_assist"]] = 1.0
        lp.eqc(co, d[sg])
        for o, (car, ratio, share, extra, liq) in opts.items():
            cap = share
            if (sg, o) in METHANE_OPTS and not prm["allow_methane_vehicles"]:
                cap = 0.0
            if eb and (sg, o) in NON_EB_OPTS:
                cap = 0.0
            if prm["liquid_required"]:
                if sg == "hdv" and o == "bet":
                    cap = 0.5
                if sg == "hdv" and o == "lng":
                    cap = 0.0
            if (sg, o) == ("hdv", "ers"):
                lp.le({U[(sg, o)]: 1.0}, min(ers_twh, d[sg]))
                continue
            if sg == "offroad" and o != "cng":
                continue
            if cap < 1.0:
                lp.le({U[(sg, o)]: 1.0}, cap * d[sg])
    for k, c in OFFROAD.items():
        el_max = c["el_max"] if prm["liquid_required"] else c["el_max_relaxed"]
        dk = c["share"] * d["offroad"]
        co = {U[("offroad", f"{k}_el")]: 1.0, U[("offroad", f"{k}_liq")]: 1.0}
        if k == "con":
            co[U[("offroad", "cng")]] = 1.0
        lp.eqc(co, dk)
        lp.le({U[("offroad", f"{k}_el")]: 1.0}, el_max * dk)
    if prm["liquid_required"]:
        lp.le({U[("hdv", "liq")]: -1.0, U[("hdv", "ed95")]: -1.0, U[("hdv", "ers")]: -1.0}, -0.5 * d["hdv"])

    def use(car):
        co = {}
        for (sg, o), i in U.items():
            if OPTIONS[sg][o][0] == car:
                add(co, i, OPTIONS[sg][o][1])
        return co

    DROPIN_SRC = ("eft", "hefa", "canola", "forest_htl", "agres", "atj")
    co = use("dropin")
    for k, v in use("jet").items(): add(co, k, v)
    add(co, F["export"], 1.0)
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["hc_gj"] * GJ2TWH)
    for f in DROPIN_SRC: add(co, F[f], -1.0)
    lp.le(co, 0.0, "dropin")
    co = use("jet")
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["jet_gj"] * GJ2TWH)
    for f in ("eft", "hefa", "canola", "forest_htl", "agres"): add(co, F[f], -0.6)
    add(co, F["atj"], -1.0)
    lp.le(co, 0.0, "jet")
    co = use("ethanol"); add(co, F["atj"], 1 / prm["atj"]["eff"]); add(co, F["cetoh"], -1.0)
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["ethanol_gj"] * GJ2TWH)
    lp.le(co, 0.0, "ethanol")
    co = use("methane")
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * (s["ch4_gj"] - s["fleet_gj_t"]) * GJ2TWH)
    add(co, F["waste_ch4"], -1); add(co, F["ech4"], -1); add(co, F["biomeoh"], prm["biomeoh"]["ch4_per_meoh"])
    lp.le(co, 0.0, "methane")
    co = use("methanol"); add(co, F["emeoh"], -1); add(co, F["biomeoh"], -1); lp.le(co, 0.0, "methanol")
    co = use("ammonia"); add(co, F["enh3"], -1); lp.le(co, 0.0, "ammonia")
    lp.le({F["eft"]: prm["eft"]["co2"], F["emeoh"]: prm["emeoh"]["co2"], F["ech4"]: prm["ech4"]["co2"],
           F["dac"]: -1, F["bco2"]: -1, F["kco2"]: -1, F["waste_ch4"]: -prm["waste_ch4"]["co2"]}, 0.0, "co2")
    co = {F["kco2"]: 1.0}
    for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["co2_t"] / 1e6)
    lp.le(co, 0.0)
    for j, nut in enumerate(("n", "p", "k")):
        co = {fert[nut + "_dom"]: 1.0, fert[nut + "_exp"]: 1.0}
        for s in systems: add(co, K[s["key"]], -s["t_km2"] * s["fert"][j] / 1e9)
        lp.le(co, 0.0)
    # process heat for kelp biorefineries
    co = {HS[k]: -1.0 for k in HS}
    for s in systems: add(co, K[s["key"]], s["t_km2"] * s["heat_mwh"] / 1e6)
    lp.le(co, 0.0, "heat")
    co = {HS["hp"]: 1.0}
    for s in systems: add(co, K[s["key"]], -h["hp_max_share"] * s["t_km2"] * s["heat_mwh"] / 1e6)
    lp.le(co, 0.0)
    # electricity: direct (vehicles, refineries, heat pumps, boilers) and flexible (electrolysis, DAC, heat storage)
    co = use("el_direct")
    for s in systems: add(co, K[s["key"]], s["t_km2"] * s["el_mwh"] / 1e6)
    add(co, HS["hp"], 1 / h["hp_cop"]); add(co, HS["eb"], 1 / h["eboiler_eff"])
    for k in [k for k in G if k.endswith("_dir")] + ["pv_day", "pv_shift", "hydro_redirect", "new_hydro"]:
        add(co, G[k], -1.0)
    lp.eqc(co, 0.0, "el_direct")
    co = {F["eft"]: prm["eft"]["el"], F["emeoh"]: prm["emeoh"]["el"], F["enh3"]: prm["enh3"]["el"],
          F["ech4"]: prm["ech4"]["el"], F["dac"]: prm["dac"]["el"], HS["tes"]: 1 / h["tes_eff"]}
    for k in [k for k in G if k.endswith("_flex")]:
        add(co, G[k], -1.0)
    lp.le(co, 0.0, "el_flex")
    co = {G["pv_day"]: 1.0}
    for k, v in use("el_direct").items(): add(co, k, -a["pv_day_share"] * v)
    lp.le(co, 0.0)
    for i, t in enumerate(prm["wind"]["tiers"]):
        lp.le({G[f"wind{i}_dir"]: 1.0, G[f"wind{i}_flex"]: 1.0}, t["cap_gw"] * t["cf"] * 8.76)
    lp.le({G["pv_day"]: 1.0, G["pv_shift"]: 1.0, G["pv_flex"]: 1.0}, prm["pv"]["cap_gw"] * prm["pv"]["cf"] * 8.76)
    for pre, amin in prm.get("kelp_min_km2", {}).items():
        co = {K[s_["key"]]: -1.0 for s_ in kelp if s_["zone"].startswith(pre + "_")}
        if co:
            lp.le(co, -amin)
    if not prm["allow_kelp"]:
        for s_ in kelp:
            lp.bounds[K[s_["key"]]] = (0, 0)
    if not prm["allow_efuels"] or eb:
        for f in ("eft", "emeoh", "enh3", "ech4"):
            lp.bounds[F[f]] = (0, 0)

    x, total, duals = lp.solve()
    return summarise(x, total, duals, prm, d, systems, vp)


def f_ret(r, n):
    """Average share of a levelised capital charge that is return on capital (not depreciation)."""
    return 1 - 1 / (n * CRF(r, n))


def summarise(x, total, duals, prm, d, systems, vp):
    s = {"objective_bn": total / 1000}
    ex = prm["export"]
    s["export_twh"] = x["export_dropin"]
    s["export_revenue_bn"] = x["export_dropin"] * ex["price"] / 1000
    s["export_logistics_bn"] = x["export_dropin"] * ex["logistics"] / 1000
    vprem = sum(x[f"use|{sg}|{o}"] * v for (sg, o), v in vp.items()) / 1000
    s["vehicle_premium_bn"] = vprem
    ers_twh, ers_cad, ers_km = ers(prm)
    on = x["use|hdv|ers"]
    s["ers"] = dict(cap_twh_diesel=ers_twh, used_twh_diesel=on, electricity_twh=on * OPTIONS["hdv"]["ers"][1],
                    cad_per_mwh_diesel=ers_cad, route_km=ers_km, built_km=(ers_km * on / ers_twh if ers_twh > 0 else 0.0),
                    cost_bn=on * ers_cad / 1000, share_of_hdv=on / d["hdv"] if d["hdv"] else 0.0,
                    trucks=on * 1e6 / (90000 * KWH_KM["truck"] * 1.09 / 1000) if on > 0 else 0.0)
    s["offroad_twh"] = {k: {"el": x[f"use|offroad|{k}_el"], "liq": x[f"use|offroad|{k}_liq"]} for k in OFFROAD}
    s["vehicle_premium_per_mwh"] = {f"{sg}|{o}": v for (sg, o), v in vp.items()}
    fert_rev = sum(x[f"fert_{n}_{w}_Mt"] * prm["fert"]["price"][n] * (1 if w == "domestic" else prm["fert"]["export_share"])
                   for n in ("n", "p", "k") for w in ("domestic", "export"))
    s["fertiliser_value_bn"] = fert_rev
    # cost of the whole supply system (domestic and export), gross of fertiliser and export revenue
    s["supply_cost_bn"] = s["objective_bn"] + s["export_revenue_bn"] + fert_rev - vprem
    s["total_cost_bn"] = s["objective_bn"] + s["export_revenue_bn"]       # incl. vehicle premia, net of fertiliser
    s["energy_cost_bn"] = s["total_cost_bn"] - vprem
    nt = len(prm["wind"]["tiers"])
    wind = sum(x[f"wind_t{i + 1}_direct"] + x[f"wind_t{i + 1}_flex"] for i in range(nt))
    gen = {"Onshore wind": wind, "PV": x["pv_direct_day"] + x["pv_direct_shifted"] + x["pv_flex"],
           "Hydro (redirected exports)": x["hydro_redirected_from_exports"], "New hydro": x["new_hydro"]}
    s["generation_twh"] = gen
    s["wind_by_tier_twh"] = [x[f"wind_t{i + 1}_direct"] + x[f"wind_t{i + 1}_flex"] for i in range(nt)]
    wind_gw = sum(v / (t["cf"] * 8.76) for v, t in zip(s["wind_by_tier_twh"], prm["wind"]["tiers"]))
    s["capacity_gw"] = {"Onshore wind": wind_gw, "PV": gen["PV"] / (prm["pv"]["cf"] * 8.76),
                        "New hydro": gen["New hydro"] / (prm["new_hydro"]["cf"] * 8.76)}
    s["electricity_delivered_twh"] = sum(gen.values())
    s["heat_twh_th"] = {"Wind-charged thermal storage": x["heat_wind_thermal_storage"], "heat pumps": x["heat_heat_pump"],
                        "electric boilers": x["heat_electric_boiler"], "residue boilers": x["heat_residue_boiler"]}
    sysd = {sy["key"]: sy for sy in systems}
    kel = {k.split("|", 1)[1]: v for k, v in x.items() if k.startswith("kelp_km2|") and v > 1e-3}
    tot = lambda f: sum(v * sysd[k]["t_km2"] * f(sysd[k]) for k, v in kel.items())
    s["kelp_km2"] = kel
    s["kelp_total_km2"] = sum(kel.values())
    s["kelp_dry_mt"] = tot(lambda q: 1) / 1e6
    s["kelp_wet_mt"] = s["kelp_dry_mt"] / prm["farm"]["dm_harvest"]
    s["kelp_ethanol_twh"] = tot(lambda q: q["ethanol_gj"]) / 3.6e6
    s["kelp_hc_twh"] = tot(lambda q: q["hc_gj"]) / 3.6e6
    s["kelp_jet_twh"] = tot(lambda q: q["jet_gj"]) / 3.6e6
    s["kelp_ch4_gross_twh"] = tot(lambda q: q["ch4_gj"]) / 3.6e6
    s["kelp_fleet_fuel_twh"] = tot(lambda q: q["fleet_gj_t"]) / 3.6e6
    s["kite_saved_twh"] = tot(lambda q: q["kite_saved_gj_t"]) / 3.6e6
    s["kelp_refinery_el_twh"] = tot(lambda q: q["el_mwh"]) / 1e6
    s["kelp_refinery_heat_twh"] = tot(lambda q: q["heat_mwh"]) / 1e6
    s["kelp_farm_cost_bn"] = sum(v * sysd[k]["t_km2"] * sysd[k]["farm_cad_t"] for k, v in kel.items()) / 1e9
    s["kelp_refinery_cost_bn"] = sum(v * sysd[k]["t_km2"] * sysd[k]["refinery_cad_t"] for k, v in kel.items()) / 1e9
    s["kelp_cost_bn"] = s["kelp_farm_cost_bn"] + s["kelp_refinery_cost_bn"]
    s["fertiliser_mt"] = {n: tot(lambda q, j=j: q["fert"][j]) / 1e9 for j, n in enumerate(("N", "P", "K"))}
    s["fertiliser_energy_avoided_pj"] = tot(lambda q: q["fert_energy_gj"]) / 1e6
    s["fertiliser_co2_avoided_mt"] = tot(lambda q: q["fert_co2_t"]) / 1e6
    s["upwelling_pipes"] = tot(lambda q: q["units_km2"] / q["t_km2"] if q["method"] in ("solar_pipe", "wave_pump", "wave_pump_xl") else 0)
    for key, field in (("kelp_by_zone_km2", "zone"), ("kelp_by_route_km2", "route"),
                       ("kelp_by_nutrient_method_km2", "method"), ("kelp_by_preprocess_km2", "pre"),
                       ("kelp_by_band_km2", "band")):
        s[key] = {}
        for k, v in kel.items():
            add(s[key], sysd[k][field], v)
    s["kelp_by_zone_band_km2"] = {}
    for k, v in kel.items():
        add(s["kelp_by_zone_band_km2"], sysd[k]["zone"] + "|" + sysd[k]["band"], v)
    # ---- freshwater lakes (one unit = 1 Mt dry)
    lak = {k.split("|", 1)[1]: v for k, v in x.items() if k.startswith("lake_Mt|") and v > 1e-9}
    ltot = lambda f: sum(v * 1e6 * f(sysd[k]) for k, v in lak.items())
    s["lake_mt"] = lak
    s["lake_dry_kt"] = ltot(lambda q: 1) / 1e3
    s["lake_dry_kt_by"] = {}
    s["lake_p_removed_t_by"] = {}
    for k, v in lak.items():
        q = sysd[k]
        add(s["lake_dry_kt_by"], q["lake"] + "|" + q["biomass"], v * 1e3)
        add(s["lake_p_removed_t_by"], q["lake"], v * 1e6 * q["p_removed_kg_t"] / 1e3)
        add(s.setdefault("lake_p_removed_t_by_biomass", {}), q["biomass"], v * 1e6 * q["p_removed_kg_t"] / 1e3)
        add(s.setdefault("lake_dry_kt_by_biomass", {}), q["biomass"], v * 1e3)
        add(s.setdefault("lake_p_removed_t_by_lake_biomass", {}), q["lake"] + "|" + q["biomass"], v * 1e6 * q["p_removed_kg_t"] / 1e3)
    s.setdefault("lake_p_removed_t_by_biomass", {}); s.setdefault("lake_dry_kt_by_biomass", {})
    s.setdefault("lake_p_removed_t_by_lake_biomass", {})
    s["lake_p_removed_t"] = ltot(lambda q: q["p_removed_kg_t"]) / 1e3
    s["lake_n_removed_t"] = ltot(lambda q: q["n_removed_kg_t"]) / 1e3
    s["lake_hc_twh"] = ltot(lambda q: q["hc_gj"]) / 3.6e6
    s["lake_jet_twh"] = ltot(lambda q: q["jet_gj"]) / 3.6e6
    s["lake_ethanol_twh"] = ltot(lambda q: q["ethanol_gj"]) / 3.6e6
    s["lake_ch4_gross_twh"] = ltot(lambda q: q["ch4_gj"]) / 3.6e6
    s["lake_fleet_fuel_twh"] = ltot(lambda q: q["fleet_gj_t"]) / 3.6e6
    s["lake_refinery_el_twh"] = ltot(lambda q: q["el_mwh"]) / 1e6
    s["lake_harvest_cost_bn"] = ltot(lambda q: q["harvest_cad_t"]) / 1e9
    s["lake_refinery_cost_bn"] = ltot(lambda q: q["refinery_cad_t"]) / 1e9
    s["lake_cleanup_payment_bn"] = ltot(lambda q: q["cleanup_credit_cad_t"]) / 1e9
    s["lake_fertiliser_kt"] = {n: ltot(lambda q, j=j: q["fert"][j]) / 1e6 for j, n in enumerate(("N", "P", "K"))}
    units = lambda b: sum(v * 1e6 * sysd[k]["units_per_t"] for k, v in lak.items() if sysd[k]["biomass"] == b)
    s["lake_vessels"] = units("algae")
    s["lake_cutters"] = units("milfoil")
    s["lake_grid_units"] = units("grid")
    s["lake_harvesters"] = s["lake_vessels"] + s["lake_cutters"] + s["lake_grid_units"]
    s["lake_grid_km2"] = sum(v * 1e6 * sysd[k]["grid_km2_per_t"] for k, v in lak.items() if sysd[k]["biomass"] == "grid")
    s["lake_grid_km2_by"] = {}
    for k, v in lak.items():
        if sysd[k]["biomass"] == "grid":
            add(s["lake_grid_km2_by"], sysd[k]["lake"], v * 1e6 * sysd[k]["grid_km2_per_t"])
    fuels = {k: x[k] for k in ("eFT_liquids", "e_methanol", "e_ammonia", "e_methane", "ATJ_jet_from_ethanol",
                               "waste_biomethane", "HEFA_waste_lipids", "canola_HVO", "forest_residue_HTL",
                               "agri_residue_FT", "grain_ethanol_existing")}
    fuels["kelp HTL diesel/jet"] = s["kelp_hc_twh"]
    atj_nongrain = max(0.0, x["ATJ_jet_from_ethanol"] / prm["atj"]["eff"] - x["grain_ethanol_existing"])
    eth_ng = s["kelp_ethanol_twh"] + s["lake_ethanol_twh"]
    atj_from_kelp = atj_nongrain * (s["kelp_ethanol_twh"] / eth_ng if eth_ng > 1e-12 else 0.0)
    atj_from_lake = atj_nongrain - atj_from_kelp
    fuels["kelp ethanol"] = max(0.0, s["kelp_ethanol_twh"] - atj_from_kelp)
    fuels["kelp biomethane (net of fleet)"] = s["kelp_ch4_gross_twh"] - s["kelp_fleet_fuel_twh"]
    fuels["lake HTL diesel/jet"] = s["lake_hc_twh"]
    fuels["lake ethanol"] = max(0.0, s["lake_ethanol_twh"] - atj_from_lake)
    fuels["lake biomethane (net of fleet)"] = s["lake_ch4_gross_twh"] - s["lake_fleet_fuel_twh"]
    s["fuels_twh"] = fuels
    s["forest_residue_modt"] = x["forest_residue_Modt"]
    s["agri_residue_modt"] = x["agri_residue_FT"] / prm["agres"]["mwh_per_odt"]
    s["bio_methanol_from_CH4_twh"] = x["bio_methanol_from_CH4"]
    s["co2_mt"] = {"DAC": x["DAC_CO2_Mt"], "other biogenic": x["other_biogenic_CO2_Mt"], "kelp": x["kelp_CO2_used_Mt"]}
    s["wind_assist_twh_saved"] = x["wind_assist_saving"]
    s["end_use_twh"] = {k[4:]: v for k, v in x.items() if k.startswith("use|") and v > 1e-6}
    el_fuels = (prm["eft"]["el"] * x["eFT_liquids"] + prm["emeoh"]["el"] * x["e_methanol"] + prm["enh3"]["el"] * x["e_ammonia"]
                + prm["ech4"]["el"] * x["e_methane"])
    s["electricity_for_efuels_twh"] = el_fuels
    s["electricity_for_dac_twh"] = prm["dac"]["el"] * x["DAC_CO2_Mt"]
    s["electricity_for_heat_storage_twh"] = x["heat_wind_thermal_storage"] / prm["heat"]["tes_eff"]
    s["electrolyser_gw"] = el_fuels * 0.95 / (0.55 * 8.76)
    ev = sum(v * OPTIONS[k.split("|")[0]][k.split("|")[1]][1] for k, v in s["end_use_twh"].items()
             if OPTIONS[k.split("|")[0]][k.split("|")[1]][0] == "el_direct")
    s["electricity_vehicles_rail_twh"] = ev
    s["electricity_refineries_twh"] = s["kelp_refinery_el_twh"] + x["heat_heat_pump"] / prm["heat"]["hp_cop"] + x["heat_electric_boiler"] / prm["heat"]["eboiler_eff"]
    s["marginal_cad_mwh"] = {k: v for k, v in duals.items() if k != "co2"}
    s["co2_marginal_cad_t"] = duals.get("co2", 0.0)
    s["demand_twh"] = d
    s["fossil_cost_bn"] = {per: sum(FOSSIL[per][k] * d[k] for k in FOSSIL[per]) / 1000 for per in FOSSIL}
    s["fossil_co2_mt"] = sum(E.CO2_T_PER_MWH[k] * d[k] for k in d)
    dem = sum(d.values())
    s["demand_total_twh"] = dem
    s["dropin_supply_twh"] = _dropin_supply(x, s)
    s["export_share_of_dropin"] = x["export_dropin"] / s["dropin_supply_twh"] if s["dropin_supply_twh"] > 1e-9 else 0.0
    kelp_fuel = s["kelp_hc_twh"] + fuels["kelp ethanol"] + atj_from_kelp * prm["atj"]["eff"] + max(fuels["kelp biomethane (net of fleet)"], 0)
    s["kelp_fuel_twh"] = kelp_fuel
    s["kelp_share_pct"] = (kelp_fuel - s["kelp_hc_twh"] * s["export_share_of_dropin"]) / dem * 100
    lake_fuel = s["lake_hc_twh"] + fuels["lake ethanol"] + atj_from_lake * prm["atj"]["eff"] + max(fuels["lake biomethane (net of fleet)"], 0)
    s["lake_fuel_twh"] = lake_fuel
    s["lake_share_pct"] = (lake_fuel - s["lake_hc_twh"] * s["export_share_of_dropin"]) / dem * 100
    s["fertiliser_total_mt"] = {n: s["fertiliser_mt"][n] + s["lake_fertiliser_kt"][n] / 1e3 for n in ("N", "P", "K")}
    s["lifecycle"] = screening_lifecycle(s)
    s["cost_items_bn"] = cost_items(x, prm, s, systems, sysd, kel)
    r = prm["wacc"]
    s["capital_return_bn"] = sum(v * cs * f_ret(r, n) for v, cs, n in s["cost_items_bn"].values())
    s["build"] = build_list(s, prm, x, ev)
    return s


def _dropin_supply(x, s):
    return (s["kelp_hc_twh"] + s.get("lake_hc_twh", 0.0) + x["eFT_liquids"] + x["HEFA_waste_lipids"] + x["canola_HVO"] + x["forest_residue_HTL"]
            + x["agri_residue_FT"] + x["ATJ_jet_from_ethanol"])


def cost_items(x, prm, s, systems, sysd, kel):
    """Annual cost by item (CAD bn), with the capital share and asset life used to split it into a return on
    capital and depreciation for the corporate accounts."""
    a = prm["adder"]; nt = len(prm["wind"]["tiers"])
    wind_dir = sum(x[f"wind_t{i + 1}_direct"] for i in range(nt)); wind_flex = sum(x[f"wind_t{i + 1}_flex"] for i in range(nt))
    wind_gen = sum((x[f"wind_t{i + 1}_direct"] + x[f"wind_t{i + 1}_flex"]) * t["lcoe"] for i, t in enumerate(prm["wind"]["tiers"]))
    pv = x["pv_direct_day"] + x["pv_direct_shifted"] + x["pv_flex"]
    direct = wind_dir + x["pv_direct_day"] + x["pv_direct_shifted"] + x["hydro_redirected_from_exports"] + x["new_hydro"]
    flex = wind_flex + x["pv_flex"]
    use_cost = sum(x[f"use|{sg}|{o}"] * OPTIONS[sg][o][3] * OPTIONS[sg][o][1] for sg in OPTIONS for o in OPTIONS[sg])
    items = {
        "Wind generation": (wind_gen / 1000, 0.85, 25),
        "PV generation": (pv * prm["pv"]["lcoe"] / 1000, 0.85, 25),
        "New hydro": (x["new_hydro"] * prm["new_hydro"]["lcoe"] / 1000, 0.90, 60),
        "Redirected hydro exports": (x["hydro_redirected_from_exports"] * prm["hydro_redirect"]["cost"] / 1000, 0.0, 25),
        "Firming and balancing": ((wind_dir * a["wind"] + x["pv_direct_day"] * a["pv_day"] + x["pv_direct_shifted"] * a["pv_shift"]
                                   + wind_flex * a["flex_wind"] + x["pv_flex"] * a["flex_pv"]) / 1000, 0.70, 25),
        "Transmission and distribution": ((direct * a["network_direct"] + flex * a["network_flex"]) / 1000, 0.80, 40),
        "Charging, fuelling and delivery": (use_cost / 1000, 0.80, 20),
        "Trans-Canada Highway catenary (electric road)": (s["ers"]["cost_bn"], 0.90, 30),
        "Kelp farms and harvest": (s["kelp_farm_cost_bn"], 0.60, 15),
        "Kelp biorefineries": (s["kelp_refinery_cost_bn"], 0.70, 25),
        "Lake harvest (blooms, milfoil)": (s["lake_harvest_cost_bn"], 0.50, 18),
        "Lake HTL plants": (s["lake_refinery_cost_bn"], 0.70, 25),
        "Refinery heat": ((x["heat_wind_thermal_storage"] * prm["heat"]["tes_cost"] + x["heat_residue_boiler"] * prm["heat"]["bio_boiler_cost"]) / 1000, 0.75, 25),
        "Forest residues (feedstock)": (x["forest_residue_Modt"] * prm["forest"]["cost_odt"] / 1000, 0.15, 15),
        "Forest-residue HTL plants": (x["forest_residue_HTL"] * prm["forest"]["conv"] / 1000, 0.70, 25),
        "Agricultural-residue FT": (x["agri_residue_FT"] * (prm["agres"]["conv"] + prm["agres"]["cost_odt"] / prm["agres"]["mwh_per_odt"]) / 1000, 0.45, 25),
        "Waste-lipid and canola HVO": ((x["HEFA_waste_lipids"] * prm["hefa"]["cost"] + x["canola_HVO"] * prm["canola"]["cost"]) / 1000, 0.15, 25),
        "Grain ethanol and ATJ": ((x["grain_ethanol_existing"] * prm["crop_etoh"]["cost"] + x["ATJ_jet_from_ethanol"] * prm["atj"]["cost"]) / 1000, 0.40, 25),
        "Biomethane and bio-methanol": ((x["waste_biomethane"] * prm["waste_ch4"]["cost"] + x["bio_methanol_from_CH4"] * prm["biomeoh"]["cost"]) / 1000, 0.50, 20),
        "Electrofuel synthesis": ((x["eFT_liquids"] * prm["eft"]["cost"] + x["e_methanol"] * prm["emeoh"]["cost"] + x["e_ammonia"] * prm["enh3"]["cost"]
                                   + x["e_methane"] * prm["ech4"]["cost"]) / 1000, 0.70, 25),
        "CO2 capture (DAC, biogenic, kelp)": ((x["DAC_CO2_Mt"] * prm["dac"]["cost"] + x["other_biogenic_CO2_Mt"] * prm["bio_co2_other"]["cost"]
                                               + x["kelp_CO2_used_Mt"] * prm["kelp_co2_capture"]) / 1000, 0.60, 20),
        "Wind-assisted ships": (x["wind_assist_saving"] * 71.0 / 1000, 0.80, 20),
        "Export logistics": (s["export_logistics_bn"], 0.70, 30),
    }
    return items


def build_list(s, prm, x, ev):
    c = s["capacity_gw"]; u = UNIT_CAPEX
    shelf = sum(v for k, v in s["kelp_by_zone_km2"].items() if k.endswith(("shelf", "slope")))
    deep = s["kelp_total_km2"] - shelf
    efuel_gw = (x["eFT_liquids"] + x["e_methanol"] + x["e_ammonia"] + x["e_methane"]) / (0.55 * 8.76)
    b = {"Onshore wind (GW)": c["Onshore wind"], "PV (GW)": c["PV"], "New hydro (GW)": c["New hydro"],
         "Electrolysers (GW)": s["electrolyser_gw"], "DAC (Mt CO2/yr)": s["co2_mt"]["DAC"],
         "Kelp farms (km2)": s["kelp_total_km2"], "Kelp (Mt dry/yr)": s["kelp_dry_mt"], "Kelp (Mt wet/yr)": s["kelp_wet_mt"],
         "Kelp biorefineries (0.5 Mt dry/yr each)": s["kelp_dry_mt"] / 0.5,
         "Residue biorefineries (5 TWh/yr each)": (x["forest_residue_HTL"] + x["agri_residue_FT"]) / 5,
         "Harvest/transport vessels (1 Mt wet/yr each)": s["kelp_wet_mt"]}
    capex = {"Onshore wind": c["Onshore wind"] * u["Onshore wind (CAD/kW)"] / 1e3, "PV": c["PV"] * u["PV (CAD/kW)"] / 1e3,
             "New hydro": c["New hydro"] * u["New hydro (CAD/kW)"] / 1e3,
             "Electrolysers": s["electrolyser_gw"] * u["Electrolysers (CAD/kW)"] / 1e3,
             "E-fuel synthesis": efuel_gw * u["E-fuel synthesis (CAD/kW fuel)"] / 1e3,
             "DAC": s["co2_mt"]["DAC"] * u["DAC (CAD per t/yr)"] / 1e3,
             "Kelp farms": (shelf * u["Kelp farm shelf (CAD/km2)"] + deep * u["Kelp farm deep (CAD/km2)"]) / 1e9,
             "Kelp biorefineries": s["kelp_dry_mt"] * u["Kelp biorefinery (CAD per t dw/yr)"] / 1e3,
             "Residue biorefineries": (x["forest_residue_HTL"] + x["agri_residue_FT"]) * u["Residue biorefinery (CAD per MWh/yr of fuel)"] / 1e3,
             "Vessels": s["kelp_wet_mt"] * u["Vessel (CAD each)"] / 1e9,
             "ATJ plants": x["ATJ_jet_from_ethanol"] / (0.9 * 8.76) * u["ATJ plant (CAD/kW jet)"] / 1e3,
             "Refinery heat (thermal storage)": x["heat_wind_thermal_storage"] * u["Thermal storage + heaters (CAD per MWh_th/yr)"] / 1e3,
             "Charging and grid": (ev - s["ers"]["electricity_twh"]) * u["Charging and grid (CAD bn per TWh/yr of EV load)"],
             "Trans-Canada Highway catenary": s["ers"]["built_km"] * u["Highway catenary (CAD per route-km, both directions)"] / 1e9,
             "Lake Grid Harvesters": s["lake_harvesters"] * u["Lake Grid Harvester (CAD each)"] / 1e9,
             "Lake algae grids": s["lake_grid_km2"] * u["Lake algae grid (CAD/km2)"] / 1e9,
             "Lake HTL plants": s["lake_dry_kt"] / 1e3 * u["Kelp biorefinery (CAD per t dw/yr)"] * 1.3 / 1e3}
    b["Trans-Canada Highway catenary (route-km)"] = s["ers"]["built_km"]
    b["Catenary-hybrid trucks"] = s["ers"]["trucks"]
    b["Lake Grid Harvesters"] = s["lake_harvesters"]
    b["Lake algae grids (km2)"] = s["lake_grid_km2"]
    b["Lake biomass (kt dry/yr)"] = s["lake_dry_kt"]
    b["capex_bn"] = capex
    b["capex_total_bn"] = sum(capex.values())
    b["capex_per_year_2027_2050_bn"] = b["capex_total_bn"] / 24
    return b


def merge(base, over):
    b = copy.deepcopy(base)
    for k, v in over.items():
        b[k] = {**b[k], **v} if isinstance(v, dict) and isinstance(b.get(k), dict) else v
    return b


if __name__ == "__main__":
    s = solve(base_params())
    print({k: round(v, 2) for k, v in demand().items()}, round(sum(demand().values()), 1))
    print("cost", round(s["total_cost_bn"], 2), "energy", round(s["energy_cost_bn"], 2), "veh", round(s["vehicle_premium_bn"], 2),
          "fossil", {k: round(v, 2) for k, v in s["fossil_cost_bn"].items()}, "ret", round(s["capital_return_bn"], 2))
    print("gen", {k: round(v, 1) for k, v in s["generation_twh"].items()}, "GW", {k: round(v, 1) for k, v in s["capacity_gw"].items()})
    print("fuels", {k: round(v, 1) for k, v in s["fuels_twh"].items() if abs(v) > 1e-3})
    print("kelp km2", round(s["kelp_total_km2"]), s["kelp_by_zone_km2"], s["kelp_by_nutrient_method_km2"], s["kelp_by_route_km2"])
    print("end use", {k: round(v, 1) for k, v in s["end_use_twh"].items()})
    print("heat", {k: round(v, 2) for k, v in s["heat_twh_th"].items()}, "co2", {k: round(v, 2) for k, v in s["co2_mt"].items()})
    print("marg", {k: round(v) for k, v in s["marginal_cad_mwh"].items()}, "LCA", round(s["lifecycle"]["reduction_pct"], 1))
