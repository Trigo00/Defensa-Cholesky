"""Compara left-looking y right-looking MPI a partir de mediciones C."""
from collections import defaultdict
import csv
import json
import math
import os
from pathlib import Path
import statistics as st
import sys

ROOT=Path(__file__).resolve().parents[2]
if os.name=='nt':sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D=Path(sys.argv[1]);NS=[64,128,256,512,1024];PS=[1,2,3,4];ALGS=['left','right']
def read(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))
def stats(values):
    if any(not math.isfinite(x) or x<=0 for x in values):raise ValueError('Tiempo invalido')
    q1,_,q3=st.quantiles(values,method='inclusive')
    return dict(median_s=st.median(values),q1_s=q1,q3_s=q3,iqr_s=q3-q1)
def write(name,rows):
    with (D/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

summary=[];maxres=0;maxdiff=0;observations=0
for n in NS:
    for p in PS:
        rows=read(D/f'n{n}_p{p}.csv')
        if len(rows)!=16:raise ValueError(f'Datos incompletos n={n}, P={p}')
        seen=set()
        for r in rows:
            rep,pos=int(r['repetition']),int(r['order']);key=(rep,pos)
            if key in seen or not 1<=rep<=8 or not 1<=pos<=2:raise ValueError('Orden duplicado/invalido')
            expected='left' if (rep+pos-1)%2 else 'right'
            if r['algorithm']!=expected:raise ValueError('Orden no alternado')
            if int(r['N'])!=n or int(r['P'])!=p:raise ValueError('Configuracion incorrecta')
            residual=float(r['relative_residual']);difference=float(r['factor_difference'])
            if not math.isfinite(residual) or not 0<=residual<=1e-12:raise ValueError('Residuo invalido')
            if not math.isfinite(difference) or not 0<=difference<=1e-12:raise ValueError('Factor invalido')
            maxres=max(maxres,residual);maxdiff=max(maxdiff,difference);seen.add(key)
        observations+=len(rows)
        for alg in ALGS:
            rr=[r for r in rows if r['algorithm']==alg]
            if len(rr)!=8 or {int(r['repetition']) for r in rr}!=set(range(1,9)):raise ValueError('Repeticiones incompletas')
            summary.append(dict(N=n,P=p,algorithm=alg,repetitions=8,**stats([float(r['seconds']) for r in rr])))
R={(r['N'],r['P'],r['algorithm']):r for r in summary}
for r in summary:
    r['speedup']=R[r['N'],1,r['algorithm']]['median_s']/r['median_s']
    r['efficiency']=r['speedup']/r['P']
    other='right' if r['algorithm']=='left' else 'left'
    r['other_over_this']=R[r['N'],r['P'],other]['median_s']/r['median_s']
write('resumen.csv',summary)

profile_rows=read(D/'profile_n1024_p3.csv')
if len(profile_rows)!=24:raise ValueError('Perfil incompleto')
profiles=[]
for alg in ALGS:
    for rank in range(3):
        rr=[r for r in profile_rows if r['algorithm']==alg and int(r['rank'])==rank]
        if len(rr)!=4 or {int(r['repetition']) for r in rr}!={1,2,3,4}:raise ValueError('Perfil invalido')
        item=dict(algorithm=alg,rank=rank)
        for field in ['total','compute','reduce','broadcast']:
            values=[float(r[field]) for r in rr]
            if any(not math.isfinite(x) or x<0 for x in values):raise ValueError('Perfil no finito')
            item[field+'_s']=st.median(values)
        item['work']=int(rr[0]['work'])
        if any(int(r['work'])!=item['work'] for r in rr):raise ValueError('Conteo variable')
        profiles.append(item)
write('perfil_resumen.csv',profiles)

best=[]
for n in NS:
    candidates=[R[n,p,a] for p in PS for a in ALGS]
    winner=min(candidates,key=lambda r:r['median_s'])
    best.append(dict(N=n,algorithm=winner['algorithm'],P=winner['P'],median_s=winner['median_s'],left_best_s=min(R[n,p,'left']['median_s'] for p in PS),right_best_s=min(R[n,p,'right']['median_s'] for p in PS)))
write('mejores.csv',best)
report=dict(observations=observations,profile_rank_observations=len(profile_rows),maximum_residual=maxres,maximum_factor_difference=maxdiff)
(D/'validacion.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
colors={'left':'#b6532d','right':'#126f85'}
fig,axes=plt.subplots(2,3,figsize=(9,5.8),layout='constrained')
for ax,n in zip(axes.flat,NS):
    for alg in ALGS:
        rr=[R[n,p,alg] for p in PS];med=[r['median_s']*1000 for r in rr]
        lo=[(r['median_s']-r['q1_s'])*1000 for r in rr];hi=[(r['q3_s']-r['median_s'])*1000 for r in rr]
        ax.errorbar(PS,med,yerr=[lo,hi],marker='o',capsize=3,color=colors[alg],label=alg.capitalize())
    ax.set(title=f'n = {n}',xlabel='Procesos',ylabel='Tiempo (ms)',xticks=PS);ax.grid(alpha=.18)
axes[1,2].axis('off');axes[0,0].legend(fontsize=8)
fig.savefig(D/'tiempos.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(7.2,3.4),layout='constrained')
for alg in ALGS:
    ax.plot(PS,[R[1024,p,alg]['speedup'] for p in PS],marker='o',color=colors[alg],label=alg.capitalize())
ax.plot(PS,PS,color='#777777',ls=':',label='Ideal')
ax.set(xlabel='Procesos',ylabel='T(1) / T(P)',title='Escalado fuerte para n = 1024',xticks=PS);ax.grid(alpha=.18);ax.legend()
fig.savefig(D/'speedup.png',dpi=180);plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(8,3.3),layout='constrained',sharey=True)
for ax,alg in zip(axes,ALGS):
    rr=[r for r in profiles if r['algorithm']==alg]
    comp=[r['compute_s']*1000 for r in rr];red=[r['reduce_s']*1000 for r in rr];bcast=[r['broadcast_s']*1000 for r in rr]
    ax.bar(range(3),comp,color='#126f85',label='Calculo')
    ax.bar(range(3),red,bottom=comp,color='#b6532d',label='Reduce')
    ax.bar(range(3),bcast,bottom=[x+y for x,y in zip(comp,red)],color='#d3a240',label='Bcast')
    ax.set(title=alg.capitalize(),xlabel='Rango',xticks=range(3));ax.grid(axis='y',alpha=.15)
axes[0].set_ylabel('Mediana del componente (ms)');axes[1].legend(fontsize=8)
fig.savefig(D/'perfil.png',dpi=180);plt.close(fig)
print(json.dumps(report))
for n in NS:
    print(f"n={n}: "+'; '.join(f"P={p} left={R[n,p,'left']['median_s']*1000:.3f} ms right={R[n,p,'right']['median_s']*1000:.3f} ms" for p in PS))
