
The model is an annual least-cost linear programme (HiGHS) for the 814 TWh of fossil transport fuel sold in Canada in 2025 (Statistics Canada 2025 end-use release), including fuel for international flights, rail, shipping and off-road machinery. Supply options are built from mass and energy balances for wet biorefineries (whole-kelp hydrothermal liquefaction with hydrotreating and solid-oxide hydrogen, ethanol fermentation with HTL of the residue, anaerobic digestion, nutrient recovery) and are placed on a spatial grid.

- **End uses.** Each segment is served by battery-electric drive, catenary-electric trucks on an electrified Trans-Canada Highway corridor (7821 km) with a renewable-diesel or biodiesel engine for off-wire driving, drop-in renewable diesel, biodiesel or jet fuel, ethanol, and, where allowed, methanol, ammonia or methane. Off-road machinery is split into farm, mining and construction and forestry equipment. The electric-or-biofuel case removes electrofuels and methane, methanol and ammonia vehicles.
- **Kelp.** The highest-yielding native kelp in each zone (giant kelp *Macrocystis pyrifera* off British Columbia; sugar kelp *Saccharina latissima* in Atlantic Canada, the Gulf of St. Lawrence, Labrador and Hudson Bay) is farmed in three study areas, with seasonal-ice zones, Hudson Bay farms sited for Manitoba and Ontario (Churchill, Moosonee), and three yield levels (demonstrated, design, learning target). All farms are harvested by the cable-guided Grid Harvester. Fleet sizing is checked both by wet-biomass throughput and by swept-area duty (three partial Pacific passes per year, one elsewhere); the engineering requirement is the larger of the two screens.
- **Lakes.** 22 large Canadian lakes and embayments. In eutrophic waters a lake Grid Harvester (no transport cable) harvests native filamentous algae grown on floating netting, skims cyanobacterial scums and cuts invasive milfoil; native cattail is cut from coastal marshes. Phosphorus exported is compared with external-load targets strictly as a mass equivalence. An idealized well-mixed equilibrium screen is reported only as a sensitivity, not as a validated prediction of lake concentrations or cleanup time.
- **Downstream accounts.** Fiscal accounts at constant pump prices with a four-way division (consumer savings, government fuel-tax and road-charge revenue, producer return, residual rent); a territorial (National Inventory boundary) emissions account kept separate from the well-to-wheel lifecycle account; exports and their resource ceiling; self-reliance; Monte Carlo analysis (1000 draws per case); stress tests; a winter low-wind screen; and a downstream screening account for employment, income and consumption taxes, property-tax capacity, retained petroleum public revenue, and exposure to fossil commodity-price shocks.

No fossil energy is used. New BWRX-300-class SMR capacity is available in an Atlantic and an inland fleet whose extraction steam can heat only refineries and distilleries in the same region (four heat pools); British Columbia and Hudson Bay fleets are tested separately. Under current tax law (clean electricity ITC only for property in service before 2035) the 2050 optimum builds no SMRs; see `smr_scenarios.py`. Monetary values are 2026 Canadian dollars. The model shows that annual transport-energy demand can be supplied under the modelled resource and process constraints; it does not establish hourly adequacy.

## Counterfactual-controlled biogenic export experiment

`kelp_productivity_sensitivity.py` evaluates 7 gross-area dry-kelp yields x 4 assumed selling prices x 2 domestic supply policies. For EACH yield and domestic policy it solves an otherwise identical *no-export counterfactual*. When testing exported biofuel, the model enforces these THREE conditions simultaneously:

1. `export_dropin <= actual_biogenic_dropin`: exported liquid must be supported by biogenic drop-in production rather than electricity-derived synthetic hydrocarbons.
2. `export_dropin <= actual_biogenic_dropin - no_export_biogenic_dropin`: the no-export domestic biogenic quantity is reserved before incremental fuel can be exported.
3. `domestic_eFT <= no_export_eFT`: extra electricity-derived Fischer-Tropsch production cannot replace domestically needed biogenic liquids while releasing them for export.

Figure 7 depicts a distinct, unrestricted synthetic-plus-biogenic drop-in export optimization and must not be confused with the additionality-constrained biogenic export experiment (Figure S6 and the export-additionality table (`outputs/kelp_productivity_export_sensitivity.csv`)). The export experiment reserves biogenic production used in the matched no-export optimum and caps domestic electricity-derived FT output at that reference level. The domestic benchmark and Monte Carlo analyses are separately calculated.

