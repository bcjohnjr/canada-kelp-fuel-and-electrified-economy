"""Regenerate Fig. S6 directly from the additionality-controlled export sweep.
Run after kelp_productivity_sensitivity.py, with matplotlib and numpy installed.
"""
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from figstyle import C, INK, save

ROOT=Path(__file__).resolve().parent
obj=json.loads((ROOT/'outputs/kelp_productivity_export_sensitivity.json').read_text())
rows=obj['rows']
fig, ax=plt.subplots(figsize=(8.0,4.25))
for policy,label,color in [('least_cost','Least-cost domestic policy',C['blue']),('electric_or_biofuel','Electric-or-biofuel domestic policy',C['green'])]:
    rr=sorted((r for r in rows if r['system']==policy and r['export_price_cad_mwh']==400),key=lambda x:x['pacific_yield_t_dry_ha'])
    xy=[(r['pacific_yield_t_dry_ha'],r['export_twh']) for r in rr if r['feasible']]
    ax.plot([v[0] for v in xy],[v[1] for v in xy],marker='o',lw=2.1,color=color,label=label)
ax.set_xlabel('Pacific dry-kelp yield (t ha$^{-1}$ yr$^{-1}$); not demonstrated at high tiers')
ax.set_ylabel('Additional biogenic-fuel exports (TWh yr$^{-1}$)')
ax.set_title('Fig. S6. Additionality-controlled exports at hypothetical CAD 400/MWh')
ax.grid(True,alpha=0.22)
ax.set_xlim(0,21);ax.set_ylim(0,340)
ax.legend(frameon=False,fontsize=9)
ax.text(0.02,0.98,'Matched no-export baseline; incremental biogenic output only;\nno increase in domestic electricity-derived FT backfill',fontsize=7.5,transform=ax.transAxes,va='top')
fig.tight_layout()
save(fig,'FigS6_yield_export')
print('Regenerated paper_figures/FigS6_yield_export.pdf and .png from 56 model rows')
