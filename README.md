# Electric drive, native kelp and lake biomass for Canada's annual transport energy

Code and source data for *Electric drive, native kelp, and lake biomass for Canada's annual transport energy: a resource-constrained process-systems optimization with wet hydrothermal liquefaction* (Bily, Pahl, and Valdés Bacallao), submitted to The Canadian Journal of Chemical Engineering. The exact version-controlled submission snapshot is supplied with the manuscript as Supporting Information in the Software and Source Data archives.

The model is an annual least-cost linear programme (HiGHS) for the 827 TWh of fossil transport fuel sold in Canada in 2025, including fuel for international flights, rail, shipping and off-road machinery. Supply options are built from mass and energy balances for wet biorefineries (whole-kelp hydrothermal liquefaction with hydrotreating and solid-oxide hydrogen, ethanol fermentation with HTL of the residue, anaerobic digestion, nutrient recovery) and are placed on a spatial grid.

- **End uses.** Each segment is served by battery-electric drive, catenary-electric trucks on an electrified Trans-Canada Highway corridor (7821 km) with a renewable-diesel or biodiesel engine for off-wire driving, drop-in renewable diesel, biodiesel or jet fuel, ethanol, and, where allowed, methanol, ammonia or methane. Off-road machinery is split into farm, mining and construction and forestry equipment. The electric-or-biofuel case removes electrofuels and methane, methanol and ammonia vehicles.
- **Kelp.** The highest-yielding native kelp in each zone (giant kelp *Macrocystis pyrifera* off British Columbia; sugar kelp *Saccharina latissima* in Atlantic Canada, the Gulf of St. Lawrence, Labrador and Hudson Bay) is farmed in three study areas, with seasonal-ice zones, Hudson Bay farms sited for Manitoba and Ontario (Churchill, Moosonee), and three yield levels (demonstrated, design, learning target). All farms are harvested by the cable-guided Grid Harvester. Fleet sizing is checked both by wet-biomass throughput and by swept-area duty (three partial Pacific passes per year, one elsewhere); the engineering requirement is the larger of the two screens.
- **Lakes.** 22 large Canadian lakes and embayments. In eutrophic waters a lake Grid Harvester (no transport cable) harvests native filamentous algae grown on floating netting, skims cyanobacterial scums and cuts invasive milfoil; native cattail is cut from coastal marshes. Phosphorus exported is compared with load targets as a mass equivalence, and the in-lake response is a first-order screening estimate.
- **Downstream accounts.** Fiscal accounts at constant pump prices with a four-way division (consumer savings, government fuel-tax and road-charge revenue, producer return, residual rent); a territorial (National Inventory boundary) emissions account kept separate from the well-to-wheel lifecycle account; exports and their resource ceiling; self-reliance; Monte Carlo analysis (1000 draws per case); stress tests; a winter low-wind screen; and a downstream screening account for employment, income and consumption taxes, property-tax capacity, retained petroleum public revenue, and exposure to fossil commodity-price shocks.

No fossil energy and no new nuclear capacity are used. Monetary values are 2026 Canadian dollars. The model shows that annual transport-energy demand can be supplied under the modelled resource and process constraints; it does not establish hourly adequacy.

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
| `figures.py`, `figstyle.py` | Figures 1–9 and supplementary Figures S1–S5, with Source Data records (Figure 10 is drawn by `transition.py`) |
| `source_data.py` | One Source Data workbook per figure (`outputs/source_data/`) |
| `data/shiplanes/` | Global Shipping Lanes v1 (Benden 2022, CC BY 4.0), clipped to the study areas |
| `illustrations/` | Grid Harvester illustrations (main Figure 3 and full-resolution Figure S1); Landsat 8 images of Lake St. Clair and western Lake Erie (NASA Earth Observatory; Figure 8) |
| `outputs/` | Machine-readable results (`results.json`, `transition.json`, `highway1.json`, `siting.json`, `yield_taxonomy.json`, `lakes.json`, `self_reliance.json`, `national_emissions*.json`, `carbon_reduction.json`, `diagnostics.json`, `exports.json`, `export_ceiling.json`, `levers.json`, `robustness.csv`, `monte_carlo*.csv`, ...) |
| `paper_figures/` | Figures (PNG, PDF) |

