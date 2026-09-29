"""Experimento 5: cruce observado entre secuencial y MPI, por ronda."""
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

D=Path(sys.argv[1]);NS=[64,96,128,160,192,224,256];PS=[1,2,3]
VARIANTS=[('contiguous','original'),('cyclic','original'),('contiguous','local'),('cyclic','local')]
ORDERS=[[0,1,3,2],[1,2,0,3],[2,3,1,0],[3,0,2,1]]
def read(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))
def summary(values):
    if any(not math.isfinite(v) or v<=0 for v in values):raise ValueError('Tiempo invalido')
    q1,_,q3=st.quantiles(values,method='inclusive')
    return dict(median_s=st.median(values),q1_s=q1,q3_s=q3)
def write(name,rows):
    with (D/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
maxres=0;maxdiff=0;mpi_count=0;seq_count=0;results=[];references=[]
def check(r):
    global maxres
    v=float(r['relative_residual'])
    if not math.isfinite(v) or not 0<=v<=1e-12:raise ValueError('Residuo invalido')
    maxres=max(maxres,v)

for campaign in [1,2,3]:
    folder=D/f'r{campaign}'
    for n in NS:
        groups=defaultdict(list);phase_times={}
        for phase in ['before','after']:
            rows=read(folder/f'seq_{phase}_n{n}.csv')
            if len(rows)!=18:raise ValueError('Referencia incompleta')
            seen=set()
            for r in rows:
                check(r);key=(r['variant'],int(r['repetition']))
                if key in seen or r['variant'] not in ['left','right','right_buffered'] or not 1<=key[1]<=6:raise ValueError('Referencia duplicada/invalida')
                if int(r['N'])!=n or int(r['seed'])!=2026:raise ValueError('Entrada inconsistente')
                seen.add(key);groups[r['variant']].append(float(r['seconds']))
            for v in groups:phase_times[phase,v]=st.median(float(r['seconds']) for r in rows if r['variant']==v)
            seq_count+=len(rows)
        stats={v:summary(values) for v,values in groups.items()}
        best=min(stats,key=lambda v:stats[v]['median_s']);base=stats[best]
        for v,s in stats.items():references.append(dict(round=campaign,N=n,variant=v,**s,before_s=phase_times['before',v],after_s=phase_times['after',v]))
        for p in PS:
            rows=read(folder/f'mpi_n{n}_p{p}.csv')
            if len(rows)!=32:raise ValueError('MPI incompleto')
            seen=set()
            for r in rows:
                check(r);rep,order=int(r['repetition']),int(r['order']);key=(rep,order)
                if key in seen or not 1<=rep<=8 or not 1<=order<=4:raise ValueError('Orden invalido')
                if (r['distribution'],r['kernel'])!=VARIANTS[ORDERS[(rep-1)%4][order-1]]:raise ValueError('Orden no equilibrado')
                if int(r['N'])!=n or int(r['P'])!=p:raise ValueError('Configuracion incorrecta')
                seen.add(key);delta=float(r['factor_difference'])
                if not math.isfinite(delta) or not 0<=delta<=1e-13:raise ValueError('Factor incorrecto')
                maxdiff=max(maxdiff,delta)
            mpi_count+=len(rows)
            for dist,kernel in VARIANTS:
                rr=[r for r in rows if (r['distribution'],r['kernel'])==(dist,kernel)]
                s=summary([float(r['seconds']) for r in rr]);speed=base['median_s']/s['median_s']
                results.append(dict(round=campaign,N=n,P=p,distribution=dist,kernel=kernel,**s,base_variant=best,base_s=base['median_s'],base_q1_s=base['q1_s'],base_q3_s=base['q3_s'],speedup=speed,passes=int(speed>1.10 and s['q3_s']<base['q1_s'])))
write('rondas.csv',results);write('referencias.csv',references)
R={(r['round'],r['N'],r['P'],r['distribution'],r['kernel']):r for r in results}
focus=[]
for n in NS:
    for p in [2,3]:
        rr=[R[c,n,p,'cyclic','local'] for c in [1,2,3]]
        focus.append(dict(N=n,P=p,S1=rr[0]['speedup'],S2=rr[1]['speedup'],S3=rr[2]['speedup'],minimum_speedup=min(r['speedup'] for r in rr),maximum_speedup=max(r['speedup'] for r in rr),median_wins=sum(r['speedup']>1 for r in rr),passes=sum(r['passes'] for r in rr)))
write('umbral.csv',focus)
thresholds={}
for p in [2,3]:
    qualified=[r['N'] for r in focus if r['P']==p and r['passes']==3]
    suffix=[n for n in NS if all(k in qualified for k in NS if k>=n)]
    thresholds[p]={'qualifying_sizes':qualified,'first_qualified':min(qualified) if qualified else None,'qualified_suffix_from':min(suffix) if suffix else None}
report=dict(mpi_observations=mpi_count,sequential_observations=seq_count,maximum_residual=maxres,maximum_factor_difference=maxdiff,thresholds=thresholds)
(D/'conclusiones.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(8,3.8),layout='constrained',sharey=True)
for ax,p in zip(axes,[2,3]):
    for c,color in zip([1,2,3],['#126f85','#b6532d','#77649d']):
        ax.plot(NS,[R[c,n,p,'cyclic','local']['speedup'] for n in NS],marker='o',color=color,label=f'Ronda {c}')
    ax.axhline(1,color='black',ls='--',lw=1,label='Iguala secuencial')
    ax.axhline(1.1,color='#41834a',ls=':',lw=1,label='Margen 10 %')
    ax.set(title=f'Ciclico + vector, P={p}',xlabel='Orden n',xticks=NS)
    ax.tick_params(axis='x',labelsize=8);ax.grid(alpha=.15)
axes[0].set_ylabel('Mejor secuencial / MPI');axes[1].legend(fontsize=8)
fig.savefig(D/'cruce.png',dpi=180);plt.close(fig)
print(json.dumps(report,indent=2))
for r in focus:print(f"n={r['N']} P={r['P']}: S={r['S1']:.3f}, {r['S2']:.3f}, {r['S3']:.3f}; criterio {r['passes']}/3")

