"""Rebuild three-panel fiscal/consumer-price comparison, including matched common-oil-receipts stress."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
OUT=Path(__file__).resolve().parent/'outputs'
ART=Path(__file__).resolve().parent/'paper_figures';ART.mkdir(exist_ok=True)
d=json.load(open(OUT/'consumer_fiscal_scenarios.json'))
keys=['2025 reference','Intermediate 50/50','October 2026 reference','Elevated: 125% of October 2026']
labels=['2025','Midpoint','Oct. 2026','125% Oct. 2026']
def find(ref,key='October 2026 reference',export=1.,factor=1.):
    return next(z for z in d['rows'] if z['price_scenario']==key and z['consumer_relief_fraction']==.25 and z['redirected_domestic_crude_exported_fraction']==export and z['royalty_retention_factor']==factor and z['refinery_case']==ref)
a=[find('A_capacity_maintained',k) for k in keys]; b=[find('B_domestic_refining_closes',k) for k in keys]
x=np.arange(4)
fig,axs=plt.subplots(1,3,figsize=(15,5),layout='constrained',gridspec_kw={'width_ratios':[1,1,1.1]})
axs[0].bar(x,[r['consumer_relief_bn'] for r in a],width=.62)
axs[0].set_title('(A) 25% pass-through to transport users',fontsize=10)
axs[0].set_ylabel('Savings (CAD billion/year)')
axs[0].set_xticks(x,labels,rotation=24,ha='right')
axs[0].set_ylim(0,26)
for xx,r in zip(x,a):axs[0].text(xx,r['consumer_relief_bn']+.5,f"{r['consumer_relief_bn']:.1f}",ha='center',fontsize=9)
axs[1].plot(x,[r['public_revenue_change_bn'] for r in a],'-o',label='Refining retained')
axs[1].plot(x,[r['public_revenue_change_bn'] for r in b],'-s',label='Refining closes')
axs[1].axhline(0,color='grey',linewidth=.8,linestyle='--')
axs[1].set_title('(B) Full export access',fontsize=10)
axs[1].set_ylabel('Public revenue Δ (CAD billion/year)')
axs[1].set_xticks(x,labels,rotation=24,ha='right')
axs[1].legend(fontsize=8,loc='upper right')
axs[1].set_ylim(-2,6.8)
fractions=[0,.5,1]
for fac in (.75,1.,1.25):
    yy=[find('B_domestic_refining_closes',export=v,factor=fac)['public_revenue_change_bn'] for v in fractions]
    axs[2].plot([100*i for i in fractions],yy,marker='o',label=f'{fac:.0%} common receipts')
axs[2].axhline(0,color='grey',linewidth=.8,linestyle='--')
axs[2].set_title('(C) Refining closes; Oct. 2026 anchor',fontsize=10)
axs[2].set_ylabel('Public revenue Δ (CAD billion/year)')
axs[2].set_xlabel('Displaced crude exported (%)')
axs[2].set_xticks([0,50,100]);axs[2].set_ylim(-4.5,1.3)
axs[2].legend(fontsize=7.6,loc='lower right')
fig.suptitle('Conditional transport-user relief, public receipts and foreign-crude sales',fontsize=12)
fig.text(.015,.004,'Fixed energy system; price anchors are scenarios. Common petroleum shocks affect BOTH comparators. Only unsold redirected crude is an incremental fiscal loss.',fontsize=8)
for ext in ('png','pdf'):fig.savefig(ART/f'FigS11_consumer_fiscal_scenarios.{ext}',dpi=250)
plt.close(fig)
print('wrote corrected FigS11')
