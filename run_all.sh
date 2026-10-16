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
python3 figures.py                         # main and Supporting Figures; maps only when the Natural Earth layers exist
python3 carbon_reduction.py > /dev/null
python3 transition.py > /dev/null          # fleet turnover, liquid-fuel demand 2025-2050, biofuel ramps, heavy machines (Figure 10)
python3 source_data.py
