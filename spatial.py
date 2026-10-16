"""Canadian marine space for native-kelp farms: depth, coast, ice, shipping, fishing and conservation constraints.

Data
  Natural Earth 1:10m land, admin-0 countries and 200 m / 1,000 m bathymetry (public domain).
  Benden (2022) Global Shipping Lanes v1, doi:10.5281/zenodo.6361763 (CC BY 4.0), clipped to the two study areas
    (data/shiplanes/shipping_lanes_canada.geojson).
  Port approaches: 10-15 km radius around the main commercial ports and refinery terminals.
  Conserved areas: ECCC, Canadian Environmental Sustainability Indicators, Canada's conserved areas (2026), share
    of each marine ecozone protected or conserved at the end of 2025 (Offshore Pacific 45.4%, Northern Shelf 16.9%,
    Southern Shelf 2.8%, Strait of Georgia 5.4%, Scotian Shelf 15.5%, Newfoundland-Labrador Shelves 11.9%).
    Conserved areas are not mapped individually: the conserved share of each ecozone is removed from the free area
    of the cells in that ecozone (farm.py), which is exact in total and approximate in location.
    Gulf of St Lawrence 10.5% and Hudson Bay Complex 0.7%.
  Sea ice and icebergs: the Pacific coast is ice-free. The Gulf of St Lawrence has seasonal sea ice from January
    to April; north-east Newfoundland and Labrador (north of 47.6 N outside the Gulf) have pack ice from January to
    June and the main iceberg drift; Hudson Bay is ice-covered for about eight months (November to July; the ice-free
    season has lengthened since the 1970s, Gough et al. 2004). These waters are kept as separate seasonal-ice zones
    (gsl, lab, hb) with submerged, ice-rated long-lines, a shorter growing season and lower yields (farm.py). Waters
    beyond 1,000 m off Labrador and north-east Newfoundland (iceberg drift, pack ice), Ungava Bay and Hudson Strait
    are excluded.
  Hudson Bay: farms are sited for industries in Manitoba and Ontario. Haul distance is measured to the two
    rail-served landing points, Churchill (Manitoba; deep-water port, Hudson Bay Railway to The Pas and Winnipeg)
    and Moosonee (Ontario; Ontario Northland Railway to Cochrane), and cells more than 370 km from both are not used.
    Southern James Bay (south of 52.5 N) is excluded because river inflow keeps its salinity below the tolerance of
    the native kelps. The Churchill shipping route through Hudson Bay is added by hand (the global lane dataset has
    no lane there).
  Fishing: a rule-based proxy (not observed effort):
    0-6 nm from the coast         -> inshore fisheries (lobster, crab, salmon, herring), First Nations food,
                                     social and ceremonial fisheries, eelgrass and kelp forests (excluded)
    6 nm to the 1,000 m isobath   -> shelf and slope fisheries (groundfish, scallop, snow crab, shrimp, halibut)
    beyond 1,000 m                -> pelagic longline (tuna, swordfish) and few other uses

Method
  0.05-degree grid in three study areas (Pacific: British Columbia; Atlantic: the Bay of Fundy, Nova Scotia, New
  Brunswick, Prince Edward Island, the Gulf of St Lawrence, Newfoundland and Labrador; Hudson Bay and James Bay). Ocean cells are assigned to the nearest country (equidistance approximation) and
  limited to 200 nm from the Canadian coast (EEZ approximation). Distances and areas are computed in a Lambert
  azimuthal equal-area projection centred on each study area. Transport distance is measured to the nearest
  Canadian land mass larger than 500 km2 (so that Sable Island, 160 km off Nova Scotia, is not a landing point).
"""
import json
import os
import pickle
from pathlib import Path

import numpy as np
import shapefile
import shapely
from shapely.geometry import shape, Point, Polygon, box
from shapely.ops import unary_union, transform
from pyproj import Transformer

