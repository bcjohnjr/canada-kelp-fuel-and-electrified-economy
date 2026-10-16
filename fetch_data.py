"""Download the public input layers used by spatial.py into data/.

Natural Earth 1:10m land, admin-0 countries and 200 m / 1,000 m bathymetry (public domain), and the Global
Shipping Lanes v1 dataset (Benden 2022, CC BY 4.0), which is clipped to the three Canadian study areas (Pacific, Atlantic and Hudson Bay).
"""
import json
from pathlib import Path
from urllib.request import urlretrieve

from shapely.geometry import shape, box, mapping

HERE = Path(__file__).resolve().parent
BASE = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
SETS = [("10m_physical", "ne_10m_land"), ("10m_cultural", "ne_10m_admin_0_countries"),
        ("10m_physical/ne_10m_bathymetry_all", "ne_10m_bathymetry_K_200"),
        ("10m_physical/ne_10m_bathymetry_all", "ne_10m_bathymetry_J_1000")]
LANES = "https://raw.githubusercontent.com/newzealandpaul/Shipping-Lanes/main/data/Shipping_Lanes_v1.geojson"

for group, name in SETS:
    d = HERE / "data" / "naturalearth" / group
    d.mkdir(parents=True, exist_ok=True)
    for ext in ("shp", "shx", "dbf", "prj"):
        f = d / f"{name}.{ext}"
        if not f.exists():
            urlretrieve(f"{BASE}{group}/{name}.{ext}", f)
    print("installed", name)

out = HERE / "data" / "shiplanes" / "shipping_lanes_canada.geojson"
if not out.exists():
    raw = HERE / "data" / "shiplanes" / "Shipping_Lanes_v1.geojson"
    raw.parent.mkdir(parents=True, exist_ok=True)
    urlretrieve(LANES, raw)
    d = json.load(open(raw))
    feats = []
    for bb, nm in ((box(-142, 44, -120, 58), "pacific"), (box(-74, 38, -38, 62), "atlantic"),
                   (box(-96, 50, -64, 66), "hudson")):
        for f in d["features"]:
            g = shape(f["geometry"]).intersection(bb)
            if not g.is_empty:
                feats.append({"type": "Feature", "properties": {**f["properties"], "region": nm}, "geometry": mapping(g)})
    json.dump({"type": "FeatureCollection", "features": feats}, open(out, "w"))
    raw.unlink()
print("shipping lanes ready")
