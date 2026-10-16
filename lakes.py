"""Freshwater biomass from Canadian lakes, harvested by the Grid Harvester, converted wet by hydrothermal
liquefaction (HTL), with the phosphorus it removes and a first-order in-lake response (CAD 2026).

Harvester
  The lake Grid Harvester is the offshore unit (primary vessel, 360-degree swivel, faired suction hose, harvesting
  head held by buoyancy control and steered by a reaction control system) on a smaller lake hull. Lakes have no tides
  and only weak currents, so the primary vessel runs free or holds station on an anchor instead of being drawn along
  a fixed transport cable. Three duties:
    grid      native filamentous algae grown on floating netting grids, cut and pumped by the 6-m head at 3 knots
              (3.33 ha/h; Bily et al., Grid Harvester design), every 10 days through the open-water season;
    skim      cyanobacterial scums skimmed by an 18-m surface head at 3 knots (10 ha/h) without netting;
    cut       nuisance beds of invasive Eurasian watermilfoil cut by a 6-m cutter head at 1.5 knots (1.67 ha/h).
  Unit cost CAD 6 M (assumption: ~25 m lake hull, pump, hose and head), 20-year life, O&M 5%/yr, two crew.
  Emergent marsh cattail grows in water too shallow for the vessel; it is cut by amphibious or farm machinery.

Species (the highest-yielding native organism for each duty)
  Grid algae   native filamentous periphyton dominated by Cladophora glomerata, with Spirogyra, Ulothrix,
               Stigeoclonium and filamentous diatoms (the community that colonizes algal turf scrubbers in North
               American fresh waters; Adey, Kangas and Mulbry 2011, BioScience 61:434). Cladophora is native to the
               Great Lakes and the most productive attached alga in them.
  Blooms       wild cyanobacteria (Microcystis, Aphanizomenon, Dolichospermum), native, harvested where they occur.
  Cattail      Typha latifolia (native; with the hybrid T. x glauca), the highest-yielding native marsh plant.
  Milfoil      Myriophyllum spicatum is invasive; it is harvested only as control.

Grid algae productivity
  Algal turf scrubbers in temperate fresh water average about 10 g dry m-2 d-1 over the growing season (Beltsville,
  Maryland, 5-25 weekly) and 25-35 in warm climates; tissue P is 0.05% in P-limited Lake Ontario Cladophora
  (Pennuto 2020) and 0.3-0.4% in moderately enriched water (Everglades), up to 1.5-2.1% on wastewater (Adey et al.
  2011). Floating netting in a lake lacks the surge of a flow-way, so productivity is scaled by ambient phosphorus:
    G = G_max * f * season,   f = TP / (TP + K),   P content = p_min + (p_max - p_min) * f
  with G_max 10 g m-2 d-1, K 0.03 mg/L, p_min 0.05%, p_max 0.50%, season 150 days (180 in the lower Great Lakes).
  Grids are placed only in waters with TP of at least 0.02 mg/L (the level above which nuisance growth is expected
  under Ontario's water quality objective) and cover at most 2% of those waters (navigation, fishing, habitat).
  Grids are deployed after ice-out and recovered before freeze-up. These are design assumptions to be demonstrated.

Water bodies (Canadian waters; all large lakes of Canada are listed, oligotrophic ones carry no harvest)
  Lake Winnipeg    Bloom extent 2002-2021: seasonal mean 5,452 km2, mean annual maximum 13,959 km2, record 21,641 km2
                   (2011; ECCC EOLakeWatch 2022). TP load 7,113 t/yr (1994-2023); TP 0.120 mg/L (south basin) and
                   0.049 (north basin); target 0.05 (Manitoba). Volume 284 km3; area 24,514 km2.
  Lake Erie        Bloom extent 2002-2021: mean 427 km2, mean annual maximum 1,227 km2, record 5,257 km2 (2011). To
                   reach the binational 40% target Canada must reduce its phosphorus loads by 212 t/yr (Canada-Ontario
                   Lake Erie Action Plan: 2024 Evaluation and Update Report). Canadian waters ~12,800 km2, of which
                   ~1,300 km2 in the western basin (TP ~0.04 mg/L). 35% of the bloom in Canadian waters (assumption).
  Lake St. Clair   Canadian half of 1,114 km2; flows to western Lake Erie, so P removed here is credited to Erie.
  Lake Ontario     Eutrophic Canadian embayments: Bay of Quinte (254 km2) and Hamilton Harbour (21 km2).
  Lake Simcoe      722 km2; Cook's Bay beds 18.1 km2 (2008); TP load ~72 t/yr, target 44 t/yr (LSRCA).
  Missisquoi Bay   (Lake Champlain, Quebec and Vermont) 77.5 km2, mostly in Quebec (45 km2 assumed); summer TP
                   0.049 mg/L (2001-2010); tributary load 195 t/yr, TMDL target 97.2 t/yr; internal load ~50 t/yr
                   (LimnoTech 2012, LCBP Technical Report 65).
  Lake of the Woods  Canadian waters ~3,150 km2; the Rainy River delivers ~500 t P/yr (LOWWSF); whole-lake load
                   650 t/yr assumed; eutrophic southern and eastern bays in Canada ~1,000 km2 at TP ~0.035 (approx.).
  Lake Manitoba    4,624 km2, eutrophic (TP ~0.09 mg/L, approximate); drains to Lake Winnipeg through the Dauphin
                   River (Manitoba load target 60 t P/yr at the Dauphin River).
  Lake Winnipegosis 5,374 km2, TP ~0.035 mg/L (approximate).
  Lesser Slave Lake 1,160 km2, TP ~0.045 mg/L (approximate). Last Mountain Lake 227 km2, TP ~0.08 (approximate).
  Lac Saint-Pierre 400 km2 (St Lawrence), TP ~0.035 (approximate).
  Oligotrophic or mesotrophic, no harvest (TP below 0.02 mg/L): Lake Superior (Canadian 28,700 km2, TP ~0.0025),
                   Lake Huron with Georgian Bay (36,000, ~0.004), Great Bear (31,153, ~0.002), Great Slave (27,200,
                   ~0.005), Athabasca (7,850, ~0.01), Reindeer (6,650, ~0.005), Nipigon (4,848, ~0.005), Mistassini
                   (2,335, ~0.004), Lac Saint-Jean (1,053, ~0.012), Nipissing (873, ~0.015). Removing P from
                   P-limited lakes would harm their fisheries.
  Harvested P is P exported from the lake in biomass. It is compared with external-load targets as a mass
  equivalence only: it is not a reduction of the external load; internal loading from sediments, recycling,
  location and season decide how much of it lowers in-lake TP. Values marked approximate are screening values.

Coastal marshes: cattail 15-20 t dry ha-1 yr-1, late-summer harvest removes 30-60 kg P ha-1 yr-1 (Grosshans 2014);
  harvest and baling CAD 50-85 per tonne (IISD). Netley-Libau (100 km2 harvestable) and Delta Marsh (60) credited to
  Lake Winnipeg; Lakes St. Clair and Erie coastal marshes (60) credited to Lake Erie.
Caps: bloom skimming removes at most `p_capture_max` (15%) of a lake's TP load; total harvest at most
  `p_total_max` (50%) of the load where a load is known; milfoil on half of each bed, two cuts.
In-lake response: TP = (L - H)/(Q + sigma V), so TP falls by H/L (Vollenweider 1975); response time M/L; chlorophyll
  follows TP with the Dillon and Rigler (1974) slope of 1.449. A first-order screening estimate.
"""
from dataclasses import dataclass, asdict
import json
from pathlib import Path

