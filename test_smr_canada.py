"""Checks for the SMR cogeneration screen (run after smr_canada_cascade.py)."""
import json
from pathlib import Path
import smr_canada_cascade as m

S = json.loads((Path(__file__).resolve().parent / "outputs" / "smr_canada_summary.json").read_text())
F = S["fleet_2041"]
fleet = [s for s in m.SITES if s["fleet"]]
assert F["modules"] == sum(s["modules"] for s in fleet) == 10
assert abs(F["electricity_twh"] - sum(S["sites_2041"][s["id"]]["electricity_twh"] for s in fleet)) < 1e-9
# energy balance: net electricity + extraction penalty = gross electricity
for s in m.SITES:
    a = m.site_year(s, 2041); pen = sum(s["heat_avg"].get(k, 0) * v for k, v in m.PARAMS["extraction_penalty_mwe_per_mwth"].items())
    assert abs(a["net_mwe_per_module"] + pen - 300.0) < 1e-9
# highway allocation sums to the archived traction demand
assert abs(sum(v["traction_twh"] for v in S["highway_allocation"].values()) - 9.9338) < 1e-6
# steam sold is worth more than the electricity it costs at every fleet site
for s in fleet:
    a = S["sites_2041"][s["id"]]; pens = m.PARAMS["extraction_penalty_mwe_per_mwth"]
    assert a["heat_value_cad_mwh_th"] > max(pens.values()) * a["power_value_cad_mwh"]
# kelp: Hudson Bay is far above break-even under both valuations
for k in S["kelp"]:
    if k["site"] == "MB_CHURCHILL":
        assert k["margin"] < 0 and k["biomass"] > 5 * max(k["breakeven_biomass_cad_t"], 1)
# heat sold never exceeds nameplate extraction, and site capital includes common infrastructure and pipes
for s in m.SITES:
    a = m.site_year(s, 2041)
    assert a["heat_twh"] <= s["modules"] * sum(s["heat"].values()) * 8760 * 0.9 / 1e6 + 1e-9
    assert a["common_infra_cad"] == m.PARAMS["site"]["common_infra_cad_bn"]["central"] * 1e9 and a["pipes_cad"] > 0
print("all checks passed")
