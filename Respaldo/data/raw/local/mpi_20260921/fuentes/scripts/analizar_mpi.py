"""Estadisticas de MPI; no implementa factorizacion ni genera matrices."""
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

directory=Path(sys.argv[1])
sizes=[64,256,512,1024]
processes=[1,2,3,4]
distributions=['contiguous','cyclic']

def read(name):
    with (directory/name).open(newline='') as f:return list(csv.DictReader(f))

def summary(values):
    if any(not math.isfinite(x) or x<=0 for x in values):raise ValueError('Tiempo invalido')
    q1,_,q3=st.quantiles(values,method='inclusive')
    return dict(median_s=st.median(values),q1_s=q1,q3_s=q3)

def residual_ok(row):
    x=float(row['relative_residual'])
    if not math.isfinite(x) or not 0<=x<=1e-12:raise ValueError('Residuo invalido')

seq={}; results=[]; maximum_residual=0
for n in sizes:
    groups=defaultdict(list)
    for phase in ['before','after']:
        rows=read(f'seq_{phase}_n{n}.csv')
        if len(rows)!=18:raise ValueError('Referencia incompleta')
        for v in ['left','right','right_buffered']:
            vr=[r for r in rows if r['variant']==v]
            if {int(r['repetition']) for r in vr}!=set(range(1,7)):raise ValueError('Repeticiones secuenciales incorrectas')
        for r in rows:
            residual_ok(r)
            if int(r['N'])!=n or int(r['seed'])!=2026:raise ValueError('Entrada inconsistente')
            groups[r['variant']].append(float(r['seconds']))
    seq[n]={v:summary(values) for v,values in groups.items()}
    base_variant=min(seq[n],key=lambda v:seq[n][v]['median_s'])
    for p in processes:
        rows=read(f'mpi_n{n}_p{p}.csv')
        if len(rows)!=16:raise ValueError('Campana MPI incompleta')
        for d in distributions:
            dr=[r for r in rows if r['distribution']==d]
            if len(dr)!=8 or {int(r['repetition']) for r in dr}!=set(range(1,9)):raise ValueError('Repeticiones MPI incorrectas')
            for r in dr:
                residual_ok(r)
                delta=float(r['factor_difference'])
                if not math.isfinite(delta) or not 0<=delta<=1e-13:raise ValueError('Factor inconsistente')
                if int(r['N'])!=n or int(r['P'])!=p:raise ValueError('Configuracion incorrecta')
                if (int(r['repetition'])+int(r['order'])-1)%2 != (d=='cyclic'):raise ValueError('Orden incorrecto')
                maximum_residual=max(maximum_residual,float(r['relative_residual']))
            stats=summary([float(r['seconds']) for r in dr])
            results.append(dict(N=n,P=p,distribution=d,repetitions=8,**stats,base_variant=base_variant,base_s=seq[n][base_variant]['median_s']))
lookup={(r['N'],r['P'],r['distribution']):r for r in results}
for r in results:
    r['speedup_mpi']=lookup[r['N'],1,r['distribution']]['median_s']/r['median_s']
    r['speedup_useful']=r['base_s']/r['median_s']
    r['efficiency_mpi']=r['speedup_mpi']/r['P']
with (directory/'resumen_mpi.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(results[0]));w.writeheader();w.writerows(results)
(directory/'referencias.json').write_text(json.dumps(seq,indent=2),encoding='utf-8')

profiles=[]
for p in processes:
    rows=read(f'profile_p{p}.csv')
    if len(rows)!=2*3*p:raise ValueError('Perfil incompleto')
    for d in distributions:
        for rank in range(p):
            rr=[r for r in rows if r['distribution']==d and int(r['rank'])==rank]
            if len(rr)!=3 or {int(r['repetition']) for r in rr}!={1,2,3}:raise ValueError('Perfil duplicado')
            n=1024;q,rem=divmod(n,p)
            start=rank*q+min(rank,rem)
            columns=range(rank,n,p) if d=='cyclic' else range(start,start+q+(rank<rem))
            expected=sum(k*(n-k) for k in columns)
            if any(int(r['updates'])!=expected for r in rr):raise ValueError('Conteo incorrecto')
            item=dict(P=p,distribution=d,rank=rank,updates=expected)
            for field in ['total','compute','broadcast']:
                values=[float(r[field]) for r in rr]
                if any(not math.isfinite(x) or x<0 for x in values):raise ValueError('Perfil invalido')
                item[field+'_s']=st.median(values)
            profiles.append(item)
with (directory/'perfil_resumen.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(profiles[0]));w.writeheader();w.writerows(profiles)

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(8,6),layout='constrained')
for n,ax in zip(sizes,axes.flat):
    for d,label,color in zip(distributions,['Contiguo','Ciclico'],['#b6532d','#126f85']):
        rr=[lookup[n,p,d] for p in processes]
        med=[r['median_s']*1000 for r in rr]
        lo=[(r['median_s']-r['q1_s'])*1000 for r in rr]
        hi=[(r['q3_s']-r['median_s'])*1000 for r in rr]
        ax.errorbar(processes,med,yerr=[lo,hi],marker='o',capsize=3,label=label,color=color)
    ax.axhline(lookup[n,1,'cyclic']['base_s']*1000,color='#41834a',ls='--',label='Mejor secuencial')
    ax.set(title=f'n = {n}',xlabel='Procesos',ylabel='Tiempo (ms)',xticks=processes)
    ax.grid(alpha=.2)
axes[0,0].legend(fontsize=8)
fig.savefig(directory/'tiempos_mpi.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(7.2,3.5),layout='constrained')
for n,color in zip(sizes,['#9a698b','#a96730','#41834a','#126f85']):
    ax.plot(processes,[lookup[n,p,'cyclic']['speedup_useful'] for p in processes],marker='o',label=f'n={n}',color=color)
ax.axhline(1,color='black',ls='--',lw=1,label='Iguala al mejor secuencial')
ax.set(xlabel='Procesos',ylabel='Mejor secuencial / MPI ciclico',xticks=processes)
ax.grid(alpha=.2);ax.legend(fontsize=8)
fig.savefig(directory/'speedup_util.png',dpi=180);plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(8,3.4),layout='constrained',sharey=True)
for ax,d in zip(axes,distributions):
    rr=[r for r in profiles if r['P']==3 and r['distribution']==d]
    comp=[r['compute_s']*1000 for r in rr];comm=[r['broadcast_s']*1000 for r in rr]
    ax.bar(range(3),comp,color='#126f85',label='Calculo local')
    ax.bar(range(3),comm,bottom=comp,color='#c87545',label='Dentro de Bcast')
    ax.set(title='Contiguo' if d=='contiguous' else 'Ciclico',xlabel='Rango',xticks=range(3))
axes[0].set_ylabel('Medianas por componente (ms)');axes[1].legend(fontsize=8)
fig.savefig(directory/'perfil_mpi.png',dpi=180);plt.close(fig)

report={'mpi_observations':len(results)*8,'sequential_observations':4*36,'profile_rank_observations':sum(2*3*p for p in processes),'maximum_residual':maximum_residual}
(directory/'validacion.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
for r in results:
    print(f"n={r['N']} P={r['P']} {r['distribution']}: {r['median_s']*1000:.4f} ms; Sutil={r['speedup_useful']:.3f}")
