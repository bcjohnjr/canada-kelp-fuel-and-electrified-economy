"""Main-text Figures 1-9 and Supporting Figures S2-S5, with Source Data recorded for every plotted panel."""
import csv
import json
import pickle
from pathlib import Path

import numpy as np
import matplotlib
import matplotlib.ticker
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch
import matplotlib.image as mpimg
import shapely

import economy as E
import fiscal as fi
import optimise as o
import scenarios as sc
from farm import ZONES, FarmCost, farm_cost
from biorefinery import routes
from spatial import PORTS, STEP, band_of, zone_of, free_mask
from figstyle import C, INK, INK2, MUTED, GRID, MM, save, hgrid, vgrid, record, dump_source

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
R = json.load(open(OUT / "results.json"))
MC = json.load(open(OUT / "monte_carlo_summary.json"))
RB = json.load(open(OUT / "robustness.json"))
LV = json.load(open(OUT / "levers.json"))
EX = json.load(open(OUT / "exports.json"))
XC = json.load(open(OUT / "export_ceiling.json"))
RF = json.load(open(OUT / "diagnostics.json"))
LKJ = json.load(open(OUT / "lakes.json"))
SRJ = json.load(open(OUT / "self_reliance.json"))
NEJ = json.load(open(OUT / "national_emissions.json"))
MCT = json.load(open(OUT / "monte_carlo_summary_transition.json"))
LOW = R["central"]          # central case: learning, 4% finance, full 2025 demand (827 TWh)
TRN = R["transition"]
F26 = LOW["fiscal"]["oct2026|avg2025"]
F25 = LOW["fiscal"]["avg2025|avg2025"]
ZL = {"pac_shelf": "Pacific shelf", "pac_slope": "Pacific slope", "pac_deep": "Pacific deep",
      "atl_shelf": "Atlantic shelf", "atl_slope": "Atlantic slope", "atl_deep": "Atlantic deep",
      "gsl_shelf": "Gulf of St Lawrence shelf", "gsl_slope": "Laurentian Channel", "lab_shelf": "Labrador shelf",
      "lab_slope": "Labrador slope", "hb_shelf": "Hudson Bay", "hb_slope": "Hudson Bay >200 m"}
ZL6 = {k: ZL[k] for k in ("pac_shelf", "pac_slope", "pac_deep", "atl_shelf", "atl_slope", "atl_deep")}


def mc_rows():
    return list(csv.DictReader(open(OUT / "monte_carlo.csv")))


# ------------------------------------------------------------------ Fig. 1 national kelp-farm siting map
HWY1 = [[(-123.37, 48.43), (-123.94, 49.17)],
        [(-123.1, 49.26), (-122.3, 49.05), (-121.44, 49.38), (-120.33, 50.67), (-119.28, 50.70), (-118.2, 51.0), (-116.96, 51.3),
         (-116.18, 51.43), (-115.57, 51.18), (-114.07, 51.05), (-110.68, 50.04), (-107.8, 50.29), (-105.53, 50.39), (-104.62, 50.45),
         (-99.95, 49.85), (-97.14, 49.9), (-94.49, 49.77), (-92.84, 49.78), (-89.25, 48.38), (-88.26, 49.01), (-86.4, 48.72),
         (-84.77, 47.99), (-84.33, 46.52), (-80.99, 46.49), (-79.46, 46.31), (-77.11, 45.83), (-75.7, 45.42), (-73.57, 45.5),
         (-72.48, 45.88), (-71.18, 46.8), (-69.53, 47.83), (-68.33, 47.37), (-66.64, 45.96), (-64.78, 46.09), (-63.28, 45.36),
         (-61.99, 45.62), (-60.25, 46.21)],
        [(-59.14, 47.57), (-57.95, 48.95), (-57.43, 49.17), (-55.66, 48.94), (-54.6, 48.95), (-53.97, 48.16), (-52.71, 47.56)]]
RAIL = {"Hudson Bay Railway": [(-94.18, 58.77), (-94.07, 57.5), (-97.0, 56.0), (-101.25, 53.82), (-100.2, 51.15), (-97.14, 49.9)],
        "Ontario Northland": [(-80.64, 51.28), (-80.9, 50.0), (-81.03, 49.07), (-79.85, 47.5), (-79.46, 46.31)]}
HUB_LABELS = {"Prince Rupert": (6, 4), "Port Alberni": (-34, -10), "Halifax": (4, -9), "Saint John": (-8, -11),
              "Sydney": (5, 3), "Argentia / Placentia Bay": (-40, -10), "Sept-Iles": (-6, 6), "Goose Bay": (-30, 5),
              "Churchill": (6, 2), "Moosonee": (6, -6)}
LAKE_LL = {"winnipeg": (-97.9, 52.5), "erie": (-81.2, 42.25), "stclair": (-82.7, 42.45), "ontario": (-77.4, 44.1),
           "simcoe": (-79.4, 44.4), "missisquoi": (-73.1, 45.03), "woods": (-94.8, 49.3), "manitoba": (-98.8, 50.9),
           "winnipegosis": (-100.1, 52.4), "lesser_slave": (-115.5, 55.45), "last_mountain": (-105.2, 51.1),
           "st_pierre": (-72.8, 46.2), "superior": (-87.5, 47.8), "huron": (-81.6, 45.3), "great_bear": (-121.0, 66.0),
           "great_slave": (-114.5, 61.6), "athabasca": (-109.0, 59.2), "reindeer": (-102.3, 57.3), "nipigon": (-88.5, 49.8),
           "mistassini": (-73.4, 51.0), "st_jean": (-72.0, 48.6), "nipissing": (-79.8, 46.25)}
REG_COL = {"pac": "#bfe3c6", "atl": "#bfe3c6", "gsl": "#c9dcef", "lab": "#c9dcef", "hb": "#ddd0ec"}


def _national_proj():
    from pyproj import Transformer
    return Transformer.from_crs("EPSG:4326", "+proj=lcc +lat_1=49 +lat_2=77 +lat_0=49 +lon_0=-91 +datum=WGS84 +units=m", always_xy=True)


def _place_farms(L, zone_band_km2, taken=None):
    """Fill free cells of each zone-band, nearest to land (or to the Hudson Bay landing points) first, up to the farm area."""
    ok = free_mask(L); band = band_of(L["dist_land"]); zone = zone_of(L)
    farm = np.zeros(L["lon"].shape, bool) if taken is None else taken.copy()
    for zb, area in zone_band_km2.items():
        z, b = zb.split("|")
        idx = np.where(ok & (zone == z) & (band == b) & ~farm)[0]
        if not len(idx):
            continue
        idx = idx[np.argsort(L["dist_land"][idx])]
        cum = np.cumsum(L["cell"][idx])
        farm[idx[: np.searchsorted(cum, area) + 1]] = True
    return farm


