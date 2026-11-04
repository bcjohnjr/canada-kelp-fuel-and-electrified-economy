"""Pan-Canadian SMR cogeneration screen: BWRX-300-class modules sited along the Trans-Canada corridor in provinces
that are pursuing nuclear power, selling electricity to the provincial grid (and, by allocation, to electrified
Highway 1 segments) and extraction steam to ethanol distilleries (E85), greenhouses, process heat and an optional
Atlantic kelp biorefinery. Comparator nodes test a hydro-grid site (British Columbia) and a Hudson Bay kelp node
(Churchill, Manitoba).

Standard-library Python. Writes outputs/*.json and outputs/*.csv. All parameters are explicit scenario assumptions
with the sources listed in PARAMS["_sources"]; none is a vendor quote, licence or contract.
"""
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"

from kelp_refinery_reference import nuc_eh  # per dry tonne mass and energy balance

PARAMS = {
    "module": {"mwe": 300.0, "mwth": 870.0, "availability": 0.90, "life_years": 40,
               "capex_cad_bn": {"noak_low": 3.5, "central": 4.4, "foak": 6.1},
               "fixed_om_cad_kw_yr": 150.0, "fuel_vom_cad_mwh": 12.0, "waste_decom_cad_mwh": 3.0},
    # Clean electricity ITC: 15% for property available for use before 2035 (labour requirements met); later modules
    # receive no credit unless the credit is extended ('itc="extended"' sensitivity)
    "finance": {"real_rate": {"low": 0.04, "central": 0.04, "high": 0.06, "merchant": 0.08}, "itc": 0.15, "itc_last_year": 2034},
    # electricity lost per MWth of extracted steam, by delivery temperature (second-law estimate, 35 C condenser)
    "extraction_penalty_mwe_per_mwth": {"high_150C": 0.19, "medium_80C": 0.09, "low_45C": 0.03},
    "heat_delivery_cad_mwh_th": 8.0,
    # Site development: the Darlington budget (CAD 20.9 bn for four units) is unit 1 CAD 6.1 bn + CAD 1.6 bn common
    # infrastructure + three later units at ~CAD 4.4 bn, so the CAD 4.4 bn module cost excludes a new site's common
    # infrastructure. Each new site carries it explicitly (low / central / high).
    "site": {"common_infra_cad_bn": {"none": 0.0, "low": 0.8, "central": 1.6, "high": 2.4},
             "pipe_cad_m_per_km": {"high_150C": 4.0, "medium_80C": 2.5}, "pipe_om_share": 0.01},
    "gas_boiler_efficiency": 0.85,
    "gas_co2_t_per_gj": 0.0501,          # 1,919 g CO2/m3 marketable gas / 38.3 MJ/m3 (ECCC offset-system factors)
    "carbon_price_path": {2026: 95, 2030: 115, 2035: 130, 2040: 140},   # federal benchmark reset (GLJ, May 2026)
    # fossil-free grid after a switch year: SMR output then displaces firm wind supply at the national model's shadow
    # value (el_direct dual 104.7 less the 25.5 network adder = 79.2 CAD/MWh) and its steam displaces heat pumps
    # (104.7 / COP 2.5 = 41.9 CAD/MWh_th); no CO2 is avoided and no capacity value is earned after the switch
    "decarbonised_grid": {"switch_year": 2045, "power_cad_mwh": 79.2, "heat_cad_mwh_th": 41.9},
    # capacity value: a scenario value near the cost of new entry of a peaking turbine (CAD 1,400/kW at 4-7% over 30 years
    # plus CAD 25/kW-yr fixed O&M = CAD 106-138/kW-yr); 0-90 tested
    "ccgt": {"heat_rate_gj_mwh": 6.9, "vom_cad_mwh": 4.0, "co2_t_mwh": 0.37, "capacity_value_cad_kw_yr": 120.0},
    "coal": {"heat_rate_gj_mwh": 10.5, "fuel_cad_gj": 2.5, "vom_cad_mwh": 6.0, "co2_t_mwh": 0.95},
    "ethanol_heat_mj_per_l": 7.25,       # 26,083 Btu/gal natural gas, US corn ethanol (RFA 2024 / GREET 2022)
    "ethanol_lhv_mj_per_l": 21.1,
    "greenhouse_heat_gj_per_m2_yr": 1.2,
    "highway1": {"traction_twh": 9.9338, "route_km": 7821.0},
    "kelp": {"fuel_value_cad_gj": {"market_2026": 45.0, "system_shadow_2041": 91.4},
             "ethanol_value_cad_gj": {"market_2026": 38.0, "system_shadow_2041": 91.4},
             "rng_value_cad_gj": 25.0, "n_cad_kg": 1.5, "p_cad_kg": 2.0, "k_cad_kg": 0.6, "eur_cad": 1.48,
             "biomass_cad_t": {"atl_shelf": 499.5, "pac_shelf": 369.5, "hb_shelf": 2200.2},
             "hb_forced_dry_mt": 0.75, "hb_forced_extra_cad_t": 942.2},
    "_sources": {
        "capex": "OPG Darlington New Nuclear: CAD 20.9 bn for four BWRX-300 (unit 1 CAD 6.1 bn + CAD 1.6 bn common); later units ~CAD 4.4 bn each",
        "carbon": "Federal benchmark after the 2026 reset: CAD 95 (2026), 115 (2030), 130 (2035), 140 (2040)",
        "grid": "ECCC federal offset system, Table 5.4 electricity consumption intensity (g CO2e/kWh)",
        "ethanol_heat": "Renewable Fuels Association (2024) using Argonne GREET 2022: 26,083 Btu natural gas per gallon",
        "kelp_biomass": "Archived national model siting solution: cheapest biomass by region (CAD/t dry)",
        "itc": "Federal Clean Electricity investment tax credit, 15%, for property available for use before 2035; available to provincial crown utilities",
    },
}

