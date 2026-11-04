"""Builds the manuscript, Supplementary Information and cover letter (DOCX) from the model outputs."""
import csv
import json
from collections import defaultdict
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
FIG = HERE / "article_figures"
OLD = HERE / "paper_figures"
ILL = HERE / "illustrations"
DOC = HERE.parent / "documents"; DOC.mkdir(exist_ok=True)

R = json.load(open(OUT / "central_smr.json"))
N = json.load(open(OUT / "central_no_smr.json"))
RES = json.load(open(OUT / "results.json"))
SC = json.load(open(OUT / "smr_scenarios.json"))
SM = json.load(open(OUT / "smr_canada_summary.json"))
CP = json.load(open(OUT / "coproduction.json"))
MC = json.load(open(OUT / "monte_carlo_summary.json"))
TR = json.load(open(OUT / "transition.json"))["summary"]
EM = json.load(open(OUT / "national_emissions.json"))
AD = json.load(open(OUT / "adequacy_stress.json"))
YT = json.load(open(OUT / "yield_taxonomy.json"))
ITCR = json.load(open(OUT / "central_smr_itc_extended.json"))
SENS = defaultdict(dict)
for r in csv.DictReader(open(OUT / "smr_site_sensitivity.csv")):
    SENS[r["case"]][r["site"]] = float(r["npv_cad_bn"])
ROW = {r["case"]: r for r in SC["rows"]}
_mc = [float(r["cost_bn"]) for r in csv.DictReader(open(OUT / "monte_carlo.csv")) if r.get("infeasible", "False") in ("False", "0", "")]
MCMIN, MCMAX = min(_mc), max(_mc)
FLEET = ["ON_CHATHAM", "SK_BELLE_PLAINE", "AB_HEARTLAND", "NB_SAINT_JOHN", "NS_POINT_TUPPER"]
fleet_npv = lambda case: sum(SENS[case][s] for s in FLEET)


def f(x, d=1):
    return f"{x:,.{d}f}".replace("-", "−")


# ------------------------------------------------------------------ key numbers
dem = R["demand_twh"]; gen = R["generation_twh"]; cap = R["capacity_gw"]; fu = R["fuels_twh"]
kz = R["kelp_by_zone_km2"]; pac = sum(v for k, v in kz.items() if k.startswith("pac")); atl = sum(v for k, v in kz.items() if k.startswith("atl"))
hp = R["heat_by_pool_twh_th"]; hpi = ITCR["heat_by_pool_twh_th"]
lc = R["lifecycle"]
lcoe0 = R["smr"]["lcoe_cad_mwh"]; lcoe_itc = ITCR["smr"]["lcoe_cad_mwh"]
steam_cost = 0.19 * lcoe0 + 8.0
b0 = ROW["No SMR (wind, solar and hydro only)"]["total_cost_bn"]
INT = SC["integer"]; BE = SC["breakeven_capex_bn"]
sw = {(w["itc"], w["capex_bn"]): w for w in SC["sweep"]}
fr = {(x["region"], x["smr"]): x for x in SC["forced"]}
fl = SM["fleet_2041"]
gh = CP["grid_harvester"]; sh = CP["shellfish"]; sa = CP["salmon"]; dr = CP["drones"]
shs = lambda k: sh["pac"][k] + sh["atl"][k]
kelp_be = {k["site"]: k for k in SM["kelp"] if k["valuation"] == "system_shadow_2041"}
bcr = ROW["BC fleet allowed (SMR steam for Pacific refineries), ITC extended"]; itcr = ROW["ITC extended beyond 2034 (15%)"]
uses_vr = R["electricity_vehicles_rail_twh"]; uses_ef = R["electricity_for_efuels_twh"]
uses_ref = R["electricity_refineries_twh"] + R["electricity_for_heat_storage_twh"]
heat_total = sum(sum(v.values()) for v in hp.values())
ATLF = ["NS_POINT_TUPPER", "NB_SAINT_JOHN", "ON_CHATHAM"]
sub_npv = lambda case: sum(SENS[case][s] for s in ATLF)
yt = {(y["case"], y["yield_set"].split(" ")[0]): y for y in YT}
ad = AD["design"]; aw = AD["worst"]
AI = {c["days"] * 100 + int(c["wind_cf"] * 100): c for c in AD["integrated"]["cases"]}
ai7, ai14, aiw = AI[710], AI[1410], AI[1405]
cv = lambda c: fleet_npv(c)
pct = lambda a, b: 100 * (a - b) / b
one_atl_steam = INT["itc_extended"]["grid"][4]["steam_atl"] if INT["itc_extended"]["grid"][4]["atl"] == 1 else 1.58

TITLE = "Where nuclear heat pays when all Canadian transport fuel is replaced with electricity, biofuels and two-coast kelp"
AUTHORS = "Jonathan Karl Bily¹*, Christoph Pahl² and Patricia Valdés Bacallao³"
AFFIL = ("¹Independent researcher, Zaragoza, Spain. ²Technical University of Munich and Max Planck Institute for Physics, Munich, Germany. "
         "³University of Málaga, Málaga, Spain. *e-mail: jonathan@cloudwashlaundry.com; ORCID 0009-0004-3526-7271")

ABSTRACT = (
    f"Canada sold {f(R['demand_total_twh'], 0)} TWh of fossil transport fuel in 2025. We replace all of it in a least-cost model with "
    "electrification, biofuels, electrofuels and kelp on both coasts, and test small modular reactors (SMRs) whose steam heats nearby "
    f"refineries and distilleries. With assumed technology learning the annual-balance system costs CAD {f(R['total_cost_bn'], 1)} billion a year, "
    f"or {f(ai7['total_cost_bn'], 1)} billion with a renewable-methane reserve for a seven-day winter lull, against {f(R['fossil_cost_bn']['avg2025'], 1)} "
    f"billion for fossil fuel at 2025 prices; the two solutions cut well-to-wheel emissions by {f(lc['reduction_pct'], 1)}% and "
    f"{f(ai7['reduction_pct'], 1)}%. Once new sites carry their own "
    "infrastructure, no reactor enters the fossil-free system unless modules cost below about CAD 2.6–2.9 billion, and of five Trans-Canada "
    "Highway sites only Point Tupper, Nova Scotia, is marginally positive during the transition. British Columbia refines kelp with wind and "
    "solar, and Hudson Bay kelp does not pay.")