from biorefinery import Feed, Proc, route_h, route_eh

OUT = Path(__file__).resolve().parent / "outputs"
CRF = lambda r, n: r * (1 + r) ** n / ((1 + r) ** n - 1)
DILLON_RIGLER_SLOPE = 1.449
PEI_KM2 = 5660.0
KNOT_KMH = 1.852


@dataclass
class Lake:
    name: str
    area_km2: float                 # Canadian waters
    eutrophic_km2: float            # Canadian waters with TP >= 0.02 mg/L (grid siting area)
    tp_mgl: float                   # TP in those waters (or the most affected basin)
    tp_target_mgl: float
    p_load_t: float                 # external TP load to which removal is compared (t/yr; 0 if unknown)
    p_load_basis: str
    p_target_cut_t: float           # load reduction sought (t/yr; 0 if none stated)
    volume_km3: float
    tp_mass_t: float                # in-lake TP mass (t), for the response time; 0 if unknown
    bloom_mean_km2: float           # seasonal mean bloom extent in Canadian waters (0 if not used)
    bloom_max_km2: float
    bloom_record_km2: float
    bed_km2: float                  # nuisance milfoil beds in Canadian waters
    bed_dw_gm2: float
    season_d: float = 150.0
    trophic: str = "eutrophic"
    credit_to: str = ""             # downstream lake whose load target the removal is credited to
    notes: str = ""