## Headline results

See `outputs/`; the manuscript quotes every number from these files. In brief: the deterministic learning-target system supplies the 827 TWh for CAD 88.3 bn/yr; across 1000 uncertainty draws the median is CAD 102.0 bn/yr (5th–95th percentile 90.6–115.8). Kelp area has an unconditional median of about 2,740 km²; 360 draws select at most 1 km², while the median among the 640 kelp-using draws is about 8,056 km² and the median break-even multiplier is 1.135 times 2025 fossil prices; an electrified Trans-Canada Highway saves about CAD 5.7 bn/yr; the electric-or-biofuel system costs about CAD 93 bn/yr and needs about 55,000 km² of kelp off British Columbia and Nova Scotia, and is infeasible at demonstrated commercial kelp yields; Gulf, Labrador and Hudson Bay kelp costs 2 to 6 times more than British Columbia kelp; lake harvest exports about 3900 t P/yr, a mass equal to half of Lake Winnipeg's load; with transport replaced and all oil exported, territorial emissions fall to about 516 Mt CO2e/yr, or about 505 Mt CO2e/yr if domestic-serving refineries close; transport lifecycle emissions fall by about 253 Mt CO2e/yr (92.8%), with an explicit redirected-crude global-displacement sensitivity. Because oil and bitumen production is held constant and the 0.90 million b/d of Canadian crude now refined for Canadian transport (70% of the 1.29 million b/d of Canadian crude received by Canadian refineries) is exported, royalties and upstream jobs are unchanged. The renewable system supports about 72,750 ongoing gross jobs and 61,200 average annual build job-years; after subtracting about 44,700 fuel-volume-linked service-station jobs, the net gain is about 28,000 ongoing jobs (89,000 during the 2027-2050 build) with refining capacity maintained, or about 17,700 (78,900) if domestic-serving refining closes. Public revenue rises by about CAD 5.4 bn/yr (CAD 1.0 bn/yr if domestic-serving refining closes) at 2025-equivalent prices. Alberta keeps its royalty base and equivalent fuel-tax or road-use revenue and gains about 1,300-12,600 net ongoing jobs with its refineries in service. The 2025-to-October-2026 fossil-price shock raises the same-demand fossil transport bill by 70.9%, while the mature renewable system has 4.6% modelled exposure to the same commodity shock. These are screening results, not a general-equilibrium forecast. In the end state, kelp and electrofuels are near substitutes: without electrofuels cost rises 1.1% while new electricity falls by 108 TWh/yr. The transition account shows 540 TWh of liquid demand in 2040 and 309 TWh in 2050, at least 186 TWh/yr above residues, existing biofuels and lake biomass; kelp built from 2030 avoids 407 Mt CO2e in 2027–2050 beyond those biofuels under fast, central or slow electrification.

## Limits

Annual rather than hourly optimisation; firming is represented by stressed cost adders and a winter low-wind screen. Kelp yields and depth-cycling response are design values extrapolated from small farms and a short trial; seasonal-ice yields are scaled by growing season. Conserved marine areas are removed as ecozone shares, not mapped. Catenary cost is linear in the share of the corridor used. The off-road split and lake values marked approximate are screening assumptions. Grid algae productivity on floating netting in lakes is a design assumption to be demonstrated. The in-lake response omits internal loading and sediment exchange. The oil-and-gas benchmark includes activity serving exports.

## Licence

Code: MIT. Outputs, figures and illustrations: CC BY 4.0. Landsat 8 images: NASA Earth Observatory (public domain, credit NASA Earth Observatory/USGS). Shipping lanes: Benden (2022), CC BY 4.0. Natural Earth: public domain.