def fig1():
    import shapefile as shp
    from shapely.geometry import shape as shp_shape, box as sbox
    from shapely.ops import transform as stf
    LL = pickle.load(open(OUT / "_layers.pkl", "rb"))
    EB = R["eb"]; SIT = json.load(open(OUT / "siting.json")); H1J = json.load(open(OUT / "highway1.json"))
    tf = _national_proj()
    fig = plt.figure(figsize=(180 * MM, 150 * MM))
    ax = fig.add_axes([0.0, 0.31, 1.0, 0.69])
    bb = sbox(-150, 30, -40, 75)
    rd = shp.Reader(str(HERE / "data/naturalearth/10m_cultural/ne_10m_admin_0_countries"))
    flds = [f[0] for f in rd.fields[1:]]
    for sr in rd.iterShapeRecords():
        rec = dict(zip(flds, sr.record))
        g = shp_shape(sr.shape.__geo_interface__)
        if not g.intersects(bb):
            continue
        g = stf(tf.transform, g.intersection(bb).simplify(0.03))
        fc = "#ece8de" if rec["ADM0_A3"] == "CAN" else "#f4f3f0"
        for p in shapely.get_parts(g):
            if p.geom_type == "Polygon" and p.area > 2e8:
                xs, ys = p.exterior.xy
                ax.fill(xs, ys, color=fc, ec="#8c8273", lw=0.25, zorder=1)
    rows = []
    for L in LL:
        ok = free_mask(L); zone = zone_of(L)
        reg = np.array([z.split("_")[0] for z in zone])
        X, Y = tf.transform(L["lon"], L["lat"])
        for r_ in np.unique(reg[ok]):
            m = ok & (reg == r_)
            ax.scatter(X[m], Y[m], s=0.7, marker="s", lw=0, color=REG_COL[r_], zorder=2, rasterized=True)
        cen = _place_farms(L, {k: v for k, v in LOW["kelp_by_zone_band_km2"].items()})
        ebf = _place_farms(L, {k: max(v - LOW["kelp_by_zone_band_km2"].get(k, 0.0), 0.0) for k, v in EB["kelp_by_zone_band_km2"].items()}, taken=cen)
        ebf &= ~cen
        ax.scatter(X[ebf], Y[ebf], s=0.8, marker="s", lw=0, color="#4f9a5e", zorder=3, rasterized=True)
        ax.scatter(X[cen], Y[cen], s=0.8, marker="s", lw=0, color="#145a32", zorder=4, rasterized=True)
        rows += [(L["region"], "central farms km2", float(L["cell"][cen].sum())), (L["region"], "additional farms, electric-or-biofuel km2", float(L["cell"][ebf].sum()))]
    lkp = {r_["key"]: r_ for r_ in LKJ["all_lakes"]}
    lrows = []
    for k, (lo, la) in LAKE_LL.items():
        r_ = lkp[k]; x_, y_ = tf.transform(lo, la)
        if r_["p_removed_t"] > 1:
            ax.scatter(x_, y_, s=8 + 40 * np.sqrt(r_["p_removed_t"] / 1000), color=C["violet"], ec="white", lw=0.5, zorder=6)
        elif r_["trophic"] == "eutrophic":
            ax.scatter(x_, y_, s=10, facecolor="white", ec=C["violet"], lw=0.8, zorder=6)
        else:
            ax.scatter(x_, y_, s=10, facecolor="white", ec=C["blue"], lw=0.8, zorder=6)
        lrows.append((r_["name"], r_["trophic"], r_["tp_mgl"], r_["p_removed_t"]))
    record("Fig1", "a_lakes", ["lake", "trophic status", "TP mg/L", "P removed t/yr (least-cost)"], lrows)
    for seg in HWY1:
        xs, ys = tf.transform(*zip(*seg))
        ax.plot(xs, ys, color=C["red"], lw=1.6, zorder=5, solid_capstyle="round")
    for nm, seg in RAIL.items():
        xs, ys = tf.transform(*zip(*seg))
        ax.plot(xs, ys, color=INK2, lw=0.8, ls=(0, (2, 1.2)), zorder=5)
    for nm, (dx, dy) in HUB_LABELS.items():
        la, lo, _ = PORTS[nm]
        x_, y_ = tf.transform(lo, la)
        ax.plot(x_, y_, "o", ms=3.0, mfc="white", mec=INK, mew=0.8, zorder=6)
        ax.annotate(nm.split(" /")[0].replace("Sept-Iles", "Sept-Îles"), (x_, y_), xytext=(dx, dy), textcoords="offset points",
                    fontsize=5.4, color=INK, zorder=7)
    lab = [(-136.0, 51.2, "British Columbia\ncoast"), (-61.5, 41.4, "Scotian Shelf and\nBay of Fundy"), (-63.0, 48.1, "Gulf of\nSt Lawrence"),
           (-53.5, 56.5, "Labrador and\nNE Newfoundland"), (-86.0, 60.6, "Hudson Bay"), (-79.6, 53.3, "James\nBay"),
           (-103.0, 55.0, "MANITOBA"), (-86.0, 50.6, "ONTARIO")]
    for lo, la, t in lab:
        x_, y_ = tf.transform(lo, la)
        ax.text(x_, y_, t, fontsize=5.8 if t.isupper() else 6.0, color=INK2, ha="center", va="center", zorder=7,
                weight="bold" if t.isupper() else "normal", style="normal" if t.isupper() else "italic")
    pts = [(-137, 48), (-138, 56), (-48.5, 46.5), (-55, 60.5), (-82, 41.3), (-70, 41.0), (-91, 64.5), (-121, 67.0), (-64, 61.5)]
    bx, by_ = tf.transform([p[0] for p in pts], [p[1] for p in pts])
    ax.set_xlim(min(bx) - 1e5, max(bx) + 1e5); ax.set_ylim(min(by_) - 1e5, max(by_) + 1e5); ax.set_aspect("equal"); ax.axis("off")
    e = EB["ers"] if "ers" in EB else H1J["eb"]["ers"]
    leg = [Patch(fc="#145a32", label=f"Farms, least-cost case ({LOW['kelp_total_km2']:,.0f} km²)"),
           Patch(fc="#4f9a5e", label=f"Added in the electric-or-biofuel case (total {EB['kelp_total_km2']:,.0f} km²)"),
           Patch(fc=REG_COL["pac"], label="Primary candidate waters (ice-free)"),
           Patch(fc=REG_COL["gsl"], label="Seasonal-ice candidate waters (Gulf, Labrador)"),
           Patch(fc=REG_COL["hb"], label="Hudson Bay candidate waters (Manitoba, Ontario)"),
           plt.Line2D([], [], color=C["red"], lw=1.6, label=f"Electrified Trans-Canada Highway ({H1J['eb']['ers']['route_km']:,.0f} km catenary)"),
           plt.Line2D([], [], color=INK2, lw=0.8, ls=(0, (2, 1.2)), label="Rail to Churchill and Moosonee"),
           plt.Line2D([], [], marker="o", ls="", mfc="white", mec=INK, ms=3.5, label="Biorefinery hubs"),
           plt.Line2D([], [], marker="o", ls="", mfc=C["violet"], mec="white", ms=5, label="Lakes harvested by Grid Harvesters (size: P removed)"),
           plt.Line2D([], [], marker="o", ls="", mfc="white", mec=C["violet"], ms=3.5, label="Eutrophic lakes, harvest not least-cost"),
           plt.Line2D([], [], marker="o", ls="", mfc="white", mec=C["blue"], ms=3.5, label="Oligotrophic lakes (no harvest)")]
    ax.legend(handles=leg, loc="lower left", bbox_to_anchor=(0.0, 0.0), fontsize=5.0, frameon=True, framealpha=0.9,
              edgecolor="none", ncol=1)
    ax.text(0.01, 0.985, "(A) Candidate kelp-farm waters and farm sites", transform=ax.transAxes, fontsize=7, weight="bold", va="top")
    record("Fig1", "a_map_farm_area", ["study area", "item", "km2"], rows,
           "Farm cells are placed nearest to land (Hudson Bay: nearest to Churchill or Moosonee) within each zone and distance band; "
           "locations are illustrative, areas are model results.")
    # (B) area by region: available at the area caps, used in the two cases
    regs = ["pac", "atl", "gsl", "lab", "hb"]
    names = ["British Columbia", "Scotian Shelf, Fundy,\nsouth Newfoundland", "Gulf of St Lawrence", "Labrador and\nNE Newfoundland",
             "Hudson Bay"]
    ax2 = fig.add_axes([0.17, 0.06, 0.31, 0.20])
    av = [SIT["available_km2"].get(r_, 0) / 1000 for r_ in regs]
    uc = [SIT["solutions"]["central"]["by_region_km2"].get(r_, 0) / 1000 for r_ in regs]
    ue = [SIT["solutions"]["eb"]["by_region_km2"].get(r_, 0) / 1000 for r_ in regs]
    y = np.arange(len(regs))
    ax2.barh(y, av, 0.75, color="#e3e3e3", label="Available at the area caps")
    ax2.barh(y + 0.15, ue, 0.3, color="#4f9a5e", label="Used, electric-or-biofuel")
    ax2.barh(y - 0.15, uc, 0.3, color="#145a32", label="Used, least-cost")
    for i in range(len(regs)):
        ax2.text(av[i] + 0.8, i, f"{av[i]:.0f}", va="center", fontsize=5.6, color=INK2)
    ax2.set_yticks(y); ax2.set_yticklabels(names, fontsize=5.8); ax2.invert_yaxis()
    ax2.set_xlabel("Farm area (thousand km²)", fontsize=6); ax2.tick_params(labelsize=6); hgrid(ax2)
    ax2.legend(fontsize=5.3, loc="lower right"); ax2.set_xlim(0, max(av) * 1.75)
    ax2.set_title("(B) Farm area by region")
    record("Fig1", "b_area_by_region", ["region", "available km2", "used least-cost km2", "used electric-or-biofuel km2"],
           [(n.replace("\n", " "), a * 1000, b * 1000, c_ * 1000) for n, a, b, c_ in zip(names, av, uc, ue)])
    # (C) cheapest biomass cost at port by region
    ax3 = fig.add_axes([0.62, 0.06, 0.34, 0.20])
    cb = SIT["cheapest_biomass_cad_t"]
    vals = [min(v for k, v in cb.items() if k.startswith(r_ + "_")) for r_ in regs]
    ax3.barh(y, vals, 0.6, color=[REG_COL[r_] for r_ in regs], ec=INK2, lw=0.4)
    for i, v in enumerate(vals):
        ax3.text(v + 60, i, f"{v:,.0f}", va="center", fontsize=5.6, color=INK2)
    ax3.set_yticks(y); ax3.set_yticklabels([n.replace("\n", " ") if len(n) < 22 else n for n in names], fontsize=5.8); ax3.invert_yaxis()
    ax3.set_xlim(0, max(vals) * 1.25); ax3.set_xlabel("Cheapest kelp at port (CAD per dry t)", fontsize=6); ax3.tick_params(labelsize=6); hgrid(ax3)
    ax3.set_title("(C) Biomass cost by region")
    record("Fig1", "c_biomass_cost", ["region", "CAD per dry t (cheapest zone, band and nutrient method; learned yields, 4% finance)"],
           list(zip([n.replace("\n", " ") for n in names], vals)))
    save(fig, "Fig1_kelp_siting_map"); dump_source("Fig1")