MARSHES = {
    "netley_libau": ("winnipeg", 100.0, "Netley-Libau Marsh, Red River delta (Lake Winnipeg)"),
    "delta_marsh": ("winnipeg", 60.0, "Delta Marsh, Lake Manitoba (drains to Lake Winnipeg)"),
    "erie_stclair_marshes": ("erie", 60.0, "Coastal marshes of Lakes St. Clair and Erie, Ontario"),
}

L_ = Lake
LAKES = {
    "winnipeg": L_("Lake Winnipeg", 24514, 24514, 0.120, 0.05, 7113, "whole-lake TP load 1994-2023", 0, 284,
                   (0.120 * 25 + 0.049 * 259) * 1000, 5452, 13959, 21641, 0, 0, notes="grids in the south basin (0.120 mg/L)"),
    "erie": L_("Lake Erie (Canadian waters)", 12800, 1300, 0.040, 0.015, 10000,
               "whole-lake TP load (~10,000 t/yr); Canadian tributaries 1,047 t/yr", 212, 484, 0.013 * 484 * 1000,
               0.35 * 427, 1227, 5257, 30, 400, 180, notes="Canadian target 212 t/yr; grids in the western basin"),
    "stclair": L_("Lake St. Clair (Canadian waters)", 557, 150, 0.030, 0.015, 0, "credited to Lake Erie", 0, 0, 0,
                  40, 0, 0, 60, 400, 180, credit_to="erie", notes="flows to western Lake Erie"),
    "ontario": L_("Lake Ontario (Bay of Quinte, Hamilton Harbour)", 10000, 275, 0.030, 0.017, 150,
                  "embayment TP loads (assumed)", 0, 0, 0, 40, 0, 0, 25, 400, 180, notes="open lake oligotrophic (~0.007)"),
    "simcoe": L_("Lake Simcoe", 722, 45, 0.022, 0.015, 72, "TP load (LSRCA)", 28, 11.6, 0.013 * 11.6 * 1000,
                 0, 0, 0, 15, 700, 165, notes="grids only in Cook's Bay"),
    "missisquoi": L_("Missisquoi Bay, Lake Champlain (Quebec)", 45, 45, 0.049, 0.025, 195,
                     "tributary load to the whole bay 2001-2010 (LCBP)", 97.8, 0, 0, 0, 0, 0, 0, 0, 165,
                     notes="TMDL target 97.2 t/yr for the whole bay"),
    "woods": L_("Lake of the Woods (Canadian waters)", 3150, 1000, 0.035, 0.020, 650, "whole-lake load (assumed)", 0,
                0, 0, 0, 0, 0, 0, 0, 150, notes="Rainy River ~500 t/yr"),
    "manitoba": L_("Lake Manitoba", 4624, 4624, 0.090, 0.050, 0, "load not used", 0, 0, 0, 0, 0, 0, 0, 0, 150,
                   notes="TP approximate; drains to Lake Winnipeg"),
    "winnipegosis": L_("Lake Winnipegosis", 5374, 5374, 0.035, 0.030, 0, "load not used", 0, 0, 0, 0, 0, 0, 0, 0, 150,
                       notes="TP approximate"),
    "lesser_slave": L_("Lesser Slave Lake", 1160, 1160, 0.045, 0.030, 0, "load not used", 0, 0, 0, 0, 0, 0, 0, 0, 140,
                       notes="TP approximate"),
    "last_mountain": L_("Last Mountain Lake", 227, 227, 0.080, 0.050, 0, "load not used", 0, 0, 0, 0, 0, 0, 0, 0, 150,
                        notes="TP approximate"),
    "st_pierre": L_("Lac Saint-Pierre", 400, 400, 0.035, 0.030, 0, "load not used", 0, 0, 0, 0, 0, 0, 0, 0, 170,
                    notes="TP approximate; flow-through river lake"),
}
OLIGO = {"superior": ("Lake Superior (Canadian waters)", 28700, 0.0025), "huron": ("Lake Huron and Georgian Bay (Canadian)", 36000, 0.004),
         "great_bear": ("Great Bear Lake", 31153, 0.002), "great_slave": ("Great Slave Lake", 27200, 0.005),
         "athabasca": ("Lake Athabasca", 7850, 0.010), "reindeer": ("Reindeer Lake", 6650, 0.005),
         "nipigon": ("Lake Nipigon", 4848, 0.005), "mistassini": ("Lac Mistassini", 2335, 0.004),
         "st_jean": ("Lac Saint-Jean", 1053, 0.012), "nipissing": ("Lake Nipissing", 873, 0.015)}
