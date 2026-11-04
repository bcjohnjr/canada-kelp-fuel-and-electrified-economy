"""Reproducible figures S9 (trim model) and S10 (engineering research concept)."""
import json
from pathlib import Path
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch
root=Path(__file__).resolve().parent
rows=json.loads((root/'outputs/giant_kelp_trim_sensitivity.json').read_text())['rows']
names=['50% packing','75% packing','Full transfer','Trim: no regrowth','Trim: +30%*','Trim: +60%*','15% dry matter*','High rope cost*']
fig,axs=plt.subplots(2,1,figsize=(11,8.2),sharex=True)
colors=['#7c9e9f','#7c9e9f','#2f6f76','#b88369','#6e8e68','#456e5d','#8e779a','#c3a26d']
for ax,field,ylabel in [(axs[0],'pac_shelf_dry_t_ha_year','Pacific shelf dry yield (t/ha/year)'),(axs[1],'no_export_cost_cad_bn','Canadian domestic model cost (CAD bn/year)')]:
 values=[r[field] for r in rows]
 ax.bar(range(len(rows)), values, color=colors)
 ax.set_ylabel(ylabel); ax.grid(axis='y',alpha=.17); ax.set_axisbelow(True)
 ax.spines[['top','right']].set_visible(False)
 for i,v in enumerate(values):ax.text(i,v+(max(values)*.018),f'{v:.2f}',ha='center',fontsize=8)
 ax.set_ylim((83 if field.startswith('no_export_cost') else 0),max(values)*1.11)
axs[1].set_xticks(range(len(rows)),names,rotation=17,ha='right',fontsize=8)
fig.suptitle('Fig. S9. Chilean giant-kelp best crop: transfer and trimming sensitivities',y=.99,fontsize=12)
fig.text(.08,.005,'Source: Camus et al. (2018), best 124 wet t/ha crop. *Hypothetical dry fraction or regrowth; +30% and +60% are unobserved\nTrimming cost CAD 15/30/50 per dry t and added 1-m line-capital costs charged on Pacific shelf ONLY; high rope cost CAD 2/m.',fontsize=7.8)
fig.subplots_adjust(left=.12,right=.98,top=.91,bottom=.25,hspace=.20)
for ext in ['png','pdf']:
 fig.savefig(root/f'paper_figures/FigS9_trim_regrowth_sensitivity.{ext}',dpi=300)
plt.close(fig)

fig,ax=plt.subplots(figsize=(11,5.5))
ax.set(xlim=(0,12),ylim=(0,6));ax.set_axis_off()
ax.plot([.4,11.5],[4.9,4.9],color='#507c9a',lw=1.6)
ax.text(11.6,5.02,'Sea surface',fontsize=10,va='bottom',ha='right')
for x in [1.2,10.8]:
 ax.add_patch(Rectangle((x-.32,5.03),.64,.35,facecolor='#d9ac5d',edgecolor='#695c3d'))
ax.plot([1.2,10.8],[4.1,4.1],color='#6e6b5d',lw=3)
ax.text(6,3.75,'Suspended seeded support rope or crop grid (not seabed root)',ha='center',fontsize=10)
for x in [2.2,3.8,5.4,7,8.6,10.2]:
 ax.plot([x,x],[4.1,4.65],color='#51735a',lw=2)
 for off in [-.18,0,.18]:
  ax.plot([x,x+off],[4.58,4.85],lw=2,color='#62916b')
 ax.scatter([x],[4.1],s=22,color='#4d704c')
ax.plot([1,11],[4.54,4.54],ls='--',lw=1.6,color='#d96b52')
ax.text(.5,3.28,'Dashed: selective canopy trim plane; retained lower tissues required',fontsize=9,color='#bd4d35')
ax.add_patch(Rectangle((4.6,5.32),2.2,.30,facecolor='#dbe4ea',edgecolor='#365469'))
ax.text(5.7,5.48,'Cable-guided vessel',ha='center',va='center',fontsize=9)
ax.add_patch(Rectangle((5.2,4.43),1.0,.19,facecolor='#d96b52',edgecolor='#713729'))
ax.annotate('',xy=(5.7,4.6),xytext=(5.7,5.30),arrowprops=dict(arrowstyle='<->',color='#375a72',lw=1.4))
ax.text(6.85,5.06,'Buoyancy-controlled cutting head\n+ suction hose (concept)',fontsize=8,va='center')
ax.text(.5,2.7,'1. First selective pass: retain viable fronds, basal growth tissues and anchors',fontsize=10)
ax.text(.5,2.2,'2. Allow regrowth if biologically demonstrated on suspended crops',fontsize=10)
ax.text(.5,1.7,'3. Second pass only if field data confirm net annual dry yield > single full harvest',fontsize=10)
ax.text(.5,.9,'Evidence distinction: Northern Chile partial-harvest wild plants regrew (Borrás-Chávez et al. 2012);',fontsize=9)
ax.text(.5,.53,'Camus et al. (2018) reported NO regrowth after mowing their shallow suspended Chilean crops.',fontsize=9,color='#9c3625')
fig.suptitle('Fig. S10. Testable Grid Harvester selective-trimming concept (not an observed farm layout)',y=.99,fontsize=12)
fig.subplots_adjust(left=.03,right=.98,top=.9,bottom=.05)
for ext in ['png','pdf']:
 fig.savefig(root/f'paper_figures/FigS10_grid_harvester_selective_trimming.{ext}',dpi=300)
plt.close(fig)
print('Regenerated Fig. S9 and S10')