REFS = [
    "Statistics Canada. End use of refined petroleum products, 2025. The Daily (27 October 2026).",
    "Environment and Climate Change Canada. Greenhouse Gas Sources and Sinks in Canada: Executive Summary 2026 (2026).",
    "Davis, S. J. et al. Net-zero emissions energy systems. Science 360, eaas9793 (2018).",
    "Sepulveda, N. A., Jenkins, J. D., de Sisternes, F. J. & Lester, R. K. The role of firm low-carbon electricity resources in deep decarbonization of power generation. Joule 2, 2403–2420 (2018).",
    "Ruth, M. F. et al. Nuclear-renewable hybrid energy systems: opportunities, interconnections, and needs. Energy Convers. Manag. 78, 684–694 (2014).",
    "Bragg-Sitton, S. M. et al. Reimagining future energy systems: overview of the US program to maximize energy utilization via integrated nuclear-renewable energy systems. Int. J. Energy Res. 44, 8156–8169 (2020).",
    "Ontario Power Generation. Darlington New Nuclear Project: small modular reactors (2025). https://www.opg.com/projects-services/projects/nuclear/smr/darlington-smr/",
    "Canadian Nuclear Safety Commission. Commission authorizes Ontario Power Generation Inc. to construct 1 BWRX-300 reactor at the Darlington New Nuclear Project site (4 April 2025).",
    "American Nuclear Society. Saskatchewan expands its nuclear plans. Nuclear Newswire (30 January 2026).",
    "World Nuclear News. Saskatchewan SMR to be located in Estevan (2024).",
    "Government of Nova Scotia. Nova Scotia–Ontario memorandum of understanding on small modular reactors (23 October 2025).",
    "The Globe and Mail. Alberta to consult public about nuclear power, premier says (7 July 2025).",
    "Reuters. Conservative party wins first election in nearly a century in British Columbia (25 October 2026).",
    "GE Vernova Hitachi Nuclear Energy. BWRX-300 small modular reactor (2026).",
    "Income Tax Act (Canada), s. 127.491, clean electricity investment tax credit: 15% for eligible property available for use before 2035 (Budget 2024 implementation; Budget 2025 extended eligibility to provincial Crown corporations).",
    "GLJ Ltd. Canada’s carbon pricing reset: a new trajectory and 2040 outlook (28 May 2026).",
    "Environment and Climate Change Canada. Emission factors and reference values. Federal Greenhouse Gas Offset System (2026).",
    "Renewable Fuels Association. Energy balance of US corn ethanol, using Argonne GREET 2022 (2024).",
    "British Columbia Utilities Commission. BCUC accepts BC Hydro 2024 Call for Power electricity purchase agreements (25 August 2025).",
    "National Renewable Energy Laboratory. Annual Technology Baseline 2024: nuclear (2024).",
    "Wargacki, A. J. et al. An engineered microbial platform for direct biofuel production from brown macroalgae. Science 335, 308–313 (2012).",
    "Anastasakis, K. & Ross, A. B. Hydrothermal liquefaction of the brown macro-alga Laminaria saccharina: effect of reaction conditions on product distribution and composition. Bioresour. Technol. 102, 4876–4883 (2011).",
    "Elliott, D. C., Biller, P., Ross, A. B., Schmidt, A. J. & Jones, S. B. Hydrothermal liquefaction of biomass: developments from batch to continuous process. Bioresour. Technol. 178, 147–156 (2015).",
    "Filbee-Dexter, K. et al. Sea ice and substratum shape extensive kelp forests in the Canadian Arctic. Front. Mar. Sci. 9, 754074 (2022).",
    "Kim, J. K., Yarish, C., Hwang, E. K., Park, M. & Kim, Y. Seaweed aquaculture: cultivation technologies, challenges and its ecosystem services. Algae 32, 1–13 (2017).",
    "Froehlich, H. E., Afflerbach, J. C., Frazier, M. & Halpern, B. S. Blue growth potential to mitigate climate change through seaweed offsetting. Curr. Biol. 29, 3087–3093 (2019).",
    "Chopin, T. et al. Integrating seaweeds into marine aquaculture systems: a key toward sustainability. J. Phycol. 37, 975–986 (2001).",
    "Troell, M. et al. Ecological engineering in aquaculture — potential for integrated multi-trophic aquaculture (IMTA) in marine offshore systems. Aquaculture 297, 1–9 (2009).",
    "Fisheries and Oceans Canada. Integrated multi-trophic aquaculture research overview (2025).",
    "Fisheries and Oceans Canada. Transition from open-net pen salmon aquaculture in British Columbia coastal waters by 30 June 2029 (2024).",
    "Arpagaus, C., Bless, F., Uhlmann, M., Schiffmann, J. & Bertsch, S. S. High temperature heat pumps: market overview, state of the art, research status, refrigerants, and application potentials. Energy 152, 985–1010 (2018).",
    "Intergovernmental Panel on Climate Change. Climate Change 2022: Mitigation of Climate Change. Working Group III, Ch. 10 (Cambridge Univ. Press, 2022).",
    "National Renewable Energy Laboratory. Life Cycle Greenhouse Gas Emissions from Electricity Generation: Update (2021).",
    "International Civil Aviation Organization. CORSIA Default Life Cycle Emissions Values for CORSIA Eligible Fuels (2024).",
    "Environment and Climate Change Canada. EOLakeWatch: Lake Winnipeg 2022 Annual Algal Bloom Summary Report (2023).",
    "Manitoba Environment and Climate. Nutrient Targets for Lake Winnipeg and Its Tributaries: proposed regulation under The Water Protection Act (2020).",
    "Bily, J. K., Pahl, C. & Valdés Bacallao, P. Energy supply costs of a constrained fossil fuel phase out in Spanish transport. SSRN preprint, https://doi.org/10.2139/ssrn.7648876 (2026).",
    "Natural Resources Canada. Comprehensive Energy Use Database: Transportation Sector, Canada, Table 1, 2000–2023 (2025).",
    "Canada Energy Regulator. Canada’s Energy Future 2026 (2026).",
    "Statistics Canada. Motor vehicle fuel sales, 2025. The Daily (2 October 2026).",
    "Gough, W. A., Cornwell, A. R. & Tsuji, L. J. S. Trends in seasonal sea ice duration in southwestern Hudson Bay. Arctic 57, 299–305 (2004).",
    "Huangfu, Q. & Hall, J. A. J. Parallelizing the dual revised simplex method. Math. Program. Comput. 10, 119–142 (2018).",
    "Benden, P. Global Shipping Lanes v1 (CC BY 4.0) (2022).",
    "Environment and Climate Change Canada. Canadian Environmental Sustainability Indicators: Canada’s Conserved Areas (2026).",
    "Bak, U. G., Mols-Mortensen, A. & Gregersen, O. Production method and cost of commercial-scale offshore cultivation of kelp in the Faroe Islands using multiple partial harvesting. Algal Res. 33, 36–47 (2018).",
    "Greene, J. M., Gulden, J., Wood, G., Huesemann, M. & Quinn, J. C. Techno-economic analysis and global warming potential of a novel offshore macroalgae biorefinery. Algal Res. 51, 102032 (2020).",
]


# ------------------------------------------------------------------ docx helpers
def base_doc(size=11, spacing=1.5):
    d = Document()
    st = d.styles["Normal"]; st.font.name = "Times New Roman"; st.font.size = Pt(size)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    st.paragraph_format.line_spacing = spacing
    for s in d.sections:
        s.left_margin = s.right_margin = Inches(1); s.top_margin = s.bottom_margin = Inches(1)
    return d


def line_numbers(d):
    for s in d.sections:
        ln = OxmlElement("w:lnNumType"); ln.set(qn("w:countBy"), "1"); ln.set(qn("w:restart"), "continuous")
        s._sectPr.append(ln)


def page_numbers(d):
    for s in d.sections:
        p = s.footer.paragraphs[0]; p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run(); fc = OxmlElement("w:fldChar"); fc.set(qn("w:fldCharType"), "begin"); r._r.append(fc)
        it = OxmlElement("w:instrText"); it.text = "PAGE"; r._r.append(it)
        fc2 = OxmlElement("w:fldChar"); fc2.set(qn("w:fldCharType"), "end"); r._r.append(fc2)


def para(d, text, bold=False, italic=False, size=None, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space=6, spacing=None):
    p = d.add_paragraph(); p.alignment = align; p.paragraph_format.space_after = Pt(space)
    if spacing: p.paragraph_format.line_spacing = spacing
    # simple superscript citation markup: text^{1,2}
    parts = text.split("^{")
    r = p.add_run(parts[0]); r.bold = bold; r.italic = italic
    if size: r.font.size = Pt(size)
    for part in parts[1:]:
        sup, rest = part.split("}", 1)
        rs = p.add_run(sup); rs.font.superscript = True; rs.bold = bold
        if size: rs.font.size = Pt(size)
        rr = p.add_run(rest); rr.bold = bold; rr.italic = italic
        if size: rr.font.size = Pt(size)
    return p


def heading(d, text, level=1):
    p = d.add_paragraph(); p.paragraph_format.space_before = Pt(10); p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text); r.bold = True; r.font.size = Pt(13 if level == 1 else 11.5)
    if level == 2: r.italic = True
    return p


def set_shade(cell, hex_):
    tcPr = cell._tc.get_or_add_tcPr(); s = OxmlElement("w:shd")
    s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hex_); tcPr.append(s)


def table(d, header, rows, caption, size=8):
    para(d, caption, bold=True, size=9.5, align=WD_ALIGN_PARAGRAPH.LEFT, spacing=1.0)
    t = d.add_table(rows=1, cols=len(header)); t.style = "Table Grid"
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(size); set_shade(c, "E8EEF3")
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""; p = cells[i].paragraphs[0]; p.paragraph_format.line_spacing = 1.0
            r = p.add_run(str(v)); r.font.size = Pt(size)
    d.add_paragraph()


def figure(d, path, caption, width=6.5):
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width))
    para(d, caption, size=9.5, spacing=1.0)