for _k, (_n, _a, _tp) in OLIGO.items():
    LAKES[_k] = L_(_n, _a, 0, _tp, _tp, 0, "oligotrophic or mesotrophic: no harvest", 0, 0, 0, 0, 0, 0, 0, 0,
                   trophic="oligotrophic" if _tp < 0.01 else "mesotrophic")


@dataclass
class LakeParams:
    # lake Grid Harvester unit
    unit_capex: float = 6.0e6
    unit_life: float = 20.0
    unit_om: float = 0.05
    crew_cad_h: float = 160.0
    speed_kn: float = 3.0
    head_m: float = 6.0
    skim_head_m: float = 18.0
    cut_speed_kn: float = 1.5
    # grid farms of native filamentous algae
    grid_g_max: float = 10.0           # g dry m-2 d-1, P-replete, temperate growing-season mean
    grid_k_mgl: float = 0.03
    grid_p_min: float = 0.0005
    grid_p_max: float = 0.0050
    grid_n: float = 0.035
    grid_k_frac: float = 0.010
    grid_ash: float = 0.30
    grid_biocrude: float = 0.22
    grid_share_max: float = 0.02       # of the eutrophic waters
    grid_capex_km2: float = 1.5e6      # floating netting, buoys and anchors
    grid_life: float = 10.0
    grid_om: float = 0.08              # includes seasonal deployment and recovery
    grid_harvest_days: float = 10.0
    grid_hours: float = 2400.0
    grid_gj_t: float = 0.35
    tp_min_grid: float = 0.02
    # bloom skimming
    scum_dw_gm2: float = 40.0
    capture: float = 0.60
    bloom_hours: float = 900.0
    km2_per_unit: float = 20.0
    p_capture_max: float = 0.15
    p_total_max: float = 0.50
    skim_gj_t: float = 0.40
    shore_dewater_cad_t: float = 45.0
    # milfoil cutting
    cut_fraction: float = 0.60
    cuts: float = 2.0
    bed_share_max: float = 0.5
    cut_hours: float = 700.0
    cut_gj_t: float = 0.30
    # transport and conversion
    haul_km: float = 60.0
    haul_cad_t_wet_km: float = 0.032
    slurry_dm: float = 0.15
    algae_biocrude: float = 0.30
    milfoil_biocrude: float = 0.20
    small_plant_mult: float = 1.3
    rate: float = 0.07
    algae_p: float = 0.008
    algae_n: float = 0.075
    algae_k: float = 0.007
    algae_ash: float = 0.15
    milfoil_p: float = 0.0030
    milfoil_n: float = 0.028
    milfoil_k: float = 0.025
    milfoil_ash: float = 0.20
    cattail_yield_t_ha: float = 15.0
    cattail_share_max: float = 0.5
    cattail_cad_t: float = 70.0
    cattail_haul_cad_t: float = 15.0
    cattail_gj_t: float = 0.25
    cattail_p: float = 0.0020
    cattail_n: float = 0.012
    cattail_k: float = 0.015
    cattail_ash: float = 0.07
    cattail_biocrude: float = 0.28


