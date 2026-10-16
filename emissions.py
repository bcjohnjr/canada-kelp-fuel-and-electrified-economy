"""Canada's greenhouse-gas accounts if transport runs on renewable energy and all oil is exported.

Two accounts are kept separate and never added together:
  territorial  the National Inventory (NIR) boundary used for Canada's 2030 and 2035 targets: emissions released in
               Canada, excluding international aviation and shipping bunkers, with biogenic CO2 from biofuel
               combustion reported as a memo item (its carbon is tracked in LULUCF);
  lifecycle    well-to-wheel emissions of the transport energy used in Canada wherever they occur (equipment
               manufacture abroad, crop and land-use effects), used to judge the technology, not the target.

Inventory (ECCC, National Inventory Report 2026, economic sectors, Mt CO2e, excluding LULUCF)
  2005: total 763; oil and gas 198, transport 156, buildings 85, electricity 116, heavy industry 89, agriculture 66,
        waste and others 54.
  2024: total 685; oil and gas 208, transport 151, buildings 81, electricity 50, heavy industry 77, agriculture 70,
        waste and others 47.
Targets: 40-45% below 2005 by 2030; 45-50% below 2005 by 2035; net zero by 2050. Progress also counts an LULUCF
  accounting contribution, reported separately and not included here.
Transport replacement, territorial account
  removes the transport sector (151 Mt) and the off-road machinery reported under other sectors (analyses emissions
  bridge: 20 Mt), and adds what the renewable system emits in Canada: CH4 and N2O from burning biofuels in vehicles,
  ships and machines (1.7 g CO2e/MJ, the 2024 inventory ratio of transport CH4 + N2O to fuel use; international
  aviation excluded) and methane slip from biogas plants and biomethane upgrading (2% of the methane produced, GWP100
  of 28). Wind, solar and hydro plants, kelp farms and biorefineries run on electricity and renewable heat and emit
  no fossil CO2 in Canada. Equipment made in Canada adds industrial emissions that are not estimated here.
Exporting all oil
  Crude production is unchanged. Canadian refineries receive ~1.29 Mb/d of Canadian crude (CAPP 2026; refinery runs
  1.6 Mb/d, CER 2026); the share that now serves Canadian transport (70%, ~0.90 Mb/d) is exported instead, as crude or
  as products from refineries that keep running, and the crude imports that served Canadian transport stop. Upstream oil and gas emissions
  therefore stay in Canada's inventory. Refining emissions (assumed 16 Mt, about 27 kg CO2e per barrel at 1.6 Mb/d)
  either stay (refineries run for export) or fall by the share of their output that served Canadian transport
  (assumed 70%; about 80% of refined products are consumed in Canada, CER 2026).
Further oil-and-gas abatement (outside the model): carbon capture and storage of up to 22 Mt/yr proposed by the
  Pathways Alliance for oil sands facilities.
Exported combustion: 2025 crude and product exports of 2,762 TWh plus the redirected domestic crude (0.70 x 1.29 =
  0.90 Mb/d at 1.61 MWh/bbl) at 0.26 t CO2/MWh are burned abroad and counted in importing countries' inventories.
"""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "outputs"
NIR = {"2005": {"Oil and gas": 198, "Transport": 156, "Buildings": 85, "Electricity": 116, "Heavy industry": 89,
                "Agriculture": 66, "Waste and others": 54},
       "2024": {"Oil and gas": 208, "Transport": 151, "Buildings": 81, "Electricity": 50, "Heavy industry": 77,
                "Agriculture": 70, "Waste and others": 47}}
TOTAL = {"2005": 763.0, "2024": 685.0}
TARGETS = {"2030": (0.40, 0.45), "2035": (0.45, 0.50)}
REFINING_MT = 16.0
REFINING_DOMESTIC_TRANSPORT_SHARE = 0.70
PATHWAYS_CCS_MT = 22.0
DOMESTIC_CRUDE_MBD = 1.29             # Canadian crude received by Canadian refineries (CAPP 2026)
REDIRECTED_CRUDE_MBD = DOMESTIC_CRUDE_MBD * REFINING_DOMESTIC_TRANSPORT_SHARE   # share now serving Canadian transport
MWH_PER_BBL = 1.61
T_PER_MWH_CRUDE = 0.26


