"""Draw additionality-controlled species-specific scenario figure from model results."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
root=Path(__file__).resolve().parent
rows=json.loads((root/'outputs/species_yield_sensitivity.json').read_text())['rows']
idx=[0,1,2,3,4,5,6,7]
labels=['Original\n12/9 dry','BC shelf Chile\nAtlantic mid','BC shelf Chile\nAtlantic low','BC shelf Chile\nAtlantic high','50% Pacific\nline occupancy','All Pacific\nAtlantic mid','All Pacific\nAtlantic high','17.6 dry\nexploratory']
fig,axes=plt.subplots(2,1,figsize=(10.8,7.4),sharex=True,gridspec_kw={'height_ratios':[1,1]})
x=np.arange(len(idx))
ys=[rows[i]['additional_biogenic_exports_twh'] for i in idx]
areas=[rows[i]['export_farm_area_km2'] for i in idx]
axes[0].bar(x,ys,color=['#8ea3b8']+['#5e99ac']*3+['#a6aa7e']+['#24586e']*3)
axes[0].set_ylabel('Additional biogenic exports (TWh/yr)')
axes[0].set_ylim(0,max(ys)*1.22)
for xi,y in zip(x,ys):axes[0].annotate(f'{y:.1f}',(xi,y),xytext=(0,4),textcoords='offset points',ha='center',fontsize=8)
axes[0].text(.01,.96,'CAD 400/MWh test price; matched no-export and electrofuel guardrails',transform=axes[0].transAxes,va='top',fontsize=8)
axes[1].bar(x,areas,color=['#9aabb6']+['#8fa5ae']*3+['#b9b394']+['#6f929e']*3)
axes[1].set_ylabel('Export-case gross farm area (km²)')
axes[1].set_ylim(0,max(areas)*1.21)
for xi,y in zip(x,areas):axes[1].annotate(f'{y/1000:.1f}k',(xi,y),xytext=(0,3),textcoords='offset points',ha='center',fontsize=8)
axes[1].set_xticks(x,labels,fontsize=8)
for a in axes:a.spines[['top','right']].set_visible(False);a.grid(axis='y',alpha=.17)
fig.suptitle('Fig. S7. Species-specific kelp productivity is conditional on farming location',fontsize=13,y=.995)
fig.text(.06,.015,'Chilean pilot conversion assumes 4 m spacing, full line occupancy and 15% Pacific dry matter. Atlantic scenarios assume 7.5% dry matter.\nOffshore transfer, species composition and otter-habitat effects are unvalidated; 17.6 dry t/ha is exploratory, not supported by the supplied LCA.',fontsize=8)
fig.subplots_adjust(bottom=.22,top=.92,hspace=.19,left=.12,right=.98)
fig.savefig(root/'paper_figures/FigS7_species_yield.png',dpi=300)
fig.savefig(root/'paper_figures/FigS7_species_yield.pdf')
plt.close(fig)
print('Wrote FigS7_species_yield.png and .pdf')