HERE = Path(__file__).resolve().parent
NE = Path(os.environ.get("NATURAL_EARTH_DIR", str(HERE / "data" / "naturalearth")))
LANES = HERE / "data/shiplanes/shipping_lanes_canada.geojson"
OUT = HERE / "outputs"
OUT.mkdir(exist_ok=True)
NM = 1.852
STEP = 0.05
BANDS = (("0-50", 0, 50, 30), ("50-100", 50, 100, 75), ("100-200", 100, 200, 150), ("200-370", 200, 371, 285))
REGIONS = {
    "Pacific": dict(bbox=(-141.0, 46.5, -122.0, 56.0), crs="+proj=laea +lat_0=51 +lon_0=-131 +datum=WGS84 +units=m",
                    neighbours=("USA",)),
    "Atlantic": dict(bbox=(-71.5, 39.5, -42.0, 60.5), crs="+proj=laea +lat_0=50 +lon_0=-58 +datum=WGS84 +units=m",
                     neighbours=("USA", "SPM", "GRL")),
    "Hudson": dict(bbox=(-95.5, 51.0, -76.0, 63.5), crs="+proj=laea +lat_0=58 +lon_0=-86 +datum=WGS84 +units=m",
                   neighbours=()),
}
HUBS = {"Churchill": (58.77, -94.18), "Moosonee": (51.28, -80.64)}     # Hudson Bay landing points
CHURCHILL_ROUTE = [(-76.0, 62.4), (-80.0, 61.9), (-85.5, 60.6), (-91.0, 59.4), (-94.18, 58.77)]
JAMES_BAY_SALINITY_LAT = 52.5
PORTS = {  # name: (lat, lon, approach radius km)
    "Vancouver": (49.29, -123.11, 15), "Roberts Bank": (49.02, -123.16, 12), "Victoria": (48.42, -123.37, 10),
    "Nanaimo": (49.17, -123.93, 10), "Prince Rupert": (54.31, -130.33, 15), "Kitimat": (53.99, -128.70, 12),
    "Port Alberni": (49.23, -124.82, 10), "Halifax": (44.65, -63.57, 15), "Saint John": (45.26, -66.06, 15),
    "Point Tupper / Port Hawkesbury": (45.60, -61.35, 12), "Sydney": (46.14, -60.19, 10), "Shelburne": (43.76, -65.32, 8),
    "Argentia / Placentia Bay": (47.30, -54.00, 15), "St. John's": (47.56, -52.71, 12),
    "Quebec City": (46.81, -71.20, 12), "Sept-Iles": (50.20, -66.38, 12), "Port-Cartier": (50.03, -66.86, 10),
    "Baie-Comeau": (49.22, -68.14, 10), "Belledune": (47.90, -65.84, 8), "Port aux Basques": (47.57, -59.13, 8),
    "Corner Brook": (48.95, -57.95, 8), "Goose Bay": (53.30, -60.40, 10), "Voisey's Bay / Edward's Cove": (56.33, -61.65, 8),
    "Churchill": (58.77, -94.18, 15), "Moosonee": (51.28, -80.64, 10),
}
GULF = Polygon([(-65.5, 46.0), (-63.6, 45.95), (-62.9, 45.65), (-61.4, 45.55), (-61.2, 46.0), (-60.6, 47.05),
                (-59.3, 47.62), (-59.3, 49.5), (-57.0, 51.6), (-66.0, 51.0), (-71.5, 47.5), (-65.5, 46.0)])
ICE_LAT = 47.6
CONSERVED = {"strait_of_georgia": 0.054, "southern_shelf": 0.028, "northern_shelf": 0.169, "offshore_pacific": 0.454,
             "scotian_shelf": 0.155, "nl_shelves": 0.119, "gulf_of_st_lawrence": 0.105, "hudson_bay_complex": 0.007}


def load(path, bbox):
    r = shapefile.Reader(str(path))
    flds = [f[0] for f in r.fields[1:]]
    out = []
    for sr in r.iterShapeRecords():
        g = shape(sr.shape.__geo_interface__)
        if g.intersects(bbox):
            out.append((dict(zip(flds, sr.record)), g.intersection(bbox)))
    return out


def bathymetry(name):
    for sub in ("10m_physical", "10m_physical/ne_10m_bathymetry_all"):
        stem = NE / sub / f"ne_10m_bathymetry_{name}"
        if stem.with_suffix(".shp").exists():
            return stem
    raise FileNotFoundError(f"ne_10m_bathymetry_{name}.shp not found under {NE}; run fetch_data.py")