# Provincial data. grid_avg: ECCC consumption intensity (g/kWh). marginal: generator displaced after the 2030 federal
# coal phase-out (gas CCGT) unless 'coal' sensitivity. gas_cad_gj: delivered industrial gas (assumption).
# tch_km: approximate Trans-Canada Highway 1 length in the province (scaled to the archived 7,821 route-km).
PROVINCES = {
    "BC": dict(name="British Columbia", grid_avg=18, marginal="hydro", power_value_cad_mwh=74.0, gas_cad_gj=4.5, tch_km=1035, nuclear_policy="Clean Energy Act excludes nuclear; governing party open to review"),
    "AB": dict(name="Alberta", grid_avg=346, marginal="ccgt", gas_cad_gj=3.5, tch_km=470, nuclear_policy="public consultation on nuclear; large-reactor proposal (Peace River)"),
    "SK": dict(name="Saskatchewan", grid_avg=581, marginal="ccgt", gas_cad_gj=4.0, tch_km=655, nuclear_policy="SaskPower BWRX-300 near Estevan; final investment decision 2029"),
    "MB": dict(name="Manitoba", grid_avg=3, marginal="hydro", power_value_cad_mwh=48.0, gas_cad_gj=5.0, tch_km=490, nuclear_policy="no provincial SMR programme"),
    "ON": dict(name="Ontario", grid_avg=73, marginal="ccgt", gas_cad_gj=5.0, tch_km=2160, nuclear_policy="Darlington BWRX-300 under construction; further units planned"),
    "QC": dict(name="Quebec", grid_avg=3, marginal="hydro", power_value_cad_mwh=60.0, gas_cad_gj=6.0, tch_km=655, nuclear_policy="no SMR programme"),
    "NB": dict(name="New Brunswick", grid_avg=375, marginal="ccgt", gas_cad_gj=8.0, tch_km=516, nuclear_policy="Point Lepreau; advanced-reactor projects"),
    "NS": dict(name="Nova Scotia", grid_avg=628, marginal="ccgt", gas_cad_gj=9.0, tch_km=435, nuclear_policy="ban on utility nuclear lifted 2025; SMR MOU with Ontario"),
    "NL": dict(name="Newfoundland and Labrador", grid_avg=17, marginal="hydro", power_value_cad_mwh=60.0, gas_cad_gj=9.0, tch_km=905, nuclear_policy="no SMR programme"),
}

