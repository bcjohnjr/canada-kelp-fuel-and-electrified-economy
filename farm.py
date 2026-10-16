"""Native-kelp farms in Canadian waters: zones, yields, nutrient supply and biomass cost (CAD 2026).

Species: the highest-yielding kelp native to each coast is farmed everywhere.
  Pacific    Macrocystis pyrifera (giant kelp), native along the British Columbia coast, the fastest-growing kelp;
             perennial, it regrows after partial harvest of its canopy, so a grid is harvested several times a year
             (Navarrete et al. 2021 for depth-cycled growth).
  Atlantic   Saccharina latissima (sugar kelp), the highest-yielding native kelp in cultivation, farmed in Nova
             Scotia, New Brunswick and Newfoundland; seeded in autumn and harvested in spring and early summer.
  Gulf of St Lawrence, north-east Newfoundland and Labrador
             Saccharina latissima, farmed in Quebec (Gaspe, Magdalen Islands) and New Brunswick (Baie des Chaleurs)
             on long-lines sunk below the winter ice and harvested in late spring and summer.
  Hudson Bay Saccharina latissima, the fastest-growing of the kelps recorded in Canadian Arctic surveys that include
             the Hudson Bay complex (with the slow-growing Laminaria solidungula; Filbee-Dexter et al. 2022, Front.
             Mar. Sci. 9:754074, who found sparse kelp cover in Hudson Bay itself, about 5%, and kelp biomass rising
             with open-water days).
  All zones are harvested by the cable-guided Grid Harvester (6-m head, 100-m span, 416.7 t wet/h at 3 knots).
             Lines are kept below the ice for about eight months and harvested in the open-water season (August to
             October). The surface layer is stratified by river inflow and nitrate-poor in summer, so natural nutrient
             supply is low and depth cycling reaches only part of the deeper nitrate.
Seasonal-ice zones carry a cost factor for ice-rated submerged moorings and a harvest fleet that works in a short
season: 1.25 (Gulf), 1.40 (Labrador and north-east Newfoundland) and 1.60 (Hudson Bay). Their design yields (5, 4
and 2.5 t dry ha-1 yr-1; learning case 7.5, 6 and 3.75) are screening assumptions scaled from the Atlantic value by
growing-season length, not measurements.
Yields are design values for dense, multiply harvested long-line or grid farms, not today's commercial averages.
Commercial offshore kelp farming in the Faroe Islands harvested 0.9-1.4 t dry ha-1 yr-1 at a cost of EUR 9-37 per
dry kg (Bak et al. 2018, Algal Res. 33:36), and Danish S. latissima trials gave 5-21 t fresh ha-1 per season
(Boderskov et al. 2023, Front. Mar. Sci. 10:992179). Fuel-oriented designs assume 10-20 t dry ha-1 yr-1 (Greene et
al. 2020; ARPA-E MARINER). The central yields here (8 Pacific, 6 Atlantic) lie between the two; the learning case
uses 12 and 9, and the Monte Carlo samples 3-15.

Nutrient demand is met partly by natural supply (winter mixing, summer upwelling off Vancouver Island, tidal
mixing in Hecate Strait and the Bay of Fundy) and partly by one of:
  wave_pump      passive wave-driven pipe pump; field test off Hawaii delivered 16-45 m3/h per 0.75 m x 300 m
                 tube, ~10% of predictions, and failed structurally (White et al. 2010).
  wave_pump_xl   the same principle at 1.5 m diameter.
  solar_pipe     wind- or PV-driven low-head pump in a 1.6 m x 400 m pipe.
  depth_cycling  farm grids lowered to the nitracline at night and raised to the light by day (Navarrete et al.
                 2021, Macrocystis, 9-80 m daily). The north-east Pacific holds 30-40 uM nitrate below 100-150 m;
                 the Scotian Shelf and slope hold 10-20 uM, so cycling meets only part of the Atlantic need.
  A salt fountain is not possible in either ocean (the deep water is not fresher than the surface water).
"""
from dataclasses import dataclass, asdict
import json
from pathlib import Path

SECONDS_YR = 3.156e7
CRF = lambda r, n: r * (1 + r) ** n / ((1 + r) ** n - 1)
OUT = Path(__file__).resolve().parent / "outputs"
REF_YIELD = 15.0   # t dry/ha/yr at which the base farm cost is defined


@dataclass
class Zone:
    name: str
    yield_t_ha: float           # t dry / ha / yr with adequate nutrients
    n_frac: float               # tissue N, fraction of dry mass
    natural_n_share: float      # share of N demand met by natural supply
    nitrate_300m: float         # uM
    nitrate_400m: float
    nitrate_700m: float
    salt_fountain_ok: bool
    depth_cycle_effect: float   # share of the supplemental N need that depth cycling can meet
    species: str
    area_km2: dict              # free area by distance band (outside lanes, ports, ice, beyond 6 nm, net of conserved share)
    mid_km: dict
    ice_factor: float = 1.0