def run_region(reg):
    cfg = REGIONS[reg]
    bb = box(*cfg["bbox"]).buffer(3.0)            # wider window so that neighbouring coasts are seen
    to_m = Transformer.from_crs("EPSG:4326", cfg["crs"], always_xy=True)
    to_ll = Transformer.from_crs(cfg["crs"], "EPSG:4326", always_xy=True)
    fm = lambda g: transform(to_m.transform, g)
    fl = lambda g: transform(to_ll.transform, g)
    land = unary_union([g for _, g in load(NE / "10m_physical/ne_10m_land", bb)])
    d200 = unary_union([g for _, g in load(bathymetry("K_200"), bb)])
    d1000 = unary_union([g for _, g in load(bathymetry("J_1000"), bb)])
    ctry = [(r["ADM0_A3"], g) for r, g in load(NE / "10m_cultural/ne_10m_admin_0_countries", bb)
            if r["ADM0_A3"] in ("CAN",) + cfg["neighbours"]]
    names = np.array([c for c, _ in ctry])
    cgeom_m = [fm(g.simplify(0.01)) for _, g in ctry]
    can_m = unary_union([g for c, g in zip(names, cgeom_m) if c == "CAN"])
    big_m = unary_union([p for p in shapely.get_parts(can_m) if p.area > 500e6])

    half = {"Major": 10e3, "Middle": 6e3, "Minor": 3e3}
    lanes = [f for f in json.load(open(LANES))["features"] if f["properties"]["region"] == reg.lower()]
    lane_polys = [fm(shape(f["geometry"])).buffer(half.get(f["properties"].get("Type", "Minor"), 3e3)) for f in lanes]
    if reg == "Hudson":
        from shapely.geometry import LineString
        lane_polys.append(fm(LineString(CHURCHILL_ROUTE)).buffer(half["Middle"]))
    x0, y0, x1, y1 = cfg["bbox"]
    port_m = [Point(*to_m.transform(lon, lat)).buffer(r * 1e3) for lat, lon, r in PORTS.values()
              if x0 <= lon <= x1 and y0 <= lat <= y1]
    ship_m = unary_union(lane_polys + port_m)

    lons = np.arange(x0 + STEP / 2, x1, STEP)
    lats = np.arange(y0 + STEP / 2, y1, STEP)
    LON, LAT = np.meshgrid(lons, lats)
    lon, lat = LON.ravel(), LAT.ravel()
    cell = (STEP * 111.32 * np.cos(np.radians(lat))) * (STEP * 110.57)
    ocean = ~shapely.contains_xy(land, lon, lat)
    lon, lat, cell = lon[ocean], lat[ocean], cell[ocean]
    X, Y = to_m.transform(lon, lat)
    pts = shapely.points(X, Y)
    tree = shapely.STRtree(cgeom_m)
    idx = tree.query_nearest(pts, return_distance=False, all_matches=False)
    nearest = names[idx[1][np.argsort(idx[0])]]
    dist = shapely.distance(can_m, pts) / 1e3
    keep = (nearest == "CAN") & (dist <= 370.4)
    lon, lat, cell, X, Y, pts, dist = (a[keep] for a in (lon, lat, cell, X, Y, pts, dist))
    if reg == "Hudson":
        hubs = [Point(*to_m.transform(lo, la)) for la, lo in HUBS.values()]
        dist_land = np.min([shapely.distance(h, pts) for h in hubs], axis=0) / 1e3
    else:
        dist_land = shapely.distance(big_m, pts) / 1e3
    depth = np.where(shapely.contains_xy(d1000, lon, lat), ">1000",
                     np.where(shapely.contains_xy(d200, lon, lat), "200-1000", "0-200"))
    ship = shapely.contains_xy(ship_m, X, Y)
    inshore = dist <= 6 * NM
    fish = np.where(inshore, "inshore_0-6nm", np.where(depth == ">1000", "deep_low", "shelf_slope_fisheries"))
    excl = np.zeros(lon.shape, bool)
    if reg == "Atlantic":
        gulf = shapely.contains_xy(GULF, lon, lat)
        ice = np.where(gulf, "gsl", np.where(lat >= ICE_LAT, "lab", "none"))
        excl = ((ice == "lab") & (depth == ">1000")) | ((lat > 58.3) & (lon < -64.3))
        eco = np.where((lon < -58.0) & (lat < 47.0), "scotian_shelf", "nl_shelves")
        eco = np.where(gulf, "gulf_of_st_lawrence", eco)
    elif reg == "Hudson":
        ice = np.full(lon.shape, "hb", dtype=object)
        excl = (dist_land > 370.4) | ((lat < JAMES_BAY_SALINITY_LAT) & (lon > -82.5))
        eco = np.full(lon.shape, "hudson_bay_complex", dtype=object)
    else:
        ice = np.full(lon.shape, "none", dtype=object)
        eco = np.where(depth == ">1000", "offshore_pacific", np.where(lat < 50.9, "southern_shelf", "northern_shelf"))
        eco = np.where((lon > -124.0) & (lat < 50.5), "strait_of_georgia", eco)
    return dict(region=reg, lon=lon, lat=lat, cell=cell, depth=depth, ship=ship, fish=fish, ice=ice, excl=excl, eco=eco, dist=dist,
                dist_land=dist_land, land=land, ship_ll=fl(ship_m), can_ll=fl(can_m), bbox=cfg["bbox"])


