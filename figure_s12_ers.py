#!/usr/bin/env python3
"""Original, editable publication schematic: proposed Canadian electric road system (ERS).
Scientific conceptual schematic only; dimensions, spacing, voltage, and vehicle design are illustrative.
Run: python figure_s12_ers.py; writes PNG, PDF, SVG and TIFF to paper_figures/.
"""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle, Polygon, FancyArrowPatch
from matplotlib.lines import Line2D
from PIL import Image

OUT=Path(__file__).resolve().parent/'paper_figures'; OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none'})
NAVY='#1c3146'; BLUE='#2270a5'; CYAN='#dcecf6'; TEAL='#147d77'; LIGHT='#f6f8fa'; GREY='#6b7886'; DARK='#293540'; ORANGE='#c4772b'; PALE='#fff4e4'
fig,ax=plt.subplots(figsize=(14.5,7.9),dpi=200)
fig.patch.set_facecolor('white');ax.set_xlim(0,15);ax.set_ylim(0,8.25);ax.axis('off')

def txt(x,y,s,fs=10,weight='normal',color=DARK,ha='left',va='center',**kw):
    return ax.text(x,y,s,fontsize=fs,fontweight=weight,color=color,ha=ha,va=va,**kw)
def line(p,q,c=DARK,lw=1.4,style='solid',z=5):ax.add_line(Line2D([p[0],q[0]],[p[1],q[1]],color=c,lw=lw,ls=style,zorder=z))
def arrow(p,q,color=BLUE,lw=2,ms=12):ax.add_patch(FancyArrowPatch(p,q,arrowstyle='-|>',mutation_scale=ms,color=color,lw=lw,zorder=8))
def roundrect(x,y,w,h,fill='white',edge='#d5dee7',r=.14,lw=1):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle=f'round,pad=0.04,rounding_size={r}',fc=fill,ec=edge,lw=lw,zorder=1))
def wheel(x,y,r=.20):
    ax.add_patch(Circle((x,y),r,fc='#182638',ec='white',lw=.6,zorder=9));ax.add_patch(Circle((x,y),r*.50,fc='#b7c2ca',ec='white',lw=.6,zorder=10))
def truck(x,y,scale=1,roof=False,fill='#e9f0f5'):
    # left-facing tractor, enclosed dry-freight trailer, four stylized wheel positions
    s=scale
    ax.add_patch(Rectangle((x+1.52*s,y+.47*s),3.17*s,1.21*s,fc=fill,ec=NAVY,lw=1.5,zorder=5))
    ax.add_patch(Polygon([(x+.23*s,y+.45*s),(x+1.52*s,y+.45*s),(x+1.52*s,y+1.60*s),(x+.48*s,y+1.60*s),(x+.21*s,y+1.15*s)],closed=True,fc=fill,ec=NAVY,lw=1.5,zorder=6))
    ax.add_patch(Polygon([(x+.35*s,y+1.23*s),(x+.58*s,y+1.5*s),(x+1.27*s,y+1.5*s),(x+1.27*s,y+1.12*s)],closed=True,fc='#a4cddd',ec=NAVY,lw=.7,zorder=7))
    line((x+.43*s,y+.44*s),(x+4.62*s,y+.44*s),NAVY,1)
    for dx in (1.03,2.16,3.47,4.12):wheel(x+dx*s,y+.44*s,r=.20*s)
    return x+1.0*s, y+1.6*s

# title
ax.text(.43,7.93,'Electric road system (ERS) for heavy-duty trucks',fontsize=17.4,color=NAVY,fontweight='bold',va='center')
ax.text(.43,7.58,'Conceptual system architecture  |  Not an as-built representation of the Trans-Canada Highway',fontsize=9.6,color=GREY,va='center')
# main panels
roundrect(.38,3.36,7.05,3.89,fill='#fafcff')
roundrect(7.62,3.36,7.0,3.89,fill='#fffdf9')
txt(.68,7.00,'A',16,'bold',BLUE);txt(1.10,7.00,'On electrified highway section',12.1,'bold',NAVY)
txt(7.92,7.00,'B',16,'bold',ORANGE);txt(8.34,7.00,'Beyond the overhead lines',12.1,'bold',NAVY)
# road and verge
for x,w in [(.55,6.73),(7.8,6.56)]:
    ax.add_patch(Rectangle((x,3.74),w,.54,fc='#e4eaf0',ec='none',zorder=1))
    line((x,4.18),(x+w,4.18),GREY,1.1)
    for xx in [x+.6,x+2.25,x+3.90,x+5.55]:line((xx,3.83),(xx+.75,3.83),'white',2.3)
