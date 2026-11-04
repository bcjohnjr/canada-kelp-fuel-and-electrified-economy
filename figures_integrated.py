"""Main Figures 1-7 of the integrated article (Nature Energy format) from the model outputs."""
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
FIG = HERE / "article_figures"; FIG.mkdir(exist_ok=True)
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
GREY, INK, INK2 = "#9a9a9a", "#0b0b0b", "#52514e"
plt.rcParams.update({"font.size": 7.5, "font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.edgecolor": "#888", "axes.labelcolor": INK, "xtick.color": INK2, "ytick.color": INK2,
                     "axes.titlesize": 8, "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
                     "savefig.facecolor": "white"})
R = json.load(open(OUT / "central_smr.json"))
N = json.load(open(OUT / "central_no_smr.json"))
SC = json.load(open(OUT / "smr_scenarios.json"))
SM = json.load(open(OUT / "smr_canada_summary.json"))
CP = json.load(open(OUT / "coproduction.json"))
SENS = defaultdict(dict)
for r in csv.DictReader(open(OUT / "smr_site_sensitivity.csv")):
    SENS[r["case"]][r["site"]] = float(r["npv_cad_bn"])
ROWS = {r["case"]: r for r in SC["rows"]}


def save(fig, name):
    fig.savefig(FIG / f"{name}.png", dpi=300, bbox_inches="tight"); fig.savefig(FIG / f"{name}.pdf", bbox_inches="tight"); plt.close(fig)


def letter(ax, s):
    ax.text(-0.2, 1.06, s, transform=ax.transAxes, fontsize=9, fontweight="bold", va="bottom")


# ---------------------------------------------------------------- Figure 1: map
SITES = {"ON_CHATHAM": ("ON Chatham-Kent", 42.40, -82.19), "SK_BELLE_PLAINE": ("SK Belle Plaine", 50.43, -105.15),
         "AB_HEARTLAND": ("AB Heartland", 53.71, -113.21), "NB_SAINT_JOHN": ("NB Saint John", 45.07, -66.45),
         "NS_POINT_TUPPER": ("NS Point Tupper", 45.61, -61.35), "BC_KAMLOOPS": ("BC Kamloops (test)", 50.67, -120.33),
         "MB_CHURCHILL": ("MB Churchill (Hudson Bay test)", 58.77, -94.17)}
TCH = [(48.43, -123.37), (49.17, -123.94), (49.25, -123.1), (49.38, -121.44), (50.67, -120.33), (51.0, -118.2), (51.3, -116.97),
       (51.18, -115.57), (51.05, -114.07), (50.04, -110.68), (50.29, -107.79), (50.39, -105.53), (50.45, -104.6), (49.85, -99.95),
       (49.9, -97.14), (49.77, -94.49), (48.38, -89.25), (49.01, -88.27), (47.99, -84.77), (46.52, -84.35), (46.49, -80.99),
       (46.31, -79.46), (45.42, -75.7), (45.5, -73.57), (46.81, -71.21), (47.83, -69.53), (47.37, -68.33), (45.96, -66.64),
       (46.09, -64.78), (45.36, -63.28), (45.62, -61.35), (46.14, -60.19)]
NL = [(47.57, -59.13), (48.95, -57.95), (48.95, -54.61), (47.56, -52.71)]
KELP_XY = {"pac": (52.3, -131.0), "atl": (44.2, -62.0), "hb": (58.2, -91.5)}