# ------------------------------------------------------------------ Fig. S5 marine use classes in the three study areas
def figS5():
    LL = pickle.load(open(OUT / "_layers.pkl", "rb"))
    cols = ["#ffffff00", "#dbe8f3", "#f6d7a7", "#e98a4d", "#c9dcef", "#d35f5f", C["green"], "#bdbdbd"]
    fig = plt.figure(figsize=(180 * MM, 190 * MM))
    axes = [fig.add_axes([0.06, 0.57, 0.36, 0.40]), fig.add_axes([0.47, 0.57, 0.50, 0.40]), fig.add_axes([0.06, 0.05, 0.50, 0.36])]
    for ax, L, title in zip(axes, LL, ("(A) Pacific: British Columbia", "(B) Atlantic Canada and Labrador",
                                       "(C) Hudson Bay and James Bay")):
        lon, lat, cell = L["lon"], L["lat"], L["cell"]
        x0, y0, x1, y1 = L["bbox"]
        nx, ny = int(round((x1 - x0) / STEP)), int(round((y1 - y0) / STEP))
        ix = np.clip(np.floor((lon - x0) / STEP).astype(int), 0, nx - 1); iy = np.clip(np.floor((lat - y0) / STEP).astype(int), 0, ny - 1)
        code = np.where(L["fish"] == "inshore_0-6nm", 3, np.where(L["fish"] == "deep_low", 1, 2))
        code = np.where(L["ice"] != "none", 4, code)
        code = np.where(L["ship"], 5, code)
        code = np.where(L["excl"] & ~L["ship"], 7, code)
        farm = _place_farms(L, R["eb"]["kelp_by_zone_band_km2"])
        code = np.where(farm, 6, code)
        grid = np.zeros((ny, nx)); grid[iy, ix] = code
        ax.imshow(np.ma.masked_equal(grid, 0), origin="lower", extent=(x0, x1, y0, y1), cmap=ListedColormap(cols),
                  vmin=0, vmax=7, interpolation="nearest")
        for g in shapely.get_parts(L["land"]):
            if g.geom_type == "Polygon":
                xs, ys = g.exterior.xy
                ax.fill(xs, ys, color="#ece8de", ec="#8c8273", lw=0.3)
        for n, (la, lo, r) in PORTS.items():
            if x0 <= lo <= x1 and y0 <= la <= y1:
                ax.plot(lo, la, "o", ms=1.8, color=INK)
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
        ax.set_aspect(1 / np.cos(np.radians((y0 + y1) / 2)))
        ax.tick_params(labelsize=5.8)
        xt = range(int(np.ceil(x0 / 5) * 5), int(x1) + 1, 5)
        ax.set_xticks(list(xt)); ax.set_xticklabels([f"{-v}°W" for v in xt])
        yt = range(int(np.ceil(y0 / 2) * 2), int(y1) + 1, 2 if L["region"] == "Pacific" else 4)
        ax.set_yticks(list(yt)); ax.set_yticklabels([f"{v}°N" for v in yt])
        ax.set_title(title, fontsize=6.6)
    axes[0].text(-125.6, 54.6, "BRITISH\nCOLUMBIA", fontsize=6, color=INK2, weight="bold", ha="center")
    axes[0].text(-137.5, 48.0, "PACIFIC OCEAN", fontsize=6.5, color=INK2)
    axes[1].text(-62.0, 48.6, "Gulf of\nSt Lawrence", fontsize=5.6, color=INK2, ha="center")
    axes[1].text(-50.0, 41.0, "ATLANTIC OCEAN", fontsize=6.5, color=INK2)
    axes[1].text(-48.0, 55.5, "Icebergs and pack ice\n(excluded beyond 1,000 m)", fontsize=5.4, color=INK2, ha="center")
    axes[1].text(-63.0, 56.8, "LABRADOR", fontsize=5.6, color=INK2, weight="bold", ha="center")
    axes[2].text(-86.0, 59.5, "HUDSON BAY", fontsize=6.5, color=INK2)
    axes[2].text(-91.0, 54.2, "MANITOBA / ONTARIO", fontsize=5.6, color=INK2, weight="bold", ha="center")
    leg = [Patch(fc=cols[6], label=f"Kelp farms, electric-or-biofuel case ({R['eb']['kelp_total_km2']:,.0f} km²)"),
           Patch(fc=cols[3], label="0–6 nm: inshore fisheries, kelp forests (excluded)"),
           Patch(fc=cols[2], label="6 nm to 1,000 m: shelf and slope fisheries"),
           Patch(fc=cols[1], label="Deep water >1,000 m"),
           Patch(fc=cols[4], label="Seasonal sea ice (ice-rated farms)"),
           Patch(fc=cols[5], label="Shipping lanes and port approaches (excluded)"),
           Patch(fc=cols[7], label="Icebergs offshore, low salinity, beyond haul range (excluded)"),
           plt.Line2D([], [], marker="o", ls="", color=INK, ms=2.5, label="Ports")]
    fig.legend(handles=leg, loc="upper center", bbox_to_anchor=(0.5, 0.525), fontsize=5.4, frameon=False, ncol=2)
    ax2 = fig.add_axes([0.72, 0.06, 0.25, 0.32])
    zs = [z for z in ZL if z in ZONES]
    bands = ["0-50", "50-100", "100-200", "200-370"]
    bc = [C["blue"], C["aqua"], C["yellow"], C["magenta"]]
    left = np.zeros(len(zs)); rows = []
    for b, cc in zip(bands, bc):
        v = np.array([ZONES[z].area_km2.get(b, 0) / 1000 for z in zs])
        ax2.barh(range(len(zs)), v, left=left, color=cc, height=0.65, ec="white", lw=0.6, label=f"{b} km")
        left += v
        rows += [(ZL[z], b, vv * 1000) for z, vv in zip(zs, v)]
    for i, t in enumerate(left):
        ax2.text(t + 4, i, f"{t:,.0f}", va="center", fontsize=5.4, color=INK2)
    ax2.set_xlim(0, 400)
    ax2.set_yticks(range(len(zs))); ax2.set_yticklabels([ZL[z] for z in zs], fontsize=5.6); ax2.invert_yaxis()
    ax2.set_xlabel("Candidate area (thousand km²)", fontsize=6); ax2.tick_params(labelsize=6)
    ax2.legend(fontsize=5.2, title="Haul distance", title_fontsize=5.2, loc="lower right")
    ax2.set_title("(D) Candidate area by zone", fontsize=6.6)
    record("FigS5", "d_candidate_area", ["zone", "distance band", "candidate area km2"], rows,
           "Outside shipping lanes, ports, excluded waters and the 0-6 nm band; conserved share of each marine ecozone removed. "
           "Haul distance is to the nearest large land mass (Hudson Bay: to Churchill or Moosonee).")
    save(fig, "FigS5_marine_use"); dump_source("FigS5")


# ------------------------------------------------------------------ Fig. 2 kelp chain
def fig2():
    fig = plt.figure(figsize=(180 * MM, 125 * MM))
    gs = fig.add_gridspec(1, 2, width_ratios=[1.3, 1.0], wspace=0.35, left=0.08, right=0.80, top=0.94, bottom=0.52)
    gs2 = fig.add_gridspec(1, 1, left=0.26, right=0.80, top=0.38, bottom=0.08)
    axs = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs2[0, 0])]
    c = FarmCost()
    ax = axs[0]
    zs = list(ZL6.items())
    meth =[("natural", "Natural supply", C["aqua"]), ("depth_cycling", "Depth cycling", C["green"]),
            ("solar_pipe", "Pumped pipe", C["yellow"]), ("wave_pump", "Wave pump", C["orange"])]
    w = 0.19; rows = []
    for j, (m, ml, cc) in enumerate(meth):
        vals = []
        for z, zl in zs:
            r = farm_cost(z, list(ZONES[z].area_km2)[0], c, m)
            v = r["total_cad_t"] if np.isfinite(r["total_cad_t"]) else np.nan
            vals.append(v); rows.append((zl, ml, v, r["yield_t_ha"]))
        ax.bar(np.arange(len(zs)) + (j - 1.5) * w, vals, w * 0.92, color=cc, label=ml)
    ax.set_yscale("log"); ax.set_ylim(500, 1e5)
    ax.set_xticks(range(len(zs))); ax.set_xticklabels([z[1].replace(" ", "\n") for z in zs], fontsize=5.8)
    ax.set_ylabel("Biomass cost at port (CAD per dry t)"); vgrid(ax)
    ax.legend(fontsize=5.5, ncol=2, loc="upper left")
    ax.set_title("(A) Kelp biomass cost by nutrient supply (today)")
    record("Fig2", "a_biomass_cost", ["zone", "nutrient method", "CAD per dry t", "effective yield t/ha/yr"], rows,
           "Today's costs, 7% finance, nearest distance band; natural supply yields only the naturally supplied share.")
    ax = axs[1]
    RT = routes()
    keys = [("EH", "Ethanol + HTL"), ("H", "Whole HTL"), ("A", "Digestion")]
    comp = [("hc_gj", "Diesel/jet", C["blue"], 1), ("ethanol_gj", "Ethanol", C["yellow"], 1), ("ch4_gj", "Biomethane", C["aqua"], 1),
            ("fert_energy_gj", "Fertiliser energy avoided", C["magenta"], 1),
            ("el_mwh", "Electricity", C["orange"], -3.6), ("heat_mwh_th", "Process heat", C["red"], -3.6)]
    rows = []
    for i, (k, kl) in enumerate(keys):
        pos = neg = 0.0
        for f, fl, cc, sgn in comp:
            v = RT[k][f] * abs(sgn) * (1 if sgn > 0 else -1)
            if v >= 0:
                ax.bar(i, v, 0.6, bottom=pos, color=cc, ec="white", lw=0.6); pos += v
            else:
                ax.bar(i, v, 0.6, bottom=neg, color=cc, ec="white", lw=0.6); neg += v
            rows.append((kl, fl, v))
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.set_xticks(range(3)); ax.set_xticklabels(["Ethanol\n+ HTL", "Whole\nHTL", "Digestion"], fontsize=6)
    ax.set_ylabel("GJ per dry t of kelp"); vgrid(ax)
    ax.legend(handles=[Patch(fc=cc, label=fl) for _, fl, cc, _ in comp], fontsize=5.5, loc="upper left", bbox_to_anchor=(1.0, 1.0))
    ax.set_ylim(-4.5, 10)
    ax.set_title("(B) Wet biorefinery balances")
    record("Fig2", "b_refinery", ["route", "flow", "GJ per dry t (inputs negative)"], rows)
    ax = axs[2]
    def heat_costs(p):
        a = p["adder"]; h = p["heat"]
        flex = p["wind"]["tiers"][1]["lcoe"] + a["flex_wind"] + a["network_flex"]
        grid = p["wind"]["tiers"][1]["lcoe"] + a["wind"] + a["network_direct"]
        res = p["forest"]["cost_odt"] / h["bio_boiler_mwh_per_odt"] + h["bio_boiler_cost"]
        return [("Wind-charged thermal storage", flex / h["tes_eff"] + h["tes_cost"]),
                ("Heat pump (low-temperature)", grid / h["hp_cop"]),
                ("Electric boiler (grid)", grid / h["eboiler_eff"]),
                ("Forest-residue boiler", res)]
    ht, hl = heat_costs(o.base_params()), heat_costs(sc.cheaper_capital(o.base_params()))
    y = np.arange(len(ht))
    ax.barh(y + 0.19, [v for _, v in ht], 0.36, color=C["orange"], label="7% finance")
    ax.barh(y - 0.19, [v for _, v in hl], 0.36, color=C["blue"], label="4% finance")
    for i in range(len(ht)):
        ax.text(ht[i][1] + 2, i + 0.19, f"{ht[i][1]:.0f}", va="center", fontsize=5.8, color=INK2)
        ax.text(hl[i][1] + 2, i - 0.19, f"{hl[i][1]:.0f}", va="center", fontsize=5.8, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels([n for n, _ in ht], fontsize=6); ax.invert_yaxis()
    ax.set_xlim(0, 160); ax.set_xlabel("Cost of delivered heat (CAD per MWh_th)"); hgrid(ax)
    ax.legend(fontsize=5.5, loc="lower right")
    ax.set_title("(C) Refinery process heat without fossil fuel")
    record("Fig2", "c_heat", ["source", "CAD/MWh_th at 7%", "CAD/MWh_th at 4%"], [(a, b, d) for (a, b), (_, d) in zip(ht, hl)],
           "Tier-2 wind; heat pumps limited to 60% of refinery heat (low-temperature duties); residues compete with residue fuels.")
    save(fig, "Fig2_kelp_chain"); dump_source("Fig2")


# ------------------------------------------------------------------ Fig. 3 least-cost system
def fig3():
    s = LOW
    fig = plt.figure(figsize=(180 * MM, 150 * MM))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.05], hspace=0.42, wspace=0.75, left=0.21, right=0.97, top=0.95, bottom=0.07)
    axs = [fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[1, :])]
    ax = axs[0]
    g = s["generation_twh"]
    sup = [("Onshore wind", g["Onshore wind"]), ("PV", g["PV"]), ("Hydro (redirected exports)", g["Hydro (redirected exports)"]),
           ("New hydro", g["New hydro"])]
    use = [("Vehicles and rail", s["electricity_vehicles_rail_twh"]), ("Biorefineries", s["electricity_refineries_twh"]),
           ("Thermal storage", s["electricity_for_heat_storage_twh"]), ("Electrofuels", s["electricity_for_efuels_twh"]),
           ("Direct air capture", s["electricity_for_dac_twh"])]
    rows = [("supply", n, v) for n, v in sup] + [("use", n, v) for n, v in use]
    colmap = {"Onshore wind": C["blue"], "PV": C["yellow"], "Hydro (redirected exports)": C["aqua"], "New hydro": C["aqua"]}
    items = [(f"Supply: {n}", v, colmap[n]) for n, v in sup if v > 1e-3] + [(f"Use: {n.lower()}", v, MUTED) for n, v in use if v > 1e-3]
    ns = sum(1 for n, v in sup if v > 1e-3)
    yy = [i if i < ns else i + 0.6 for i in range(len(items))]
    ax.barh(yy, [v for _, v, _ in items], 0.6, color=[c_ for _, _, c_ in items])
    for y_, (n, v, _) in zip(yy, items):
        ax.text(v + 4, y_, f"{v:.0f}", va="center", fontsize=5.8, color=INK2)
    ax.set_yticks(yy); ax.set_yticklabels([n for n, _, _ in items], fontsize=5.8); ax.invert_yaxis()
    ax.set_xlim(0, max(v for _, v, _ in items) * 1.25); ax.set_xlabel("New electricity (TWh yr⁻¹)"); hgrid(ax)
    ax.set_title("(A) Electricity")
    record("Fig4", "a_electricity", ["side", "item", "TWh/yr"], rows)
    ax = axs[1]
    f = s["fuels_twh"]
    keep = 1 - (s["export_twh"] / s["dropin_supply_twh"] if s["dropin_supply_twh"] else 0)
    fl = [("Forest-residue HTL", f["forest_residue_HTL"], C["orange"]), ("Farm-residue FT", f["agri_residue_FT"], C["yellow"]),
          ("Kelp HTL diesel/jet", f["kelp HTL diesel/jet"], C["green"]), ("Kelp biomethane", f["kelp biomethane (net of fleet)"], C["aqua"]),
          ("Lake and marsh biomass (HTL)", f["lake HTL diesel/jet"], C["blue"]),
          ("Waste-lipid HVO", f["HEFA_waste_lipids"], C["magenta"]), ("Canola HVO", f["canola_HVO"], C["magenta"]),
          ("Grain ethanol", f["grain_ethanol_existing"], C["yellow"]), ("Landfill/manure biomethane", f["waste_biomethane"], C["red"]),
          ("e-Fischer–Tropsch", f["eFT_liquids"], C["violet"]), ("e-Methanol", f["e_methanol"], C["violet"])]
    rows = [(n, v) for n, v, cc in fl]
    fl2 = [x for x in fl if x[1] > 1e-3]
    ax.barh(range(len(fl2)), [v for _, v, _ in fl2], 0.6, color=[cc for _, _, cc in fl2])
    for i, (n, v, cc) in enumerate(fl2):
        ax.text(v + 1.5, i, f"{v:.1f}", va="center", fontsize=5.8, color=INK2)
    ax.set_yticks(range(len(fl2))); ax.set_yticklabels([n for n, _, _ in fl2], fontsize=5.8); ax.invert_yaxis()
    ax.set_xlim(0, max(v for _, v, _ in fl2) * 1.25); ax.set_xlabel("Fuel supply (TWh yr⁻¹)"); hgrid(ax)
    ax.set_title("(B) Fuels")
    record("Fig4", "b_fuels", ["fuel", "TWh/yr"], rows)
    ax = axs[2]
    H1J = json.load(open(OUT / "highway1.json"))
    car = [("battery", "Battery-electric", C["blue"]), ("catenary", "Catenary-electric, Trans-Canada Highway", C["red"]),
           ("biofuel", "Renewable liquid", C["green"]), ("other", "Methanol, ammonia, methane", C["violet"])]
    segs = [r["segment"] for r in H1J["central"]["end_use"]]
    rows = []
    for i, sl in enumerate(segs):
        for j, (case, off) in enumerate((("central", -0.19), ("eb", 0.19))):
            r = next(x for x in H1J[case]["end_use"] if x["segment"] == sl)
            left = 0.0
            for k, cl, cc in car:
                v = r[k]
                if v > 1e-3:
                    ax.barh(i + off, v, 0.34, left=left, color=cc, ec="white", lw=0.4, alpha=1.0 if case == "eb" else 0.55)
                    left += v
                rows.append((sl, "least-cost" if case == "central" else "electric-or-biofuel", cl, v))
        ax.text(r["demand_twh"] + 6, i, f"{r['demand_twh']:.0f}", va="center", fontsize=5.6, color=INK2)
    ax.set_yticks(range(len(segs))); ax.set_yticklabels([x.replace("Construction, forestry machinery", "Construction and forestry\nmachinery") for x in segs], fontsize=5.6); ax.invert_yaxis()
    ax.set_xlabel("Fossil energy replaced (TWh yr⁻¹)"); hgrid(ax); ax.set_xlim(0, 480)
    ax.legend(handles=[Patch(fc=cc, label=cl) for _, cl, cc in car], fontsize=5.6, loc="lower right")
    ax.set_title("(C) Segments: least-cost case (pale, upper bar) and electric-or-biofuel case (lower bar)")
    record("Fig4", "c_segments", ["segment", "case", "carrier", "TWh fossil replaced"], rows,
           "Renewable liquid = drop-in diesel/jet and ethanol; in the least-cost case the drop-in pool includes electrofuels.")
    save(fig, "Fig4_least_cost_system"); dump_source("Fig4")