def _areas():
    """Free areas from spatial.py (outputs/marine_space.json); falls back to the archived values."""
    archived = {"pac_shelf": {"0-50": 23593.0, "50-100": 8696.0, "100-200": 1018.0},
                "pac_slope": {"0-50": 9117.0, "50-100": 8591.0, "100-200": 1857.0},
                "pac_deep": {"0-50": 7037.0, "50-100": 19114.0, "100-200": 48580.0, "200-370": 88734.0},
                "atl_shelf": {"0-50": 42626.0, "50-100": 44416.0, "100-200": 94442.0, "200-370": 88718.0},
                "atl_slope": {"0-50": 8072.0, "50-100": 12233.0, "100-200": 17317.0, "200-370": 12712.0},
                "atl_deep": {"100-200": 6039.0, "200-370": 120068.0}}
    f = OUT / "marine_space.json"
    if f.exists():
        return json.load(open(f))["free_area_by_zone_and_band_km2"]
    return archived


MID = {"0-50": 30, "50-100": 75, "100-200": 150, "200-370": 285}
A = _areas()
PAC = "Macrocystis pyrifera (giant kelp; highest-yielding native, perennial, re-harvested)"
ATL = "Saccharina latissima (sugar kelp; highest-yielding native)"
HB = "Saccharina latissima (sugar kelp; highest-yielding native in the Hudson Bay complex)"
ZONES = {
    "pac_shelf": Zone("Pacific shelf 0-200 m", 8.0, 0.020, 0.85, 34, 38, 42, False, 1.0, PAC, A["pac_shelf"], MID),
    "pac_slope": Zone("Pacific slope 200-1,000 m", 8.0, 0.020, 0.65, 34, 38, 42, False, 1.0, PAC, A["pac_slope"], MID),
    "pac_deep": Zone("Pacific deep >1,000 m", 8.0, 0.020, 0.40, 34, 38, 42, False, 1.0, PAC, A["pac_deep"], MID),
    "atl_shelf": Zone("Atlantic shelf 0-200 m", 6.0, 0.020, 0.75, 14, 17, 20, False, 0.8, ATL, A["atl_shelf"], MID),
    "atl_slope": Zone("Atlantic slope 200-1,000 m", 6.0, 0.020, 0.55, 14, 17, 20, False, 0.8, ATL, A["atl_slope"], MID),
    "atl_deep": Zone("Atlantic deep >1,000 m", 6.0, 0.020, 0.30, 14, 17, 20, False, 0.8, ATL, A["atl_deep"], MID),
    "gsl_shelf": Zone("Gulf of St Lawrence shelf 0-200 m", 5.0, 0.020, 0.75, 18, 22, 24, False, 0.8, ATL, A.get("gsl_shelf", {}), MID, 1.25),
    "gsl_slope": Zone("Gulf of St Lawrence, Laurentian Channel 200-500 m", 5.0, 0.020, 0.60, 18, 22, 24, False, 0.8, ATL,
                      A.get("gsl_slope", {}), MID, 1.25),
    "lab_shelf": Zone("Labrador and north-east Newfoundland shelf 0-200 m", 4.0, 0.020, 0.70, 14, 16, 18, False, 0.8, ATL,
                      A.get("lab_shelf", {}), MID, 1.40),
    "lab_slope": Zone("Labrador and north-east Newfoundland slope 200-1,000 m", 4.0, 0.020, 0.55, 14, 16, 18, False, 0.8, ATL,
                      A.get("lab_slope", {}), MID, 1.40),
    "hb_shelf": Zone("Hudson Bay 0-200 m", 2.5, 0.020, 0.50, 9, 10, 10, False, 0.5, HB, A.get("hb_shelf", {}), MID, 1.60),
    "hb_slope": Zone("Hudson Bay >200 m", 2.5, 0.020, 0.45, 9, 10, 10, False, 0.5, HB, A.get("hb_slope", {}), MID, 1.60),
}
ZONES = {k: z for k, z in ZONES.items() if z.area_km2}
for _z in ZONES.values():
    _z.mid_km = {b: MID[b] for b in _z.area_km2}


@dataclass
class FarmCost:
    base_cad_t: float = 520.0          # CAD per dry t at 15 t/ha: long-line/grid farm incl. harvest and 40 km transport
    deep_factor: float = 1.45          # moorings beyond 1,000 m in North Pacific / North Atlantic storm climates
    slope_factor: float = 1.20
    transport_cad_t_wet_km: float = 0.032
    capture_eff: float = 0.25
    wave_unit_m3s: float = 0.0083
    wave_unit_capex: float = 95e3
    wave_unit_life: float = 5
    wave_xl_m3s: float = 0.033
    wave_xl_capex: float = 396e3
    solar_pipe_m3s_avg: float = 0.67
    solar_pipe_capex: float = 790e3
    solar_pipe_life: float = 15
    depth_cycle_capex_km2: float = 1.6e6
    depth_cycle_opex_km2: float = 80e3
    depth_cycle_life: float = 15
    om_frac: float = 0.03
    rate: float = 0.07
    dm_harvest: float = 0.12           # S. latissima 10-15% dry matter