def fig1():
    from mpl_toolkits.basemap import Basemap
    fig, ax = plt.subplots(figsize=(7.2, 4.3))
    m = Basemap(projection="lcc", lat_0=54, lon_0=-95, lat_1=49, lat_2=60, width=7.4e6, height=3.9e6, resolution="l", ax=ax)
    m.fillcontinents(color="#f2f2ee", lake_color="#dfeaf2"); m.drawmapboundary(fill_color="#dfeaf2")
    m.drawcountries(color="#888", linewidth=0.6); m.drawstates(color="#c8c8c8", linewidth=0.35); m.drawcoastlines(color="#888", linewidth=0.35)
    for pts in (TCH, NL):
        x, y = m([p[1] for p in pts], [p[0] for p in pts]); ax.plot(x, y, color=C[0], lw=1.8, zorder=3)
    kp = CP["kelp_km2"]
    for reg, area, lab in (("pac", kp["pac"], "Pacific kelp\n%s km²\nwind/solar heat" % f"{kp['pac']:,.0f}"),
                           ("atl", kp["atl"], "Atlantic kelp\n%s km²\nSMR steam eligible" % f"{kp['atl']:,.0f}")):
        la, lo = KELP_XY[reg]; x, y = m(lo, la)
        ax.scatter(x, y, s=area / 18, color=C[2], alpha=0.55, edgecolor=C[2], lw=1.2, zorder=4)
        ax.text(x + (-9.5e5 if reg == "pac" else 2.4e5), y + (-1.0e5 if reg == "pac" else -4.2e5), lab, fontsize=6.6, color=INK)
    la, lo = KELP_XY["hb"]; x, y = m(lo, la)
    ax.scatter(x, y, s=2000 / 18, facecolor="none", edgecolor=C[2], lw=1.2, ls="--", zorder=4)
    ax.text(x + 1.6e5, y - 0.6e5, "Hudson Bay test\n2,000 km² forced:\n+CAD 0.71 bn yr⁻¹", fontsize=6.4)
    x, y = m(-97.0, 52.3)
    ax.scatter(x, y, s=40, marker="D", color=C[6], edgecolor="w", lw=0.6, zorder=6)
    ax.text(x + 0.9e5, y + 0.2e5, "Lake Winnipeg\nGrid Harvesters", fontsize=6.4)
    off = {"ON_CHATHAM": (1.0e5, -2.6e5), "SK_BELLE_PLAINE": (-2.0e5, -3.3e5), "AB_HEARTLAND": (1.0e5, 0.6e5),
           "NB_SAINT_JOHN": (-9.5e5, -2.4e5), "NS_POINT_TUPPER": (-3.5e5, 2.6e5), "BC_KAMLOOPS": (-2.5e5, -3.2e5), "MB_CHURCHILL": (-12.0e5, 0.9e5)}
    for sid, (lab, la, lo) in SITES.items():
        x, y = m(lo, la)
        c = SENS["central"][sid]; d = SENS["grid_fossil_free_2045"][sid]
        test = sid in ("BC_KAMLOOPS", "MB_CHURCHILL")
        col = C[7] if test else (C[5] if d >= 0 else C[3] if c >= 0 else C[1])
        ax.scatter(x, y, s=46, marker="s" if test else "o", color=col, edgecolor="k", lw=0.5, zorder=7)
        ax.text(x + off[sid][0], y + off[sid][1], f"{lab}\nNPV {c:+.1f} / {d:+.1f}", fontsize=6.2)
    h = [Line2D([], [], color=C[0], lw=1.8, label="Trans-Canada Highway (catenary, 7,821 km)"),
         *([Line2D([], [], marker="o", ls="", color=C[5], mec="k", label="SMR pair, NPV ≥ 0 even if grid fossil-free by 2045")]
           if any(SENS["grid_fossil_free_2045"][k] >= 0 for k in SITES if k not in ("BC_KAMLOOPS", "MB_CHURCHILL")) else []),
         Line2D([], [], marker="o", ls="", color=C[3], mec="k", label="SMR pair, NPV ≥ 0 only while gas is displaced"),
         Line2D([], [], marker="o", ls="", color=C[1], mec="k", label="SMR pair, NPV < 0 (staged later)"),
         Line2D([], [], marker="s", ls="", color=C[7], mec="k", label="Test site, NPV < 0"),
         Line2D([], [], marker="o", ls="", color=C[2], alpha=0.55, label="Kelp farms (area ∝ marker)")]
    ax.legend(handles=h, loc="lower left", fontsize=6.2, frameon=True, framealpha=0.9, edgecolor="#ccc")
    ax.set_title("NPV: CAD bn per two-module site, current law (ITC to 2034) / grid fossil-free from 2045", fontsize=7, fontweight="normal", color=INK2)
    save(fig, "Figure_1_system_map")