# Sites: modules, first year and heat users. Each user: grade, MWth per module, load factor (share of operating hours the
# user takes heat), pipe length (km) and a description. Users and distances are screening assumptions that need
# confirmation with the named or proposed heat customers; new users are built beside the reactor site.
SITES = [
    dict(id="ON_CHATHAM", prov="ON", place="Chatham-Kent industrial area (Highway 401)", modules=2, first_year=2034, fleet=True,
         users=[dict(grade="high_150C", mwth=60.0, lf=0.90, pipe_km=3.0, user="Chatham grain-ethanol distillery (existing) and expansion"),
                dict(grade="medium_80C", mwth=140.0, lf=0.45, pipe_km=2.0, user="new greenhouse and grain-drying cluster beside the site (seasonal)")]),
    dict(id="SK_BELLE_PLAINE", prov="SK", place="Belle Plaine / Moose Jaw (Highway 1)", modules=2, first_year=2037, fleet=True,
         users=[dict(grade="high_150C", mwth=180.0, lf=0.90, pipe_km=5.0, user="Belle Plaine ethanol distillery and potash solution-mining steam"),
                dict(grade="medium_80C", mwth=20.0, lf=0.45, pipe_km=2.0, user="greenhouses beside the site (seasonal)")]),
    dict(id="AB_HEARTLAND", prov="AB", place="Alberta Industrial Heartland, Fort Saskatchewan (Yellowhead Highway 16)", modules=2, first_year=2038, fleet=True,
         users=[dict(grade="high_150C", mwth=200.0, lf=0.90, pipe_km=5.0, user="petrochemical and upgrader process steam; ethanol distillation")]),
    dict(id="NB_SAINT_JOHN", prov="NB", place="East Saint John industrial area", modules=2, first_year=2035, fleet=True,
         users=[dict(grade="high_150C", mwth=120.0, lf=0.90, pipe_km=5.0, user="Saint John refinery process steam"),
                dict(grade="high_150C", mwth=80.0, lf=0.85, pipe_km=1.0, user="Atlantic kelp biorefinery built beside the site")]),
    dict(id="NS_POINT_TUPPER", prov="NS", place="Point Tupper / Port Hawkesbury (Highway 104)", modules=2, first_year=2036, fleet=True,
         users=[dict(grade="high_150C", mwth=120.0, lf=0.90, pipe_km=3.0, user="Port Hawkesbury paper-mill process steam"),
                dict(grade="high_150C", mwth=80.0, lf=0.85, pipe_km=1.0, user="Atlantic kelp biorefinery built beside the site")]),
    dict(id="BC_KAMLOOPS", prov="BC", place="Kamloops (Highway 1) - test site", modules=1, first_year=2040, fleet=False,
         users=[dict(grade="high_150C", mwth=100.0, lf=0.90, pipe_km=3.0, user="pulp-mill process steam")]),
    dict(id="MB_CHURCHILL", prov="MB", place="Churchill, Hudson Bay - test site", modules=1, first_year=2040, fleet=False,
         users=[dict(grade="high_150C", mwth=150.0, lf=0.60, pipe_km=1.0, user="Hudson Bay kelp biorefinery (seasonal biomass)")]),
]
for _s in SITES:   # nameplate MWth per module by grade, and the load-weighted average actually sold
    _s["heat"] = {}; _s["heat_avg"] = {}
    for _u in _s["users"]:
        _s["heat"][_u["grade"]] = _s["heat"].get(_u["grade"], 0.0) + _u["mwth"]
        _s["heat_avg"][_u["grade"]] = _s["heat_avg"].get(_u["grade"], 0.0) + _u["mwth"] * _u["lf"]
    _s["uses"] = "; ".join(f"{_u['user']} ({_u['grade'].split('_')[1]}, {_u['mwth']:.0f} MWth/module, load factor {_u['lf']:.2f}, {_u['pipe_km']:.0f} km)" for _u in _s["users"])


def carbon_price(year):
    pts = sorted(PARAMS["carbon_price_path"].items())
    if year <= pts[0][0]:
        return pts[0][1]
    for (y0, p0), (y1, p1) in zip(pts, pts[1:]):
        if year <= y1:
            return p0 + (p1 - p0) * (year - y0) / (y1 - y0)
    return pts[-1][1]


def crf(r, n):
    return r * (1 + r) ** n / ((1 + r) ** n - 1)


