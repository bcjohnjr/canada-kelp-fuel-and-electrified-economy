"""Screening employment, public-revenue and price-stability accounts for the mature Canadian transport system.

This module is deliberately downstream of the least-cost optimisation. It does not alter the technology mix.
It estimates gross jobs supported and associated tax channels from transparent macro ratios; it is not a
computable-general-equilibrium model and should not be interpreted as net employment creation.

Empirical anchors
-----------------
* NRCan/Statistics Canada clean technology, clean energy and environmental goods/services (2023):
  GDP CAD 80.8 bn, 354,257 jobs, average compensation CAD 105,768/job.
* Statistics Canada average weekly earnings: CAD 1,204.92 in 2023 and CAD 1,347.14 in July 2026.
  The 2023 clean-sector compensation is scaled by that national earnings ratio for a 2026 compensation proxy.
* General government household income taxes were CAD 389.437 bn in 2024 and total compensation for all jobs
  CAD 1,651.926 bn. We use a more conservative 20% central effective personal-income-tax rate on modelled
  labour compensation (15-24% sensitivity), rather than the raw 23.6% macro ratio.
* 2025 household final consumption was CAD 1,760.646 bn; general sales tax revenue was CAD 67.001 bn.
  The effective general-sales-tax yield is therefore 3.81% of household consumption. Q2-2026 household
  saving was 3.7%, so 96.3% of disposable cash wages is treated as consumed in the central screen.
* Property tax is a policy/assessment screen, not an observed project tax bill. The central case applies a 0.5%
  effective local property-tax rate to 50% of modelled onshore/taxable fixed capital; ranges vary the taxable
  share and rate.
"""
from __future__ import annotations

import fiscal as F
import economy as E

CLEAN_GDP_2023_BN = 80.8
CLEAN_JOBS_2023 = 354_257
CLEAN_COMP_PER_JOB_2023 = 105_768.0
EARN_WEEKLY_2023 = 1_204.92
EARN_WEEKLY_JUL2026 = 1_347.14
AVG_COMP_2026 = CLEAN_COMP_PER_JOB_2023 * EARN_WEEKLY_JUL2026 / EARN_WEEKLY_2023
LABOUR_SHARE_CLEAN_GDP = CLEAN_JOBS_2023 * CLEAN_COMP_PER_JOB_2023 / (CLEAN_GDP_2023_BN * 1e9)

# Screening assumptions. Sensitivities are returned alongside central values.
DOMESTIC_VALUE_ADDED_SHARE = 0.60
DOMESTIC_VALUE_ADDED_RANGE = (0.50, 0.70)
LABOUR_SHARE_RANGE = (0.40, 0.52)
AVG_COMP_RANGE = (105_000.0, 130_000.0)
PERSONAL_INCOME_TAX_RATE = 0.20
PERSONAL_INCOME_TAX_RANGE = (0.15, 0.24)
CASH_WAGE_SHARE = 0.90
CONSUMPTION_SHARE = 0.963
GENERAL_SALES_TAX_EFFECTIVE = 67.001 / 1760.646
PROPERTY_TAX_RATE = 0.005
PROPERTY_TAX_RATE_RANGE = (0.0025, 0.0075)
PROPERTY_TAXABLE_SHARE = 0.50
PROPERTY_TAXABLE_SHARE_RANGE = (0.35, 0.65)

# Kelp farms and vessels are offshore/mobile and are excluded from the central municipal property-tax base.
PROPERTY_EXCLUDE = {"Kelp farms", "Vessels"}


def _capital_charge(s):
    return sum(float(v) * float(cap_share) for v, cap_share, _life in s["cost_items_bn"].values())