def results_text():
    s = {}
    s["intro"] = [
        "Transport is Canada’s second-largest source of greenhouse gases^{2}, and its fuel serves more uses than one technology can: cars, "
        "long-haul trucks on the 7,821-km Trans-Canada Highway, railways, tractors and mine haulers, international flights and ships. In 2025 "
        f"these segments used {f(R['demand_total_twh'], 0)} TWh of gasoline, diesel, jet and marine fuel^{{1,38,40}}. Net-zero studies pair "
        "electrification with low-carbon fuels and firm low-carbon power or heat^{3,4,32}, but national studies seldom replace every segment "
        "in one optimization, and seldom ask where nuclear heat, rather than nuclear electricity, earns its place^{5,6}.",
        "Canada is testing that question. Ontario is building the first BWRX-300 small modular reactor (SMR) at Darlington^{7,8,14}; Saskatchewan "
        "has chosen an Estevan site^{9,10}; Nova Scotia lifted its ban on utility nuclear power^{11}; Alberta is consulting^{12}; and British "
        "Columbia held a provincial election in October 2026, with final counting due on 6–10 November^{13}. Canada also has large native kelp resources from the Pacific to Hudson Bay^{24}, "
        "which no one yet farms for fuel at scale^{25,26}. A companion study for Spain coupled kelp fuels with nuclear retention and solar heat^{37}.",
        "Here we add SMR fleets to a national annual linear programme of Canadian transport energy. Steam cannot travel far, so refinery heat "
        "is balanced in four regional pools, and steam reaches only refineries and distilleries built beside a module. We report whole-module "
        "results, apply the clean electricity tax credit only where current law allows, charge every new reactor site for its common "
        "infrastructure and heat pipelines, test each Trans-Canada Highway site during the transition, force kelp into the Gulf of St Lawrence, Labrador and Hudson Bay, stress the system with winter low-wind periods, and "
        "add a winter renewable-methane reserve to the optimization, and account for the Grid Harvesters, shellfish, salmon and utility "
        "drones that can share the kelp farms.",
    ]
    s["r1"] = [
        f"The least-cost 2050 system replaces all {f(R['demand_total_twh'], 0)} TWh in the annual energy balance (Fig. 2a). Light vehicles become "
        f"battery-electric, as do {f(R['end_use_twh']['hdv|bet'], 0)} TWh of the {f(dem['hdv'], 0)} TWh used by trucks and buses; catenary on the whole "
        f"Trans-Canada Highway replaces another {f(R['ers']['used_twh_diesel'], 1)} TWh of truck diesel. Farm, mining and construction machinery use "
        f"electric drive ({f(sum(v['el'] for v in R['offroad_twh'].values()), 1)} TWh) and drop-in diesel ({f(sum(v['liq'] for v in R['offroad_twh'].values()), 1)} TWh); "
        f"aviation, including international flights, uses {f(dem['aviation'], 1)} TWh of renewable jet fuel; ships use methanol. Liquid and gaseous "
        f"fuels total {f(sum(fu.values()), 0)} TWh (Fig. 2b): residues {f(fu['forest_residue_HTL'] + fu['agri_residue_FT'], 0)}, wind electrofuels "
        f"{f(fu['eFT_liquids'], 0)} from {f(R['electrolyser_gw'], 1)} GW of electrolysers, kelp {f(R['kelp_fuel_twh'], 1)} (of which {f(R['kelp_jet_twh'], 1)} jet), "
        f"lipids, canola and biomethane {f(fu['HEFA_waste_lipids'] + fu['canola_HVO'] + fu['waste_biomethane'], 0)}, grain ethanol {f(fu['grain_ethanol_existing'], 0)} "
        f"and lake biomass {f(R['lake_fuel_twh'], 1)} TWh. Kelp grows on {f(R['kelp_total_km2'], 0)} km² — {f(pac, 0)} off British Columbia and "
        f"{f(atl, 0)} off Atlantic Canada — giving {f(R['kelp_dry_mt'], 1)} Mt of dry biomass. New electricity is {f(R['electricity_delivered_twh'], 0)} TWh: "
        f"{f(gen['Onshore wind'], 0)} from {f(cap['Onshore wind'], 1)} GW of wind and {f(gen['PV'], 0)} from {f(cap['PV'], 1)} GW of solar.",
        f"The system costs CAD {f(R['total_cost_bn'], 2)} billion a year in the annual balance, including CAD {f(R['vehicle_premium_bn'], 1)} billion of vehicle premia, "
        f"and CAD {f(ai7['total_cost_bn'], 2)} billion with the winter reserve described below. This is a "
        "technology-learning scenario, not a forecast: it assumes 4% real finance and learning in kelp farming, conversion and electrofuels "
        f"(Supplementary Table 1). The same fossil fuel cost CAD {f(R['fossil_cost_bn']['avg2025'], 1)} billion at 2025 average prices, "
        f"{f(pct(R['total_cost_bn'], R['fossil_cost_bn']['avg2025']), 1)}% less than the system, and CAD {f(R['fossil_cost_bn']['oct2026'], 1)} billion at "
        f"October 2026 prices. At today’s technology costs and 7% finance the system costs CAD {f(RES['today']['total_cost_bn'], 1)} billion and uses no kelp. "
        f"Kelp yields matter: at demonstrated commercial yields^{{45}} the model uses no kelp and costs CAD {f(yt[('central', 'demonstrated')]['cost_bn'], 1)} billion; "
        f"at design yields of 8 and 6 t ha⁻¹ yr⁻¹ it uses {f(yt[('central', 'design')]['kelp_km2'], 0)} km² for CAD {f(yt[('central', 'design')]['cost_bn'], 1)} billion; "
        f"the central case uses learning-target yields of 12 and 9 t ha⁻¹ yr⁻¹, within the range of fuel-oriented designs^{{46}}. Well-to-wheel emissions fall "
        f"from {f(lc['fossil_wtw_mtco2e'], 0)} to {f(lc['lowcarbon_wtw_mtco2e'], 1)} Mt CO₂e a year ({f(lc['reduction_pct'], 1)}%; "
        f"{f(lc['reduction_factor_sensitivity_pct'][0], 1)}–{f(lc['reduction_factor_sensitivity_pct'][1], 1)}% across emission factors).",
    ]
    s["r2"] = [
        f"Refineries and distilleries need {f(heat_total, 1)} TWh of process heat. Without reactors, heat pumps supply the 60% their temperature lift "
        "allows^{31} and wind-charged thermal storage the rest (Fig. 3a). A module’s 150 °C steam costs 0.19 MWh of forgone electricity plus delivery, "
        f"CAD {f(steam_cost, 0)} per MWh at CAD {f(lcoe0, 0)} per MWh of SMR electricity — cheaper than storage heat, but every module also makes "
        "electricity dearer than firm wind. The CAD 4.4 billion module cost comes from the later Darlington units and excludes the CAD 1.6 billion "
        "of common site infrastructure in that budget^{7}, so each new site of up to two modules is charged CAD 1.6 billion (0.8–2.4 tested). The clean "
        "electricity tax credit covers only property in service before 2035^{15}, so modules in a 2050 system get none.",
        "On that basis the model builds no reactors, and it builds none even with the credit extended. Without site costs and with the credit, the "
        f"continuous solution would build {f(INT['itc_extended']['relaxed_atl'], 1)} Atlantic and {f(INT['itc_extended']['relaxed_inl'], 1)} inland modules and the "
        f"best whole fleet would be one Atlantic module saving CAD {f(INT['itc_extended_no_site_cost']['saving_best_bn'] * 1000, 0)} million a year (Fig. 4a). "
        f"With site costs, one Atlantic module beside kelp refineries breaks even at CAD {f(BE['one_atlantic_module'], 2)} billion of module capital, and "
        f"two modules sharing one site at {f(BE['two_atlantic_modules'], 2)} ({f(BE['two_atlantic_modules_itc'], 2)} with the credit), against CAD 4.4 billion "
        f"today. At CAD 3.5 billion with the credit, two Atlantic modules on one site save CAD {f(INT['capex_3p5_itc']['saving_best_bn'] * 1000, 0)} million "
        f"a year, or {f(INT['capex_3p5_itc_site_0p8']['saving_best_bn'] * 1000, 0)} million if the site costs CAD 0.8 billion. Inland steam is limited by geography: "
        "only distilleries beside a candidate site — about a quarter of Canadian ethanol capacity — can take it. Larger fleets cost more: ten forced "
        f"modules on five sites add CAD {f(ROW['Forced fleet 10 modules (4 Atlantic, 6 inland)']['delta_with_sites_bn'], 2)} billion a year and forty "
        f"{f(ROW['Forced fleet 40 modules (10 Atlantic, 30 inland)']['delta_with_sites_bn'], 2)}; they break even at CAD {f(BE['10_modules'], 2)} and "
        f"{f(BE['40_modules'], 2)} billion per module.",
    ]
    s["r3"] = [
        "During the transition the provinces with nuclear programmes still burn gas for power and steam. We screen five two-module sites on or near "
        "the Trans-Canada Highway (Supplementary Table 8), each with named or proposed heat users, pipe lengths and load factors: Chatham-Kent "
        "(ethanol distillery and a new greenhouse and drying cluster), Belle Plaine (ethanol and potash steam), the Alberta Industrial Heartland "
        "(process steam), East Saint John (refinery steam and a kelp refinery) and Point Tupper (paper-mill steam and a kelp refinery) (Fig. 3b). "
        "Greenhouse heat is sold only 45% of the time. Staged from 2034 to 2038, the ten modules deliver "
        f"{f(fl['electricity_twh'], 1)} TWh of electricity and {f(fl['heat_twh'], 1)} TWh of heat in 2041 and avoid {f(fl['co2_avoided_mt'], 1)} Mt CO₂ a year; "
        f"their 150 °C steam could distil {f(fl['ethanol_bl'], 2)} billion litres of ethanol for E85 and ED95, which needs new distilling capacity beside the modules.",
        "With CAD 1.6 billion of common infrastructure per site, steam pipelines, the tax credit only for the 2034 Chatham-Kent units and a capacity "
        f"value of CAD 120 per kW-year (close to the cost of a new peaking turbine), the fleet’s net present value is CAD {f(cv('central'), 1)} billion (Fig. 4b). "
        f"Only Point Tupper is positive ({f(SENS['central']['NS_POINT_TUPPER'], 2)}); Saint John is {f(SENS['central']['NB_SAINT_JOHN'], 2)}, Chatham-Kent "
        f"{f(SENS['central']['ON_CHATHAM'], 1)}, Belle Plaine {f(SENS['central']['SK_BELLE_PLAINE'], 1)} and the Heartland {f(SENS['central']['AB_HEARTLAND'], 1)}. "
        f"Site infrastructure decides the sign: without it the fleet is worth {f(cv('no_common_infrastructure'), 1)} and the three eastern sites "
        f"{f(sub_npv('no_common_infrastructure'), 1)}; at CAD 0.8 billion per site the fleet is worth {f(cv('common_infrastructure_low_0p8'), 1)}, at 2.4 billion "
        f"{f(cv('common_infrastructure_high_2p4'), 1)}. Capacity payments of CAD 90, 60 and 0 per kW-year give {f(cv('capacity_value_90'), 1)}, "
        f"{f(cv('capacity_value_60'), 1)} and {f(cv('capacity_value_0'), 1)}; 75% of the carbon-price value gives {f(cv('carbon_realisation_75'), 1)}, and a grid that "
        f"is fossil-free from 2045 gives {f(cv('grid_fossil_free_2045'), 1)}. Point Tupper, Saint John and Chatham-Kent break even at CAD "
        f"{f(SM['breakeven_capex_cad_bn_per_module']['NS_POINT_TUPPER'], 1)}, {f(SM['breakeven_capex_cad_bn_per_module']['NB_SAINT_JOHN'], 1)} and "
        f"{f(SM['breakeven_capex_cad_bn_per_module']['ON_CHATHAM'], 1)} billion per module; with CAD 3.5 billion modules and CAD 0.8 billion sites the three "
        f"are worth {f(sub_npv('capex_3p5_common_low'), 1)} billion and the fleet {f(cv('capex_3p5_common_low'), 1)}.",
    ]
    s["r4"] = [
        f"British Columbia refines its {f(pac, 0)} km² of kelp with heat pumps and wind-charged storage. Allowing a British Columbia fleet with the credit "
        f"extended moves kelp to the Pacific ({f(bcr['kelp_pacific_km2'], 0)} km²) and saves a further CAD {f((itcr['total_cost_bn'] - bcr['total_cost_bn']) * 1000, 0)} "
        "million a year, about 0.04% of system cost, so wind and solar refining is as cheap for practical purposes; the province’s recent clean-power "
        "procurement averaged CAD 74 per MWh^{19}. Forcing 2,000 km² of kelp elsewhere raises cost by CAD "
        f"{f(fr[('gsl', 'no SMR')]['extra_cost_bn'], 2)} billion a year in the Gulf of St Lawrence, {f(fr[('lab', 'no SMR')]['extra_cost_bn'], 2)} off Labrador "
        f"and {f(fr[('hb', 'no SMR')]['extra_cost_bn'], 2)} in Hudson Bay (Fig. 5a), where seasonal ice^{{41}} limits growth to about two-fifths of the Atlantic "
        f"yield. Even a Hudson Bay module at CAD 3.5 billion with the credit leaves the cost at {f(fr[('hb', 'SMR CAD 3.5 bn with ITC, Hudson Bay fleet allowed')]['extra_cost_bn'], 2)}: "
        "a dry tonne needs 0.57 MWh of heat and 0.33 MWh of electricity, worth about CAD 70, while Hudson Bay biomass costs CAD 2,200 per tonne against "
        f"a break-even of CAD {f(kelp_be['MB_CHURCHILL']['breakeven_biomass_cad_t'], 0)} (Fig. 5b). Atlantic biomass at CAD 500 is near its break-even "
        f"(CAD {f(kelp_be['NS_POINT_TUPPER']['breakeven_biomass_cad_t'], 0)}).",
    ]
    s["r5"] = [
        "The model balances energy over a year, so we test cold, low-wind periods of 3 to 14 days in which electrolysers, air capture and heat "
        "storage stop and vehicle demand rises by a quarter (Fig. 7a). In a seven-day lull at 10% wind capacity factor with 10% of weekly hydro "
        f"output reshaped from exports, vehicles, rail and refineries lack {f(ai7['turbine_gw'], 1)} GW at peak. We add this backup to the optimization: "
        f"{f(ai7['turbine_gw'], 1)} GW of turbines and a {f(ai7['methane_reserve_twh'], 1)} TWh reserve of renewable methane that the model must produce and "
        f"store each year. Re-optimized, the system costs CAD {f(ai7['total_cost_bn'], 2)} billion, {f(ai7['extra_vs_annual_bn'], 2)} billion "
        f"({f(ai7['extra_pct'], 1)}%) more than the annual balance; the extra methane comes from waste biomethane, kelp digestion and a rearranged fuel mix "
        f"(Fig. 7b). The reserve changes the solution as well as its cost: kelp grows on {f(ai7['kelp_km2'], 0)} km² instead of "
        f"{f(R['kelp_total_km2'], 0)} km² ({f(ai7['kelp_dry_mt'], 1)} instead of {f(R['kelp_dry_mt'], 1)} Mt of dry biomass, because kelp digestion supplies "
        f"reserve methane), new electricity falls from {f(R['electricity_delivered_twh'], 0)} to {f(ai7['electricity_twh'], 0)} TWh, and the well-to-wheel "
        f"reduction is {f(ai7['reduction_pct'], 1)}% instead of {f(lc['reduction_pct'], 1)}%; other figures in this article describe the annual-balance "
        f"solution unless stated (Supplementary Table 10b). A 14-day lull costs {f(ai14['total_cost_bn'], 2)} billion and the worst case tested — 14 days at 5% capacity factor without hydro "
        f"support, {f(aiw['turbine_gw'], 1)} GW and {f(aiw['methane_reserve_twh'], 0)} TWh of methane — {f(aiw['total_cost_bn'], 2)} billion. This is an energy "
        "and cost screen with an optimized fuel reserve, not a chronological dispatch model with network constraints.",
    ]
    s["r6"] = [
        f"The farms are harvested by {f(gh['units'], 0)} cable-guided Grid Harvesters (Supplementary Figs 1–3), whose 33.9 MJ per 14,400 m² cycle against "
        f"90.9 MJ for a conventional harvester cuts fleet harvest energy from {f(gh['conventional_energy_gwh'], 0)} to {f(gh['energy_gwh'], 0)} GWh a year (Fig. 6a); "
        f"lake Grid Harvesters remove {f(R['lake_p_removed_t'], 0)} t of phosphorus a year^{{35,36}}. Mussel and oyster blocks at "
        f"{f(shs('operable_sites'), 0)} sites that pass oxygen and carbonate screens produce {f(shs('mussel_t'), 0)} t and {f(shs('oyster_t'), 0)} t a year, with "
        f"margins of CAD {f(shs('margin_manual_cad_m'), 1)} million manually and {f(shs('margin_robot_shared_lease_cad_m'), 1)} million with shared ROVs and leases (Fig. 6b). "
        f"Salmon pens upstream of kelp and mussels^{{27-29}} — 50,000 t with {sa['robots']:,} utility robots for capture and laser delousing — break even at "
        f"CAD {f(sa['breakeven_price_atlantic_cad_kg'], 2)} per kg in Atlantic pens and CAD {f(sa['breakeven_price_bc_cad_kg']['1.0'], 2)}–{f(sa['breakeven_price_bc_cad_kg']['3.0'], 2)} "
        "in British Columbia closed containment, required there from 30 June 2029^{30} (Fig. 6c). Solar-charged underwater utility drones "
        f"({f(dr['drones'], 0)}, two per km²) cost about {f(100 * dr['annual_cost_cad_m'] / 1e3 / R['cost_items_bn']['Kelp farms and harvest'][0], 1)}% of "
        "kelp-farm cost. These screening accounts are outside the energy cost.",
    ]
    s["r7"] = [
        f"Across 1,000 Monte Carlo draws of the annual-balance model (without the winter reserve) the system cost has a 5th–95th percentile "
        f"interval of CAD {f(MC['cost_p5_p50_p95'][0], 1)}–{f(MC['cost_p5_p50_p95'][2], 1)} billion and a median of CAD {f(MC['cost_p5_p50_p95'][1], 1)} billion "
        f"(full range {f(MCMIN, 1)}–{f(MCMAX, 1)}). All draws beat October 2026 fossil prices, but only {MC['n_breakeven_below_2025_prices']} of 1,000 beat 2025 "
        f"prices. Kelp is the least robust supply: its median area is {f(MC['kelp_km2_p5_p50_p95'][1], 0)} km², because residues and electrofuels replace "
        "it when farming disappoints. Over 2025–2050, with fleet turnover, the system avoids "
        f"{f(TR['avoided_mt']['+ … kelp and electrofuels'], 0)} Mt CO₂e relative to electrification alone; a flexible-fuel vehicle policy would let the "
        f"gasoline fleet take {f(TR['ethanol_cap_2035']['FFV policy'], 0)} TWh of ethanol in 2035 instead of {f(TR['ethanol_cap_2035']['E10 only'], 0)} TWh, "
        "widening the market for E85 distilled with reactor steam.",
    ]
    s["disc"] = [
        "Canada can replace every litre of fossil transport fuel with a system that is mostly wind, solar and biomass and that carries its own "
        f"winter fuel reserve, at CAD {f(ai7['total_cost_bn'], 1)} billion a year against {f(R['fossil_cost_bn']['avg2025'], 1)} billion for fossil fuel at 2025 "
        "prices. That result is conditional on learning in kelp farming, conversion and electrofuels that has not happened yet, and on kelp yields "
        "well above today’s commercial farms. Within it, reactors earn money only through steam kept near its users, and only if a new site costs "
        "much less than Darlington’s common infrastructure suggests or modules fall towards CAD 3 billion. During the transition, the strongest case "
        "is an Atlantic site that sells steam to an existing mill and a kelp refinery while displacing gas; it is marginal and depends on capacity "
        "payments and the full carbon price. This agrees with studies finding that firm low-carbon resources pay most where they supply services "
        "renewables supply poorly^{4,5,6}.",
        "British Columbia does not need reactors to refine kelp, and its nearshore kelp is the cheapest in Canada. Hudson Bay kelp is limited by "
        "growth and ice, not heat. The limits are clear: annual balancing with an optimized winter reserve rather than chronological dispatch, SMR "
        "costs from a single project, site heat users that need confirmation, kelp yields and costs that rest on learning^{21-23,45,46}, and marine "
        "permits, conserved areas^{44} and Indigenous rights holders’ consent that need field work. Within them, the result is a complete fuel system "
        "in which kelp, residues, electrofuels and electricity carry the load, and reactors are an option for heat where a site can be built cheaply.",
    ]
    s["methods"] = [
        ("Model and scope", [
            "The model is an annual linear programme solved with HiGHS^{42} that chooses generation, refinery heat, fuel production, end-use "
            "technologies and kelp, lake and residue supply at least annualized cost. Demand is 2025 end-use sales of gasoline (43.7 GL), diesel "
            "fuel oil (29.4 GL) and aviation turbo fuel (9.2 GL) from Statistics Canada^{1}, with road, rail, marine and off-road splits from fuel-sales and energy-use data^{38,40}, "
            "including international aviation and marine fuel sold in Canada. Costs are 2026 Canadian dollars. Capital is annualized at 4% real in the "
            "central case and 7% in the today case. Kelp is modelled in British Columbia, Atlantic Canada, the Gulf of St Lawrence, Labrador and Hudson "
            "Bay with depth bands, haul distances, shipping lanes and conserved areas from a marine GIS^{43,44}; giant kelp is farmed off British "
            "Columbia and sugar kelp elsewhere^{24,25}. Wet biorefineries convert kelp by hydrothermal liquefaction or ethanol fermentation with "
            "liquefaction of the residue^{21-23}. Demonstrated, design and learning-target yields are compared (Supplementary Table 2). All principal "
            "inputs, with source, date, units, conversion and range, are listed in a machine-readable provenance table (Supplementary Data).",
        ]),
        ("SMR fleets, heat pools and whole modules", [
            "SMRs are BWRX-300-class modules of 300 MWe and 870 MWth^{14} at 90% availability over 40 years, costing CAD 4.4 billion each (Darlington "
            "budget of CAD 20.9 billion for four units^{7}; 3.5 and 6.1 tested), with fixed O&M of CAD 150 per kW-year and variable, fuel and waste costs "
            f"of CAD 15 per MWh^{{20}}, giving CAD {f(lcoe0, 1)} per MWh at 4% without the tax credit and {f(lcoe_itc, 1)} with it. The 15% clean electricity "
            "credit applies to property available for use before 2035^{15}; the 2050 system therefore receives none in the central case. Modules form "
            "an Atlantic fleet (New Brunswick and Nova Scotia, up to 3 GW) and an inland fleet (Ontario, Saskatchewan, Alberta, up to 9 GW); British "
            "Columbia and Hudson Bay fleets are tested separately. Each module sells direct or flexible electricity and up to 200 MWth of 150 °C steam "
            "at 0.19 MWh of forgone electricity per MWh, delivered for CAD 8 per MWh. Heat is balanced in four pools: Pacific kelp refineries; "
            "Atlantic, Gulf and Labrador kelp refineries, built beside the Atlantic modules; inland grain-ethanol distilleries (7.25 MJ per litre^{18}) "
            "and lake refineries; and Hudson Bay refineries. Steam reaches only its own region, and inland steam only the 25% of distilling capacity "
            "beside a candidate site (0–100% tested). Heat pumps (COP 2.5, at most 60% of a pool^{31}), thermal storage and boilers are available in "
            "every pool. The linear programme treats capacity as continuous; whole-module optima are found by enumerating 0–4 Atlantic and 0–3 inland "
            "modules with all other decisions re-optimized.",
        ]),
        ("Site cascade screen", [
            "Each two-module site sells net electricity at the cost of the generator it displaces (combined-cycle gas after the 2030 coal phase-out; "
            "hydro value in British Columbia and Manitoba^{19}) plus a capacity value of CAD 120 per kW-year, near the cost of new entry of a peaking "
            "turbine (CAD 1,400 per kW over 30 years plus fixed O&M, CAD 106–138 per kW-year at 4–7%; 0–90 tested). Steam is sold to named or proposed "
            "users at the avoided cost of a gas boiler at provincial gas prices and the federal carbon-price path (CAD 95, 115, 130 and 140 per tonne "
            "in 2026, 2030, 2035 and 2040^{16}) with Environment and Climate Change Canada emission factors^{17}, for the share of operating hours each "
            "user takes heat (0.90 for process steam, 0.85 for kelp refineries, 0.45 for greenhouses); when a user takes no steam the module makes "
            "full electricity. Capital is CAD 4.4 billion per module plus CAD 1.6 billion of common infrastructure per site (0, 0.8 and 2.4 tested) and "
            "steam or hot-water pipelines at CAD 4.0 or 2.5 million per km. Net present value is at 4% over 40 years from first operation (Ontario "
            "2034, New Brunswick 2035, Nova Scotia 2036, Saskatchewan 2037, Alberta 2038); the tax credit applies only to sites in service by 2034. "
            "Sensitivities scale the carbon-price value to 75% and 50%, replace the power and steam values from 2040 or 2045 with the national "
            "model’s fossil-free shadow values (CAD 79 per MWh of firm power, CAD 42 per MWh of heat-pump heat), cut heat load factors by 20%, and "
            "vary capital, finance and availability (Supplementary Tables 7 and 8).",
        ]),
        ("Winter adequacy stress tests", [
            "For 3-, 7- and 14-day periods at wind capacity factors of 5, 10 and 15% and solar at 3%, flexible loads stop, battery-electric vehicle "
            "demand rises 25% with a 1.35 peak factor, SMRs run at 95% and 0, 10 or 25% of weekly Canadian hydro energy is reshaped from exports and "
            "reservoirs. The remaining peak sets the turbine capacity (CAD 1,400 per kW, 30 years, CAD 25 per kW-year) and the energy gap, at 38% "
            "efficiency, sets a renewable-methane reserve that is added to the methane balance of the linear programme with a storage charge of CAD 3 "
            "per MWh-year. The model is re-solved and the gap recomputed until the cost changes by less than CAD 0.01 billion (Supplementary Table 10).",
        ]),
        ("Co-production, uncertainty and emissions", [
            "Grid Harvester fleets are the larger of a biomass-throughput and a swept-area screen; harvest energy and missed area come from a model of "
            "the harvesting head. Shellfish, salmon, drone, ROV and raft accounts use screening parameters (Supplementary Tables 12 and 13) and are "
            "outside the linear programme. Monte Carlo analysis draws 1,000 sets of cost, yield, conversion and resource parameters; SMR parameters "
            "are tested separately. Well-to-wheel emissions use fuel-cycle and electricity life-cycle factors^{32-34}.",
        ]),
    ]
    return s