def heat_value_cad_mwh_th(gas_cad_gj, cp):
    """Avoided natural-gas boiler cost per MWh of delivered steam, including carbon, less delivery cost."""
    per_gj = (gas_cad_gj + cp * PARAMS["gas_co2_t_per_gj"]) / PARAMS["gas_boiler_efficiency"]
    return per_gj * 3.6 - PARAMS["heat_delivery_cad_mwh_th"]


def power_value(prov, cp, marginal=None):
    """Value of one MWh of nuclear electricity (CAD/MWh) and the CO2 it displaces (t/MWh)."""
    P = PROVINCES[prov]; m = marginal or P["marginal"]
    if m == "hydro":
        return P["power_value_cad_mwh"], P["grid_avg"] / 1e3
    if m == "grid_avg":
        g = PARAMS["ccgt"]; co2 = P["grid_avg"] / 1e3
        return g["heat_rate_gj_mwh"] * P["gas_cad_gj"] + g["vom_cad_mwh"] + co2 * cp, co2
    g = PARAMS[m]
    fuel = g["heat_rate_gj_mwh"] * (P["gas_cad_gj"] if m == "ccgt" else g["fuel_cad_gj"])
    return fuel + g["vom_cad_mwh"] + g["co2_t_mwh"] * cp, g["co2_t_mwh"]


def itc_rate(site, itc):
    """Credit applied to a site's capital: by in-service year under current law, or to every site if extended."""
    F = PARAMS["finance"]
    if itc == "extended": return F["itc"]
    if itc == "law": return F["itc"] if site["first_year"] <= F["itc_last_year"] else 0.0
    return 0.0


def site_year(site, year, capex_case="central", rate_case="central", itc="law", marginal=None, carbon_scale=1.0,
              availability=None, decarb_year=None, common="central", capacity_value=None, lf_scale=1.0):
    """Annual physical and money flows for one site in one calendar year (all modules on line)."""
    M = PARAMS["module"]; n = site["modules"]; P = PROVINCES[site["prov"]]
    av = availability or M["availability"]; h = 8760 * av
    cp = carbon_price(year) * carbon_scale
    havg = {k: min(v * lf_scale, site["heat"][k]) for k, v in site["heat_avg"].items()}   # MWth per module, load-weighted
    pen = sum(havg.get(k, 0.0) * v for k, v in PARAMS["extraction_penalty_mwe_per_mwth"].items())
    net_mwe = M["mwe"] - pen
    e_twh = n * net_mwe * h / 1e6
    heat_twh = {k: n * v * h / 1e6 for k, v in havg.items()}
    pv, co2_mwh = power_value(site["prov"], cp, marginal)
    hv = heat_value_cad_mwh_th(P["gas_cad_gj"], cp)
    cv = PARAMS["ccgt"]["capacity_value_cad_kw_yr"] if capacity_value is None else capacity_value
    cap_value = (cv * n * net_mwe * 1e3 * av if (marginal or P["marginal"]) != "hydro" else 0.0)
    if decarb_year and year >= decarb_year:
        D = PARAMS["decarbonised_grid"]; pv, co2_mwh, hv, cap_value = D["power_cad_mwh"], 0.0, D["heat_cad_mwh_th"], 0.0
    rev_power = e_twh * 1e6 * pv
    rev_heat = sum(heat_twh.values()) * 1e6 * hv
    SP = PARAMS["site"]
    common_cad = SP["common_infra_cad_bn"][common] * 1e9
    pipes_cad = sum(u["pipe_km"] * SP["pipe_cad_m_per_km"][u["grade"]] * 1e6 for u in site["users"])
    capex = (M["capex_cad_bn"][capex_case] * 1e9 * n + common_cad) * (1 - itc_rate(site, itc))
    r = PARAMS["finance"]["real_rate"][rate_case]
    ann_cap = (capex + pipes_cad) * crf(r, M["life_years"])
    gross_twh = n * M["mwe"] * h / 1e6
    opex = (M["fixed_om_cad_kw_yr"] * n * M["mwe"] * 1e3 + (M["fuel_vom_cad_mwh"] + M["waste_decom_cad_mwh"]) * gross_twh * 1e6
            + pipes_cad * SP["pipe_om_share"])
    co2_power = e_twh * 1e6 * co2_mwh / 1e6
    co2_heat = (0.0 if (decarb_year and year >= decarb_year) else 1.0) * sum(heat_twh.values()) * 3.6e6 * PARAMS["gas_co2_t_per_gj"] / PARAMS["gas_boiler_efficiency"] / 1e6
    margin = rev_power + rev_heat + cap_value - ann_cap - opex
    return dict(site=site["id"], prov=site["prov"], year=year, modules=n, carbon_price=cp, net_mwe_per_module=net_mwe,
                electricity_twh=e_twh, heat_twh=sum(heat_twh.values()), heat_by_grade_twh=heat_twh,
                power_value_cad_mwh=pv, heat_value_cad_mwh_th=hv, revenue_power_cad=rev_power, revenue_heat_cad=rev_heat,
                capacity_value_cad=cap_value, annualised_capital_cad=ann_cap, opex_cad=opex, margin_cad=margin,
                lcoe_cad_mwh=(ann_cap + opex) / (gross_twh * 1e6), co2_avoided_mt=co2_power + co2_heat,
                co2_power_mt=co2_power, co2_heat_mt=co2_heat, capex_cad=capex, pipes_cad=pipes_cad, common_infra_cad=common_cad)