# ------------------------------------------------------------------ Fig. 4 prices, taxes and profits
def fig4():
    fig = plt.figure(figsize=(180 * MM, 140 * MM))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.15, 1.0], height_ratios=[1.0, 0.95], hspace=0.62, wspace=0.32,
                          left=0.08, right=0.98, top=0.95, bottom=0.08)
    ax = fig.add_subplot(gs[0, 0])
    bars = []
    for per, lab in (("oct2026", "Oct 2026\nprices"), ("avg2025", "2025\nprices")):
        a = LOW["fiscal"][f"{per}|avg2025"]
        fossil = dict(tax=a["fuel_tax_now_bn"], supply=a["fossil_pretax_bn"])
        opdep = LOW["objective_bn"] - LOW["vehicle_premium_bn"] - a["capital_return_bn"]
        ren = dict(tax=a["fuel_tax_bn"], veh=LOW["vehicle_premium_bn"], opdep=opdep, ret=a["capital_return_bn"], rent=a["rent_bn"])
        bars.append((f"Fossil,\n{lab}", fossil, a)); bars.append((f"Renewable,\n{lab}", ren, a))
    comp = [("tax", "Statutory per-unit fuel taxes (fossil: as levied)", MUTED), ("supply", "Fossil fuel, pre-tax", "#7b6f62"),
            ("veh", "Vehicle purchase premia", "#b9d8b0"), ("opdep", "Operating costs and depreciation", C["blue"]),
            ("ret", "Return on capital", C["aqua"]), ("rent", "Economic rent, if collected (deficit hatched)", C["green"])]
    rows = []
    for i, (lab, d, a) in enumerate(bars):
        pos, neg = 0.0, 0.0
        for k, kl, cc in comp:
            v = d.get(k, 0.0)
            if v >= 0:
                ax.bar(i, v, 0.62, bottom=pos, color=cc, ec="white", lw=0.5); pos += v
            else:
                ax.bar(i, v, 0.62, bottom=neg, color=C["red"], ec="white", lw=0.5, hatch="////"); neg += v
            rows.append((lab.replace("\n", " "), kl, v))
        ax.text(i, pos + 3, f"{a['user_spend_pre_sales_tax_bn']:.0f}", ha="center", fontsize=5.8, color=INK2)
    ax.axhline(0, color=MUTED, lw=0.6)
    ax.set_xticks(range(len(bars))); ax.set_xticklabels([b[0] for b in bars], fontsize=5.8)
    ax.set_ylabel("CAD billion per year"); vgrid(ax); ax.set_ylim(-25, 250)
    ax.legend(handles=[Patch(fc=cc, label=kl) for _, kl, cc in comp], fontsize=4.8, loc="upper left", ncol=2, columnspacing=0.8)
    ax.set_title("(A) Where users' fuel spending goes at constant pump prices")
    record("Fig5", "a_spending", ["system and price", "component", "CAD bn/yr"], rows,
           "Spending before sales tax (identical in each pair; labels above bars). Renewable: central case (827 TWh) with statutory taxes restored.")
    ax = fig.add_subplot(gs[0, 1])
    oil = R["oil"]["avg2025"]
    groups = [("Oil and gas\n(2019–23 taxes,\n2025 profits)", oil["royalties_land"], oil["income_tax"], oil["operating_profit"] - oil["income_tax"])]
    for per, lab in (("oct2026", "Renewable,\nOct 2026 prices"), ("avg2025", "Renewable,\n2025 prices")):
        a = LOW["fiscal"][f"{per}|avg2025"]
        groups.append((lab, a["royalty_bn"], a["cit_bn"], a["after_tax_profit_bn"]))
    rows = []
    for i, (lab, roy, cit, prof) in enumerate(groups):
        ax.bar(i, roy, 0.6, color=C["orange"], ec="white", lw=0.5)
        ax.bar(i, cit, 0.6, bottom=roy, color=C["yellow"], ec="white", lw=0.5)
        ax.bar(i, prof, 0.6, bottom=roy + cit, color=C["blue"], ec="white", lw=0.5)
        ax.text(i, roy + cit + prof + 1.5, f"{roy + cit + prof:.1f}", ha="center", fontsize=6, color=INK)
        rows.append((lab.replace("\n", " "), roy, cit, prof, roy + cit + prof))
    ax.set_xticks(range(len(groups))); ax.set_xticklabels([g[0] for g in groups], fontsize=5.8)
    ax.set_ylabel("CAD billion per year"); vgrid(ax); ax.set_ylim(0, 100)
    ax.legend(handles=[Patch(fc=C["orange"], label="Royalties and land sales"), Patch(fc=C["yellow"], label="Corporate income tax"),
                       Patch(fc=C["blue"], label="After-tax operating profit")], fontsize=5.5, loc="upper right", ncol=1)
    ax.set_title("(B) Surplus and its split (rent fully collected)")
    record("Fig5", "b_surplus", ["system", "royalties and land sales bn", "corporate income tax bn", "after-tax operating profit bn", "total bn"], rows,
           "Renewable royalty set equal to the oil-and-gas royalties and land sales it replaces (capped at the surplus).")
    ax = fig.add_subplot(gs[1, 0])
    pr26 = LOW["fiscal"]["oct2026|price"]; pr25 = LOW["fiscal"]["avg2025|price"]
    mc26 = MC["pump_oil_oct2026_p50"]; mcbe = MC["pump_breakeven_oct2026_p50"]
    marks = [("2025 average", {k: E.RETAIL["avg2025"][k] for k in ("gasoline", "diesel")}, MUTED, "s"),
             ("Renewable break-even (least-cost case)", pr26["pump_breakeven"], C["aqua"], "o"),
             ("Renewable break-even (Monte Carlo median)", mcbe, C["aqua"], "D"),
             ("October 2026 (held constant)", {k: E.RETAIL["oct2026"][k] for k in ("gasoline", "diesel")}, INK, "|"),
             ("Matches oil-and-gas benchmark (least-cost case)", pr26["pump_oil_2025"], C["green"], "o"),
             ("Replaces oil-and-gas surplus (Monte Carlo median)", mc26, C["green"], "D")]
    rows = []
    for j, f in enumerate(("gasoline", "diesel")):
        yb = 1 - j
        ax.plot([min(m[1][f] for m in marks), max(m[1][f] for m in marks)], [yb, yb], color=GRID, lw=2.5, zorder=0)
        for lab, d, cc, mk in marks:
            ax.plot(d[f], yb, marker=mk, color=cc, ms=7 if mk == "|" else 5, mew=2 if mk == "|" else 0.8, ls="", zorder=3)
            rows.append((f, lab, d[f]))
        ax.text(E.RETAIL["oct2026"][f], yb + 0.2, f"{E.RETAIL['oct2026'][f]:.1f}", ha="center", fontsize=5.8)
        ax.text(pr26["pump_breakeven"][f], yb - 0.27, f"{pr26['pump_breakeven'][f]:.0f}", ha="center", fontsize=5.6, color=C["aqua"])
        ax.text(E.RETAIL["avg2025"][f], yb + 0.2, f"{E.RETAIL['avg2025'][f]:.1f}", ha="center", fontsize=5.6, color=INK2)
        ax.text(mc26[f], yb - 0.27, f"{mc26[f]:.0f}", ha="center", fontsize=5.6, color=C["green"])
    ax.set_yticks([1, 0]); ax.set_yticklabels(["Gasoline", "Diesel"]); ax.set_ylim(-0.6, 2.1)
    ax.set_xlabel("Retail pump price (CAD cents per litre, all taxes)"); hgrid(ax)
    ax.set_xlim(125, 300); ax.set_ylim(-0.6, 3.3)
    ax.legend(handles=[plt.Line2D([], [], marker=mk, color=cc, ls="", ms=5, mew=2 if mk == "|" else 0.8, label=lab) for lab, _, cc, mk in marks],
              fontsize=4.9, loc="upper center", ncol=2, frameon=False)
    ax.set_title("(C) Pump prices that pay for the renewable system")
    record("Fig5", "c_pump_prices", ["fuel", "price point", "c/L"], rows,
           "Break-even: covers system cost incl. normal return, vehicle premia and statutory fuel taxes. Oil replacement: also earns the "
           "CAD 66.8 bn pre-royalty commercial and fiscal surplus of oil and gas extraction and refining (2025 profits); assumes the rent is fully collected.")
    ax = fig.add_subplot(gs[1, 1])
    cap = RF["capture"]
    xs = [r["capture"] * 100 for r in cap["central"]["rows"]]
    ax.plot(xs, [r["coverage"] for r in cap["central"]["rows"]], "-o", color=C["green"], ms=3.5, lw=1.4, label="Least-cost case (827 TWh)")
    ax.plot(xs, [r["coverage"] for r in cap["transition"]["rows"]], "--s", color=C["blue"], ms=3, lw=1.1, label="Transition case (796 TWh)")
    for x_, r in zip(xs, cap["central"]["rows"]):
        ax.text(x_, r["coverage"] - 0.075, f"{r['coverage']:.2f}", ha="center", fontsize=5.6, color=C["green"])
    ax.axhline(1.0, color=INK, lw=0.9)
    ax.text(2, 1.02, "Oil-and-gas benchmark", fontsize=5.6)
    ax.set_xlim(-5, 105); ax.set_ylim(0, 1.12); ax.set_xticks(xs)
    ax.set_xlabel("Share of the economic rent collected (%)"); ax.set_ylabel("Share of oil-and-gas benchmark (Oct 2026)"); vgrid(ax)
    ax.legend(fontsize=5.4, loc="lower right")
    cc_ = cap["central"]
    ax.text(-3, 0.80, f"Rent {cc_['rent_bn']:.1f} bn: electrified km {cc_['efficiency_surplus_bn']:+.1f},\nrenewable liquids {cc_['liquid_rent_bn']:+.1f}",
            fontsize=5.2, color=INK2)
    ax.set_title("(D) Only a collected rent becomes surplus")
    rows = [(k, r["capture"], r["coverage"], r["ebit_bn"], r["user_saving_bn"]) for k in ("central", "transition") for r in cap[k]["rows"]]
    record("Fig5", "d_capture", ["case", "share of rent collected", "surplus replaced", "EBIT bn", "left with users bn"], rows,
           f"Central case: rent {cc_['rent_bn']:.2f} bn = efficiency surplus on electrified km {cc_['efficiency_surplus_bn']:.2f} bn "
           f"+ renewable liquids {cc_['liquid_rent_bn']:.2f} bn (electricity valued at its marginal cost); return on capital {cc_['capital_return_bn']:.2f} bn.")
    save(fig, "Fig5_prices_taxes_profits"); dump_source("Fig5")