LEGENDS = [
    ("Figure_1_system_map.png", "Fig. 1 | The integrated Canadian system. Kelp farms in the least-cost 2050 solution off British Columbia and Atlantic Canada, the "
     "Hudson Bay test area, the electrified Trans-Canada Highway and Lake Winnipeg Grid Harvesters. Circles are two-module SMR sites coloured by net "
     "present value (CAD bn) under current tax law and if the grid becomes fossil-free from 2045; squares are one-module test sites."),
    ("Figure_2_complete_replacement.png", "Fig. 2 | Annual replacement of Canadian transport energy in the central 2050 case. a, Fossil energy replaced in each "
     "segment, by the carrier that replaces it. b, Renewable liquid and gaseous fuels by source. c, New electricity by source and its uses."),
    ("Figure_3_heat_cascade.png", "Fig. 3 | Heat in regional pools. a, Refinery and distillery heat in the Pacific, Atlantic and inland pools under current law, "
     "with the clean electricity credit extended, and with a British Columbia fleet also allowed, with annual system cost. b, Output of each two-module "
     "Trans-Canada Highway site in 2041: electricity, 150 °C steam and 80 °C heat."),
    ("Figure_4_smr_economics.png", "Fig. 4 | SMR economics. a, Annual saving of the fossil-free 2050 system relative to no SMRs against module capital cost, "
     "with and without the tax credit (continuous solution, excluding site infrastructure), and the best whole-module fleet including CAD 1.6 bn of "
     "common infrastructure per site at CAD 4.4 and 3.5 bn per module (A, Atlantic modules; I, inland). b, Net present value of each transition site "
     "under central assumptions (CAD 1.6 bn site infrastructure, pipelines, heat load factors, capacity value CAD 120 per kW-year, credit only to 2034), "
     "without site infrastructure, with CAD 3.5 bn modules and CAD 0.8 bn sites, with a capacity value of CAD 60 per kW-year, and with 75% of the "
     "carbon-price value."),
    ("Figure_5_regional_tests.png", "Fig. 5 | Regional tests. a, Extra annual system cost of forcing 2,000 km² of kelp into the Gulf of St Lawrence, Labrador and "
     "Hudson Bay, without SMRs, with the SMR option under current law, and with CAD 3.5 bn modules, the credit and a Hudson Bay module allowed. "
     "b, Modelled kelp biomass cost against the break-even biomass cost of a biorefinery using SMR heat at the 2041 system fuel value."),
    ("Figure_6_marine_coproduction.png", "Fig. 6 | Marine co-production on the kelp farms. a, Annual harvest energy of the national Grid Harvester fleet against "
     "conventional harvesters. b, Shellfish margins with manual or ROV harvesting, with and without a shared kelp lease. c, Net margin of a 50,000-t "
     "salmon block with utility robots in Atlantic pens and British Columbia closed containment at three salmon prices."),
    ("Figure_7_winter_adequacy.png", "Fig. 7 | Winter adequacy. a, Energy that vehicles, rail and refineries lack during cold low-wind periods of 3 to 14 "
     "days, by wind capacity factor and share of weekly hydro energy reshaped. b, Added annual system cost when backup turbines and a "
     "renewable-methane reserve for three design events are added to the linear programme and the system is re-optimized."),
]