def site_npv(site, **kw):
    """Net present value over the economic life from the first operating year (real, CAD), annuity-consistent."""
    M = PARAMS["module"]; r = PARAMS["finance"]["real_rate"][kw.get("rate_case", "central")]
    y0 = site["first_year"]; npv = 0.0; abate = 0.0; disc_abate = 0.0
    for t in range(M["life_years"]):
        s = site_year(site, y0 + t, **kw)
        df = (1 + r) ** -(t + 1)
        npv += s["margin_cad"] * df
        abate += s["co2_avoided_mt"]; disc_abate += s["co2_avoided_mt"] * df
    first = site_year(site, y0, **kw)
    # cost of abatement: present value of (cost - non-carbon revenue) per discounted tonne
    nc = 0.0
    for t in range(M["life_years"]):
        s = site_year(site, y0 + t, carbon_scale=0.0, **{k: v for k, v in kw.items() if k != "carbon_scale"})
        nc += -s["margin_cad"] * (1 + r) ** -(t + 1)
    return dict(site=site["id"], prov=site["prov"], npv_cad_bn=npv / 1e9, lifetime_co2_mt=abate,
                abatement_cost_cad_t=(nc / (disc_abate * 1e6)) if disc_abate > 0 else None,
                first_year=first)


def highway_allocation():
    H = PARAMS["highway1"]; tot = sum(p["tch_km"] for p in PROVINCES.values())
    return {k: dict(km=p["tch_km"] * H["route_km"] / tot, traction_twh=H["traction_twh"] * p["tch_km"] / tot) for k, p in PROVINCES.items()}


def kelp_economics(biomass_key, valuation, heat_value_mwh_th, power_value_mwh):
    """Per dry tonne economics of the reference kelp biorefinery (CAD)."""
    K = PARAMS["kelp"]; r = nuc_eh()
    fuel = r["hc_gj"] * K["fuel_value_cad_gj"][valuation] + r["ethanol_gj"] * K["ethanol_value_cad_gj"][valuation] + r["ch4_gj"] * K["rng_value_cad_gj"]
    fert = r["fert_n_kg"] * K["n_cad_kg"] + r["fert_p_kg"] * K["p_cad_kg"] + r["fert_k_kg"] * K["k_cad_kg"]
    process = r["cost_eur"] * K["eur_cad"]
    energy = r["el_mwh"] * power_value_mwh + r["heat_mwh_th"] * heat_value_mwh_th
    biomass = K["biomass_cad_t"][biomass_key]
    margin = fuel + fert - process - energy - biomass
    return dict(biomass_key=biomass_key, valuation=valuation, revenue_fuel=fuel, revenue_fertiliser=fert, process=process,
                energy=energy, biomass=biomass, margin=margin, breakeven_biomass_cad_t=fuel + fert - process - energy,
                fuel_gj_per_t=r["hc_gj"] + r["ethanol_gj"] + r["ch4_gj"], ethanol_l_per_t=r["ethanol_t"] * 1000 / 0.789,
                heat_mwh_th_per_t=r["heat_mwh_th"], el_mwh_per_t=r["el_mwh"])