def unit_cost(c: LakeParams, hours):
    return c.unit_capex * (CRF(c.rate, c.unit_life) + c.unit_om) + c.crew_cad_h * hours


def grid_harvester(c: LakeParams):
    """Per-unit area rates (ha/h) and annual cost for the three lake duties."""
    v = c.speed_kn * KNOT_KMH * 1000
    return dict(grid_ha_h=c.head_m * v / 1e4, skim_ha_h=c.skim_head_m * v / 1e4,
                cut_ha_h=c.head_m * c.cut_speed_kn * KNOT_KMH * 1000 / 1e4,
                cost_grid=unit_cost(c, c.grid_hours), cost_skim=unit_cost(c, c.bloom_hours), cost_cut=unit_cost(c, c.cut_hours))


def grid_yield(c: LakeParams, L: Lake):
    f = L.tp_mgl / (L.tp_mgl + c.grid_k_mgl)
    t_ha = c.grid_g_max * f * L.season_d / 100.0             # g m-2 -> t ha-1
    return dict(f=f, t_ha=t_ha, p=c.grid_p_min + (c.grid_p_max - c.grid_p_min) * f)


def grid_cost(c: LakeParams, L: Lake):
    """CAD per dry t at the lakeshore for grid algae, and Grid Harvester units per km2 of grid."""
    gh = grid_harvester(c)
    y = grid_yield(c, L)
    harvests = L.season_d / c.grid_harvest_days
    ha_per_unit = gh["grid_ha_h"] * c.grid_hours / harvests
    units_km2 = 100.0 / ha_per_unit
    ann_km2 = c.grid_capex_km2 * (CRF(c.rate, c.grid_life) + c.grid_om) + units_km2 * gh["cost_grid"]
    t_km2 = y["t_ha"] * 100
    return dict(units_per_km2=units_km2, cad_t=ann_km2 / t_km2 if t_km2 > 0 else float("inf"), t_km2=t_km2, **y)


def skim(c: LakeParams):
    gh = grid_harvester(c)
    t_h = gh["skim_ha_h"] * 1e4 * c.scum_dw_gm2 * c.capture / 1e6
    t_yr = t_h * c.bloom_hours
    return dict(t_dw_per_h=t_h, t_dw_per_yr=t_yr, harvest_cad_t=gh["cost_skim"] / t_yr)


def cut(c: LakeParams, dw_gm2):
    gh = grid_harvester(c)
    t_ha = dw_gm2 * c.cut_fraction / 100.0
    t_yr = gh["cut_ha_h"] * c.cut_hours * t_ha
    return dict(t_dw_per_ha_cut=t_ha, t_dw_per_yr=t_yr, harvest_cad_t=gh["cost_cut"] / t_yr)