# ------------------------------------------------------------------ Fig. 5 robustness of the answer
def fig5():
    mc = mc_rows()
    cov = np.array([float(r["coverage_oct2026"]) for r in mc])
    m26 = np.array([float(r["mult_oil_oct2026"]) for r in mc]); be26 = np.array([float(r["mult_breakeven_oct2026"]) for r in mc])
    m25 = np.array([float(r["mult_oil_2025"]) for r in mc]); be25 = np.array([float(r["mult_breakeven_2025"]) for r in mc])
    fig = plt.figure(figsize=(180 * MM, 128 * MM))
    gt = fig.add_gridspec(1, 2, wspace=0.3, left=0.08, right=0.98, top=0.95, bottom=0.62)
    gs = fig.add_gridspec(1, 2, wspace=0.95, left=0.08, right=0.98, top=0.46, bottom=0.12, width_ratios=[1, 0.85])
    gs = {(0, 0): gt[0, 0], (0, 1): gt[0, 1], (1, 0): gs[0, 0], (1, 1): gs[0, 1]}
    ax = fig.add_subplot(gs[(0, 0)])
    bins = np.linspace(0.5, 1.1, 37)
    ax.hist(cov, bins=bins, color=C["green"], ec="white", lw=0.5)
    ax.axvline(1.0, color=INK, lw=1.1); ax.axvline(F26["pie_coverage"], color=INK2, lw=0.8, ls=":")
    yl = ax.get_ylim()[1]
    ax.text(1.005, yl * 0.9, "Oil-and-gas\nsurplus", fontsize=5.6)
    ax.text(F26["pie_coverage"] - 0.005, yl * 0.62, "Central\ncase", fontsize=5.6, ha="right", color=INK2)
    ax.set_xlabel("Renewable operating surplus ÷ oil-and-gas surplus\n(October 2026 pump prices)"); ax.set_ylabel("Draws (of 1,000)")
    ax.set_title("(A) Monte Carlo: share of the oil-and-gas benchmark")
    h, e = np.histogram(cov, bins=bins)
    record("Fig6", "a_coverage", ["bin low", "bin high", "draws"], [(e[i], e[i + 1], int(h[i])) for i in range(len(h))],
           f"Central case (827 TWh); rent fully collected. Median {MC['coverage_oct2026_p5_p50_p95'][1]:.3f}; deterministic central case {F26['pie_coverage']:.3f}.")
    ax = fig.add_subplot(gs[(0, 1)])
    data = [be26, m26, be25, m25]
    labels = ["Break-even\nvs Oct 2026", "Replace oil\nvs Oct 2026", "Break-even\nvs 2025", "Replace oil\nvs 2025"]
    bp = ax.boxplot(data, whis=(5, 95), widths=0.5, patch_artist=True, showfliers=False, medianprops=dict(color=INK, lw=1.0))
    for patch, cc in zip(bp["boxes"], [C["aqua"], C["green"], C["aqua"], C["green"]]):
        patch.set_facecolor(cc); patch.set_alpha(0.75); patch.set_edgecolor(INK2)
    ax.axhline(1.0, color=INK, lw=0.9)
    ax.set_xticks(range(1, 5)); ax.set_xticklabels(labels, fontsize=5.8)
    ax.set_ylabel("Multiplier (box 25–75%, whiskers 5–95%)"); vgrid(ax)
    for i, d in enumerate(data, 1):
        ax.text(i + 0.3, np.median(d), f"{np.median(d):.2f}", va="center", fontsize=5.6, color=INK2)
    ax.set_title("(B) Pump-price multiplier needed")
    record("Fig6", "b_multipliers", ["measure", "p5", "p25", "median", "p75", "p95"],
           [(l.replace("\n", " "), *np.percentile(d, [5, 25, 50, 75, 95]).tolist()) for l, d in zip(labels, data)])
    ax = fig.add_subplot(gs[(1, 0)])
    cum = LV["cumulative"]
    labs = ["Today's\ncosts", "Farm\ncost", "Yield", "Deep\nstructures", "Conver-\nsion", "Refinery\ncapex", "Electro-\nfuels", "4%\nfinance", "Demand"]
    vals = [x["coverage"] for x in cum]
    ax.plot(range(len(vals)), vals, "-o", color=C["green"], ms=3.5, lw=1.4)
    for i, v in enumerate(vals):
        ax.text(i - 0.1, v + 0.014, f"{v:.2f}", ha="center", fontsize=5.4, color=INK2)
    for i, x in enumerate(cum):
        ax.text(i, 0.665, f"{x['kelp_share']:.0f}%", ha="center", fontsize=5.4, color=C["green"])
    ax.text(-0.45, 0.69, "Kelp share of transport energy:", fontsize=5.4, color=C["green"])
    ax.axhline(1.0, color=INK, lw=0.9)
    ax.set_xticks(range(len(vals))); ax.set_xticklabels([l.replace("\n", " ").replace("- ", "") for l in labs], fontsize=5.4, rotation=35, ha="right")
    ax.set_ylabel("Share of oil-and-gas benchmark (Oct 2026)"); ax.set_ylim(0.65, 1.15); vgrid(ax)
    ax.set_title("(C) Cost levers applied cumulatively")
    record("Fig6", "c_levers", ["step", "surplus replaced", "cost bn", "kelp share %", "kelp km2"],
           [(x["key"], x["coverage"], x["cost"], x["kelp_share"], x["kelp_km2"]) for x in cum])
    ax = fig.add_subplot(gs[(1, 1)])
    rows = sorted([r for r in RB["cases"] if not r.get("infeasible")], key=lambda r: r["coverage_oct2026"])
    sel = [r for r in rows if r["group"] == "stress"]
    y = np.arange(len(sel))
    ax.barh(y, [r["coverage_oct2026"] for r in sel], 0.66, color=[C["orange"] if r["coverage_oct2026"] < RB["central_coverage"] else C["blue"] for r in sel])
    ax.axvline(1.0, color=INK, lw=0.9); ax.axvline(RB["central_coverage"], color=INK2, lw=0.8, ls=":")
    for i, r in enumerate(sel):
        ax.text(r["coverage_oct2026"] + 0.005, i, f"{r['coverage_oct2026']:.2f}", va="center", fontsize=5.2, color=INK2)
    short = lambda t: t.replace(" (7%, no kelp, residues halved, adders ×2, wind +25%, high vehicle premia)", "").replace(" (transition case)", " (transition)")
    ax.set_yticks(y); ax.set_yticklabels([short(r["case"]) for r in sel], fontsize=4.9)
    ax.set_xlim(0.25, 1.16); ax.set_xlabel("Share of oil-and-gas benchmark (Oct 2026)"); hgrid(ax)
    ax.set_title("(D) Stress tests")
    record("Fig6", "d_stress", ["case", "surplus replaced", "cost bn", "price multiplier vs Oct 2026"],
           [(r["case"], r["coverage_oct2026"], r["cost_bn"], r["mult_oil_oct2026"]) for r in sel])
    save(fig, "Fig6_robustness"); dump_source("Fig6")