def main():
    OUT.mkdir(exist_ok=True)
    year = 2041
    base = {s["id"]: site_year(s, year) for s in SITES}
    npv = {s["id"]: site_npv(s) for s in SITES}
    # sensitivities on NPV (CAD bn) for each site
    cases = {
        "central": {}, "capex_noak_3p5": dict(capex_case="noak_low"), "capex_foak_6p1": dict(capex_case="foak"),
        "rate_6pct": dict(rate_case="high"), "rate_8pct_merchant": dict(rate_case="merchant"), "no_itc": dict(itc=False),
        "itc_extended": dict(itc="extended"), "carbon_realisation_75": dict(carbon_scale=0.75),
        "carbon_realisation_50": dict(carbon_scale=0.50),
        "carbon_frozen_95": dict(carbon_scale=None), "displaces_grid_average": dict(marginal="grid_avg"),
        "displaces_coal": dict(marginal="coal"), "availability_85": dict(availability=0.85),
        "grid_fossil_free_2045": dict(decarb_year=2045),
        "no_common_infrastructure": dict(common="none"), "common_infrastructure_low_0p8": dict(common="low"),
        "common_infrastructure_high_2p4": dict(common="high"),
        "capacity_value_90": dict(capacity_value=90.0), "capacity_value_60": dict(capacity_value=60.0),
        "capacity_value_0": dict(capacity_value=0.0), "heat_load_factor_minus_20pct": dict(lf_scale=0.8),
        "itc_extended_no_common_infrastructure": dict(itc="extended", common="none"),
        "capex_3p5_common_low": dict(capex_case="noak_low", common="low"), "grid_fossil_free_2040": dict(decarb_year=2040),
    }
    sens = []
    for s in SITES:
        for name, kw in cases.items():
            if name == "carbon_frozen_95":
                M = PARAMS["module"]; r = PARAMS["finance"]["real_rate"]["central"]; v = 0.0
                for t in range(M["life_years"]):
                    yy = s["first_year"] + t
                    v += site_year(s, yy, carbon_scale=95.0 / carbon_price(yy))["margin_cad"] * (1 + r) ** -(t + 1)
                sens.append(dict(site=s["id"], case=name, npv_cad_bn=v / 1e9))
                continue
            if name == "displaces_coal" and (PROVINCES[s["prov"]]["marginal"] == "hydro" or s["prov"] == "ON"):  # Ontario has no coal
                continue
            sens.append(dict(site=s["id"], case=name, npv_cad_bn=site_npv(s, **kw)["npv_cad_bn"]))
    # break-even capex per module (CAD bn) at central finance, ITC included
    be = {}
    for s in SITES:
        lo, hi = 0.5, 12.0
        for _ in range(60):
            mid = (lo + hi) / 2
            PARAMS["module"]["capex_cad_bn"]["_probe"] = mid
            v = site_npv(s, capex_case="_probe")["npv_cad_bn"]
            lo, hi = (mid, hi) if v > 0 else (lo, mid)
        be[s["id"]] = (lo + hi) / 2
    PARAMS["module"]["capex_cad_bn"].pop("_probe", None)
    hw = highway_allocation()
    # E85: ethanol distilled with nuclear steam at sites whose high-grade heat serves distillation
    eth_share = {"ON_CHATHAM": 1.0, "SK_BELLE_PLAINE": 0.6, "AB_HEARTLAND": 0.25}
    e85 = {}
    for sid, share in eth_share.items():
        b = base[sid]; q = b["heat_by_grade_twh"].get("high_150C", 0.0) * share * 3.6e9 / PARAMS["ethanol_heat_mj_per_l"] / 1e9  # billion L
        e85[sid] = dict(ethanol_bl=q, e85_bl=q / 0.75, ethanol_pj=q * PARAMS["ethanol_lhv_mj_per_l"],
                        heat_co2_avoided_g_per_mj=PARAMS["ethanol_heat_mj_per_l"] * PARAMS["gas_co2_t_per_gj"] / PARAMS["gas_boiler_efficiency"] / PARAMS["ethanol_lhv_mj_per_l"] * 1e3)
    # kelp: Atlantic (NS, NB) and Hudson Bay (Churchill) at each node's heat and power value
    kelp = []
    for sid, key in (("NS_POINT_TUPPER", "atl_shelf"), ("NB_SAINT_JOHN", "atl_shelf"), ("MB_CHURCHILL", "hb_shelf")):
        b = base[sid]
        for val in ("market_2026", "system_shadow_2041"):
            k = kelp_economics(key, val, b["heat_value_cad_mwh_th"], b["power_value_cad_mwh"]); k["site"] = sid; kelp.append(k)
    ns = base["NS_POINT_TUPPER"]; per_t = nuc_eh()["heat_mwh_th"]
    kelp_capacity_mt = ns["heat_by_grade_twh"]["high_150C"] * 1e6 / per_t / 1e6
    hb_mod = base["MB_CHURCHILL"]; hb_capacity_mt = hb_mod["heat_by_grade_twh"]["high_150C"] * 1e6 / per_t / 1e6
    fleet = [s for s in SITES if s["fleet"]]
    tot = dict(modules=sum(s["modules"] for s in fleet), gwe=sum(s["modules"] for s in fleet) * 0.3,
               electricity_twh=sum(base[s["id"]]["electricity_twh"] for s in fleet),
               heat_twh=sum(base[s["id"]]["heat_twh"] for s in fleet),
               co2_avoided_mt=sum(base[s["id"]]["co2_avoided_mt"] for s in fleet),
               margin_cad_bn=sum(base[s["id"]]["margin_cad"] for s in fleet) / 1e9,
               capex_cad_bn=sum(base[s["id"]]["capex_cad"] for s in fleet) / 1e9,
               capex_before_itc_cad_bn=sum(s["modules"] for s in fleet) * PARAMS["module"]["capex_cad_bn"]["central"]
               + len(fleet) * PARAMS["site"]["common_infra_cad_bn"]["central"],
               npv_cad_bn=sum(npv[s["id"]]["npv_cad_bn"] for s in fleet),
               highway_traction_fleet_provinces_twh=sum(hw[p]["traction_twh"] for p in ("ON", "SK", "AB", "NB", "NS")),
               ethanol_bl=sum(v["ethanol_bl"] for v in e85.values()), e85_bl=sum(v["e85_bl"] for v in e85.values()))
    deploy = []
    for y in range(2034, 2042):
        on = [s for s in fleet if s["first_year"] <= y]
        deploy.append(dict(year=y, modules=sum(s["modules"] for s in on),
                           electricity_twh=sum(site_year(s, y)["electricity_twh"] for s in on),
                           co2_avoided_mt=sum(site_year(s, y)["co2_avoided_mt"] for s in on)))
    summary = dict(year=year, fleet_2041=tot, sites_2041=base, npv=npv, breakeven_capex_cad_bn_per_module=be,
                   highway_allocation=hw, e85=e85, kelp=kelp, kelp_capacity_ns_mt_dry=kelp_capacity_mt,
                   kelp_capacity_churchill_mt_dry=hb_capacity_mt, deployment=deploy, sites=SITES,
                   provinces=PROVINCES, params={k: v for k, v in PARAMS.items()})
    (OUT / "smr_canada_summary.json").write_text(json.dumps(summary, indent=1, default=str))
    with (OUT / "smr_site_sensitivity.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["site", "case", "npv_cad_bn"]); w.writeheader(); w.writerows(sens)
    with (OUT / "smr_sites_2041.csv").open("w", newline="") as f:
        keys = [k for k in base["ON_CHATHAM"] if k != "heat_by_grade_twh"]
        w = csv.DictWriter(f, fieldnames=keys); w.writeheader()
        for v in base.values():
            w.writerow({k: v[k] for k in keys})
    with (OUT / "kelp_biorefinery_economics.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(kelp[0].keys())); w.writeheader(); w.writerows(kelp)
    print(json.dumps({"fleet_2041": tot, "npv": {k: round(v["npv_cad_bn"], 2) for k, v in npv.items()},
                      "abatement_cost": {k: (round(v["abatement_cost_cad_t"]) if v["abatement_cost_cad_t"] else None) for k, v in npv.items()},
                      "breakeven_capex": {k: round(v, 2) for k, v in be.items()}}, indent=1))


if __name__ == "__main__":
    main()