def _job_bounds(noncapital_bn, annual_build_bn):
    op, build = [], []
    for dom in DOMESTIC_VALUE_ADDED_RANGE:
        for labour in LABOUR_SHARE_RANGE:
            for comp in AVG_COMP_RANGE:
                op.append(noncapital_bn * dom * labour * 1e9 / comp)
                build.append(annual_build_bn * dom * labour * 1e9 / comp)
    return dict(ongoing_jobs=(min(op), max(op)), build_jobs=(min(build), max(build)),
                build_phase_total_jobs=(min(a + b for a, b in zip(op, build)),
                                        max(a + b for a, b in zip(op, build))))


def employment_and_tax(s):
    """Return screening gross employment and tax channels for one solved system.

    Ongoing employment uses the non-capital part of annual system cost as the spending base. Construction and
    manufacturing job-years use the model's physical build capital spread uniformly over 2027-2050. For each,
    domestic value added is 60% centrally and labour compensation is the 2023 clean-sector compensation share
    of GDP. This avoids applying a jobs-per-dollar coefficient directly to imported equipment or intermediate
    purchases.
    """
    cap_charge = _capital_charge(s)
    noncapital = float(s["objective_bn"]) - cap_charge
    annual_build = float(s["build"]["capex_per_year_2027_2050_bn"])

    op_labour = noncapital * DOMESTIC_VALUE_ADDED_SHARE * LABOUR_SHARE_CLEAN_GDP
    build_labour = annual_build * DOMESTIC_VALUE_ADDED_SHARE * LABOUR_SHARE_CLEAN_GDP
    ongoing_jobs = op_labour * 1e9 / AVG_COMP_2026
    build_jobs = build_labour * 1e9 / AVG_COMP_2026

    # Gross taxes associated with the modelled labour flows.
    pit_steady = op_labour * PERSONAL_INCOME_TAX_RATE
    pit_build = (op_labour + build_labour) * PERSONAL_INCOME_TAX_RATE
    wage_consumption_steady = op_labour * CASH_WAGE_SHARE * (1 - PERSONAL_INCOME_TAX_RATE) * CONSUMPTION_SHARE
    wage_consumption_build = (op_labour + build_labour) * CASH_WAGE_SHARE * (1 - PERSONAL_INCOME_TAX_RATE) * CONSUMPTION_SHARE
    wage_sales_steady = wage_consumption_steady * GENERAL_SALES_TAX_EFFECTIVE
    wage_sales_build = wage_consumption_build * GENERAL_SALES_TAX_EFFECTIVE

    capex = s["build"]["capex_bn"]
    onshore_capex = sum(float(v) for k, v in capex.items() if k not in PROPERTY_EXCLUDE)
    property_tax = onshore_capex * PROPERTY_TAXABLE_SHARE * PROPERTY_TAX_RATE
    property_low = onshore_capex * PROPERTY_TAXABLE_SHARE_RANGE[0] * PROPERTY_TAX_RATE_RANGE[0]
    property_high = onshore_capex * PROPERTY_TAXABLE_SHARE_RANGE[1] * PROPERTY_TAX_RATE_RANGE[1]

    # At roughly 2025 pump prices the mature system is at break-even; keep existing petroleum royalties/taxes
    # because the paper's export case holds upstream crude production constant. Do not assign the oil royalty
    # benchmark a second time to the renewable system.
    a2025 = F.accounts(s, period="avg2025", profit_year="avg2025", royalty_bn=0.0, capture=1.0)
    retained_petroleum_gov = E.OIL_GOV["upstream"]
    stable_total_steady = (retained_petroleum_gov + a2025["fuel_tax_bn"] + a2025["cit_bn"] +
                           pit_steady + wage_sales_steady + property_tax)
    stable_total_build = (retained_petroleum_gov + a2025["fuel_tax_bn"] + a2025["cit_bn"] +
                          pit_build + wage_sales_build + property_tax)
    benchmark_statutory = retained_petroleum_gov + a2025["fuel_tax_bn"]
    full_petroleum_upper = (E.OIL_GOV["total"] + a2025["fuel_tax_bn"] + a2025["cit_bn"] +
                            pit_steady + wage_sales_steady + property_tax)

    # Export redirection: gross trade value only, not government revenue or incremental GDP.
    import emissions as EM
    domestic_crude_mbd = EM.REDIRECTED_CRUDE_MBD   # 70% of the 1.29 Mb/d of Canadian crude refined in Canada
    extra_export_value = E.OIL_EXPORTS_2025["crude_value_bn"] * domestic_crude_mbd / E.OIL_EXPORTS_2025["crude_mbd"]

    bounds = _job_bounds(noncapital, annual_build)
    return dict(
        basis_case="deterministic_learning_target_full_2025_demand_4pct_finance",
        interpretation="Screening gross employment and fiscal capacity for the deterministic learning-target system; not Monte Carlo medians or net macroeconomic effects.",
        assumptions=dict(domestic_value_added_share=DOMESTIC_VALUE_ADDED_SHARE,
                         clean_sector_labour_share=LABOUR_SHARE_CLEAN_GDP,
                         average_compensation_2026_cad=AVG_COMP_2026,
                         personal_income_tax_rate=PERSONAL_INCOME_TAX_RATE,
                         cash_wage_share=CASH_WAGE_SHARE, consumption_share=CONSUMPTION_SHARE,
                         effective_general_sales_tax=GENERAL_SALES_TAX_EFFECTIVE,
                         property_tax_rate=PROPERTY_TAX_RATE, property_taxable_share=PROPERTY_TAXABLE_SHARE),
        cost_base=dict(objective_bn=float(s["objective_bn"]), annual_capital_charge_bn=cap_charge,
                       noncapital_annual_cost_bn=noncapital, build_capex_total_bn=float(s["build"]["capex_total_bn"]),
                       build_capex_per_year_bn=annual_build, onshore_property_base_bn=onshore_capex),
        employment=dict(ongoing_jobs=ongoing_jobs, average_build_jobs=build_jobs,
                        average_jobs_during_build=ongoing_jobs + build_jobs,
                        ongoing_jobs_range=bounds["ongoing_jobs"], build_jobs_range=bounds["build_jobs"],
                        build_phase_total_jobs_range=bounds["build_phase_total_jobs"]),
        labour_compensation=dict(ongoing_bn=op_labour, build_bn=build_labour,
                                 build_phase_total_bn=op_labour + build_labour),
        tax_channels=dict(personal_income_tax_steady_bn=pit_steady,
                          personal_income_tax_build_phase_bn=pit_build,
                          wage_induced_sales_tax_steady_bn=wage_sales_steady,
                          wage_induced_sales_tax_build_phase_bn=wage_sales_build,
                          property_tax_capacity_bn=property_tax,
                          property_tax_capacity_range_bn=(property_low, property_high),
                          renewable_corporate_income_tax_at_2025_prices_bn=a2025["cit_bn"],
                          statutory_transport_taxes_and_road_charges_bn=a2025["fuel_tax_bn"],
                          retained_petroleum_government_revenue_bn=retained_petroleum_gov,
                          stable_price_fiscal_capacity_steady_bn=stable_total_steady,
                          stable_price_fiscal_capacity_build_phase_bn=stable_total_build,
                          retained_petroleum_plus_statutory_transport_baseline_bn=benchmark_statutory,
                          incremental_tax_capacity_above_baseline_bn=stable_total_steady - benchmark_statutory,
                          full_petroleum_sector_upper_sensitivity_bn=full_petroleum_upper),
        crude_redirection=dict(domestic_crude_redirected_mbd=domestic_crude_mbd,
                               existing_crude_exports_mbd=E.OIL_EXPORTS_2025["crude_mbd"],
                               existing_crude_export_value_bn=E.OIL_EXPORTS_2025["crude_value_bn"],
                               gross_added_export_value_bn=extra_export_value,
                               gross_crude_export_value_if_redirected_bn=E.OIL_EXPORTS_2025["crude_value_bn"] + extra_export_value),
    )