# kept for the optimiser's unit counts
def bloom_vessel(c: LakeParams):
    return skim(c)


def cutter(c: LakeParams, dw_gm2):
    return cut(c, dw_gm2)


def feeds(c: LakeParams, grid_p=None):
    algae = Feed(ash=c.algae_ash, mannitol=0.0, laminarin=0.0, cellulose=0.0, alginate=0.0, fucoidan=0.0,
                 protein=0.45, lipid=0.07, n=c.algae_n, p=c.algae_p, k=c.algae_k)
    milfoil = Feed(ash=c.milfoil_ash, mannitol=0.0, laminarin=0.0, cellulose=0.375, alginate=0.0, fucoidan=0.0,
                   protein=0.17, lipid=0.02, n=c.milfoil_n, p=c.milfoil_p, k=c.milfoil_k)
    cattail = Feed(ash=c.cattail_ash, mannitol=0.0, laminarin=0.0, cellulose=0.60, alginate=0.0, fucoidan=0.0,
                   protein=0.07, lipid=0.02, n=c.cattail_n, p=c.cattail_p, k=c.cattail_k)
    grid = Feed(ash=c.grid_ash, mannitol=0.0, laminarin=0.0, cellulose=0.20, alginate=0.0, fucoidan=0.0,
                protein=0.25, lipid=0.04, n=c.grid_n, p=grid_p if grid_p is not None else c.grid_p_max, k=c.grid_k_frac)
    return algae, milfoil, cattail, grid


def conversion(c: LakeParams, proc: dict | None = None, grid_p=None):
    """Outputs per dry tonne for each lake biomass and route (same structure as biorefinery.routes)."""
    base = {**asdict(Proc()), **(proc or {})}
    learn = base["htl_biocrude_whole"] / Proc().htl_biocrude_whole
    algae, milfoil, cattail, grid = feeds(c, grid_p)
    pa = Proc(**{**base, "htl_biocrude_whole": c.algae_biocrude * learn, "ht_h2": 0.05, "ht_yield": 0.80})
    pg = Proc(**{**base, "htl_biocrude_whole": c.grid_biocrude * learn, "ht_h2": 0.05, "ht_yield": 0.80})
    pm = Proc(**{**base, "htl_biocrude_whole": c.milfoil_biocrude * learn})
    pc = Proc(**{**base, "htl_biocrude_whole": c.cattail_biocrude * learn})
    out = {"algae|H": route_h(algae, pa), "grid|H": route_h(grid, pg), "milfoil|H": route_h(milfoil, pm),
           "milfoil|EH": route_eh(milfoil, pm), "cattail|H": route_h(cattail, pc), "cattail|EH": route_eh(cattail, pc)}
    for v in out.values():
        v["cost_cad"] *= c.small_plant_mult
    return out


