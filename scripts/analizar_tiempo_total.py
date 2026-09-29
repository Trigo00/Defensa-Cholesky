"""Analiza entrada, factorizacion, reunion y total medidos en C/MPI."""
from collections import defaultdict
import csv,json,math,os
from pathlib import Path
import statistics as st
import sys
ROOT=Path(__file__).resolve().parents[2]
if os.name=='nt':sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

D=Path(sys.argv[1]);NS=[64,128,256,512,1024];PS=[1,2,3,4]
ALGS=['right','left','sequential'];ORDERS=[(0,1,2),(0,2,1),(1,0,2),(1,2,0),(2,0,1),(2,1,0)]
def read(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))
def stats(values):
    if any(not math.isfinite(x) or x<0 for x in values):raise ValueError('Tiempo invalido')
    q1,_,q3=st.quantiles(values,method='inclusive')
    return st.median(values),q1,q3
def write(name,rows):
    with (D/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

summary=[];maxres=0;maxdiff=0;observations=0
for n in NS:
  for p in PS:
    rows=read(D/f'n{n}_p{p}.csv')
    if len(rows)!=36:raise ValueError('Campana incompleta')
    seen=set()
    for r in rows:
        rep,pos=int(r['repetition']),int(r['order']);key=(rep,pos)
        if key in seen or not 1<=rep<=12 or not 1<=pos<=3:raise ValueError('Orden duplicado/invalido')
        if r['algorithm']!=ALGS[ORDERS[(rep-1)%6][pos-1]]:raise ValueError('Orden incorrecto')
        if int(r['N'])!=n or int(r['P'])!=p:raise ValueError('Configuracion incorrecta')
        residual=float(r['relative_residual']);difference=float(r['factor_difference'])
        if not math.isfinite(residual) or not 0<=residual<=1e-12:raise ValueError('Residuo invalido')
        if not math.isfinite(difference) or not 0<=difference<=1e-12:raise ValueError('Factor invalido')
        maxres=max(maxres,residual);maxdiff=max(maxdiff,difference);seen.add(key)
    observations+=len(rows)
    for alg in ALGS:
        rr=[r for r in rows if r['algorithm']==alg]
        if len(rr)!=12 or {int(r['repetition']) for r in rr}!=set(range(1,13)):raise ValueError('Repeticiones incompletas')
        item=dict(N=n,P=p,algorithm=alg,repetitions=12)
        for source,name in [('input_s','input'),('factor_s','factor'),('gather_s','gather'),('total_s','total')]:
            median,q1,q3=stats([float(r[source]) for r in rr]);item[name+'_median_s']=median;item[name+'_q1_s']=q1;item[name+'_q3_s']=q3
        if alg=='sequential' and any(float(r['gather_s'])!=0 for r in rr):raise ValueError('Reunion secuencial inesperada')
        summary.append(item)
R={(r['N'],r['P'],r['algorithm']):r for r in summary}
for r in summary:
    seq=R[r['N'],r['P'],'sequential']
    r['total_speedup']=seq['total_median_s']/r['total_median_s']
    r['factor_speedup']=seq['factor_median_s']/r['factor_median_s']
    r['total_over_factor']=r['total_median_s']/r['factor_median_s']
write('resumen.csv',summary)

decisions=[]
for n in NS:
    for alg in ['right','left']:
        best=min((R[n,p,alg] for p in PS),key=lambda x:x['total_median_s'])
        decisions.append(dict(N=n,algorithm=alg,best_P=best['P'],best_total_s=best['total_median_s'],sequential_s=R[n,best['P'],'sequential']['total_median_s'],speedup=best['total_speedup']))
write('mejores.csv',decisions)
report=dict(observations=observations,maximum_residual=maxres,maximum_factor_difference=maxdiff)
(D/'validacion.json').write_text(json.dumps(report,indent=2),encoding='utf-8')

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
colors={'left':'#b6532d','right':'#126f85','sequential':'#41834a'}
fig,axes=plt.subplots(2,3,figsize=(9,5.8),layout='constrained')
for ax,n in zip(axes.flat,NS):
    for alg in ALGS:
        rr=[R[n,p,alg] for p in PS];med=[r['total_median_s']*1000 for r in rr]
        lo=[(r['total_median_s']-r['total_q1_s'])*1000 for r in rr];hi=[(r['total_q3_s']-r['total_median_s'])*1000 for r in rr]
        ax.errorbar(PS,med,yerr=[lo,hi],marker='o',capsize=2,color=colors[alg],label=alg.capitalize())
    ax.set(title=f'n = {n}',xlabel='Procesos MPI lanzados',ylabel='Tiempo total (ms)',xticks=PS);ax.grid(alpha=.18)
axes[1,2].axis('off');axes[0,0].legend(fontsize=8)
fig.savefig(D/'tiempo_total.png',dpi=180);plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(8,3.5),layout='constrained',sharey=True)
for ax,alg in zip(axes,['right','left']):
    for field,label,color in [('input','Entrada','+'),('factor','Factorizacion','o'),('gather','Reunion','x'),('total','Total','s')]:
        ax.plot(PS,[R[1024,p,alg][field+'_median_s']*1000 for p in PS],marker=color,label=label)
    ax.set(title=alg.capitalize()+' n=1024',xlabel='Procesos',xticks=PS);ax.grid(alpha=.18)
axes[0].set_ylabel('Mediana (ms)');axes[1].legend(fontsize=8)
fig.savefig(D/'fases_1024.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(7.2,3.4),layout='constrained')
for alg in ['right','left']:
    ax.plot(PS,[R[1024,p,alg]['total_speedup'] for p in PS],marker='o',color=colors[alg],label=alg.capitalize())
ax.axhline(1,color='black',ls='--',lw=1,label='Iguala secuencial completo')
ax.set(xlabel='Procesos',ylabel='Secuencial total / MPI total',title='Aceleracion total para n=1024',xticks=PS);ax.grid(alpha=.18);ax.legend()
fig.savefig(D/'speedup_total.png',dpi=180);plt.close(fig)
print(json.dumps(report))
for n in NS:
    print(f"n={n}: "+'; '.join(f"P={p} seq={R[n,p,'sequential']['total_median_s']*1000:.3f} right={R[n,p,'right']['total_median_s']*1000:.3f} left={R[n,p,'left']['total_median_s']*1000:.3f}" for p in PS))