# ------------------------------------------------------------------ Fig. 6 exports
def fig6():
    fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 68 * MM), gridspec_kw={"width_ratios": [1.1, 1.0]})
    ax = axs[0]
    sc_ = EX["supply_curve"]
    xs = [r["volume_twh"] for r in sc_]; ys = [r["marginal_cad_mwh"] for r in sc_]
    ax.step(xs, ys, where="post", color=C["green"], lw=1.5)
    ax.plot(xs, ys, "o", color=C["green"], ms=2.5)
    ref = EX["reference_prices_cad_mwh"]
    refl = [("fossil_jet_2025", "Fossil jet, 2025", MUTED, "--"), ("fossil_jet_oct2026", "Fossil jet, Oct 2026", INK, "-"),
            ("saf_europe_jul2026", "European SAF, Jul 2026", C["blue"], "-"), ("saf_europe_mar2026_peak", "European SAF peak, Mar 2026", C["blue"], ":")]
    for k, l, cc, ls in refl:
        ax.axhline(ref[k], color=cc, lw=0.9, ls=ls)
        ax.text(330 if "SAF" in l else 8, ref[k] + (-22 if "SAF" in l else 7), f"{l} ({ref[k]:.0f})", fontsize=5.4, color=cc, ha="left")
    ext = [r for r in XC["beyond_500"] if not r.get("infeasible")]
    ax.plot([xs[-1]] + [r["volume_twh"] for r in ext], [ys[-1]] + [r["marginal_cad_mwh"] for r in ext], ":", color=C["green"], lw=1.2)
    ax.plot([r["volume_twh"] for r in ext], [r["marginal_cad_mwh"] for r in ext], "o", mfc="white", mec=C["green"], ms=3)
    cl = XC["central"]["ceiling_twh"]
    ax.axvline(cl, color=C["red"], lw=1.0)
    ax.text(cl - 8, 120, f"Resource ceiling\n{cl:.0f} TWh yr⁻¹\n({XC['central']['share_of_oil_exports'] * 100:.0f}% of 2025\ncrude and product\nexports, {XC['oil_export_energy_twh']:,.0f} TWh)",
            fontsize=5.2, color=C["red"], ha="right")
    ax.set_xlim(0, 800); ax.set_ylim(0, 620)
    ax.set_xlabel("Drop-in fuel exported (TWh yr⁻¹)"); ax.set_ylabel("Marginal cost at port (CAD per MWh)"); vgrid(ax)
    ax.set_title("(A) Export supply curve (least-cost case)")
    record("Fig7", "a_supply_curve", ["export TWh", "marginal CAD/MWh", "added cost bn", "kelp km2", "e-FT TWh"],
           [(r["volume_twh"], r["marginal_cad_mwh"], r["added_cost_bn"], r["kelp_km2"], r["efuels_twh"]) for r in sc_]
           + [(r["volume_twh"], r["marginal_cad_mwh"], "", r["kelp_km2"], "") for r in ext],
           "Reference prices: " + "; ".join(f"{l} {ref[k]:.0f}" for k, l, _, _ in refl) + f" CAD/MWh. Forced exports above {cl:.0f} TWh/yr are infeasible "
           "under the encoded wind, PV, hydro, kelp-area and residue bounds.")
    ax = axs[1]
    ap = EX["at_price"]
    P = [r["price_cad_mwh"] for r in ap]
    ax.bar(np.arange(len(P)) - 0.2, [r["volume_twh"] for r in ap], 0.38, color=C["green"], label="Exports (TWh yr⁻¹)")
    ax2 = ax.twinx()
    ax2.bar(np.arange(len(P)) + 0.2, [r["added_ebit_bn"] for r in ap], 0.38, color=C["orange"], label="Added operating surplus (CAD bn yr⁻¹)")
    ax.set_xticks(range(len(P))); ax.set_xticklabels([f"{p}\n{r['price_usd_t'] / 1000:.1f}k" for p, r in zip(P, ap)], fontsize=5.4)
    ax.set_xlabel("Export price: CAD per MWh (top), US$ thousand per tonne (bottom)"); ax.set_ylabel("Exports (TWh yr⁻¹)", color=C["green"])
    ax2.set_ylabel("Added operating surplus (CAD bn yr⁻¹)", color=C["orange"]); ax2.spines["right"].set_visible(True)
    ax.set_ylim(0, 560); ax2.set_ylim(0, 160)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=5.4, loc="upper left")
    ax.set_title("(B) Profit-maximizing exports by price")
    record("Fig7", "b_exports_by_price", ["price CAD/MWh", "price USD/t", "exports TWh", "added operating surplus bn", "surplus replaced"],
           [(r["price_cad_mwh"], r["price_usd_t"], r["volume_twh"], r["added_ebit_bn"], r["coverage"]) for r in ap],
           f"Exports capped at 500 TWh/yr (Canada exported {EX['oil_export_energy_twh']:,.0f} TWh of crude oil and products in 2025).")
    fig.tight_layout(w_pad=2.0)
    save(fig, "Fig7_exports"); dump_source("Fig7")


# ------------------------------------------------------------------ Fig. 7 eutrophic lakes
def fig7():
    import lakes as lk
    fig = plt.figure(figsize=(180 * MM, 150 * MM))
    top = fig.add_gridspec(1, 2, left=0.02, right=0.98, top=0.95, bottom=0.56, wspace=0.04, width_ratios=[1.25, 1.5])
    bot = fig.add_gridspec(1, 3, left=0.07, right=0.97, top=0.45, bottom=0.10, wspace=0.62, width_ratios=[1.0, 1.15, 0.95])
    for g, f, t in ((top[0, 0], "lake_st_clair_landsat8_20150728.jpg", "(A) Lake St. Clair, 28 July 2015 (Ontario shore on the right)"),
                    (top[0, 1], "lake_erie_western_basin_landsat8.jpg", "(B) Bloom in western Lake Erie around Pelee Island")):
        ax = fig.add_subplot(g); ax.imshow(mpimg.imread(HERE / "illustrations" / f)); ax.axis("off"); ax.set_title(t, fontsize=6.6)
    fig.text(0.98, 0.535, "Landsat 8 OLI natural colour; NASA Earth Observatory", ha="right", fontsize=5.2, color=INK2)
    L = lk.LAKES
    ax = fig.add_subplot(bot[0, 0])
    items = [("Lake Winnipeg", L["winnipeg"]), ("Lake Erie", L["erie"])]
    x = np.arange(len(items)); w = 0.25
    mean_whole = {"Lake Winnipeg": L["winnipeg"].bloom_mean_km2, "Lake Erie": 427.0}
    vals = [("Seasonal mean", [mean_whole[n] for n, _ in items], C["aqua"]),
            ("Mean annual maximum", [l_.bloom_max_km2 for _, l_ in items], C["green"]),
            ("Record (2011)", [l_.bloom_record_km2 for _, l_ in items], C["orange"])]
    rows = []
    for j, (lab, v, cc) in enumerate(vals):
        ax.bar(x + (j - 1) * w, np.array(v) / 1000, w, color=cc, label=lab)
        for i, vv in enumerate(v):
            ax.text(x[i] + (j - 1) * w, vv / 1000 + 0.3, f"{vv / 1000:.1f}", ha="center", fontsize=5.0, color=INK2)
            rows.append((items[i][0], lab, vv))
    ax.axhline(lk.PEI_KM2 / 1000, color=C["red"], lw=0.9, ls="--")
    ax.text(0.5, lk.PEI_KM2 / 1000 + 0.7, "PEI\n5.7", fontsize=5.0, color=C["red"], ha="center")
    ax.set_xticks(x); ax.set_xticklabels([n for n, _ in items], fontsize=6); ax.set_ylabel("Bloom extent (thousand km²)"); vgrid(ax)
    ax.set_ylim(0, 31); ax.legend(fontsize=5.0, loc="upper right")
    ax.set_title("(C) Bloom extent, 2002–2022")
    record("Fig8", "c_bloom_extent", ["lake", "measure", "km2"], rows, "Whole-lake extents (chlorophyll >10 ug/L), ECCC EOLakeWatch annual bloom reports; PEI 5,660 km2.")
    ax = fig.add_subplot(bot[0, 1])
    bio = ["grid", "algae", "milfoil", "cattail"]
    pb = LKJ["central"]["p_by_lake_biomass"]
    tot_by = {}
    for kb, v in pb.items():
        tot_by[kb.split("|")[0]] = tot_by.get(kb.split("|")[0], 0.0) + v
    keys = [k for k, v in sorted(tot_by.items(), key=lambda kv: -kv[1]) if v > 1]
    lab = {k: L[k].name.replace(" (Canadian waters)", " (Cdn)").replace(" (Bay of Quinte, Hamilton Harbour)", " embayments") for k in keys}
    bcol = {"grid": C["violet"], "algae": C["green"], "milfoil": C["blue"], "cattail": C["orange"]}
    blab = {"grid": "Native filamentous algae on grids", "algae": "Cyanobacterial blooms (skimmed)",
            "milfoil": "Eurasian watermilfoil (invasive, cut)", "cattail": "Cattail, coastal marshes (native)"}
    y = np.arange(len(keys)); rows = []
    for i_, k in enumerate(keys):
        left = 0.0
        for b in bio:
            v = pb.get(f"{k}|{b}", 0.0)
            if v > 0:
                ax.barh(i_, v, 0.6, left=left, color=bcol[b]); left += v
            rows.append((lab[k], b, v))
        ax.text(left + 40, i_, f"{left:,.0f} t", va="center", fontsize=5.2, color=INK2)
    xmax = max(tot_by.values()) * 1.45
    ax.set_yticks(y); ax.set_yticklabels([lab[k] for k in keys], fontsize=5.4); ax.invert_yaxis()
    ax.set_xlim(0, xmax); ax.set_xlabel("Phosphorus removed (t P/a)"); hgrid(ax)
    ax.legend(handles=[Patch(fc=bcol[b], label=blab[b]) for b in bio], fontsize=4.6, loc="lower right")
    rng = LKJ["ranges"]; tot = LKJ["central"]["p_removed_t"]
    ax.text(xmax * 0.98, len(keys) * 0.42, f"Total {tot:,.0f} t P/a\n{LKJ['central']['dry_kt']:.0f} kt dry\n{LKJ['central']['fuel_twh']:.1f} TWh fuel\n"
            f"{LKJ['central']['harvesters']:.0f} Grid Harvesters", ha="right", va="center", fontsize=5.0, color=INK2)
    ax.set_title("(D) Phosphorus removed by harvest")
    record("Fig8", "d_p_removed", ["water body", "biomass", "t P/yr"], rows,
           f"Least-cost case; total {tot:.0f} t P/yr. Harvestable P across low and high parameter sets: {rng['low']['p_t']:.0f}-{rng['high']['p_t']:.0f} t P/yr.")
    ax = fig.add_subplot(bot[0, 2])
    rs = LKJ["response"]["winnipeg"]
    hs = np.linspace(0, 0.6, 61)
    tp = L["winnipeg"].tp_mgl * (1 - hs)
    chl = (1 - hs) ** lk.DILLON_RIGLER_SLOPE
    ax.plot(hs * 100, tp * 1000, color=C["green"], lw=1.4, label="South-basin TP (µg L⁻¹)")
    ax.plot(hs * 100, chl * 100, color=C["blue"], lw=1.2, ls="--", label="Chlorophyll (% of now)")
    ax.axhline(L["winnipeg"].tp_target_mgl * 1000, color=C["red"], lw=0.8, ls=":")
    ax.text(59, L["winnipeg"].tp_target_mgl * 1000 + 3, "TP target 50", fontsize=5.2, color=C["red"], ha="right")
    ax.axvline(rs["share_of_load"] * 100, color=INK2, lw=0.8)
    ax.text(rs["share_of_load"] * 100 - 1, 8, f"Harvest\n{rs['p_removed_t']:,.0f} t\n({rs['share_of_load'] * 100:.0f}% of load)", fontsize=5.2, color=INK2, ha="right")
    ax.set_xlabel("P removed (% of annual load)"); ax.set_ylim(0, 130); vgrid(ax)
    ax.legend(fontsize=5.0, loc="upper right")
    ax.set_title("(E) Lake Winnipeg")
    record("Fig8", "e_winnipeg_response", ["P removed share of load", "south-basin TP ug/L", "chlorophyll % of now"],
           [(float(h_), float(t_ * 1000), float(c_ * 100)) for h_, t_, c_ in zip(hs[::5], tp[::5], chl[::5])],
           "Steady-state mass balance (TP falls in proportion to the load removed); chlorophyll from Dillon and Rigler (1974), slope 1.449; "
           "response time about 2 years; legacy sediment P slows it.")
    save(fig, "Fig8_lakes"); dump_source("Fig8")