def supply(c: LakeParams = LakeParams()):
    """Harvestable dry biomass (t/yr), harvest cost at the plant (CAD/t dry) and Grid Harvester units per tonne."""
    sk = skim(c)
    rows = []
    wet_haul = (1 / c.slurry_dm) * c.haul_km * c.haul_cad_t_wet_km
    for lk, L in LAKES.items():
        if L.eutrophic_km2 > 0 and L.tp_mgl >= c.tp_min_grid:
            g = grid_cost(c, L)
            km2 = c.grid_share_max * L.eutrophic_km2
            t = km2 * g["t_km2"]
            rows.append(dict(lake=lk, biomass="grid", cap_t=t, binding="grid area", area_km2=km2,
                             units_per_t=g["units_per_km2"] / g["t_km2"], harvest_cad_t=g["cad_t"],
                             port_cad_t=g["cad_t"] + c.shore_dewater_cad_t + wet_haul, fleet_gj_t=c.grid_gj_t,
                             p_kg_t=g["p"] * 1000, n_kg_t=c.grid_n * 1000, t_ha=g["t_ha"], grid_p=g["p"]))
        if L.bloom_mean_km2 > 0 and L.p_load_t > 0:
            t_area = L.bloom_mean_km2 / c.km2_per_unit * sk["t_dw_per_yr"]
            t_p = c.p_capture_max * L.p_load_t / c.algae_p
            t = min(t_area, t_p)
            rows.append(dict(lake=lk, biomass="algae", cap_t=t, binding="P cap" if t_p < t_area else "fleet/area",
                             units_per_t=1 / sk["t_dw_per_yr"], harvest_cad_t=sk["harvest_cad_t"],
                             port_cad_t=sk["harvest_cad_t"] + c.shore_dewater_cad_t + wet_haul,
                             fleet_gj_t=c.skim_gj_t, p_kg_t=c.algae_p * 1000, n_kg_t=c.algae_n * 1000))
        if L.bed_km2 > 0:
            cu = cut(c, L.bed_dw_gm2)
            t = L.bed_km2 * 100 * c.bed_share_max * c.cuts * cu["t_dw_per_ha_cut"]
            rows.append(dict(lake=lk, biomass="milfoil", cap_t=t, binding="bed area", units_per_t=1 / cu["t_dw_per_yr"],
                             harvest_cad_t=cu["harvest_cad_t"],
                             port_cad_t=cu["harvest_cad_t"] + c.shore_dewater_cad_t * 0.5 + wet_haul * 0.75,
                             fleet_gj_t=c.cut_gj_t, p_kg_t=c.milfoil_p * 1000, n_kg_t=c.milfoil_n * 1000))
    for mk, (lk, km2, _) in MARSHES.items():
        t = km2 * 100 * c.cattail_share_max * c.cattail_yield_t_ha
        rows.append(dict(lake=lk, marsh=mk, biomass="cattail", cap_t=t, binding="stand area", units_per_t=0.0,
                         harvest_cad_t=c.cattail_cad_t, port_cad_t=c.cattail_cad_t + c.cattail_haul_cad_t,
                         fleet_gj_t=c.cattail_gj_t, p_kg_t=c.cattail_p * 1000, n_kg_t=c.cattail_n * 1000,
                         ha=km2 * 100 * c.cattail_share_max))
    return rows


def lake_systems(prm):
    """LP systems in the same format as optimise.kelp_systems; one unit of the variable = 1 Mt dry per year.
    p_group / p_group_cap_t limit the total P harvested from a lake to p_total_max of its known load."""
    lp_ = prm.get("lakes", {})
    if not lp_.get("enabled", True):
        return []
    c = LakeParams(**{k: v for k, v in lp_.items() if k in LakeParams.__dataclass_fields__})
    conv = conversion(c, prm["proc"])
    pay = lp_.get("cleanup_cad_kg_p", 0.0)
    out = []
    for r in supply(c):
        routes = ("H",) if r["biomass"] in ("algae", "grid") else ("H", "EH")
        L = LAKES[r["lake"]]
        tgt = L.credit_to or r["lake"]
        for rt in routes:
            cv = conversion(c, prm["proc"], r["grid_p"])["grid|H"] if r["biomass"] == "grid" else conv[f"{r['biomass']}|{rt}"]
            out.append(dict(key=f"lake|{r.get('marsh', r['lake'])}|{r['biomass']}|{rt}", zone="lake:" + r.get("marsh", r["lake"]),
                            band=r["biomass"], method="Grid Harvester" if r["biomass"] != "cattail" else "amphibious harvester",
                            pre="wet", route=rt, lake=r["lake"], biomass=r["biomass"],
                            area_cap=r["cap_t"] / 1e6, t_km2=1e6,
                            farm_cad_t=r["port_cad_t"] - pay * r["p_kg_t"], refinery_cad_t=cv["cost_cad"] * prm["refinery_cost_mult"],
                            harvest_cad_t=r["port_cad_t"], cleanup_credit_cad_t=pay * r["p_kg_t"],
                            fleet_gj_t=r["fleet_gj_t"], kite_saved_gj_t=0.0,
                            ethanol_gj=cv["ethanol_gj"], hc_gj=cv["hc_gj"], jet_gj=cv["jet_gj"], ch4_gj=cv["ch4_gj"],
                            el_mwh=cv["el_mwh"], heat_mwh=cv["heat_mwh_th"], co2_t=cv["co2_ferm_t"],
                            fert=(cv["fert_n_kg"], cv["fert_p_kg"], cv["fert_k_kg"]), fert_energy_gj=cv["fert_energy_gj"],
                            fert_co2_t=cv["fert_co2_t"], units_km2=0.0, deep_water_m3_t=0.0, wet_mass_t=1 / c.slurry_dm,
                            p_removed_kg_t=r["p_kg_t"], n_removed_kg_t=r["n_kg_t"], units_per_t=r["units_per_t"],
                            grid_km2_per_t=(r["area_km2"] / r["cap_t"]) if r["biomass"] == "grid" and r["cap_t"] > 0 else 0.0,
                            p_group=tgt if LAKES[tgt].p_load_t > 0 else "",
                            p_group_cap_t=c.p_total_max * LAKES[tgt].p_load_t, force=lp_.get("force", False)))
    return out


