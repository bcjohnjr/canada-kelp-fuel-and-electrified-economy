#!/usr/bin/env bash
# Reproduce the quantitative model outputs and Source Data tables; marine maps require the public Natural Earth layers.
set -euo pipefail
cd "$(dirname "$0")"
NE="${NATURAL_EARTH_DIR:-data/naturalearth}"
if [[ -f "$NE/10m_physical/ne_10m_land.shp" ]]; then
  python3 spatial.py > /dev/null          # marine GIS -> outputs/marine_space.json, outputs/_layers.pkl
else
  echo "Natural Earth not found: using the committed outputs/marine_space.json (run fetch_data.py to rebuild maps)"
fi
python3 farm.py
python3 biorefinery.py > /dev/null
python3 preprocess.py > /dev/null
python3 lakes.py > /dev/null              # lakes: Grid Harvester duties, conversion, P exported
python3 economy.py
python3 grid_harvester.py
python3 analyses.py                        # cases, accounts, rent capture, levers, exports and ceiling, robustness, Monte Carlo, lakes
python3 jobs_fiscal_balance.py              # net jobs and public revenue against today, two refinery cases, Alberta account
python3 consumer_fiscal_scenarios.py        # consumer-price relief, oil export access, reserve and government-revenue sensitivity
python3 figure_s11_fiscal.py                # Figure S11 and additional analysis source data
python3 figures.py                         # main and Supporting Figures; maps only when the Natural Earth layers exist
python3 carbon_reduction.py > /dev/null
python3 transition.py > /dev/null          # fleet turnover, liquid-fuel demand 2025-2050, biofuel ramps, heavy machines (Figure 10)
python3 source_data.py

# Counterfactual additionality study: exports cannot displace domestic biogenic supply via more synthetic eFT
python3 kelp_productivity_sensitivity.py
python3 figure_s6.py                       # Figure S6 from current additionality sensitivity data

# Independent site- and species-specific transfer cases (not a new observed BC yield)
python3 species_yield_sensitivity.py
python3 figure_s7.py

# North Canada passive/unheated willow tunnel + wind powered regional HTL sensitivity
python3 northern_willow_sensitivity.py

# Chilean pilot crop and unvalidated Grid Harvester canopy-trimming research cases
python3 giant_kelp_trim_sensitivity.py
python3 figure_s9_s10.py
# Marine area cap report is deterministic and included for reproducibility
python3 binding_caps_check.py > /dev/null

# Original fully reproducible proposed electric road system (ERS) architecture artwork (no model input changes)
python3 figure_s12_ers.py

# SMR cogeneration, regional heat pools, Trans-Canada Highway site cascade, marine co-production and article figures
python3 smr_scenarios.py
python3 smr_canada_cascade.py > /dev/null
python3 test_smr_canada.py
python3 coproduction.py > /dev/null
python3 adequacy_stress.py > /dev/null      # 3-14 day winter low-wind stress tests and backup cost
python3 provenance_inputs.py               # outputs/input_provenance.csv
python3 figures_integrated.py
python3 build_documents_integrated.py