def manuscript():
    d = base_doc(); s = results_text()
    para(d, TITLE, bold=True, size=16, align=WD_ALIGN_PARAGRAPH.LEFT, space=10, spacing=1.15)
    para(d, AUTHORS, size=11.5, align=WD_ALIGN_PARAGRAPH.LEFT, spacing=1.15)
    para(d, AFFIL, size=9.5, align=WD_ALIGN_PARAGRAPH.LEFT, space=12, spacing=1.15)
    para(d, ABSTRACT, bold=True)
    for p in s["intro"]: para(d, p)
    heading(d, "Results")
    for key, title in (("r1", "Every transport segment replaced"), ("r2", "Where nuclear steam earns its place"),
                       ("r3", "Trans-Canada Highway SMR sites during the transition"), ("r4", "British Columbia, the Atlantic and Hudson Bay"),
                       ("r5", "Winter low-wind periods"), ("r6", "Grid Harvesters, shellfish, salmon and utility drones"),
                       ("r7", "Uncertainty and the transition")):
        heading(d, title, 2)
        for p in s[key]: para(d, p)
    heading(d, "Discussion")
    for p in s["disc"]: para(d, p)
    heading(d, "Methods")
    for title, ps in s["methods"]:
        heading(d, title, 2)
        for p in ps: para(d, p)
    heading(d, "Data availability")
    para(d, "All inputs (with a machine-readable provenance table), scenario definitions and outputs, including the Source Data for Figs 1–7, are provided "
         "as Supplementary Data. They will be deposited in a public GitHub repository archived on Zenodo with a DOI before publication.")
    heading(d, "Code availability")
    para(d, "The Python code for the national linear programme, SMR scenarios, site cascade screen, winter stress tests, co-production accounts and all "
         "figures is provided as Supplementary Software (MIT licence) and reproduces every number in the article with one command (run_all.sh). It "
         "will be archived with the data on Zenodo with a DOI before publication.")
    heading(d, "References")
    for i, r in enumerate(REFS, 1):
        para(d, f"{i}. {r}", size=9.5, align=WD_ALIGN_PARAGRAPH.LEFT, space=2, spacing=1.15)
    heading(d, "Acknowledgements")
    para(d, "This research received no external funding.")
    heading(d, "Author contributions")
    para(d, "J.K.B. conceived the study, developed the methodology and software and wrote the original draft. C.P. contributed to the software and reviewed "
         "and edited the manuscript. P.V.B. contributed to the visualization and reviewed and edited the manuscript. All authors approved the submission.")
    heading(d, "Competing interests")
    para(d, "The authors declare no competing interests.")
    heading(d, "Use of artificial intelligence")
    para(d, "Artificial Inventor/Synthetic Scientist V63 was used for drafting, code development, numerical checks, plotting and document preparation. The "
         "authors are responsible for the scientific content and conclusions.")
    d.add_page_break()
    heading(d, "Figures")
    for fn, cap in LEGENDS:
        figure(d, FIG / fn, cap)
    line_numbers(d); page_numbers(d)
    d.save(DOC / "Manuscript_Nature_Energy.docx")
    words = sum(len(p.split()) for k in ("intro", "r1", "r2", "r3", "r4", "r5", "r6", "r7", "disc") for p in s[k])
    mwords = sum(len(p.split()) for _, ps in s["methods"] for p in ps)
    return words, mwords