# ---------------------------------------------------------------- Figure 2: complete replacement
def fig2():
    eu = R["end_use_twh"]
    segs = [("ldv_gasoline", "Light-duty\ngasoline"), ("ldv_diesel", "Light-duty\ndiesel"), ("hdv", "Heavy trucks\nand buses"),
            ("rail", "Rail"), ("offroad", "Farm, mine,\nconstruction"), ("aviation", "Aviation\n(incl. intl.)"), ("shipping", "Shipping")]
    car = [("Battery and catenary electric", ("bev", "bet", "ers", "el", "farm_el", "mine_el", "con_el"), C[0]),
           ("Drop-in diesel", ("liq", "farm_liq", "mine_liq", "con_liq"), C[1]), ("Ethanol (ED95, E85)", ("ed95", "e85", "ffv"), C[3]),
           ("Jet fuel", ("jet",), C[6]), ("Methanol", ("meoh",), C[2])]
    fig, axs = plt.subplots(1, 3, figsize=(7.4, 2.9), gridspec_kw=dict(width_ratios=[1.45, 1.1, 0.9]))
    ax = axs[0]; letter(ax, "a")
    y = np.arange(len(segs))
    left = np.zeros(len(segs))
    for name, keys, col in car:
        v = np.array([sum(val for k, val in eu.items() if k.split("|")[0] == sg and k.split("|")[1] in keys) for sg, _ in segs])
        ax.barh(y, v, left=left, color=col, edgecolor="white", lw=0.8, label=name, height=0.68)
        left += v
    for i, (sg, _) in enumerate(segs):
        ax.text(left[i] + 6, i, f"{R['demand_twh'][sg]:.0f}", va="center", fontsize=6.5, color=INK2)
    ax.set_yticks(y, [s[1] for s in segs], fontsize=6.6); ax.invert_yaxis()
    ax.set_xlabel(f"Fossil energy replaced, TWh yr⁻¹ (total {R['demand_total_twh']:.0f})")
    ax.set_title("Every transport segment replaced")
    ax.legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.45, -0.2), ncol=2)
    ax = axs[1]; letter(ax, "b")
    f = R["fuels_twh"]
    src = [("Kelp HTL diesel/jet", f["kelp HTL diesel/jet"] + f["kelp biomethane (net of fleet)"], C[2]),
           ("Forest and farm residues", f["forest_residue_HTL"] + f["agri_residue_FT"], C[5]),
           ("Electrofuels (wind)", f["eFT_liquids"] + f["e_methanol"], C[0]),
           ("Lipids, canola, biomethane", f["HEFA_waste_lipids"] + f["canola_HVO"] + f["waste_biomethane"], C[4]),
           ("Grain ethanol", f["grain_ethanol_existing"], C[3]),
           ("Lake biomass", f["lake HTL diesel/jet"] + f["lake biomethane (net of fleet)"], C[6])]
    bottom = 0; last = -1e9
    for name, v, col in src:
        ax.bar(0, v, bottom=bottom, color=col, edgecolor="white", lw=0.8, width=0.55)
        yl = max(bottom + v / 2, last + 15); last = yl
        ax.text(0.34, yl, f"{name} {v:.0f}", va="center", fontsize=6.2)
        bottom += v
    ax.set_xlim(-0.4, 1.9); ax.set_xticks([]); ax.set_ylabel("Liquid and gaseous fuels, TWh yr⁻¹")
    ax.set_title("Renewable fuels")
    ax.spines["bottom"].set_visible(False)
    ax = axs[2]; letter(ax, "c")
    g = R["generation_twh"]
    gen = [(n, v, c) for n, v, c in (("Onshore wind", g["Onshore wind"], C[0]), ("Solar PV", g["PV"], C[3]),
                                     ("SMR (net)", g["SMR (net of steam extraction)"], C[7])) if v > 0.05]
    bottom = 0
    for name, v, col in gen:
        ax.bar(0, v, bottom=bottom, color=col, edgecolor="white", lw=0.8, width=0.55)
        ax.text(0.34, bottom + v / 2, f"{name} {v:.0f}", va="center", fontsize=6.2)
        bottom += v
    use = [("Vehicles and rail", R["electricity_vehicles_rail_twh"]), ("Electrolysers", R["electricity_for_efuels_twh"]),
           ("Refineries and heat", R["electricity_refineries_twh"] + R["electricity_for_heat_storage_twh"])]
    ax.text(0.0, -0.08, "Used by: " + "\n".join(f"{a} {b:.0f}" for a, b in use), transform=ax.transAxes, va="top", fontsize=6, color=INK2)
    ax.set_xlim(-0.4, 1.9); ax.set_xticks([]); ax.set_ylabel("New electricity, TWh yr⁻¹")
    ax.set_title("Electricity"); ax.spines["bottom"].set_visible(False)
    fig.tight_layout(w_pad=2.5)
    save(fig, "Figure_2_complete_replacement")


