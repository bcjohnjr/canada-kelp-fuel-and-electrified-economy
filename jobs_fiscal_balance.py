"""Net employment and public-revenue balance against today's petroleum transport-fuel system, with an Alberta account.

employment_fiscal.py gives the gross jobs and tax channels of the renewable system. This module subtracts what the
transition removes, so that the result is a net change relative to today, at 2025 prices, in steady state.

Production rule
  Upstream crude and bitumen production is held at its 2025 level in every case: the share of the 1.29 million b/d
  of Canadian crude received by Canadian refineries that now serves Canadian transport (70%, about 0.90 million b/d)
  is exported (as crude, or as refined products) to countries that still need it while they transition. Royalties, land sales and upstream jobs therefore do not change, which is why the oil-producing
  provinces keep their resource revenue.
Two refinery cases
  A  Capacity maintained (central): domestic refineries keep running and export the products Canada no longer
     burns, or convert units to renewable hydrotreating; refining jobs and refining income taxes are retained.
  B  Domestic-serving refining closes: 70% of refining labour and the refining part of petroleum-sector
     government revenue (CAD 4.0 bn/a of the CAD 24.0 bn/a) are lost.
What the transition removes in both cases
  Fuel-volume-linked labour at gasoline stations and cardlocks. The retail margin is 6.3% of the pump price
  (Library of Parliament, first half of 2026); 40% of it is taken as labour (25-55% range), and it falls with the
  share of road fuel that is no longer sold as liquid at stations (charging and the remaining renewable liquids are
  served by the renewable system, whose delivery labour is already counted in its gross jobs).
Taxes on displaced labour use the same personal-income and wage-induced sales-tax rates as the gross account.
Statutory per-unit fuel taxes are kept in both systems (on renewable fuels and, through a road-use charge, on electric
kilometres), so they cancel in the comparison and are reported only to show that they are retained.

Alberta account
  Royalties and land sales: unchanged because production is unchanged (Budget 2026-27 bitumen royalties CAD 9.7 bn).
  Alberta fuel-tax revenue: an equivalent provincial fuel-tax or road-use revenue, benchmarked to the fully reinstated
  13 c/L statutory rate on Alberta's 14.5% of national gasoline and 22% of road diesel (collection is suspended from
  1 October 2026), kept through taxes on renewable fuel and a road-use charge on electric kilometres.
  Refining: Alberta holds 522 of 1898 thousand b/d of crude-refining capacity (CAPP, April 2026), 27.5%.
  New ongoing and build jobs located in Alberta: from Alberta's share of population (12.1%, 1 October 2025) to its
  share of national planned renewable-power additions to 2030 (27.6%, Canada Energy Regulator 2025).
  Displaced station labour in Alberta: Alberta's share of national road-fuel sales, weighted by retail margin.
"""
from __future__ import annotations

import json
from pathlib import Path

import economy as E
import employment_fiscal as EF

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"

RETAIL_MARGIN_SHARE = 0.063               # of pump price; Library of Parliament HillNotes, 17 Aug 2026
RETAIL_LABOUR_SHARE = 0.40
RETAIL_LABOUR_SHARE_RANGE = (0.25, 0.55)
RETAIL_COMP_CAD = 48_000.0                # annual compensation per station job (part-time weighted), assumption
RETAIL_COMP_RANGE = (40_000.0, 60_000.0)

REFINING_SALARIES_2023_BN = 1.6           # NAICS 324 total salaries 2023 (Statistics Canada 16-10-0117-01 via ISED)
BENEFIT_UPLIFT = 1.15                     # salaries to total compensation
REFINING_COMP_CAD = 140_000.0             # compensation per refining job, assumption
REFINING_COMP_RANGE = (120_000.0, 160_000.0)
DOMESTIC_SERVING_REFINING = 0.70
REFINING_GOV_BN = E.OIL_GOV["total"] - E.OIL_GOV["upstream"]   # 4.0

AB_POP_SHARE = 5_040_871 / 41_575_585     # Statistics Canada preliminary estimates, 1 October 2025
AB_RENEWABLE_ADDITIONS_SHARE = 2413 / 8745  # CER, planned additions to 2030 (MW)
AB_REFINING_SHARE = 522 / 1898            # CAPP, crude-refining capacity, 1 April 2026
AB_FUEL_TAX_CL = 13.0
AB_BITUMEN_ROYALTY_2026_27_BN = 9.7       # Alberta Budget 2026 (RBC Economics summary)

ROAD = ("ldv_gasoline", "ldv_diesel", "hdv")


