"""Screening well-to-wheel lifecycle greenhouse-gas accounting for the domestic part of the solved system.

This layer evaluates the economic solution; it does not change the optimiser and is not an ISO 14040/44 process
LCA. Functional unit: one year of the modelled Canadian transport energy service. Exported fuel is excluded
(its emissions are counted where it is burned). Vehicle manufacture is excluded. Electricity-generation factors
are cradle-to-grave; fuel factors are fuel-cycle intensities that already include the energy used to make the
fuel, so that electricity is not counted a second time.

Central factors
  road gasoline/diesel 92 gCO2e/MJ (IPCC AR6 WGIII Ch. 10); fossil jet 89 (ICAO CORSIA); marine 93.3 (IMO)
  e-fuels with renewable electricity 12; renewable ammonia 3.2 (IPCC)
  forest and agricultural residue fuels 15 (range 8-30; residue removal and soil-carbon effects), waste lipids 20,
  biomethane 20, existing grain ethanol 35 (25-50), canola HVO 45 (30-60, incl. indirect land use)
  offshore macroalgal fuels 22 (Greene et al. 2020; range 14-29); lake bloom and milfoil fuels as residue fuels (15)
  electricity: onshore wind 9.3, PV 40, hydro 15 (range 4-60 for reservoir emissions) gCO2e/kWh
  (NREL 2021; IPCC AR5 Annex III)
"""

FOSSIL_G_PER_MJ = {"ldv_gasoline": 92.0, "ldv_diesel": 92.0, "hdv": 92.0, "rail": 92.0, "offroad": 92.0,
                   "aviation": 89.0, "shipping": 93.3}
ELECTRICITY_G_PER_KWH = {"Onshore wind": 9.3, "PV": 40.0, "Hydro (redirected exports)": 15.0, "New hydro": 15.0}

FUEL_G_PER_MJ = {
    "eFT_liquids": 12.0, "e_methanol": 12.0, "e_ammonia": 3.2, "e_methane": 12.0,
    "ATJ_jet_from_ethanol": 35.0, "waste_biomethane": 20.0, "HEFA_waste_lipids": 20.0, "canola_HVO": 45.0,
    "forest_residue_HTL": 15.0, "agri_residue_FT": 15.0, "grain_ethanol_existing": 35.0,
    "kelp HTL diesel/jet": 22.0, "kelp ethanol": 22.0, "kelp biomethane (net of fleet)": 22.0,
    "lake HTL diesel/jet": 15.0, "lake ethanol": 15.0, "lake biomethane (net of fleet)": 15.0,
}
RES = ("forest_residue_HTL", "agri_residue_FT")
CROP = ("ATJ_jet_from_ethanol", "grain_ethanol_existing", "canola_HVO")
WASTE = ("waste_biomethane", "HEFA_waste_lipids")
SEA = ("kelp HTL diesel/jet", "kelp ethanol", "kelp biomethane (net of fleet)")
LAKE = ("lake HTL diesel/jet", "lake ethanol", "lake biomethane (net of fleet)")
EF = ("eFT_liquids", "e_methanol", "e_methane")
DROPIN = ("eFT_liquids", "HEFA_waste_lipids", "canola_HVO", "forest_residue_HTL", "agri_residue_FT", "ATJ_jet_from_ethanol",
          "kelp HTL diesel/jet", "lake HTL diesel/jet")

LOW = {"electricity": {"Onshore wind": 7.0, "PV": 20.0, "Hydro (redirected exports)": 4.0, "New hydro": 4.0},
       "residue": 8.0, "crop": 25.0, "canola": 30.0, "waste": 14.0, "kelp": 14.0, "efuel": 8.0, "ammonia": 2.0}
HIGH = {"electricity": {"Onshore wind": 15.0, "PV": 60.0, "Hydro (redirected exports)": 60.0, "New hydro": 60.0},
        "residue": 30.0, "crop": 50.0, "canola": 60.0, "waste": 30.0, "kelp": 29.0, "efuel": 25.0, "ammonia": 19.0}