# ---------------------------------------------------------------- Figure 3: heat cascade by pool
POOL_LAB = {"pac": "Pacific", "atl": "Atlantic", "inl": "Inland", "hb": "Hudson Bay"}
SRCS = [("smr_steam", "SMR extraction steam", C[7]), ("heat_pump", "Heat pumps", C[0]),
        ("wind_thermal_storage", "Wind-charged thermal storage", C[2]), ("electric_boiler", "Electric boilers", C[3]),
        ("residue_boiler", "Residue boilers", C[5])]


def fig3():
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.9), gridspec_kw=dict(width_ratios=[1.35, 1]))
    ax = axs[0]; letter(ax, "a")
    ITC = ROWS["ITC extended beyond 2034 (15%)"]; BC = ROWS["BC fleet allowed (SMR steam for Pacific refineries), ITC extended"]
    cases = [("Current law", N["heat_by_pool_twh_th"], N["total_cost_bn"]), ("ITC extended", ITC["heat"], ITC["total_cost_bn"]),
             ("ITC + BC fleet", BC["heat"], BC["total_cost_bn"])]
    pools = ["pac", "atl", "inl"]
    x = []; labels = []; vals = []; xpos = 0; centres = []
    for name, h, cost in cases:
        start = xpos
        for pl in pools:
            x.append(xpos); labels.append(POOL_LAB[pl]); vals.append(h[pl]); xpos += 1
        centres.append(((start + xpos - 1) / 2, name, cost)); xpos += 0.6
    bottom = np.zeros(len(x))
    for k, name, col in SRCS:
        v = np.array([h.get(k, 0.0) for h in vals])
        ax.bar(x, v, bottom=bottom, color=col, edgecolor="white", lw=0.8, width=0.8, label=name)
        bottom += v
    ax.set_xticks(x, labels, fontsize=5.8, rotation=90)
    top = bottom.max()
    for cx, name, cost in centres:
        ax.text(cx, top * 1.10, name, ha="center", fontsize=6.4, fontweight="bold")
        ax.text(cx, top * 1.02, f"CAD {cost:.2f} bn yr⁻¹", ha="center", fontsize=5.8, color=INK2)
    ax.set_ylim(0, top * 1.2)
    ax.set_ylabel("Refinery heat, TWh$_{th}$ yr⁻¹")
    ax.set_title("Heat by regional pool")
    ax.legend(fontsize=5.8, loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3)
    ax = axs[1]; letter(ax, "b")
    sites = ["ON_CHATHAM", "SK_BELLE_PLAINE", "AB_HEARTLAND", "NB_SAINT_JOHN", "NS_POINT_TUPPER"]
    lab = ["ON", "SK", "AB", "NB", "NS"]
    S = SM["sites_2041"]
    e = np.array([S[s]["electricity_twh"] for s in sites])
    hi = np.array([S[s]["heat_by_grade_twh"].get("high_150C", 0) for s in sites])
    me = np.array([S[s]["heat_by_grade_twh"].get("medium_80C", 0) for s in sites])
    xx = np.arange(len(sites))
    ax.bar(xx, e, color=C[0], width=0.62, edgecolor="white", label="Electricity to grid and catenary")
    ax.bar(xx, hi, bottom=e, color=C[7], width=0.62, edgecolor="white", label="150 °C steam: E85/ED95 distillation, kelp refinery, industry")
    ax.bar(xx, me, bottom=e + hi, color=C[3], width=0.62, edgecolor="white", label="80 °C heat: greenhouses, grain and kelp drying")
    ax.set_xticks(xx, lab); ax.set_ylabel("Site output in 2041, TWh yr⁻¹")
    ax.set_title("Heat cascade at each Highway 1 site")
    ax.legend(fontsize=5.6, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=1)
    fig.tight_layout(w_pad=1.5)
    save(fig, "Figure_3_heat_cascade")