def _station_liquid_remaining(s):
    """Share of road transport energy still sold as liquid fuel at stations in the solved system."""
    road = sum(s["demand_twh"][k] for k in ROAD)
    liq = sum(v for k, v in s["end_use_twh"].items()
              if k.split("|")[0] in ROAD and k.split("|")[1] in ("liq", "ed95", "e85", "ffv", "lng", "cng", "meoh"))
    return liq / road


def _retail_margin_bn():
    gas = E.VOL_GL["gasoline"] * E.RETAIL["avg2025"]["gasoline"] * RETAIL_MARGIN_SHARE / 100
    dsl = E.VOL_GL["road_diesel"] * E.RETAIL["avg2025"]["diesel"] * RETAIL_MARGIN_SHARE / 100
    ab = (E.VOL_GL["gasoline"] * E.AB_SHARE["gasoline"] * E.RETAIL["avg2025"]["gasoline"]
          + E.VOL_GL["road_diesel"] * E.AB_SHARE["diesel"] * E.RETAIL["avg2025"]["diesel"]) * RETAIL_MARGIN_SHARE / 100
    return gas + dsl, ab / (gas + dsl)


def _taxes_on(comp_bn):
    pit = comp_bn * EF.PERSONAL_INCOME_TAX_RATE
    sales = comp_bn * EF.CASH_WAGE_SHARE * (1 - EF.PERSONAL_INCOME_TAX_RATE) * EF.CONSUMPTION_SHARE * EF.GENERAL_SALES_TAX_EFFECTIVE
    return pit + sales


def balance(s, ef, labour_share=RETAIL_LABOUR_SHARE, retail_comp=RETAIL_COMP_CAD, refining_comp=REFINING_COMP_CAD):
    tc, em, lc = ef["tax_channels"], ef["employment"], ef["labour_compensation"]
    margin, ab_retail_share = _retail_margin_bn()
    lost_volume = 1 - _station_liquid_remaining(s)
    retail_comp_bn = margin * labour_share * lost_volume
    retail_jobs = retail_comp_bn * 1e9 / retail_comp
    refining_comp_bn = REFINING_SALARIES_2023_BN * BENEFIT_UPLIFT * EF.EARN_WEEKLY_JUL2026 / EF.EARN_WEEKLY_2023 * DOMESTIC_SERVING_REFINING
    refining_jobs = refining_comp_bn * 1e9 / refining_comp

    gross_tax_gain = (tc["renewable_corporate_income_tax_at_2025_prices_bn"] + tc["personal_income_tax_steady_bn"]
                      + tc["wage_induced_sales_tax_steady_bn"] + tc["property_tax_capacity_bn"])
    gross_tax_gain_build = gross_tax_gain + (tc["personal_income_tax_build_phase_bn"] - tc["personal_income_tax_steady_bn"]) \
        + (tc["wage_induced_sales_tax_build_phase_bn"] - tc["wage_induced_sales_tax_steady_bn"])
    status_quo = E.OIL_GOV["total"] + tc["statutory_transport_taxes_and_road_charges_bn"]
    cases = {}
    for key, keep_refining in (("A_capacity_maintained", True), ("B_domestic_refining_closes", False)):
        jobs_lost = retail_jobs + (0.0 if keep_refining else refining_jobs)
        comp_lost = retail_comp_bn + (0.0 if keep_refining else refining_comp_bn)
        gov_lost = _taxes_on(comp_lost) + (0.0 if keep_refining else REFINING_GOV_BN)
        net_fiscal = gross_tax_gain - gov_lost
        cases[key] = dict(
            jobs_created_ongoing=em["ongoing_jobs"], jobs_created_build_average=em["average_build_jobs"],
            jobs_displaced=jobs_lost, net_jobs_ongoing=em["ongoing_jobs"] - jobs_lost,
            net_jobs_during_build=em["average_jobs_during_build"] - jobs_lost,
            labour_compensation_created_bn=lc["ongoing_bn"], labour_compensation_displaced_bn=comp_lost,
            new_tax_revenue_bn=gross_tax_gain, revenue_lost_bn=gov_lost,
            net_public_revenue_bn=net_fiscal, net_public_revenue_build_phase_bn=gross_tax_gain_build - gov_lost,
            public_revenue_status_quo_bn=status_quo, public_revenue_after_bn=status_quo + net_fiscal,
            petroleum_royalties_land_retained_bn=E.OIL_GOV["royalties_land"],
            statutory_transport_taxes_retained_bn=tc["statutory_transport_taxes_and_road_charges_bn"])

        # Alberta
        lo_new = em["ongoing_jobs"] * AB_POP_SHARE
        hi_new = em["ongoing_jobs"] * AB_RENEWABLE_ADDITIONS_SHARE
        ab_lost = retail_jobs * ab_retail_share + (0.0 if keep_refining else refining_jobs * AB_REFINING_SHARE)
        ab_fuel_tax = (E.VOL_GL["gasoline"] * E.AB_SHARE["gasoline"] + E.VOL_GL["road_diesel"] * E.AB_SHARE["diesel"]) * AB_FUEL_TAX_CL / 100
        cases[key]["alberta"] = dict(
            royalty_base_change_bn=0.0, bitumen_royalties_budget_2026_27_bn=AB_BITUMEN_ROYALTY_2026_27_BN,
            fuel_tax_retained_bn=ab_fuel_tax,
            new_ongoing_jobs_range=(lo_new, hi_new),
            new_build_jobs_range=(em["average_build_jobs"] * AB_POP_SHARE, em["average_build_jobs"] * AB_RENEWABLE_ADDITIONS_SHARE),
            jobs_displaced=ab_lost,
            net_ongoing_jobs_range=(lo_new - ab_lost, hi_new - ab_lost),
            net_jobs_during_build_range=(lo_new + em["average_build_jobs"] * AB_POP_SHARE - ab_lost,
                                         hi_new + em["average_build_jobs"] * AB_RENEWABLE_ADDITIONS_SHARE - ab_lost),
            refining_capacity_share=AB_REFINING_SHARE)
    return dict(retail_margin_bn=margin, station_liquid_share_remaining=1 - lost_volume,
                displaced_station_labour_bn=retail_comp_bn, displaced_station_jobs=retail_jobs,
                domestic_serving_refining_labour_bn=refining_comp_bn, domestic_serving_refining_jobs=refining_jobs,
                alberta_share_of_station_margin=ab_retail_share, cases=cases)


