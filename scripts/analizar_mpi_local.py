"""Experimento 4: estadisticas de cuatro variantes MPI medidas en C."""
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

D=Path(sys.argv[1]); NS=[64,256,512,1024]; PS=[1,2,3,4]
VARIANTS=[('contiguous','original'),('cyclic','original'),('contiguous','local'),('cyclic','local')]
ORDERS=[[0,1,3,2],[1,2,0,3],[2,3,1,0],[3,0,2,1]]
def read(name):
    with (D/name).open(newline='') as f:return list(csv.DictReader(f))
def stats(values):
    if any(not math.isfinite(x) or x<=0 for x in values):raise ValueError('Tiempo invalido')
    q1,_,q3=st.quantiles(values,method='inclusive')
    return dict(median_s=st.median(values),q1_s=q1,q3_s=q3)
def validate(r):
    residual=float(r['relative_residual'])
    if not math.isfinite(residual) or not 0<=residual<=1e-12:raise ValueError('Residuo invalido')
    return residual
def write(name,rows):
    with (D/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

seq={}; results=[]; max_res=0; max_diff=0
for n in NS:
    groups=defaultdict(list);phases={}
    for phase in ['before','after']:
        rows=read(f'seq_{phase}_n{n}.csv')
        if len(rows)!=18:raise ValueError('Referencia incompleta')
        for v in ['left','right','right_buffered']:
            vr=[r for r in rows if r['variant']==v]
            if len(vr)!=6 or {int(r['repetition']) for r in vr}!=set(range(1,7)):raise ValueError('Repeticiones invalidas')
            phases[phase+'_'+v]=st.median(float(r['seconds']) for r in vr)
        for r in rows:
            validate(r)
            if int(r['N'])!=n or int(r['seed'])!=2026:raise ValueError('Entrada incorrecta')
            groups[r['variant']].append(float(r['seconds']))
    seq[n]={v:stats(values) for v,values in groups.items()}
    best=min(seq[n],key=lambda v:seq[n][v]['median_s'])
    seq[n]['phases']=phases
    for p in PS:
        rows=read(f'mpi_n{n}_p{p}.csv');seen=set()
        if len(rows)!=32:raise ValueError('Campana incompleta')
        for r in rows:
            rep,order=int(r['repetition']),int(r['order'])
            key=(rep,order)
            if key in seen or not 1<=rep<=8 or not 1<=order<=4:raise ValueError('Orden duplicado/invalido')
            seen.add(key)
            if (r['distribution'],r['kernel'])!=VARIANTS[ORDERS[(rep-1)%4][order-1]]:raise ValueError('Orden desequilibrado')
            if int(r['N'])!=n or int(r['P'])!=p:raise ValueError('Configuracion incorrecta')
            max_res=max(max_res,validate(r));delta=float(r['factor_difference'])
            if not math.isfinite(delta) or not 0<=delta<=1e-13:raise ValueError('Factor incorrecto')
            max_diff=max(max_diff,delta)
        for dist,kernel in VARIANTS:
            rr=[r for r in rows if (r['distribution'],r['kernel'])==(dist,kernel)]
            if len(rr)!=8:raise ValueError('Repeticiones incompletas')
            results.append(dict(N=n,P=p,distribution=dist,kernel=kernel,repetitions=8,**stats([float(r['seconds']) for r in rr]),base_variant=best,base_s=seq[n][best]['median_s']))
R={(r['N'],r['P'],r['distribution'],r['kernel']):r for r in results}
for r in results:
    r['speedup_useful']=r['base_s']/r['median_s']
    r['speedup_mpi']=R[r['N'],1,r['distribution'],r['kernel']]['median_s']/r['median_s']
    r['original_over_local']=R[r['N'],r['P'],r['distribution'],'original']['median_s']/R[r['N'],r['P'],r['distribution'],'local']['median_s']
write('resumen.csv',results)
(D/'referencias.json').write_text(json.dumps(seq,indent=2),encoding='utf-8')

profiles=[];pr=read('profile_p3.csv')
if len(pr)!=48:raise ValueError('Perfil incompleto')
for dist,kernel in VARIANTS:
    for rank in range(3):
        rr=[r for r in pr if (r['distribution'],r['kernel'],int(r['rank']))==(dist,kernel,rank)]
        if len(rr)!=4 or {int(r['repetition']) for r in rr}!={1,2,3,4}:raise ValueError('Repeticiones de perfil incorrectas')
        start=rank*341+min(rank,1)
        cols=range(rank,1024,3) if dist=='cyclic' else range(start,start+341+(rank==0))
        expected=sum(k*(1024-k) for k in cols)
        if any(int(r['updates'])!=expected or int(r['N'])!=1024 or int(r['P'])!=3 for r in rr):raise ValueError('Conteo incorrecto')
        item=dict(distribution=dist,kernel=kernel,rank=rank,updates=expected)
        for field in ['total','compute','broadcast']:
            values=[float(r[field]) for r in rr]
            if any(not math.isfinite(x) or x<0 for x in values):raise ValueError('Perfil invalido')
            item[field+'_s']=st.median(values)
        profiles.append(item)
write('perfil_resumen.csv',profiles)

plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
colors={'contiguous':'#b6532d','cyclic':'#126f85'}
names={'contiguous':'Contiguo','cyclic':'Ciclico'}
fig,axes=plt.subplots(2,2,figsize=(8,6),layout='constrained')
for ax,n in zip(axes.flat,NS):
    for dist,kernel in VARIANTS:
        rr=[R[n,p,dist,kernel] for p in PS]
        med=[r['median_s']*1000 for r in rr]
        lo=[(r['median_s']-r['q1_s'])*1000 for r in rr];hi=[(r['q3_s']-r['median_s'])*1000 for r in rr]
        ax.errorbar(PS,med,yerr=[lo,hi],color=colors[dist],linestyle='--' if kernel=='original' else '-',marker='x' if kernel=='original' else 'o',capsize=2,label=names[dist]+(' original' if kernel=='original' else ' + vector'))
    ax.axhline(R[n,1,'cyclic','local']['base_s']*1000,color='#41834a',ls=':',label='Mejor secuencial')
    ax.set(title=f'n = {n}',xlabel='Procesos',ylabel='Tiempo (ms)',xticks=PS);ax.grid(alpha=.18)
fig.legend(*axes[0,0].get_legend_handles_labels(),loc='outside lower center',ncol=3,fontsize=8)
fig.savefig(D/'tiempos.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(7.2,3.2),layout='constrained')
for dist in ['contiguous','cyclic']:
    ax.plot(PS,[R[1024,p,dist,'local']['speedup_useful'] for p in PS],marker='o',color=colors[dist],label=names[dist]+' + vector')
ax.axhline(1,color='black',ls='--',lw=1,label='Iguala al mejor secuencial')
ax.set(xlabel='Procesos',ylabel='Mejor secuencial / MPI',xticks=PS,title='Aceleracion util: n = 1024');ax.grid(alpha=.18);ax.legend(fontsize=8)
fig.savefig(D/'speedup.png',dpi=180);plt.close(fig)
checks={'mpi_observations':512,'sequential_observations':144,'profile_rank_observations':48,'maximum_residual':max_res,'maximum_factor_difference':max_diff}
(D/'validacion.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
print(json.dumps(checks))
for n in NS:
    print(f"N={n}, referencia {R[n,1,'cyclic','local']['base_s']*1000:.3f} ms")
    for p in PS:
        print('P='+str(p)+'; '+'; '.join(f"{dist}/{k}: {R[n,p,dist,k]['median_s']*1000:.3f} ms" for dist,k in VARIANTS))

