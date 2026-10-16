"""Carbon-reduction accounting for the Canadian renewable-transport model.

Three questions are kept distinct:
1) Canadian territorial emissions under the National Inventory boundary;
2) well-to-wheel lifecycle emissions of transport energy used in Canada; and
3) a global sensitivity for redirected Canadian crude.  The third is not a forecast of world
   oil demand.  It asks what fraction (alpha) of the combustion of crude displaced from
   Canadian refineries would be additional globally rather than displacing other crude supply.

This avoids claiming that exporting the displaced crude is automatically a global climate
benefit or, conversely, that every exported barrel is automatically additional combustion.
"""
from __future__ import annotations
import csv, json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "outputs"


def percentile(vals, q):
    vals = sorted(float(x) for x in vals)
    if not vals:
        return None
    pos = (len(vals)-1) * q / 100.0
    lo = int(pos); hi = min(lo+1, len(vals)-1); w = pos-lo
    return vals[lo]*(1-w)+vals[hi]*w


def build():
    n = json.load(open(OUT / "national_emissions.json"))
    base = float(n["total"]["2024"])
    rows = n["rows"]
    territorial = []
    for r in rows[1:]:
        mt = float(r["mt"])
        territorial.append({
            "case": r["case"],
            "emissions_mtco2e_a": mt,
            "avoided_vs_2024_mtco2e_a": base-mt,
            "reduction_vs_2024_pct": 100.0*(base-mt)/base,
            "below_2005_pct": float(n["share_below_2005_pct"][r["case"]]),
        })

    lc = n["lifecycle"]
    fossil = float(lc["fossil_wtw_mt"])
    renewable = float(lc["renewable_wtw_mt"])
    avoided = fossil-renewable

    mc_path = OUT / "monte_carlo.csv"
    mc = []
    if mc_path.exists():
        for r in csv.DictReader(open(mc_path)):
            if str(r.get("infeasible", "")).lower() in ("true", "1"):
                continue
            mc.append(float(r["fossil_lifecycle_mtco2e"])-float(r["lowcarbon_lifecycle_mtco2e"]))
    mc_avoided = [percentile(mc,q) for q in (5,50,95)] if mc else [None,None,None]

    redirected_combustion = float(n["redirected_crude_twh"]) * 0.26
    additivity = []
    for alpha in (0.0, 0.25, 0.5, 0.75, 1.0):
        net = avoided-alpha*redirected_combustion
        additivity.append({
            "redirected_crude_additional_combustion_fraction": alpha,
            "net_global_avoided_mtco2e_a": net,
            "net_reduction_vs_fossil_transport_pct": 100.0*net/fossil,
        })

    # Illustrative cumulative reduction if deployment rises linearly from zero in 2027 to the
    # full annual territorial reduction in 2050.  This is a rollout sensitivity, not an optimiser output.
    years = 24
    ramp_factor = years/2.0
    cumulative = [{
        **r,
        "illustrative_linear_2027_2050_avoided_gtco2e": r["avoided_vs_2024_mtco2e_a"]*ramp_factor/1000.0
    } for r in territorial]

    out = {
        "territorial": territorial,
        "lifecycle": {
            "fossil_transport_wtw_mtco2e_a": fossil,
            "renewable_transport_wtw_mtco2e_a": renewable,
            "avoided_mtco2e_a": avoided,
            "reduction_pct": 100.0*avoided/fossil,
            "monte_carlo_avoided_p5_p50_p95_mtco2e_a": mc_avoided,
        },
        "redirected_crude": {
            "energy_twh_a": float(n["redirected_crude_twh"]),
            "combustion_mtco2_a": redirected_combustion,
            "global_additivity_sensitivity": additivity,
            "interpretation": "alpha=0 means redirected Canadian crude displaces other crude supply; alpha=1 is a conservative upper bound in which all redirected combustion is additional globally."
        },
        "illustrative_linear_rollout": {
            "start_year": 2027, "full_year": 2050, "years": years,
            "note": "Illustrative linear deployment only; not an endogenous deployment pathway.",
            "cases": cumulative,
        }
    }
    json.dump(out, open(OUT / "carbon_reduction.json", "w"), indent=1)
    return out

if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