# ------------------------------------------------------------------ Fig. 8 self-reliance and national emissions
def fig8():
    fig = plt.figure(figsize=(180 * MM, 86 * MM))
    gs = fig.add_gridspec(1, 3, width_ratios=[1.25, 1.0, 0.45], wspace=0.45, left=0.07, right=0.99, top=0.88, bottom=0.2)
    ax = fig.add_subplot(gs[0, 0])
    cases = [r for r in SRJ["cases"] if not r.get("infeasible") and "no lake" not in r["case"]]
    short = {"All routes (central case)": "All routes\n(least-\ncost)", "No electrofuels": "No\nelectro-\nfuels",
             "Electric or biofuel only": "Electric\nor biofuel\nonly",
             "Electrification, seaweed and existing biofuels only": "Electricity,\nseaweed,\nexisting\nbiofuels",
             "Electrification, seaweed and existing biofuels, transition demand": "Same,\ntransition\ndemand"}
    parts = [("kelp_hc_twh", "Kelp HTL fuel", C["green"]), ("lake_fuel_twh", "Lake and marsh fuel", C["aqua"]),
             ("existing_biofuels_twh", "Existing biofuel feedstocks", C["yellow"]), ("residues_twh", "Forest and farm residues", C["orange"]),
             ("efuels_twh", "Electrofuels", C["violet"])]
    rows = []
    for i, r in enumerate(cases):
        b = 0.0
        for k, l, cc in parts:
            ax.bar(i, r[k], 0.6, bottom=b, color=cc, ec="white", lw=0.4); b += r[k]
            rows.append((r["case"], l, r[k]))
        ax.text(i, b + 6, f"{r['kelp_km2'] / 1000:.0f}k km²", ha="center", fontsize=5.0, color=INK2)
    ax.set_xticks(range(len(cases))); ax.set_xticklabels([short.get(r["case"], r["case"]) for r in cases], fontsize=5.0)
    top = max(sum(r[k] for k, _, _ in parts) for r in cases)
    ax.set_ylabel("Liquid and gaseous fuel supplied (TWh/a)"); vgrid(ax); ax.set_ylim(0, top * 1.45)
    ax.legend(handles=[Patch(fc=cc, label=l) for _, l, cc in parts], fontsize=4.9, loc="upper center", ncol=3)
    ax.set_title("(A) Fuel supply by supply set (kelp area on top)")
    record("Fig9", "a_self_reliance", ["case", "source", "TWh/yr"], rows,
           f"Labels: kelp farm area and share of the oil-and-gas surplus replaced (rent collected). Kelp area permitted by the farm caps: "
           f"{SRJ['kelp_area_available_km2']:.0f} km2. The strict case is feasible only if kelp yields reach {SRJ['strict_min_yield_factor'] * 100:.0f}% of the "
           f"learned yields, and in {SRJ['mc_strict_feasible']} of {SRJ['mc_n']} Monte Carlo draws.")
    ax = fig.add_subplot(gs[0, 1])
    rr = NEJ["rows"]
    labels = ["2024\ninventory", "Renewable\ntransport,\noil exported", "Domestic\nrefining\ncloses", "Oil sands\nCCS"]
    vals = [r["mt"] for r in rr]
    og = NEJ["nir"]["2024"]["Oil and gas"]
    for i, v in enumerate(vals):
        ax.bar(i, v, 0.6, color=MUTED if i == 0 else C["blue"])
        ax.bar(i, og - (NEJ["nir"]["2024"]["Oil and gas"] * 0 + (16.0 * 0.7 if i >= 2 else 0) + (22.0 if i >= 3 else 0)), 0.6, color=C["red"], alpha=0.85)
        ax.text(i, v + 12, f"{v:.0f}\n(−{NEJ['share_below_2005_pct'][rr[i]['case']]:.0f}%)", ha="center", fontsize=5.2, color=INK2)
    t30 = NEJ["targets_mt"]["2030"]; t35 = NEJ["targets_mt"]["2035"]
    ax.axhspan(t30[1], t30[0], color=C["green"], alpha=0.18); ax.axhspan(t35[1], t35[0], color=C["aqua"], alpha=0.12)
    ax.axhline(NEJ["total"]["2005"], color=INK, lw=0.7, ls=":"); ax.text(-0.3, NEJ["total"]["2005"] + 8, "2005: 763", fontsize=5.0)
    ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=5.2); ax.set_ylim(0, 960)
    ax.set_ylabel("Territorial emissions, NIR boundary (Mt CO₂e/a)"); vgrid(ax)
    ax.legend(handles=[Patch(fc=C["red"], alpha=0.85, label="Oil and gas sector"), Patch(fc=C["blue"], label="Other sectors"),
                       Patch(fc=C["green"], alpha=0.3, label="2030 target (−40 to −45%)"), Patch(fc=C["aqua"], alpha=0.2, label="2035 target (−45 to −50%)")],
              fontsize=4.8, loc="upper right", ncol=2)
    ax.set_title("(B) Territorial account (targets)")
    record("Fig9", "b_territorial", ["case", "Mt CO2e", "% below 2005"], [(r["case"], r["mt"], NEJ["share_below_2005_pct"][r["case"]]) for r in rr],
           f"NIR boundary: transport and off-road removed; adds {NEJ['territorial_addition_mt']:.1f} Mt released in Canada by the renewable "
           f"system (CH4 and N2O from biofuel combustion, biogas methane slip). Targets 2030: {t30[1]:.0f}-{t30[0]:.0f} Mt; 2035: "
           f"{t35[1]:.0f}-{t35[0]:.0f} Mt (excluding the LULUCF accounting contribution).")
    ax = fig.add_subplot(gs[0, 2])
    lc = NEJ["lifecycle"]
    ax.bar(0, lc["fossil_wtw_mt"], 0.6, color=MUTED); ax.bar(1, lc["renewable_wtw_mt"], 0.6, color=C["green"])
    lo, hi = lc["renewable_wtw_range_mt"]; ax.plot([1, 1], [lo, hi], color=INK, lw=0.8)
    ax.text(0, lc["fossil_wtw_mt"] + 6, f"{lc['fossil_wtw_mt']:.0f}", ha="center", fontsize=5.4)
    ax.text(1, hi + 6, f"{lc['renewable_wtw_mt']:.0f}\n(−{lc['reduction_pct']:.0f}%)", ha="center", fontsize=5.4)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Fossil", "Renew-\nable"], fontsize=5.4); ax.set_ylim(0, lc["fossil_wtw_mt"] * 1.25)
    ax.set_ylabel("Well-to-wheel, all locations (Mt CO₂e/a)", fontsize=5.6); vgrid(ax)
    ax.set_title("(C) Lifecycle\naccount", fontsize=6.4)
    record("Fig9", "c_lifecycle", ["system", "Mt CO2e/yr well-to-wheel"], [("fossil transport fuels", lc["fossil_wtw_mt"]),
                                                                           ("renewable system", lc["renewable_wtw_mt"])],
           f"Separate account, not added to the territorial inventory. Combustion abroad of exported oil: "
           f"{NEJ['exported_combustion_abroad_mt']:.0f} Mt CO2/yr (counted in importing countries).")
    save(fig, "Fig9_self_reliance_emissions"); dump_source("Fig9")