def _electricity_intensity(s, factors):
    gen = s["generation_twh"]
    tot = sum(gen.values())
    return sum(gen[k] * factors[k] for k in gen) / tot if tot > 0 else 0.0


def _fuel_factors(b):
    f = dict(FUEL_G_PER_MJ)
    for k in RES + LAKE: f[k] = b["residue"]
    for k in ("ATJ_jet_from_ethanol", "grain_ethanol_existing"): f[k] = b["crop"]
    f["canola_HVO"] = b["canola"]
    for k in WASTE: f[k] = b["waste"]
    for k in SEA: f[k] = b["kelp"]
    for k in EF: f[k] = b["efuel"]
    f["e_ammonia"] = b["ammonia"]
    return f


def fossil_lifecycle_mt(s):
    # 1 TWh = 3.6e9 MJ; 1 Mt = 1e12 g -> 0.0036
    return sum(s["demand_twh"].get(k, 0.0) * v * 0.0036 for k, v in FOSSIL_G_PER_MJ.items())


def domestic_fuels(s):
    """Fuel volumes used in Canada: drop-in volumes net of the exported share."""
    keep = 1 - s.get("export_share_of_dropin", 0.0)
    return {k: max(v, 0.0) * (keep if k in DROPIN else 1.0) for k, v in s["fuels_twh"].items()}


def lowcarbon_lifecycle_mt(s, electricity_factors=None, fuel_factors=None, parts=False):
    ef = electricity_factors or ELECTRICITY_G_PER_KWH
    ff = fuel_factors or FUEL_G_PER_MJ
    e_ci = _electricity_intensity(s, ef)
    direct_el = s["electricity_vehicles_rail_twh"] * e_ci * 0.001
    by = {k: v * ff[k] * 0.0036 for k, v in domestic_fuels(s).items()}
    if parts:
        return {"Direct electric transport": direct_el,
                "Kelp fuels": sum(by[k] for k in SEA),
                "Residue and lake fuels": sum(by[k] for k in RES + LAKE),
                "Crop and waste biofuels": sum(by[k] for k in CROP + WASTE),
                "Electrofuels": sum(by[k] for k in EF) + by["e_ammonia"]}
    return direct_el + sum(by.values())


def screening_lifecycle(s):
    fossil = fossil_lifecycle_mt(s)
    low = lowcarbon_lifecycle_mt(s)
    lo = lowcarbon_lifecycle_mt(s, LOW["electricity"], _fuel_factors(LOW))
    hi = lowcarbon_lifecycle_mt(s, HIGH["electricity"], _fuel_factors(HIGH))
    return {"fossil_wtw_mtco2e": fossil, "lowcarbon_wtw_mtco2e": low, "lowcarbon_factor_sensitivity_mtco2e": [lo, hi],
            "avoided_wtw_mtco2e": fossil - low, "reduction_pct": 100.0 * (fossil - low) / fossil,
            "reduction_factor_sensitivity_pct": [100.0 * (fossil - hi) / fossil, 100.0 * (fossil - lo) / fossil],
            "parts_mtco2e": lowcarbon_lifecycle_mt(s, parts=True),
            "electricity_ci_gco2e_kwh": _electricity_intensity(s, ELECTRICITY_G_PER_KWH)}


def sampled_lifecycle(s, rng):
    tri = rng.triangular
    el = {"Onshore wind": tri(7, 9.3, 15), "PV": tri(20, 40, 60), "Hydro (redirected exports)": tri(4, 15, 60)}
    el["New hydro"] = el["Hydro (redirected exports)"]
    b = {"residue": tri(8, 15, 30), "crop": tri(25, 35, 50), "canola": tri(30, 45, 60), "waste": tri(14, 20, 30),
         "kelp": tri(14, 22, 29), "efuel": tri(8, 12, 25), "ammonia": tri(2, 3.2, 19)}
    low = lowcarbon_lifecycle_mt(s, el, _fuel_factors(b))
    fossil = fossil_lifecycle_mt(s)
    return low, fossil, 100.0 * (fossil - low) / fossil