Scenario constraints are annual aggregate mass/energy allocations, not legal chain-of-custody or chemical certification. Selling prices (CAD 330, 400, 500/MWh) are hypothetical, and yields 12–20 dry t per gross farm hectare annually are not established commercial productivity in British Columbia. This study is not an hourly winter adequacy model. Concentrated solar power is outside the Canadian model boundary by choice, not universally ruled out physically.

The related Spanish model preprint is identified by DOI `10.2139/ssrn.7648876`. Related UK and Costa Rican case studies are disclosed in the manuscript and cover letter; Costa Rica is in preparation for Revista Ingeniería and the UK manuscript was submitted to Energy & Environmental Science (Royal Society of Chemistry) and is awaiting a decision.

## Reproduce

```bash
python -m pip install -r requirements-lock.txt   # tested with Python 3.13
python fetch_data.py                             # Natural Earth 1:10m layers and the Global Shipping Lanes dataset
./run_all.sh                                     # about five minutes
```

Without the downloaded layers, `run_all.sh` reproduces the numerical optimization, Grid Harvester screening calculations, employment/fiscal accounts and Source Data tables from the committed inputs. Marine GIS/map regeneration requires the public Natural Earth layers (`python fetch_data.py`); without them the committed marine-space output and figure files remain the submission record.

## Files

| File | Content |
|---|---|
| `spatial.py` | Marine GIS for British Columbia, Atlantic Canada to Labrador, and Hudson Bay: EEZ, depth, haul distance, shipping lanes, ports, seasonal ice and exclusions, conserved share of each marine ecozone, fishing proxy |
| `farm.py` | Kelp zones and species, yields, ice-rated structures, nutrient supply (natural, depth cycling, pumped upwelling) and biomass cost |
| `biorefinery.py` | Wet kelp biorefinery routes per dry tonne (HTL, ethanol + HTL, digestion) |
| `preprocess.py` | Offshore pressing and drying options |
| `lakes.py` | 22 lakes; lake Grid Harvester duties (grid algae, bloom skimming, milfoil cutting); cattail marshes; HTL conversion; phosphorus caps; first-order response |
| `carbon_reduction.py` | Territorial, lifecycle, and redirected-crude carbon-reduction accounting and sensitivity |
| `transition.py` | Fleet-turnover account 2025–2050: liquid-fuel demand by segment, gasoline and drop-in fuel pools, biofuel and kelp build-up, cumulative emissions, E10 blend wall, flexible-fuel and E85-conversion cases, battery needs of heavy machines (Figure 10, Table 4, Section S24) |
| `emissions.py` | Territorial account (2024 inventory, transport replaced, oil exported, refining, CCS, 2030/2035 targets) with the lifecycle account kept separate |
| `economy.py` | Fuel volumes, pump prices, statutory taxes and the oil-and-gas fiscal and profit benchmark |
| `optimise.py` | End uses, Trans-Canada Highway catenary, off-road split, vehicle premia, supply options, exports and the linear programme |
| `fiscal.py` | Accounts at constant pump prices: fuel taxes, rent and the share collected, four-way division, efficiency surplus of electric kilometres, return on capital, royalties, corporate tax |
| `employment_fiscal.py` | Gross screening jobs, labour compensation, income/consumption tax channels, property-tax capacity, retained petroleum public revenue, crude-export redirection and price-shock exposure assumptions |
| `scenarios.py` | Today's costs and the learning, finance and demand levers |
| `lifecycle.py` | Screening lifecycle GHG accounting (domestic use; exports excluded) |
| `jobs_fiscal_balance.py` | Net jobs and public revenue against today's petroleum transport-fuel system with oil and bitumen production held constant and exported; two refinery cases (capacity maintained, domestic-serving refining closed); Alberta account (royalty base, fuel tax, refining share, new and displaced jobs) |
| `analyses.py` | Cases, accounts, levers, exports, stress tests, Monte Carlo (least-cost, transition, electric-or-biofuel), Trans-Canada Highway, yield levels, siting by region, lakes and clean-up payments, self-reliance, emissions accounts |
| `figures.py`, `figstyle.py`, `figure_s6.py` | Figures 1–9 and supplementary Figures S1–S6 (S6 is regenerated after the additionality export sweep); Figure 10 is drawn by `transition.py` |
| `source_data.py` | One Source Data workbook per figure (`outputs/source_data/`) |
| `data/shiplanes/` | Global Shipping Lanes v1 (Benden 2022, CC BY 4.0), clipped to the study areas |
| `illustrations/` | Grid Harvester illustrations (main Figure 3 and full-resolution Figure S1); Landsat 8 images of Lake St. Clair and western Lake Erie (NASA Earth Observatory; Figure 8) |
| `archived_outputs_not_used_in_article/` | Two historical Monte Carlo full-variant files without recovered generating configuration, retained for provenance, not used for manuscript claims. See its README.
| `outputs/` | Machine-readable results (`results.json`, `transition.json`, `highway1.json`, `siting.json`, `yield_taxonomy.json`, `lakes.json`, `self_reliance.json`, `national_emissions*.json`, `carbon_reduction.json`, `diagnostics.json`, `exports.json`, `export_ceiling.json`, `levers.json`, `robustness.csv`, `monte_carlo*.csv`, ...) |
| `paper_figures/` | Figures (PNG, PDF) |