# ------------------------------------------------------------------ Supporting figures
def fig_s1():
    fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 62 * MM))
    for ax, f, t in zip(axs, ("grid_harvester_side.jpg", "grid_harvester_top.jpg"), ("(A) Side view", "(B) Top view and head path")):
        ax.imshow(mpimg.imread(HERE / "illustrations" / f)); ax.axis("off"); ax.set_title(t)
    fig.tight_layout()
    save(fig, "FigS1_grid_harvester")


def ed2():
    fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 64 * MM), gridspec_kw={"width_ratios": [1, 1.2]})
    ax = axs[0]
    lc = LOW["lifecycle"]
    ax.bar(0, lc["fossil_wtw_mtco2e"], 0.55, color=MUTED)
    parts = [("Direct electric transport", C["blue"]), ("Kelp fuels", C["green"]), ("Residue and lake fuels", C["orange"]),
             ("Crop and waste biofuels", C["yellow"]), ("Electrofuels", C["violet"])]
    b = 0; rows = [("Fossil comparator", "total", lc["fossil_wtw_mtco2e"])]
    for n, cc in parts:
        v = lc["parts_mtco2e"][n]
        ax.bar(1, v, 0.55, bottom=b, color=cc, ec="white", lw=0.5); b += v
        rows.append(("Renewable system", n, v))
    lo, hi = lc["lowcarbon_factor_sensitivity_mtco2e"]
    ax.plot([1, 1], [lo, hi], color=INK, lw=0.8)
    ax.text(0, lc["fossil_wtw_mtco2e"] + 4, f"{lc['fossil_wtw_mtco2e']:.0f}", ha="center", fontsize=6)
    ax.text(1, hi + 4, f"{lc['lowcarbon_wtw_mtco2e']:.1f}\n(−{lc['reduction_pct']:.1f}%)", ha="center", fontsize=6)
    ax.set_xticks([0, 1]); ax.set_xticklabels(["Fossil fuels", "Renewable system"]); ax.set_ylabel("MtCO₂e yr⁻¹ (well-to-wheel)")
    ax.legend(handles=[Patch(fc=cc, label=n) for n, cc in parts], fontsize=5.5, loc="upper right"); vgrid(ax)
    ax.set_ylim(0, lc["fossil_wtw_mtco2e"] * 1.15)
    ax.set_title("(A) Screening lifecycle emissions (transport)")
    record("FigS2", "a_lifecycle", ["system", "component", "MtCO2e/yr"], rows,
           f"Factor sensitivity of the renewable system {lo:.1f}-{hi:.1f} MtCO2e/yr; vehicle manufacture excluded; exported fuel excluded.")
    ax = axs[1]
    ex = R["exposure"]
    low = LOW["total_cost_bn"]
    items = [("Fossil fuels (pre-tax)", ex["fossil_2025_bn"], ex["fossil_oct2026_bn"]), ("Renewable system", low - ex["lowcarbon_swing_bn"], low)]
    x = np.arange(2)
    ax.bar(x - 0.18, [i[1] for i in items], 0.34, color=C["blue"], label="2025 average prices")
    ax.bar(x + 0.18, [i[2] for i in items], 0.34, color=C["orange"], label="October 2026 prices")
    for i, (n, a, b2) in enumerate(items):
        ax.text(i - 0.18, a + 2, f"{a:.1f}", ha="center", fontsize=6); ax.text(i + 0.18, b2 + 2, f"{b2:.1f}", ha="center", fontsize=6)
        ax.text(i, max(a, b2) + 14, f"+{b2 - a:.1f} bn ({(b2 / a - 1) * 100:+.0f}%)", ha="center", fontsize=6.2, color=INK)
    ax.set_xticks(x); ax.set_xticklabels([i[0] for i in items]); ax.set_ylabel("CAD bn yr⁻¹ (central-case demand)")
    ax.set_ylim(0, 175); ax.legend(fontsize=5.8, loc="upper right"); vgrid(ax)
    ax.set_title("(B) Exposure to the 2025–2026 oil-price shock")
    record("FigS2", "b_exposure", ["system", "2025 prices bn", "Oct 2026 prices bn"], [(n, a, b2) for n, a, b2 in items],
           "Renewable system: only commodity-priced inputs (waste lipids, canola oil, grain ethanol) repriced.")
    fig.tight_layout(w_pad=1.5)
    save(fig, "FigS2_lifecycle_exposure"); dump_source("FigS2")


def ed3():
    nok = [r for r in RB["cases"] if r["case"] == "No kelp"][0]
    s = LOW
    fig, axs = plt.subplots(1, 2, figsize=(180 * MM, 62 * MM))
    ax = axs[0]
    labels = ["New\nelectricity\n(×10 TWh yr⁻¹)", "Onshore\nwind (GW)", "Electro-\nlysers (GW)", "Direct air\ncapture\n(Mt CO₂ yr⁻¹)"]
    a = [s["electricity_delivered_twh"] / 10, s["capacity_gw"]["Onshore wind"], s["electrolyser_gw"], s["co2_mt"]["DAC"]]
    b = [nok["electricity_twh"] / 10, nok["wind_gw"], nok["electrolyser_gw"], nok["dac_mt"]]
    x = np.arange(len(a))
    ax.bar(x - 0.18, a, 0.34, color=C["green"], label="With native kelp")
    ax.bar(x + 0.18, b, 0.34, color=C["violet"], label="Without kelp")
    for i in range(len(a)):
        ax.text(i - 0.18, a[i] + 1.5, f"{a[i]:.1f}", ha="center", fontsize=5.6); ax.text(i + 0.18, b[i] + 1.5, f"{b[i]:.1f}", ha="center", fontsize=5.6)
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=5.6); ax.legend(fontsize=6); vgrid(ax)
    ax.set_title("(A) Infrastructure with and without kelp")
    record("FigS3", "a_with_without", ["item", "with kelp", "without kelp"], list(zip([l.replace("\n", " ") for l in labels], a, b)))
    ax = axs[1]
    mc = mc_rows()
    yv = np.array([float(r["yield_pacific_t_ha"]) for r in mc]); km = np.array([float(r["kelp_km2"]) for r in mc])
    al = np.array([r["kelp_allowed"] == "True" for r in mc])
    ax.scatter(yv[al], km[al] / 1000, s=4, color=C["green"], alpha=0.5, lw=0, label="Kelp allowed")
    ax.scatter(yv[~al], km[~al] / 1000, s=4, color=MUTED, alpha=0.6, lw=0, label="Kelp disabled (10% of draws)")
    ax.set_xlabel("Sampled Pacific kelp yield (t dry ha⁻¹ yr⁻¹)"); ax.set_ylabel("Kelp farm area chosen (thousand km²)")
    ax.legend(fontsize=5.6, markerscale=2); vgrid(ax)
    ax.set_title("(B) Monte Carlo: farm area against yield")
    record("FigS3", "b_mc_yield_area", ["Pacific yield t/ha/yr", "farm km2", "kelp allowed"], [(float(a_), float(b_), bool(c_)) for a_, b_, c_ in zip(yv, km, al)])
    fig.tight_layout()
    save(fig, "FigS3_kelp_value"); dump_source("FigS3")


def ed4():
    infe = [r["case"] for r in RB["cases"] if r.get("infeasible")]
    rows = sorted([r for r in RB["cases"] if not r.get("infeasible")], key=lambda r: r["delta_bn"])
    fig, ax = plt.subplots(figsize=(180 * MM, 150 * MM))
    y = np.arange(len(rows))
    cols = [C["blue"] if r["group"] == "option" else C["orange"] for r in rows]
    ax.barh(y, [r["delta_bn"] for r in rows], 0.62, color=cols)
    for i, r in enumerate(rows):
        d = r["delta_bn"]
        ax.text(max(d, 0) + 0.3, i, f"{d:+.1f}  ({r['kelp_km2']:,.0f} km², {r['electricity_twh']:.0f} TWh, surplus {r['coverage_oct2026']:.2f})",
                va="center", ha="left", fontsize=5.4, color=INK2)
    ax.set_yticks(y); ax.set_yticklabels([r["case"].replace(" (7%, no kelp, residues halved, adders ×2, wind +25%, high vehicle premia)", " (7%, no kelp,\nresidues ½, adders ×2, wind +25%, high premia)")
                        .replace("Windsor-Montréal corridor (Highways", "Windsor-Montréal corridor\n(Highways")
                        .replace("(no electrofuels; no methane,", "(no electrofuels;\nno methane,") for r in rows], fontsize=5.4)
    ax.axvline(0, color=MUTED, lw=0.7)
    ax.set_xlim(-30, 165); hgrid(ax)
    ax.set_xlabel(f"Change in annual cost relative to the least-cost case\n(CAD bn yr⁻¹; least-cost {RB['central_bn']:.1f})")
    if infe:
        ax.text(163, 7, "Infeasible (no solution):\n" + "\n".join(infe), ha="right", va="center", fontsize=5.6, color=C["red"])
    ax.legend(handles=[Patch(fc=C["blue"], label="Design option forced"), Patch(fc=C["orange"], label="Stress test")], fontsize=6, loc="lower right")
    ax.set_title("Design options and stress tests")

    record("FigS4", "options", ["group", "case", "delta bn", "cost bn", "kelp km2", "electricity TWh", "surplus replaced", "lifecycle reduction %"],
           [(r["group"], r["case"], r["delta_bn"], r["cost_bn"], r["kelp_km2"], r["electricity_twh"], r["coverage_oct2026"], r["lifecycle_reduction_pct"]) for r in rows]
           + [("stress", c_, "infeasible", "", "", "", "", "") for c_ in infe])
    fig.subplots_adjust(left=0.37, right=0.985, top=0.95, bottom=0.13)
    fig.text(0.99, 0.01, "Labels: change in cost, kelp farm area, new electricity, share of the oil-and-gas surplus benchmark that could be captured (October 2026 prices)",
             ha="right", fontsize=5.6, color=INK2)
    save(fig, "FigS4_options"); dump_source("FigS4")


if __name__ == "__main__":
    # Marine maps (Figure 1, Figure S5) need the Natural Earth layers built by spatial.py; every other figure and its
    # Source Data are regenerated from the committed model outputs.
    have_layers = (OUT / "_layers.pkl").exists()
    for f in (fig1, fig2, fig3, fig4, fig5, fig6, fig7, fig8, fig_s1, ed2, ed3, ed4, figS5):
        if f in (fig1, figS5) and not have_layers:
            print("skipped", f.__name__, "(Natural Earth layers not found; committed map and Source Data retained)")
            continue
        f(); print("done", f.__name__)