def fig4():
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0))
    ax = axs[0]; letter(ax, "a")
    integ = SC["integer"]; b0 = ROWS["No SMR (wind, solar and hydro only)"]["total_cost_bn"]
    for itc, col, name in ((0.0, C[7], "Current law (no ITC)"), (0.15, C[0], "ITC extended (15%)")):
        sw = [w for w in SC["sweep"] if w["itc"] == itc]
        ax.plot([w["capex_bn"] for w in sw], [w["saving_vs_nosmr"] * 1000 for w in sw], color=col, lw=1.8, marker="o", ms=3.5,
                label=f"{name}, continuous, excl. site infrastructure")
    pts = [("current_law", 4.4, C[7]), ("itc_extended", 4.4, C[0]), ("capex_3p5", 3.5, C[7]), ("capex_3p5_itc", 3.5, C[0])]
    for k, cap, col in pts:
        v = integ[k]; sv = v["saving_best_bn"] * 1000
        ax.scatter([cap], [sv], marker="s", s=34, facecolor="white", edgecolor=col, lw=1.4, zorder=5)
        off = {"capex_3p5_itc": (-36, 4), "itc_extended": (6, 5), "current_law": (6, -11), "capex_3p5": (6, -11)}[k]
        ax.annotate(f"{v['best']['atl']}A+{v['best']['inl']}I", (cap, sv), xytext=off, textcoords="offset points", fontsize=5.6, color=col)
    ax.scatter([], [], marker="s", facecolor="white", edgecolor=INK2, label="Best whole-module fleet incl. CAD 1.6 bn per site (A Atlantic, I inland)")
    ax.axvline(4.4, color=GREY, lw=0.8, ls=":"); ax.text(4.47, 0.55, "Central 4.4", fontsize=6, color=INK2, transform=ax.get_xaxis_transform())
    ax.set_yscale("symlog", linthresh=50)
    ax.set_xlabel("SMR capital cost, CAD bn per 300 MWe module")
    ax.set_ylabel("Saving vs no SMRs, CAD M yr⁻¹")
    ax.set_title("Fossil-free 2050 system")
    ax.legend(fontsize=5.6, loc="upper left", bbox_to_anchor=(0.0, -0.2))
    ax = axs[1]; letter(ax, "b")
    sites = ["NS_POINT_TUPPER", "NB_SAINT_JOHN", "ON_CHATHAM", "SK_BELLE_PLAINE", "AB_HEARTLAND", "BC_KAMLOOPS", "MB_CHURCHILL"]
    lab = ["NS", "NB", "ON", "SK", "AB", "BC*", "MB*"]
    cs = [("central", "Central (site infrastructure CAD 1.6 bn)", C[0]), ("no_common_infrastructure", "No site infrastructure", C[5]),
          ("capex_3p5_common_low", "CAD 3.5 bn modules, 0.8 bn site", C[2]), ("capacity_value_60", "Capacity value CAD 60/kW-yr", C[3]),
          ("carbon_realisation_75", "75% carbon-price value", C[1])]
    w = 0.16; xx = np.arange(len(sites))
    for i, (k, name, col) in enumerate(cs):
        ax.bar(xx + (i - 2) * w, [SENS[k][s] for s in sites], width=w, color=col, label=name, edgecolor="white", lw=0.4)
    ax.axhline(0, color="#666", lw=0.6)
    ax.set_xticks(xx, lab); ax.set_ylabel("Net present value, CAD bn per site")
    ax.set_title("Transition: two-module Highway 1 sites")
    ax.legend(fontsize=5.6, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    ax.text(0.99, 0.02, "* test sites, one module", transform=ax.transAxes, ha="right", fontsize=5.8, color=INK2)
    fig.tight_layout(w_pad=1.5)
    save(fig, "Figure_4_smr_economics")


def fig5():
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.7))
    ax = axs[0]; letter(ax, "a")
    F = SC["forced"]; regs = [("gsl", "Gulf of\nSt Lawrence"), ("lab", "Labrador"), ("hb", "Hudson Bay\n(Churchill/Moosonee)")]
    opts = [("no SMR", "No SMR", C[0]), ("SMR option (current law)", "SMR option (current law)", C[7]),
            ("SMR CAD 3.5 bn with ITC, Hudson Bay fleet allowed", "CAD 3.5 bn + ITC, Hudson Bay module allowed", C[5])]
    w = 0.26; xx = np.arange(3)
    for i, (o_, name, col) in enumerate(opts):
        v = [next(f["extra_cost_bn"] for f in F if f["region"] == r and f["smr"] == o_) for r, _ in regs]
        ax.bar(xx + (i - 1) * w, v, width=w, color=col, label=name, edgecolor="white", lw=0.4)
        for xi, vi in zip(xx + (i - 1) * w, v):
            ax.text(xi, vi + 0.01, f"{vi:.2f}", ha="center", fontsize=5.4, color=INK2)
    ax.set_xticks(xx, [r[1] for r in regs]); ax.set_ylabel("Extra cost, CAD bn yr⁻¹")
    ax.set_title("Forcing 2,000 km² of northern kelp")
    ax.set_ylim(0, 0.85)
    ax.legend(fontsize=5.8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=1)
    ax = axs[1]; letter(ax, "b")
    sm = SM["kelp"]
    rows = [k for k in sm if k["valuation"] == "system_shadow_2041"]
    names = {"NS_POINT_TUPPER": "Atlantic (NS)", "NB_SAINT_JOHN": "Atlantic (NB)", "MB_CHURCHILL": "Hudson Bay (MB)"}
    xx = np.arange(len(rows))
    ax.bar(xx - 0.18, [k["biomass"] for k in rows], width=0.34, color=C[1], label="Modelled kelp biomass cost")
    ax.bar(xx + 0.18, [k["breakeven_biomass_cad_t"] for k in rows], width=0.34, color=C[2], label="Break-even biomass cost with SMR heat")
    ax.set_xticks(xx, [names[k["site"]] for k in rows]); ax.set_ylabel("CAD per dry tonne")
    ax.set_title("Per tonne at the 2041 system fuel value"); ax.legend(fontsize=6)
    fig.tight_layout(w_pad=1.5)
    save(fig, "Figure_5_regional_tests")