NONCO2_G_MJ = 1.7
CH4_SLIP = 0.02
GWP_CH4 = 28.0


def territorial_addition(biofuel_domestic_twh, biomethane_twh):
    """Mt CO2e released in Canada by the renewable transport system (NIR boundary)."""
    comb = biofuel_domestic_twh * 3.6e9 * NONCO2_G_MJ / 1e12
    slip = biomethane_twh * 3.6e6 / 50.0 * CH4_SLIP * GWP_CH4 / 1e6     # GJ / (50 GJ/t CH4) -> t CH4
    return dict(combustion_non_co2_mt=comb, methane_slip_mt=slip, total_mt=comb + slip)


def ledger(offroad_mt, territorial_mt, oil_export_twh, lifecycle=None):
    """Territorial ledger against the targets; lifecycle (fossil and renewable well-to-wheel, Mt) is reported beside
    it as a separate account."""
    base = TOTAL["2024"]
    rows = [("2024 inventory", base, "ECCC NIR 2026")]
    s1 = base - NIR["2024"]["Transport"] - offroad_mt + territorial_mt
    rows.append(("Transport and off-road machinery on renewable energy; all oil exported, refineries run for export", s1,
                 f"-{NIR['2024']['Transport']} transport, -{offroad_mt:.0f} off-road, +{territorial_mt:.1f} emitted in Canada by the renewable system"))
    s2 = s1 - REFINING_MT * REFINING_DOMESTIC_TRANSPORT_SHARE
    rows.append(("… and refineries that served Canadian transport close or convert", s2, f"-{REFINING_MT * REFINING_DOMESTIC_TRANSPORT_SHARE:.1f} refining"))
    s3 = s2 - PATHWAYS_CCS_MT
    rows.append(("… and oil sands carbon capture (Pathways, 22 Mt)", s3, "-22 CCS"))
    t = {y: [TOTAL["2005"] * (1 - a) for a in rng] for y, rng in TARGETS.items()}
    gap = {name: {y: [v - x for x in t[y]] for y in t} for name, v, _ in rows}
    og_needed_2030 = NIR["2024"]["Oil and gas"] - (s2 - t["2030"][0])
    redirected_twh = REDIRECTED_CRUDE_MBD * 1e6 * 365 * MWH_PER_BBL / 1e6
    abroad = (oil_export_twh + redirected_twh) * T_PER_MWH_CRUDE
    res = dict(nir=NIR, total=TOTAL, targets_mt=t, rows=[dict(case=a, mt=b, note=c) for a, b, c in rows], gap_mt=gap,
               og_allowed_2030_upper_mt=og_needed_2030, og_cut_needed_2030_pct=(1 - og_needed_2030 / NIR["2024"]["Oil and gas"]) * 100,
               share_below_2005_pct={a: (1 - b / TOTAL["2005"]) * 100 for a, b, _ in rows},
               oil_and_gas_share_of_remaining_pct=NIR["2024"]["Oil and gas"] / s2 * 100,
               redirected_crude_mbd=REDIRECTED_CRUDE_MBD, redirected_crude_twh=redirected_twh, exported_combustion_abroad_mt=abroad,
               exported_combustion_now_mt=oil_export_twh * T_PER_MWH_CRUDE, territorial_addition_mt=territorial_mt,
               lifecycle=lifecycle or {})
    json.dump(res, open(OUT / "national_emissions.json", "w"), indent=1)
    return res


if __name__ == "__main__":
    r = ledger(20.0, 2.0, 2762.0)
    for x in r["rows"]:
        print(round(x["mt"], 1), x["case"])
    print(r["targets_mt"], r["share_below_2005_pct"], round(r["og_cut_needed_2030_pct"], 1), round(r["exported_combustion_abroad_mt"]))