# catenary, on A only
for px in (1.05,6.62):
    line((px,4.20),(px,6.37),GREY,2.4)
    line((px-.14,6.35),(px+.44,6.35),GREY,1.7)
# two electrically separate conductors, side-view diagram is stylized
line((.95,6.10),(7.16,6.10),BLUE,2.2)
line((.95,6.23),(7.16,6.23),TEAL,2.1)
for tx in (2.0,4.1,6.15):
    line((tx,6.33),(tx,6.23),GREY,1.0)
ax.text(4.00,6.58,'Two-pole overhead contact system',fontsize=10.1,color=NAVY,ha='center',fontweight='bold')
# truck A
rx,ry=truck(1.34,3.89,scale=.96,roof=True)
# pantograph x=2.5, top 6.1, foot 5.42
line((2.63,5.43),(2.86,5.75),NAVY,3)
line((2.86,5.75),(2.60,6.03),NAVY,3)
line((2.60,6.10),(2.92,6.10),ORANGE,3)
# A second isolated collector shoe is represented schematically in the side view.
line((2.97,6.23),(3.19,6.23),ORANGE,3)
line((2.47,5.43),(2.63,5.43),NAVY,2.3)
arrow((4.77,5.89),(4.77,5.32),BLUE,1.8,11)
txt(4.90,5.73,'Electricity to traction drive',8.35,'normal',BLUE,zorder=12)
txt(.86,3.56,'Pantograph engaged • electric traction • battery can recharge',9.1,color=BLUE)
# off wire truck with lowered collector
rx,ry=truck(8.30,3.89,scale=.96,roof=False,fill='#f4eee4')
line((9.35,5.43),(9.57,5.50),NAVY,2.5)
line((9.57,5.50),(9.79,5.43),NAVY,2.5)
# renewable liquid or battery storage note
roundrect(11.70,5.63,2.45,1.03,'#fff7ec','#e9ccac',.10)
txt(12.93,6.40,'Off-wire energy',10.7,'bold',ORANGE,'center')
txt(12.93,6.07,'On-board battery',9.3,color=DARK,ha='center')
txt(12.93,5.80,'or renewable fuel',9.3,color=DARK,ha='center')
arrow((11.95,5.61),(11.40,5.46),ORANGE,1.7,11)
txt(8.03,3.56,'Pantograph stowed • electric/hybrid operation continues',9.1,color=ORANGE)
# Bottom C diagram
roundrect(.38,.46,14.24,2.58,'#fafbfc')
txt(.68,2.78,'C',16,'bold',TEAL);txt(1.1,2.78,'Power supply and vehicle energy flow',12.1,'bold',NAVY)
boxes=[(.80,'Generation / grid','Wind, hydro, other sources'),(4.22,'Roadside substation','Power conversion & control'),(8.08,'Two-pole catenary','Continuous on-wire feed'),(11.64,'Truck traction system','Converter → electric motor')]
for x,h,b in boxes:
    roundrect(x,1.45,2.76,1.01,'white','#cdd9e4',.10)
    txt(x+1.38,2.07,h,10.5,'bold',NAVY,'center')
    txt(x+1.38,1.69,b,8.45,color=GREY,ha='center')
for a,b in [((3.57,1.95),(4.15,1.95)),((7.01,1.95),(8.02,1.95)),((10.90,1.95),(11.55,1.95))]:arrow(a,b,BLUE,2.0,13)
# Offwire branch
line((13.02,1.45),(13.02,1.10),ORANGE,1.8)
arrow((13.02,1.14),(11.95,1.14),ORANGE,1.7,11)
txt(8.14,.84,'Off wire: on-board battery and/or renewable-fuel range extender',9.3,color=ORANGE)
# notes
fig.subplots_adjust(left=.01,right=.99,bottom=.02,top=.98)
base=OUT/'FigS12_electric_road_system_schematic'
fig.savefig(base.with_suffix('.pdf'),bbox_inches='tight',facecolor='white')
fig.savefig(base.with_suffix('.svg'),bbox_inches='tight',facecolor='white')
fig.savefig(base.with_suffix('.png'),bbox_inches='tight',dpi=350,facecolor='white')
fig.savefig(base.with_suffix('.tiff'),bbox_inches='tight',dpi=500,facecolor='white',pil_kwargs={'compression':'tiff_lzw'})
plt.close(fig)
print('Figure S12 created: PDF SVG PNG TIFF')