def sensitivity(s, ef):
    """Ranges over retail labour share, station and refinery compensation, combined with the gross-job range of
    employment_fiscal (domestic value-added share, labour share and compensation)."""
    disp = {}
    fis = {}
    for ls in RETAIL_LABOUR_SHARE_RANGE:
        for rc in RETAIL_COMP_RANGE:
            for fc in REFINING_COMP_RANGE:
                b = balance(s, ef, ls, rc, fc)
                for k, c in b["cases"].items():
                    disp.setdefault(k, []).append(c["jobs_displaced"]); fis.setdefault(k, []).append(c["net_public_revenue_bn"])
    lo, hi = ef["employment"]["ongoing_jobs_range"]
    return {k: dict(jobs_displaced_range=(min(disp[k]), max(disp[k])),
                    net_jobs_ongoing_range=(lo - max(disp[k]), hi - min(disp[k])),
                    net_public_revenue_range_bn=(min(fis[k]), max(fis[k]))) for k in disp}


def main():
    R = json.load(open(OUT / "results.json"))
    ef = json.load(open(OUT / "employment_fiscal.json"))
    res = balance(R["central"], ef)
    res["sensitivity"] = sensitivity(R["central"], ef)
    res["assumptions"] = dict(retail_margin_share_of_pump_price=RETAIL_MARGIN_SHARE, retail_labour_share=RETAIL_LABOUR_SHARE,
                              retail_compensation_cad=RETAIL_COMP_CAD, refining_salaries_2023_bn=REFINING_SALARIES_2023_BN,
                              benefit_uplift=BENEFIT_UPLIFT, refining_compensation_cad=REFINING_COMP_CAD,
                              domestic_serving_refining_share=DOMESTIC_SERVING_REFINING,
                              refining_government_revenue_bn=REFINING_GOV_BN, alberta_population_share=AB_POP_SHARE,
                              alberta_renewable_additions_share=AB_RENEWABLE_ADDITIONS_SHARE,
                              alberta_refining_capacity_share=AB_REFINING_SHARE)
    json.dump(res, open(OUT / "jobs_fiscal_balance.json", "w"), indent=1, default=float)
    for k, c in res["cases"].items():
        a = c["alberta"]
        print(f"{k}: net jobs {c['net_jobs_ongoing']:,.0f} ongoing ({c['net_jobs_during_build']:,.0f} during build); "
              f"net public revenue {c['net_public_revenue_bn']:+.2f} bn/a; Alberta net jobs "
              f"{a['net_ongoing_jobs_range'][0]:,.0f} to {a['net_ongoing_jobs_range'][1]:,.0f}")


if __name__ == "__main__":
    main()