def fig7():
    A = json.load(open(OUT / "adequacy_stress.json"))
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.7))
    ax = axs[0]; letter(ax, "a")
    for hs, col in ((0.0, C[1]), (0.10, C[0]), (0.25, C[2])):
        for cf, ls in ((0.05, ":"), (0.10, "-"), (0.15, "--")):
            r = [x for x in A["rows"] if x["hydro_share"] == hs and x["wind_cf"] == cf]
            ax.plot([x["days"] for x in r], [x["gap_energy_twh"] for x in r], color=col, ls=ls, marker="o", ms=3, lw=1.3)
    h = [Line2D([], [], color=c, lw=1.5, label=f"{int(s * 100)}% of weekly hydro reshaped") for s, c in ((0.0, C[1]), (0.10, C[0]), (0.25, C[2]))]
    h += [Line2D([], [], color=INK2, ls=l, label=f"wind capacity factor {cf:.2f}") for cf, l in ((0.05, ":"), (0.10, "-"), (0.15, "--"))]
    ax.legend(handles=h, fontsize=5.4, loc="upper left")
    ax.set_xlabel("Duration of cold low-wind period, days"); ax.set_ylabel("Unserved energy before backup, TWh")
    ax.set_title("Winter lull: energy gap")
    ax = axs[1]; letter(ax, "b")
    I = A["integrated"]["cases"]
    labs = ["7 days\nCF 0.10\nhydro 10%", "14 days\nCF 0.10\nhydro 10%", "14 days\nCF 0.05\nno hydro"]
    fixed = [c["reserve_cost_item_bn"] for c in I]; other = [c["extra_vs_annual_bn"] - c["reserve_cost_item_bn"] for c in I]
    xx = np.arange(len(I))
    ax.bar(xx, fixed, color=C[6], width=0.55, label="Backup turbines and methane storage")
    ax.bar(xx, other, bottom=fixed, color=C[3], width=0.55, label="Re-optimized methane production and system")
    for xi, c in zip(xx, I):
        ax.text(xi, c["extra_vs_annual_bn"] + 0.1, f"+{c['extra_vs_annual_bn']:.2f}\n({c['methane_reserve_twh']:.0f} TWh CH₄)", ha="center", fontsize=5.8, color=INK2)
    ax.set_xticks(xx, labs, fontsize=6)
    ax.set_ylim(0, max(c["extra_vs_annual_bn"] for c in I) * 1.3)
    ax.set_ylabel("Added system cost, CAD bn yr⁻¹"); ax.set_title("Winter reserve inside the optimization")
    ax.legend(fontsize=5.6, loc="upper left")
    fig.tight_layout(w_pad=1.5)
    save(fig, "Figure_7_winter_adequacy")