def nitrate_gN_m3(uM):
    return uM * 1e-3 * 14.0


def nutrient_options(z: Zone, c: FarmCost):
    """CAD per dry tonne of kelp for each nutrient method (inf if not applicable)."""
    t_km2 = z.yield_t_ha * 100
    n_need = t_km2 * z.n_frac * 1000 * (1 - z.natural_n_share)
    out, units = {}, {}

    def pipe(q, capex, life, uM):
        kgN_unit = q * SECONDS_YR * nitrate_gN_m3(uM) * c.capture_eff / 1000
        n_units = n_need / kgN_unit if kgN_unit > 0 else float("inf")
        ann = n_units * capex * (CRF(c.rate, life) + c.om_frac)
        return ann / t_km2, n_units
    out["wave_pump"], units["wave_pump"] = pipe(c.wave_unit_m3s, c.wave_unit_capex, c.wave_unit_life, z.nitrate_300m)
    out["wave_pump_xl"], units["wave_pump_xl"] = pipe(c.wave_xl_m3s, c.wave_xl_capex, c.wave_unit_life, z.nitrate_300m)
    out["solar_pipe"], units["solar_pipe"] = pipe(c.solar_pipe_m3s_avg, c.solar_pipe_capex, c.solar_pipe_life, z.nitrate_400m)
    out["depth_cycling"] = (c.depth_cycle_capex_km2 * CRF(c.rate, c.depth_cycle_life) + c.depth_cycle_opex_km2) / t_km2
    units["depth_cycling"] = 1.0
    m3_per_t = n_need / t_km2 * 1000 / (nitrate_gN_m3(z.nitrate_400m) * c.capture_eff) if n_need > 0 else 0.0
    return out, units, {"n_supplement_kgN_per_t": n_need / t_km2, "deep_water_m3_per_t_dw": m3_per_t}


def farm_cost(zone_key, band, c: FarmCost, method="depth_cycling", yield_override=None):
    z = ZONES[zone_key]
    y = yield_override or z.yield_t_ha
    factor = 1.0 if zone_key.endswith("shelf") else (c.slope_factor if zone_key.endswith("slope") else c.deep_factor)
    factor *= z.ice_factor
    wet = 1 / c.dm_harvest
    transport = wet * max(z.mid_km[band] - 40, 0) * c.transport_cad_t_wet_km
    zz = Zone(**{**asdict(z), "yield_t_ha": y})
    nut, units, info = nutrient_options(zz, c)
    eff_yield = y
    if z.natural_n_share >= 1.0 or method == "natural":
        method = "natural"
        eff_yield = y * min(1.0, z.natural_n_share)
        nut_cost = 0.0
    elif method == "depth_cycling" and z.depth_cycle_effect < 1.0:
        unmet = (1 - z.natural_n_share) * (1 - z.depth_cycle_effect)
        eff_yield = y * (1 - unmet)
        nut_cost = nut["depth_cycling"] * y / eff_yield
    else:
        nut_cost = nut[method]
    base = c.base_cad_t * factor * (0.4 + 0.6 * REF_YIELD / eff_yield)
    return dict(zone=zone_key, band=band, method=method, yield_t_ha=eff_yield, base_cad_t=base,
                transport_cad_t=transport, nutrient_cad_t=nut_cost, total_cad_t=base + transport + nut_cost,
                transport_km=z.mid_km[band], units_per_km2=units.get(method, 0), **info)


METHODS = ("natural", "depth_cycling", "solar_pipe", "wave_pump", "wave_pump_xl")

if __name__ == "__main__":
    c = FarmCost()
    tab = {}
    for k, z in ZONES.items():
        nut, units, info = nutrient_options(z, c)
        rows = {m: farm_cost(k, list(z.area_km2)[0], c, m) for m in METHODS}
        tab[k] = {"species": z.species, "nutrient_cad_per_t": {m: (v if v != float("inf") else None) for m, v in nut.items()},
                  "units_per_km2": units, **info,
                  "biomass_cost_nearest_band_cad_per_t": {m: (r["total_cad_t"] if r["total_cad_t"] != float("inf") else None)
                                                          for m, r in rows.items()},
                  "effective_yield_t_ha": {m: r["yield_t_ha"] for m, r in rows.items()}}
        print(k, {m: (round(v) if v is not None else "n/a") for m, v in tab[k]["biomass_cost_nearest_band_cad_per_t"].items()})
    json.dump(tab, open(OUT / "nutrient_supply_options.json", "w"), indent=1)
