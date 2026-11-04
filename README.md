# Where nuclear heat pays when all Canadian transport fuel is replaced with electricity, biofuels and two-coast kelp

Code and data for the article by Jonathan Karl Bily, Christoph Pahl and Patricia Valdés Bacallao (submitted to Nature Energy).

The national model is an annual least-cost linear programme (HiGHS) for all 814 TWh of fossil transport fuel sold in Canada in 2025 (Statistics Canada, End use of refined petroleum products, 2025): light-duty gasoline and diesel, heavy trucks and buses, rail, farm, mining and construction machinery, aviation including international flights, and shipping. It chooses end-use technologies (battery and catenary electric, drop-in diesel and jet, ethanol, methanol), electricity (wind, solar, hydro, BWRX-300-class SMRs), refinery heat and fuel supply (kelp on the Pacific and Atlantic coasts and, when forced, the Gulf of St Lawrence, Labrador and Hudson Bay; forest and farm residues; lake biomass; waste lipids; canola; biomethane; grain ethanol; electrofuels).

SMRs (300 MWe, 870 MWth, CAD 4.4 bn per module) form an Atlantic fleet (NB, NS) and an inland fleet (ON, SK, AB); British Columbia and Hudson Bay fleets are tested separately. Each can sell direct and flexible electricity and 150 °C extraction steam (0.19 MWh of electricity forgone per MWh of steam, at most 200 MWth per module). Steam reaches only the heat pool of its own region: Pacific (BC kelp refineries), Atlantic (Atlantic, Gulf and Labrador kelp refineries built beside the modules), inland (grain-ethanol distilleries, of which 25% are beside a candidate site, and lake refineries) and Hudson Bay. The 15% clean electricity ITC applies only to property in service before 2035, so the 2050 central case has none (an extension is a sensitivity). The LP treats capacity as continuous; `smr_scenarios.py` also enumerates whole modules. Whole-module fleets and the site screen carry CAD 1.6 bn of common infrastructure per new site of up to two modules (the Darlington budget's common costs; 0–2.4 tested).

A site screen (`smr_canada_cascade.py`) values two-module SMR sites, each with listed heat users, load factors and pipelines, along the Trans-Canada Highway during the transition (electricity, 150 °C and 80 °C heat, carbon-price path, gas displacement, fossil-free-grid sensitivity). `coproduction.py` accounts for Grid Harvesters, shellfish co-culture, salmon co-location with utility robots, solar utility drones, ROVs and service rafts outside the energy cost.

## Reproduce

```bash
python -m pip install -r requirements-lock.txt shapely pyproj basemap python-docx
./run_all.sh          # about three minutes; maps need the Natural Earth layers (python fetch_data.py)
```

Key outputs: `outputs/central_smr.json` (central case, current law), `outputs/central_smr_itc_extended.json`, `outputs/adequacy_stress.json`, `outputs/input_provenance.csv`, `outputs/central_no_smr.json`, `outputs/smr_scenarios.json` (all SMR, heat-pool and regional cases, capital sweep, break-even), `outputs/smr_canada_summary.json` and `outputs/smr_site_sensitivity.csv` (sites), `outputs/coproduction.json`, `outputs/results.json`, `outputs/monte_carlo_summary.json`, `outputs/transition.json`. Article figures: `article_figures/`. Documents: `../documents/` (built by `build_documents_integrated.py`).

## New files for this article

| File | Content |
|---|---|
| `optimise.py` | National linear programme with regional SMR fleets and four regional heat pools |
| `smr_scenarios.py` | Current-law and ITC-extended cases, whole-module enumeration, capital and finance sweeps, co-location, forced fleets, BC and Hudson Bay fleets, forced Gulf/Labrador/Hudson Bay kelp, break-even capital |
| `smr_canada_cascade.py`, `kelp_refinery_reference.py`, `test_smr_canada.py` | Trans-Canada Highway SMR site cascade screen and its checks |
| `coproduction.py` | Grid Harvester fleet and energy, shellfish, salmon, utility drones, ROVs, service rafts |
| `adequacy_stress.py` | 3–14 day winter low-wind stress tests; adds the backup turbines and renewable-methane reserve to the LP and re-optimizes |
| `provenance_inputs.py` | `outputs/input_provenance.csv`: source, date, units, conversion and range of each principal input |
| `figures_integrated.py` | Figures 1–7 |
| `build_documents_integrated.py` | Manuscript, Supplementary Information and cover letter |

`MODEL_NOTES.md` documents the underlying national model modules, the export additionality experiment and the yield, trimming and fiscal sensitivities.

Code: MIT. Outputs and figures: CC BY 4.0. Shipping lanes: Benden (2022), CC BY 4.0. Natural Earth: public domain. Landsat 8 images: NASA Earth Observatory/USGS.