## Headline results

See `outputs/`; the manuscript quotes every number from these files. In brief: the deterministic learning-target system supplies the 814 TWh for CAD 87.28 bn/yr (fossil fuel for the same service: CAD 84.2 bn at 2025 prices, 144.1 bn at October 2026 prices; today's costs at 7%: CAD 110.3 bn); across 1000 uncertainty draws the median is CAD 101.3 bn/yr (5th–95th percentile 89.4–115.4) and the median kelp area 2,550 km². Kelp covers 25,216 km² (20.1 Mt dry/yr); the electric-or-biofuel system costs CAD 91.8 bn/yr. Lifecycle emissions fall by 92.8%. SMRs: none in the current-law optimum, with CAD 1.6 bn common infrastructure per new site; see `outputs/smr_scenarios.json` and `outputs/smr_site_sensitivity.csv` for break-even capital and site net present values. Winter reserve costs: `outputs/adequacy_stress.json`. Over 2025–2050 the system avoids 1,176 Mt CO2e relative to electrification alone. Employment and fiscal accounts are in `outputs/jobs_fiscal_balance.json` and `outputs/consumer_fiscal_scenarios.json`. These are screening results, not a general-equilibrium forecast.

## Limits

Annual rather than hourly optimisation; firming is represented by stressed cost adders and a winter low-wind screen. Kelp yields and depth-cycling response are design values extrapolated from small farms and a short trial; seasonal-ice yields are scaled by growing season. Conserved marine areas are removed as ecozone shares, not mapped. Catenary cost is linear in the share of the corridor used. The off-road split and lake values marked approximate are screening assumptions. Grid algae productivity on floating netting in lakes is a design assumption to be demonstrated. The in-lake response omits internal loading and sediment exchange. The oil-and-gas benchmark includes activity serving exports.

## Licence

Code: MIT. Outputs, figures and illustrations: CC BY 4.0. Landsat 8 images: NASA Earth Observatory (public domain, credit NASA Earth Observatory/USGS). Shipping lanes: Benden (2022), CC BY 4.0. Natural Earth: public domain.

## Interpreting the export-additionality table (`outputs/kelp_productivity_export_sensitivity.csv`)

The no-export farm area and power are not those of the biogenic-export cases. For example, at the Pacific 12 t/ha/yr learning target, no-export optimization uses 25,216 km² of kelp and 341.0 TWh/yr of new electricity. At an assumed CAD 400/MWh sales price, the additionality-controlled case sells 127.2 TWh/yr of biogenic fuel, using 76,992 km² of kelp and 389.2 TWh/yr of new electricity. At 15 t/ha/yr, 206.9 TWh/yr exports use 114,057 km² (versus a no-export 34,705 km²). Machine-readable counterfactual and export-case values are in outputs/kelp_productivity_export_sensitivity.json and .csv.

## Verified reproduction boundaries

`./run_all.sh` regenerates the modelled main Monte Carlo cases and the additionality sweep and now **also redraws Figure S6** from the current sweep JSON. The separate, legacy `monte_carlo_full.csv` and `monte_carlo_summary_full.json` are preserved under `archived_outputs_not_used_in_article/` because their exact generating settings cannot be recovered. They are intentionally not claimed as reproducible and are not cited for article conclusions. Figures with third-party raster basemaps or maps requiring separately downloaded Natural Earth layers have additional provenance requirements, stated above.

At CAD 500/MWh, equal LC/EB farm areas at 12, 15 and 20 t dry/ha/yr are explained by binding geographic area caps in all selected zone-bands (25, 29 and 34 binding zone-bands respectively; executable `binding_caps_check.py` and machine-readable `outputs/binding_marine_area_500.json`). The per-zone upper bounds are `ZONES[zone].area_km2[band] * area_share[zone]` in `optimise.py`; the model operates on gross farm area rather than biological carrying capacity measurements. Any binding claim should be checked against those per-zone limits.


## Species-specific sensitivity: Macrocystis (Pacific) and Saccharina (Atlantic)

The additional `species_yield_sensitivity.py` test and generated `outputs/species_yield_sensitivity.{csv,json}` and `paper_figures/FigS7_species_yield.{png,pdf}` distinguish measured Chilean wet kelp production per line metre from an assumed full-coverage gross farm hectare. Correa et al. (DOI 10.1111/are.12529) reported 41.3 **kg wet per metre of line per year** at 4 m spacing. The calculated full-line-packing farm figure is 103.25 wet t/ha/yr or 15.4875 dry t/ha/yr **if** harvested dry matter is 15%; offshore BC transfer is not empirically proven. The Atlantic Sæther et al. (2024, DOI 10.1007/s10811-024-03213-1) sugar-kelp review reports 75–200 wet t/ha/yr but strongly discourages direct cross-system yield comparisons; 7.5% dry matter is an explicit test parameter (5.625–15 dry t/ha/yr). The alleged 17.6 dry t/ha value is NOT verified by the supplied Journal of Cleaner Production LCA; it appears only in a labelled non-evidentiary exploratory sensitivity.

Optional `farm.dm_pacific` and `farm.dm_atlantic` parameters calculate different wet-haul and preprocessing demands by farm region, without modifying reference 12%-DM cases. No ecological kelp benefit from hypothetical floating sea-otter shelters is assumed. Those installations are not established habitat conservation practice and would require government and First Nation approvals and site-specific welfare assessment. The original farm yield, export and Monte Carlo output files remain separately reproducible; the new Figure S7 shows the sensitivity without relabelling original Figure S6.


## Chilean observed crop: dense ropes and optional selective trimming
The measured 124 wet t/ha best crop at Quenac occurred in five months on approximately 1-m seed-line spacing (Camus et al., Reviews in Aquaculture 10 (2018) 543–559; DOI:10.1111/raq.12185), *not* a demonstrated repeated-crop annual output. Camus et al., Aquaculture 502 (2019) 80–86 (DOI:10.1016/j.aquaculture.2018.12.030) criticize annual assumptions of two productive crop cycles in the earlier Correa study. Their farm had ~9,900 line m/ha rather than ~2,500 m/ha for an illustrative 4-m reference grid. The supplemental scenario parameter `zone_extra_farm_cost_cad_t` adds only to `pac_shelf` and comprises annualized 1-m seeded-line capital (CAD 0.50/m, 5-year replacement, 7% financing, 3% operations; CAD 2.00/m stress) and hypothetical selective-trimming cost (CAD 15/30/50 per dry tonne). Extra cost is NOT added to base `farm.base_cad_t` or to other Pacific/Atlantic zones. `giant_kelp_trim_sensitivity.py` recreates the eight scenarios in the trimming table (`outputs/giant_kelp_trim_sensitivity.csv`) and source CSV/JSON; `figure_s9_s10.py` recreates figures S9/S10. Trim +30% and +60% net yields are hypothetical, and the failed-regrowth case is retained because Camus (2018) observed no regrowth in shallow suspended kelp despite wild-bed partial-harvest regrowth reported elsewhere. Historic national/Monte Carlo input defaults do not change.


## Simultaneous Canadian transport-user savings and public-revenue sensitivity
`consumer_fiscal_scenarios.py` adds no new optimizing decision or transport technology assumption. It uses the committed national solved system, `jobs_fiscal_balance.json`, `employment_fiscal.json`, and the additionality-controlled biogenic-fuel yield sweep to examine 360 transparent combinations. Fuel-service price references: 2025, 50/50 between 2025 and October 2026, October 2026, and an elevated 125% October 2026 stress. There is no forecast of a return to 2025 petroleum prices, and no prediction of sustained 2026 crisis prices. Each level evaluates 0%, 10%, 25%, 50% and 100% consumer pass-through of positive economic margin. Government taxes are adjusted for a proxy lost retail sales-tax base (51.06% light-duty user expenditure, national 12.54% sales-tax proxy) while statutory per-unit transport charges remain. The first-level consolidated fiscal baselines are the existing job/tax screen (refining retained vs refining closure); no further taxes are added on unallocated producer rent. The 0.466 bn low-price negative margin is explicitly shown as an optional public backstop.

Alberta petroleum continuity is an **assumption** not a promise: the 0%, 50%, or 100% of 0.903 Mb/d redirected crude reaching foreign buyers and the petroleum-fiscal receipt realization factors (75%, 100%, 125%) show important downside fiscal risks. Gross crude sales are not tax receipts. Strategic reserve sensitivity uses an unvalidated 127.208 TWh/year controlled biofuel surplus in the 12-t-ha learning-target case at hypothetical CAD 400/MWh; reserve fractions 0/10/25/50% include CAD 20/MWh/year carrying costs but do not include fuel-inventory plant capex, refill dynamics or firm buyers. No double-counting of exports/reserves and fiscal receipts.

Recreate new screen: `python3 consumer_fiscal_scenarios.py` then `python3 figure_s11_fiscal.py`. Both also run in `run_all.sh`. Outputs: `outputs/consumer_fiscal_scenarios.csv`, `.json`, `outputs/renewable_fuel_reserve_screen.csv`, `paper_figures/FigS11_consumer_fiscal_scenarios.png/.pdf`. The full pipeline still regenerates the original deterministic/Monte Carlo/biomass calculations.


## Simultaneous Canadian transport-user savings and public-revenue sensitivity
`consumer_fiscal_scenarios.py` adds no new optimizing decision or transport technology assumption. It uses the committed national solved system, `jobs_fiscal_balance.json`, `employment_fiscal.json`, and the additionality-controlled biogenic-fuel yield sweep to examine 360 transparent combinations. Fuel-service price references: 2025, 50/50 between 2025 and October 2026, October 2026, and an elevated 125% October 2026 stress. There is no forecast of a return to 2025 petroleum prices, and no prediction of sustained 2026 crisis prices. Each level evaluates 0%, 10%, 25%, 50% and 100% consumer pass-through of positive economic margin. Government taxes are adjusted for a proxy lost retail sales-tax base (51.06% light-duty user expenditure, national 12.54% sales-tax proxy) while statutory per-unit transport charges remain. The first-level consolidated fiscal baselines are the existing job/tax screen (refining retained vs refining closure); no further taxes are added on unallocated producer rent. The 0.466 bn low-price negative margin is explicitly shown as an optional public backstop.

Alberta petroleum continuity is an **assumption** not a promise: the 0%, 50%, or 100% of 0.903 Mb/d redirected crude reaching foreign buyers and the petroleum-fiscal receipt realization factors (75%, 100%, 125%) show important downside fiscal risks. Gross crude sales are not tax receipts. Strategic reserve sensitivity uses an unvalidated 127.208 TWh/year controlled biofuel surplus in the 12-t-ha learning-target case at hypothetical CAD 400/MWh; reserve fractions 0/10/25/50% include CAD 20/MWh/year carrying costs but do not include fuel-inventory plant capex, refill dynamics or firm buyers. No double-counting of exports/reserves and fiscal receipts.

Recreate new screen: `python3 consumer_fiscal_scenarios.py` then `python3 figure_s11_fiscal.py`. Both also run in `run_all.sh`. Outputs: `outputs/consumer_fiscal_scenarios.csv`, `.json`, `outputs/renewable_fuel_reserve_screen.csv`, `paper_figures/FigS11_consumer_fiscal_scenarios.png/.pdf`. The full pipeline still regenerates the original deterministic/Monte Carlo/biomass calculations.


## Figure S12: conceptual electric road system (ERS) operation
`python3 figure_s12_ers.py` regenerates the original, non-photographic technical schematic `paper_figures/FigS12_electric_road_system_schematic.pdf`, `.svg`, `.png` and `.tiff`. The vector PDF/SVG and 500-dpi lossless TIFF are supplied for journal artwork. Two-pole catenary, rising pantograph, electric traction and off-wire battery or renewable-fuel hybrid operation are schematic only; no 7,821-km installation is claimed to exist. This adds no technology parameter to the already-reproduced optimizer.


## Corrected petroleum fiscal comparison
consumer_fiscal_scenarios.py applies the common petroleum-receipts realization factor to both the baseline and transition. Only incremental government receipts lost on redirected domestic crude *without international buyers* enter the transition-versus-status-quo difference: upstream_receipts × common_factor × redirected_share × (1 − export_access). At full export access all such incremental losses are zero for all factors. Existing public-revenue gains arise from the prior fiscal account less sales-tax erosion on a hypothetical consumer rebate; rebates do not independently generate new government revenues. The remaining 75% economic rent at 25% pass-through is unallocated, with no profit taxes attributed. Complete redirected crude sales may also generate additional global combustion: at a wholly additional 0.903 Mb/d, approx. 138 Mt CO₂/year. Fig. S11 and the consumer-fiscal table (`outputs/consumer_fiscal_scenarios.csv`) show corrected stress. Results are screening assumptions rather than forecasts.