def band_of(km):
    out = np.full(km.shape, "", dtype=object)
    for name, lo, hi, _ in BANDS:
        out[(km >= lo) & (km < hi)] = name
    return out


def zone_of(L):
    base = {"Pacific": "pac", "Atlantic": "atl", "Hudson": "hb"}[L["region"]]
    pre = [i if i != "none" else base for i in L["ice"]]
    return np.array([f"{p}_{'shelf' if d == '0-200' else 'slope' if d == '200-1000' else 'deep'}" for p, d in zip(pre, L["depth"])],
                    dtype=object)


def free_mask(L):
    return (~L["ship"]) & (L["fish"] != "inshore_0-6nm") & (~L["excl"])


def summarise(LL):
    s = {"study_area_eez_km2": {}, "free_area_by_zone_band_eco_km2": {}, "free_area_by_zone_and_band_km2": {}}
    for L in LL:
        c = L["cell"]; reg = L["region"]
        r = {"total_km2": float(c.sum()), "shipping_km2": float(c[L["ship"]].sum()),
             "inshore_0_6nm_km2": float(c[L["fish"] == "inshore_0-6nm"].sum()), "excluded_km2": float(c[L["excl"]].sum()),
             "seasonal_ice_km2": float(c[L["ice"] != "none"].sum())}
        for dep in ("0-200", "200-1000", ">1000"):
            r[f"depth_{dep}_km2"] = float(c[L["depth"] == dep].sum())
        r["by_ecozone_km2"] = {e: float(c[L["eco"] == e].sum()) for e in np.unique(L["eco"])}
        s["study_area_eez_km2"][reg] = r
        ok = free_mask(L)
        band = band_of(L["dist_land"]); zone = zone_of(L)
        for z in np.unique(zone):
            for b, *_ in BANDS:
                for e in np.unique(L["eco"]):
                    m = ok & (zone == z) & (band == b) & (L["eco"] == e)
                    a = float(c[m].sum())
                    if a > 0:
                        s["free_area_by_zone_band_eco_km2"].setdefault(z, {}).setdefault(b, {})[e] = round(a, 0)
    # conserved shares removed by ecozone
    for z, bands in s["free_area_by_zone_band_eco_km2"].items():
        for b, ecos in bands.items():
            v = sum(a * (1 - CONSERVED.get(e, 0.0)) for e, a in ecos.items())
            if v > 0:
                s["free_area_by_zone_and_band_km2"].setdefault(z, {})[b] = round(v, 0)
    s["conserved_share_by_ecozone"] = CONSERVED
    return s


if __name__ == "__main__":
    LL = [run_region(r) for r in REGIONS]
    S = summarise(LL)
    json.dump(S, open(OUT / "marine_space.json", "w"), indent=1)
    pickle.dump(LL, open(OUT / "_layers.pkl", "wb"))
    print(json.dumps({k: S[k] for k in ("study_area_eez_km2", "free_area_by_zone_and_band_km2")}, indent=1))
