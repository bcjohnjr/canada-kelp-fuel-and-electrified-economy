"""Write one Source Data workbook per figure (outputs/source_data/Source_Data_FigN.xlsx).

Each workbook has one sheet per panel holding the exact values plotted, as recorded by the figure scripts.
"""
import json
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

D = Path(__file__).resolve().parent / "outputs" / "source_data"


def main():
    for f in sorted(D.glob("*Fig*.json")):
        data = json.load(open(f))
        wb = Workbook(); wb.remove(wb.active)
        for panel, tab in data.items():
            ws = wb.create_sheet(panel[:31])
            r0 = 1
            if tab.get("note"):
                ws.cell(1, 1, tab["note"]).font = Font(italic=True); r0 = 3
            for j, c in enumerate(tab["columns"], 1):
                ws.cell(r0, j, c).font = Font(bold=True)
            for i, row in enumerate(tab["rows"], r0 + 1):
                for j, v in enumerate(row, 1):
                    ws.cell(i, j, v)
            for j, c in enumerate(tab["columns"], 1):
                ws.column_dimensions[ws.cell(r0, j).column_letter].width = max(12, min(48, len(str(c)) + 2))
        out = D / f"Source_Data_{f.stem}.xlsx"
        wb.save(out); print("wrote", out.name)

    # Employment/fiscal screening source data are not plotted but are supplied as a reviewer-auditable workbook.
    ef = D.parent / "employment_fiscal.json"
    if ef.exists():
        data = json.load(open(ef))
        wb = Workbook(); ws = wb.active; ws.title = "Results"
        ws.append(["Metric", "Value", "Units / note"])
        tc = data["tax_channels"]; em = data["employment"]; cb = data["cost_base"]
        rows = [
            ("Mature annual system cost", cb["objective_bn"], "CAD bn/a"),
            ("Ongoing gross jobs supported", em["ongoing_jobs"], "jobs"),
            ("Average annual build job-years", em["average_build_jobs"], "job-years/a"),
            ("Personal income tax, steady state", tc["personal_income_tax_steady_bn"], "CAD bn/a"),
            ("Wage-induced general sales tax, steady state", tc["wage_induced_sales_tax_steady_bn"], "CAD bn/a"),
            ("Property-tax capacity", tc["property_tax_capacity_bn"], "CAD bn/a; screening capacity"),
            ("Renewable corporate income tax at 2025-equivalent prices", tc["renewable_corporate_income_tax_at_2025_prices_bn"], "CAD bn/a"),
            ("Statutory transport taxes and road charges", tc["statutory_transport_taxes_and_road_charges_bn"], "CAD bn/a"),
            ("Retained upstream petroleum government revenue", tc["retained_petroleum_government_revenue_bn"], "CAD bn/a"),
            ("Retained upstream + transport-tax baseline", tc["retained_petroleum_plus_statutory_transport_baseline_bn"], "CAD bn/a"),
            ("Incremental screened tax capacity above baseline", tc["incremental_tax_capacity_above_baseline_bn"], "CAD bn/a"),
            ("Gross fiscal capacity, steady state", tc["stable_price_fiscal_capacity_steady_bn"], "CAD bn/a"),
            ("Gross fiscal capacity, build phase", tc["stable_price_fiscal_capacity_build_phase_bn"], "CAD bn/a"),
            ("Full-petroleum-sector upper sensitivity", tc["full_petroleum_sector_upper_sensitivity_bn"], "CAD bn/a; only if refining revenue is retained"),
        ]
        for r in rows: ws.append(list(r))
        for c in ws[1]: c.font = Font(bold=True)
        nb = D.parent / "jobs_fiscal_balance.json"
        if nb.exists():
            jb = json.load(open(nb))
            ws2 = wb.create_sheet("Net_balance")
            ws2.append(["Metric", "A: refining capacity maintained", "B: domestic-serving refining closes", "Units / note"])
            A, B = jb["cases"]["A_capacity_maintained"], jb["cases"]["B_domestic_refining_closes"]
            sA, sB = jb["sensitivity"]["A_capacity_maintained"], jb["sensitivity"]["B_domestic_refining_closes"]
            for lab, key, unit in (("Ongoing jobs created", "jobs_created_ongoing", "jobs"),
                                   ("Average build jobs created, 2027-2050", "jobs_created_build_average", "job-years/a"),
                                   ("Jobs displaced (station fuel work; refining in B)", "jobs_displaced", "jobs"),
                                   ("Net ongoing jobs", "net_jobs_ongoing", "jobs"),
                                   ("Net jobs during build", "net_jobs_during_build", "jobs"),
                                   ("New tax revenue", "new_tax_revenue_bn", "CAD bn/a"),
                                   ("Revenue lost", "revenue_lost_bn", "CAD bn/a"),
                                   ("Net public revenue, steady state", "net_public_revenue_bn", "CAD bn/a"),
                                   ("Net public revenue, build phase", "net_public_revenue_build_phase_bn", "CAD bn/a"),
                                   ("Public revenue today (petroleum + statutory transport taxes)", "public_revenue_status_quo_bn", "CAD bn/a"),
                                   ("Public revenue after transition", "public_revenue_after_bn", "CAD bn/a"),
                                   ("Petroleum royalties and land sales retained", "petroleum_royalties_land_retained_bn", "CAD bn/a; production unchanged")):
                ws2.append([lab, A[key], B[key], unit])
            ws2.append(["Net ongoing jobs, low", sA["net_jobs_ongoing_range"][0], sB["net_jobs_ongoing_range"][0], "joint extremes of all ranges"])
            ws2.append(["Net ongoing jobs, high", sA["net_jobs_ongoing_range"][1], sB["net_jobs_ongoing_range"][1], "joint extremes of all ranges"])
            ws2.append(["Net public revenue, low", sA["net_public_revenue_range_bn"][0], sB["net_public_revenue_range_bn"][0], "CAD bn/a"])
            ws2.append(["Net public revenue, high", sA["net_public_revenue_range_bn"][1], sB["net_public_revenue_range_bn"][1], "CAD bn/a"])
            ws3 = wb.create_sheet("Alberta")
            ws3.append(["Metric", "A: refining capacity maintained", "B: domestic-serving refining closes", "Units / note"])
            a_, b_ = A["alberta"], B["alberta"]
            ws3.append(["Change in royalty base", a_["royalty_base_change_bn"], b_["royalty_base_change_bn"], "CAD bn/a; production unchanged"])
            ws3.append(["Bitumen royalties, Budget 2026-27", a_["bitumen_royalties_budget_2026_27_bn"], b_["bitumen_royalties_budget_2026_27_bn"], "CAD bn/a; retained"])
            ws3.append(["Alberta equivalent fuel-tax or road-use revenue at the statutory 13 c/L", a_["fuel_tax_retained_bn"], b_["fuel_tax_retained_bn"], "CAD bn/a"])
            for lab, key in (("New ongoing jobs", "new_ongoing_jobs_range"), ("New build jobs", "new_build_jobs_range"),
                             ("Net ongoing jobs", "net_ongoing_jobs_range"), ("Net jobs during build", "net_jobs_during_build_range")):
                ws3.append([lab + ", low", a_[key][0], b_[key][0], "population share"])
                ws3.append([lab + ", high", a_[key][1], b_[key][1], "share of planned renewable additions"])
            ws3.append(["Jobs displaced", a_["jobs_displaced"], b_["jobs_displaced"], "jobs"])
            for w in (ws2, ws3):
                for c in w[1]: c.font = Font(bold=True)
        out = D / "Source_Data_Employment_Fiscal.xlsx"; wb.save(out); print("wrote", out.name)

    gh = D.parent / "grid_harvester.json"
    if gh.exists():
        data = json.load(open(gh))
        wb = Workbook(); ws = wb.active; ws.title = "Turning"
        ws.append(["Metric", "Value"]);
        for k,v in data["turning"].items(): ws.append([k,v])
        ws2 = wb.create_sheet("Energy"); ws2.append(["Dry solids fraction", "Grid energy (MJ/cycle)", "Conventional (MJ/cycle)", "Reduction (%)", "Advantage ratio"])
        for r in data["energy"]["rows"]:
            ws2.append([r["dry_solids_fraction"], r["grid_total_mj"], r["conventional_total_mj"], r["energy_reduction_pct"], r["conventional_to_grid_ratio"]])
        for wsx in (ws,ws2):
            for c in wsx[1]: c.font = Font(bold=True)
        for name in ("Source_Data_Fig3.xlsx", "Source_Data_Grid_Harvester.xlsx"):
            out = D / name; wb.save(out); print("wrote", out.name)


if __name__ == "__main__":
    main()