def response(removed_t_by_lake):
    """First-order steady-state screening estimate of in-lake TP and chlorophyll response to the P exported (t/yr) in
    each lake: TP falls in proportion to the share of the external load removed. Internal loading, sediment
    exchange, hydrodynamics and biological feedbacks are not represented; share_of_target_cut is a mass equivalence."""
    res = {}
    for lk, H in removed_t_by_lake.items():
        L = LAKES[lk]
        if L.p_load_t <= 0:
            continue
        f = min(H / L.p_load_t, 0.99)
        res[lk] = dict(p_removed_t=H, share_of_load=f, tp_now_mgl=L.tp_mgl, tp_new_mgl=L.tp_mgl * (1 - f),
                       tp_target_mgl=L.tp_target_mgl, chl_change=(1 - f) ** DILLON_RIGLER_SLOPE - 1,
                       share_of_target_cut=(H / L.p_target_cut_t) if L.p_target_cut_t > 0 else None,
                       response_time_yr=(L.tp_mass_t / L.p_load_t) if L.tp_mass_t > 0 else None)
    return res


def table():
    c = LakeParams()
    return dict(lakes={k: asdict(v) for k, v in LAKES.items()}, marshes=MARSHES, params=asdict(c),
                grid_harvester=grid_harvester(c), skim=skim(c), cut_400=cut(c, 400.0), cut_700=cut(c, 700.0),
                grid={k: grid_cost(c, L) for k, L in LAKES.items() if L.eutrophic_km2 > 0 and L.tp_mgl >= c.tp_min_grid},
                supply=supply(c),
                conversion={k: {a: b for a, b in v.items() if isinstance(b, (int, float, str))} for k, v in conversion(c).items()},
                pei_km2=PEI_KM2)


if __name__ == "__main__":
    T = table()
    print("harvester", {k: round(v, 2) for k, v in T["grid_harvester"].items()})
    print("skim", {k: round(v, 2) for k, v in T["skim"].items()}, "cut", {k: round(v, 2) for k, v in T["cut_400"].items()})
    for k, g in T["grid"].items():
        print("grid", k, {a: round(b, 4) for a, b in g.items()})
    for r in T["supply"]:
        print(r["lake"], r["biomass"], round(r["cap_t"]), r["binding"], "port", round(r["port_cad_t"]),
              "P t", round(r["cap_t"] * r["p_kg_t"] / 1000, 1))
    json.dump(T, open(OUT / "lakes_inputs.json", "w"), indent=1, default=float)