def supplementary():
    d = base_doc(10.5, 1.15)
    para(d, "Supplementary Information", bold=True, size=15, align=WD_ALIGN_PARAGRAPH.LEFT)
    para(d, TITLE, bold=True, size=12, align=WD_ALIGN_PARAGRAPH.LEFT)
    para(d, AUTHORS, align=WD_ALIGN_PARAGRAPH.LEFT); para(d, AFFIL, size=9, align=WD_ALIGN_PARAGRAPH.LEFT, space=12)
    heading(d, "Contents")
    para(d, "Supplementary Methods 1–7; Supplementary Tables 1–14; Supplementary Figures 1–9. The machine-readable input provenance table "
         "(input_provenance.csv) is supplied with the Supplementary Data.", align=WD_ALIGN_PARAGRAPH.LEFT)
    heading(d, "Supplementary Methods 1. Learning, finance and demand levers")
    para(d, "The central case applies six learning levers and 4% real finance to today’s costs with 2025 demand held constant; the transition case adds "
         "demand levers. The central cost is a technology-learning scenario, not a forecast of 2050 expenditure.")
    lv = json.load(open(OUT / "levers.json"))
    table(d, ["Lever (applied cumulatively)", "System cost, CAD bn yr⁻¹", "Kelp, km²"], [[r["label"], f(r["cost"], 2), f(r["kelp_km2"], 0)] for r in lv["cumulative"]],
          "Supplementary Table 1 | Learning, finance and demand levers.")
    table(d, ["Case", "Yield set", "Cost, CAD bn yr⁻¹", "Kelp, km²", "Kelp, Mt dry"],
          [[y["case"], y["yield_set"], f(y["cost_bn"], 2) if y.get("feasible", True) and "cost_bn" in y else "infeasible",
            f(y.get("kelp_km2", 0), 0), f(y.get("kelp_dry_mt", 0), 2)] for y in YT],
          "Supplementary Table 2 | Demonstrated, design and learning-target kelp yields (central; electric-or-biofuel, eb; electrification, seaweed and "
          "existing biofuels only, strict). Demonstrated commercial yields (0.9–1.4 t dry ha⁻¹ yr⁻¹, Faroe Islands) select no kelp.")
    heading(d, "Supplementary Methods 2. SMR fleets and regional heat pools in the linear programme")
    para(d, "For each fleet f (Atlantic, inland; British Columbia and Hudson Bay in tests): direct electricity x_dir,f, flexible electricity x_flex,f, "
         "electricity forgone for steam x_loss,f and steam q_f (TWh). Constraints: x_dir,f + x_flex,f + x_loss,f ≤ 8.76·0.90·G_max,f (and ≥ 8.76·0.90·G_min,f in "
         "forced or whole-module cases); 0.19·q_f ≤ x_loss,f; q_f ≤ 0.667·(x_dir,f + x_flex,f + x_loss,f). Steam q_f enters only the heat balance of pool f. "
         "Inland steam is further limited to the co-located share of distillation heat: q_inl ≤ 0.25·0.344·E_grain. Costs: x_dir at the levelized cost plus "
         "CAD 5 per MWh and the direct network adder; x_flex at the levelized cost plus the flexible adder; x_loss at the levelized cost; q at CAD 8 per MWh. "
         "Levelized cost = (capital·(1 − ITC)·CRF(r, 40) + fixed O&M)/(8.76·availability) + variable cost, with ITC = 0 after 2034 under current law.")
    rows = [[r["case"], f(r["total_cost_bn"], 3), f(r["atl_gw"], 2), f(r["inl_gw"], 2), f(r["pac_gw"], 2), f(r["smr_steam_twh"], 2),
             f(r["kelp_pacific_km2"], 0), f(r["kelp_atlantic_km2"], 0)] for r in SC["rows"]]
    table(d, ["Case", "Cost, CAD bn", "Atlantic GW", "Inland GW", "BC GW", "Steam TWh", "Pacific kelp km²", "Atlantic kelp km²"], rows,
          f"Supplementary Table 3 | National scenarios (2050, {f(R['demand_total_twh'], 0)} TWh demand unless stated). Capacities are the continuous solution.", size=7)
    rows = []
    for k, lab in (("current_law", "Current law, CAD 4.4 bn, site 1.6"), ("itc_extended", "ITC extended, CAD 4.4 bn, site 1.6"),
                   ("itc_extended_no_site_cost", "ITC extended, CAD 4.4 bn, no site cost"), ("capex_3p5", "Current law, CAD 3.5 bn, site 1.6"),
                   ("capex_3p5_itc", "ITC extended, CAD 3.5 bn, site 1.6"), ("capex_3p5_itc_site_0p8", "ITC extended, CAD 3.5 bn, site 0.8")):
        v = INT[k]
        rows.append([lab, f(v["relaxed_modules"], 2), f(v["saving_relaxed_bn"] * 1000, 1), f"{v['best']['atl']} + {v['best']['inl']}",
                     f(v["best"]["site_cost_bn"] * 1000, 1), f(v["saving_best_bn"] * 1000, 1), f(v["best"]["steam_atl"] + v["best"]["steam_inl"], 2)])
    table(d, ["Case", "Continuous modules (no site cost)", "Continuous saving, CAD M", "Best whole fleet (Atlantic + inland)", "Site cost, CAD M yr⁻¹",
              "Whole-fleet saving, CAD M", "Steam, TWh"], rows,
          "Supplementary Table 4 | Continuous and whole-module SMR optima (savings relative to no SMRs; whole fleets include annualized common "
          "infrastructure of CAD 1.6 bn per site of up to two modules unless stated).", size=7)
    g = INT["itc_extended"]["grid"]
    table(d, ["Atlantic modules", "Inland modules", "Site cost, CAD bn yr⁻¹", "System cost incl. sites, CAD bn (ITC extended)", "System cost incl. sites, CAD bn (current law)"],
          [[x["atl"], x["inl"], f(x["site_cost_bn"], 3), f(x["cost"], 3), f(INT["current_law"]["grid"][i]["cost"], 3)] for i, x in enumerate(g)],
          "Supplementary Table 5 | Whole-module enumeration (all other decisions re-optimized).", size=7.5)
    rows = [[("ITC 15%" if w["itc"] else "no ITC"), f(w["capex_bn"], 1), f(w["lcoe"], 1), f(w["atl_gw"], 2), f(w["inl_gw"], 2), f(w["steam"], 2),
             f(w["saving_vs_nosmr"] * 1000, 1)] for w in SC["sweep"]]
    table(d, ["Credit", "Capital, CAD bn/module", "LCOE, CAD/MWh", "Atlantic GW", "Inland GW", "Steam TWh", "Saving, CAD M yr⁻¹"], rows,
          "Supplementary Table 6 | Capital-cost sweep (continuous). Break-even capital per module: " +
          "; ".join(f"{k.replace('_', ' ')} {v:.2f}" for k, v in BE.items()) + " (CAD bn).", size=7.5)
    heading(d, "Supplementary Methods 3. Site cascade screen")
    for st in SM["sites"]:
        para(d, f"{st['place']} ({st['prov']}): {st['modules']} module(s) from {st['first_year']}; steam "
             + ", ".join(f"{v:.0f} MWth at {k.split('_')[1]}" for k, v in st["heat"].items()) + f" per module; uses: {st['uses']}.", size=9.5)
    cases = ["central", "no_common_infrastructure", "common_infrastructure_low_0p8", "common_infrastructure_high_2p4", "capacity_value_90",
             "capacity_value_60", "capacity_value_0", "heat_load_factor_minus_20pct", "itc_extended", "itc_extended_no_common_infrastructure", "no_itc",
             "carbon_realisation_75", "carbon_realisation_50", "carbon_frozen_95", "grid_fossil_free_2045", "grid_fossil_free_2040", "capex_noak_3p5",
             "capex_3p5_common_low", "capex_foak_6p1", "rate_6pct", "rate_8pct_merchant", "displaces_grid_average", "displaces_coal", "availability_85"]
    sites = ["NS_POINT_TUPPER", "NB_SAINT_JOHN", "ON_CHATHAM", "SK_BELLE_PLAINE", "AB_HEARTLAND", "BC_KAMLOOPS", "MB_CHURCHILL"]
    rows = [[c.replace("_", " ")] + [f(SENS[c][s_], 2) if s_ in SENS[c] else "–" for s_ in sites] +
            [f(sum(SENS[c].get(s_, 0) for s_ in FLEET), 2), f(sum(SENS[c].get(s_, 0) for s_ in ATLF), 2)] for c in cases]
    table(d, ["Case", "NS", "NB", "ON", "SK", "AB", "BC*", "MB*", "Fleet", "NS+NB+ON"], rows,
          "Supplementary Table 7 | Net present value by site (CAD bn). Central: CAD 4.4 bn per module plus CAD 1.6 bn common infrastructure per site, "
          "pipelines, heat load factors, capacity value CAD 120/kW-yr, credit only for sites in service by 2034. *Test sites, one module.", size=6.5)
    import smr_canada_cascade as SMRM
    rows = []
    for st in SMRM.SITES:
        a = SM["sites_2041"][st["id"]]
        for u in st["users"]:
            rows.append([st["place"], u["user"], u["grade"].split("_")[1].replace("C", " °C"), f(u["mwth"] * st["modules"], 0), f(u["lf"], 2),
                         f(u["mwth"] * st["modules"] * u["lf"] * 8760 * 0.9 / 1e6, 2), f(u["pipe_km"], 0),
                         f(u["pipe_km"] * SMRM.PARAMS["site"]["pipe_cad_m_per_km"][u["grade"]], 0)])
    table(d, ["Site", "Heat user (assumed; to be confirmed)", "Grade", "MWth (site)", "Load factor", "Heat sold, TWh yr⁻¹", "Pipe, km", "Pipe capital, CAD M"],
          rows, "Supplementary Table 8 | Reactor sites, heat users, annual heat, pipelines and load factors. Each site also carries CAD 1.6 bn of "
          "common infrastructure. Users marked new are built beside the reactor.", size=6.5)
    rows = [[st, f(v["electricity_twh"], 2), f(v["heat_twh"], 2), f(v["power_value_cad_mwh"], 1), f(v["heat_value_cad_mwh_th"], 1),
             f(v["margin_cad"] / 1e6, 0), f(v["co2_avoided_mt"], 2)] for st, v in SM["sites_2041"].items()]
    table(d, ["Site", "Electricity TWh", "Heat TWh", "Power value CAD/MWh", "Heat value CAD/MWh", "Margin CAD M", "CO₂ avoided Mt"], rows,
          "Supplementary Table 9 | Site accounts in 2041 (central assumptions).", size=7.5)
    heading(d, "Supplementary Methods 4. Winter adequacy stress tests")
    rows = [[f(r["wind_cf"], 2), r["days"], f(r["hydro_share"] * 100, 0), f(r["gap_peak_gw"], 1), f(r["gap_energy_twh"], 2), f(r["methane_twh"], 1),
             f(r["turbine_bn"], 2), f(r["fuel_bn"], 2)] for r in AD["rows"]]
    table(d, ["Wind CF", "Days", "Hydro reshaped, %", "Peak gap, GW", "Gap energy, TWh", "Methane, TWh", "Turbines, CAD bn", "Fuel, CAD bn"], rows,
          "Supplementary Table 10a | Winter stress tests: backup needed (screen at the central capacities).", size=7)
    AI_ = AD["integrated"]
    rows = [["Annual balance only", "–", "–", f(AI_["annual_only_bn"], 2), "–", "–", f(AI_["annual_only_kelp_km2"], 0), f(AI_["annual_only_kelp_dry_mt"], 2),
             f(AI_["annual_only_electricity_twh"], 0), f(AI_["annual_only_reduction_pct"], 1)]]
    rows += [[c["case"], f(c["turbine_gw"], 1), f(c["methane_reserve_twh"], 1), f(c["total_cost_bn"], 2), f(c["extra_vs_annual_bn"], 2), f(c["extra_pct"], 1),
              f(c["kelp_km2"], 0), f(c["kelp_dry_mt"], 2), f(c["electricity_twh"], 0), f(c["reduction_pct"], 1)] for c in AI_["cases"]]
    table(d, ["Case", "Turbines, GW", "Methane reserve, TWh", "System cost, CAD bn", "Added, CAD bn", "Added, %", "Kelp, km²", "Kelp, Mt dry",
              "New electricity, TWh", "Well-to-wheel reduction, %"],
          rows, f"Supplementary Table 10b | Winter reserve inside the optimization (annual-balance cost CAD {f(AD['integrated']['annual_only_bn'], 2)} bn).", size=7)
    heading(d, "Supplementary Methods 5. Forced northern and Gulf kelp")
    rows = [[x["region"].upper(), x["smr"], f(x["extra_cost_bn"], 3), f(x["smr_steam_twh"], 2), f(x["hb_steam_twh"], 2)] for x in SC["forced"]]
    table(d, ["Region", "SMR assumption", "Extra cost, CAD bn yr⁻¹", "SMR steam, TWh", "Hudson Bay steam, TWh"], rows,
          "Supplementary Table 11 | Forcing 2,000 km² of kelp into the Gulf of St Lawrence (GSL), Labrador (LAB) and Hudson Bay (HB).")
    heading(d, "Supplementary Methods 6. Co-production parameters and salmon")
    rows = [[grp, k.replace("_", " "), json.dumps(v)] for grp, vals in CP["params"].items() for k, v in vals.items()]
    table(d, ["Group", "Parameter", "Value"], rows, "Supplementary Table 12 | Co-production parameters (screening assumptions).", size=7)
    rows = [[r["region"], f(r["price_cad_kg"], 0), f(r["revenue_cad_m"], 1), f(r["cost_cad_m"], 1), f(r["net_cad_m"], 1)] for r in sa["rows"]]
    table(d, ["Salmon block (50,000 t)", "Price CAD/kg", "Revenue CAD M", "Cost CAD M", "Net CAD M"], rows, "Supplementary Table 13 | Salmon co-location.")
    heading(d, "Supplementary Methods 7. Territorial emissions and fuel volumes")
    para(d, "Fuel volumes are Statistics Canada 2025 end-use sales (gasoline 43.7 GL, diesel fuel oil 29.4 GL, aviation turbo fuel 9.2 GL), with road "
         "diesel from motor-vehicle fuel sales, rail and marine fuel from the Comprehensive Energy Use Database, and off-road machinery as the "
         "remainder after 1.4 GL of stationary diesel.")
    table(d, ["Account", "Canada total, Mt CO₂e"], [[r["case"], f(r["mt"], 1)] for r in EM["rows"]], "Supplementary Table 14 | Territorial account against the 2024 national inventory (685 Mt).")
    heading(d, "Supplementary Figures")
    sfig = [(ILL / "grid_harvester_top.jpg", "Supplementary Fig. 1 | Grid Harvester, plan view: harvesting head with buoyancy and reaction control, 360° swivel, "
             "suction hose, transport cable and primary vessel moving along the seaweed netting."),
            (ILL / "grid_harvester_side.jpg", "Supplementary Fig. 2 | Grid Harvester, side view."),
            (OLD / "FigS1_grid_harvester.png", "Supplementary Fig. 3 | Grid Harvester turning losses and harvest energy by slurry solids content."),
            (OLD / "Fig4_least_cost_system.png", "Supplementary Fig. 4 | Least-cost system composition in the today, central, transition and electric-boiler cases."),
            (OLD / "Fig5_prices_taxes_profits.png", "Supplementary Fig. 5 | Pump prices, fuel taxes and producer returns at constant pump prices."),
            (OLD / "Fig6_robustness.png", "Supplementary Fig. 6 | Robustness and Monte Carlo results."),
            (OLD / "Fig8_lakes.png", "Supplementary Fig. 7 | Lake biomass harvest and phosphorus removal."),
            (OLD / "Fig10_transition.png", "Supplementary Fig. 8 | Fleet turnover and liquid-fuel demand, 2025–2050."),
            (OLD / "FigS12_electric_road_system_schematic.png", "Supplementary Fig. 9 | Trans-Canada Highway catenary (electric road system) schematic.")]
    for pth, cap in sfig:
        if pth.exists():
            figure(d, pth, cap, width=6.2)
    page_numbers(d)
    d.save(DOC / "Supplementary_Information.docx")