def fig6():
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.6), gridspec_kw=dict(width_ratios=[0.8, 1.1, 1.3]))
    gh = CP["grid_harvester"]
    ax = axs[0]; letter(ax, "a")
    ax.bar([0, 1], [gh["conventional_energy_gwh"], gh["energy_gwh"]], color=[GREY, C[0]], width=0.6)
    for i, v in enumerate([gh["conventional_energy_gwh"], gh["energy_gwh"]]):
        ax.text(i, v + 1, f"{v:.0f}", ha="center", fontsize=6.5)
    ax.set_xticks([0, 1], ["Conventional\nharvester\n(90.9 MJ/cycle)", "Grid\nHarvester\n(33.9 MJ/cycle)"], fontsize=6)
    ax.set_ylabel("Harvest energy, GWh yr⁻¹")
    ax.set_title(f"{gh['units']:.0f} Grid Harvesters")
    ax = axs[1]; letter(ax, "b")
    sh = CP["shellfish"]
    cats = [("margin_manual_cad_m", "Manual"), ("margin_robot_cad_m", "ROV harvest"), ("margin_robot_shared_lease_cad_m", "ROV + shared lease"),
            ("margin_manual_shared_lease_cad_m", "Manual + shared lease")]
    xx = np.arange(len(cats)); w = 0.36
    for i, (reg, lab, col) in enumerate((("pac", "BC", C[0]), ("atl", "Atlantic", C[2]))):
        ax.bar(xx + (i - 0.5) * w, [sh[reg][c] for c, _ in cats], width=w, color=col, label=f"{lab}: {sh[reg]['operable_sites']:.0f} sites")
    ax.axhline(0, color="#666", lw=0.6)
    ax.set_xticks(xx, [c[1] for c in cats], fontsize=5.6, rotation=20, ha="right")
    ax.set_ylabel("Shellfish margin, CAD M yr⁻¹")
    ax.set_title("Shellfish in kelp leases"); ax.legend(fontsize=5.8)
    ax = axs[2]; letter(ax, "c")
    rows = CP["salmon"]["rows"]
    regs = ["Atlantic, open-net pens in kelp lease", "British Columbia, closed containment (+CAD 1/kg)",
            "British Columbia, closed containment (+CAD 2/kg)", "British Columbia, closed containment (+CAD 3/kg)"]
    labs = ["Atlantic\npens", "BC closed\n+CAD 1/kg", "BC closed\n+CAD 2/kg", "BC closed\n+CAD 3/kg"]
    for i, (p, col) in enumerate(((6.0, C[1]), (8.0, C[3]), (10.0, C[5]))):
        v = [next(r["net_cad_m"] for r in rows if r["region"] == g and r["price_cad_kg"] == p) for g in regs]
        ax.bar(np.arange(4) + (i - 1) * 0.26, v, width=0.26, color=col, label=f"CAD {p:.0f}/kg")
    ax.axhline(0, color="#666", lw=0.6)
    ax.set_xticks(np.arange(4), labs, fontsize=5.6); ax.set_ylabel("Net, CAD M yr⁻¹ per 50 kt block")
    ax.set_title("Salmon with 1,544 utility robots"); ax.legend(fontsize=5.8, loc="upper right")
    fig.tight_layout(w_pad=1.0)
    save(fig, "Figure_6_marine_coproduction")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5(); fig6(); fig7()
    print("figures written to", FIG)