def cover_letter(words, mwords):
    d = base_doc(11, 1.15)
    para(d, "4 November 2026", align=WD_ALIGN_PARAGRAPH.LEFT)
    para(d, "The Editors\nNature Energy", align=WD_ALIGN_PARAGRAPH.LEFT)
    para(d, "Dear Editors,", align=WD_ALIGN_PARAGRAPH.LEFT)
    para(d, f"We submit our Article “{TITLE}” for consideration in Nature Energy.")
    para(d, "Canada is building its first small modular reactors while several provinces debate whether to follow, and its transport sector — from "
         "cars to international flights and ships — remains almost entirely fossil-fuelled. We ask whether every category of transport fuel can be "
         "replaced in one national model, and where in such a system reactors earn their place once steam is kept near its users, reactors are built "
         "in whole modules, and the clean electricity tax credit is applied as the law now stands.")
    para(d, f"The least-cost system replaces all {f(R['demand_total_twh'], 0)} TWh of Canadian transport fuel in an annual energy balance at CAD "
         f"{f(R['total_cost_bn'], 1)} billion a year with assumed learning, or {f(ai7['total_cost_bn'], 1)} billion with an optimized renewable-methane "
         f"reserve for a seven-day winter lull, against {f(R['fossil_cost_bn']['avg2025'], 1)} billion for the same fuel at 2025 prices, and cuts "
         f"well-to-wheel emissions by {f(lc['reduction_pct'], 1)}% ({f(ai7['reduction_pct'], 1)}% with the reserve). Once each new reactor site carries its common infrastructure, no reactor enters the "
         f"fossil-free system unless modules cost below about CAD {f(BE['one_atlantic_module'], 1)}–{f(BE['two_atlantic_modules'], 1)} billion, and of five "
         "Trans-Canada Highway sites only Point Tupper, Nova Scotia, is marginally positive during the transition; we report every assumption that "
         "could reverse that result. British Columbia refines kelp as cheaply with wind and solar, and Hudson Bay kelp does not pay. "
         "We also quantify the Grid Harvesters, shellfish, salmon and utility drones that can share the kelp farms.")
    para(d, "The work will interest readers in energy-system modelling, nuclear–renewable integration, sustainable fuels and marine bioenergy, and "
         "policymakers in Canada and elsewhere who are weighing SMRs.")
    para(d, f"The main text has about {words:,} words and seven display items; Methods have about {mwords:,} words. Supplementary Information, code, data "
         "and a machine-readable input provenance table are provided; code and data will be archived on Zenodo with a DOI before publication. A related "
         "Spanish study is available as an SSRN preprint (https://doi.org/10.2139/ssrn.7648876) and is cited. The manuscript has not been submitted "
         "elsewhere. All authors approved the submission. The authors declare no competing interests, and the work received no external funding. We "
         "would prefer the subscription publication route. The use of Artificial Inventor/Synthetic Scientist V63 is disclosed in the manuscript.")
    para(d, "Yours sincerely,", align=WD_ALIGN_PARAGRAPH.LEFT)
    para(d, "Jonathan Karl Bily (corresponding author), on behalf of Christoph Pahl and Patricia Valdés Bacallao\nIndependent researcher, Zaragoza, Spain\n"
         "jonathan@cloudwashlaundry.com · ORCID 0009-0004-3526-7271", align=WD_ALIGN_PARAGRAPH.LEFT)
    d.save(DOC / "Cover_Letter_Nature_Energy.docx")


if __name__ == "__main__":
    w, mw = manuscript()
    supplementary()
    cover_letter(w, mw)
    print("main-text words", w, "methods words", mw, "abstract words", len(ABSTRACT.split()))
