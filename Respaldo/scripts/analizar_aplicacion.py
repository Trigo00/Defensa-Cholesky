"""Analiza totales medidos directamente y proporciones por ejecucion."""
from pathlib import Path
import csv,json,math,os,sys,statistics as st
if os.name=='nt':sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(sys.argv[1]);NS=(512,1024,2048);PS=(1,3,6)
METHODS=('centralized','distributed','sequential')
ORDERS=((0,1,2),(0,2,1),(1,0,2),(1,2,0),(2,0,1),(2,1,0))
PHASES=('allocation','generation','distribution','factor','gather')
summary=[];obs=0;maxres=0.;maxdiff=0.
for n in NS:
    for p in PS:
        with (D/f'n{n}_p{p}.csv').open() as f:rows=list(csv.DictReader(f))
        assert len(rows)==18
        assert {(int(r['repetition']),int(r['order'])) for r in rows}=={(a,b) for a in range(1,7) for b in range(1,4)}
        for r in rows:
            assert int(r['N'])==n and int(r['P'])==p
            assert r['method']==METHODS[ORDERS[int(r['repetition'])-1][int(r['order'])-1]]
            for k in PHASES+('total','max_local','validation'):
                assert math.isfinite(float(r[k+'_s'])) and float(r[k+'_s'])>=0
            total=float(r['total_s']);assert total>0
            assert math.isclose(sum(float(r[k+'_s']) for k in PHASES),total,rel_tol=1e-8,abs_tol=1e-9)
            for key in ('projected_residual','factor_difference'):
                assert math.isfinite(float(r[key])) and 0<=float(r[key])<=1e-12
            maxres=max(maxres,float(r['projected_residual']));maxdiff=max(maxdiff,float(r['factor_difference']))
        obs+=len(rows)
        for method in METHODS:
            rr=[r for r in rows if r['method']==method];item=dict(N=n,P=p,method=method)
            for k in PHASES+('total','max_local','validation'):
                v=[float(r[k+'_s']) for r in rr];q1,_,q3=st.quantiles(v,method='inclusive')
                item[k+'_median_s']=st.median(v);item[k+'_q1_s']=q1;item[k+'_q3_s']=q3
            for k in PHASES:
                item[k+'_share_median']=st.median(float(r[k+'_s'])/float(r['total_s']) for r in rr)
            summary.append(item)
lookup={(r['N'],r['P'],r['method']):r for r in summary}
for r in summary:
    r['speedup']=lookup[r['N'],r['P'],'sequential']['total_median_s']/r['total_median_s']
with (D/'resumen.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
(D/'validacion.json').write_text(json.dumps(dict(observations=obs,max_projected=maxres,max_difference=maxdiff),indent=2))
fig,axes=plt.subplots(1,3,figsize=(11,3.4),layout='constrained')
labels={'centralized':'Centralizada','distributed':'Distribuida','sequential':'Secuencial'}
for ax,n in zip(axes,NS):
    for method in METHODS:
        rr=[lookup[n,p,method] for p in PS]
        ax.errorbar(PS,[r['total_median_s']*1000 for r in rr],yerr=[[1000*(r['total_median_s']-r['total_q1_s']) for r in rr],[1000*(r['total_q3_s']-r['total_median_s']) for r in rr]],marker='o',capsize=3,label=labels[method])
    ax.set(title=f'n={n}',xlabel='Procesos MPI lanzados',ylabel='Tiempo hasta resultado (ms)',xticks=PS);ax.grid(alpha=.2)
axes[0].legend();fig.savefig(D/'total.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(8,3.5),layout='constrained')
for method in METHODS:
    r=lookup[2048,6,method]
    ax.plot(range(5),[100*r[k+'_share_median'] for k in PHASES],marker='o',label=labels[method])
ax.set(xticks=range(5),xticklabels=['Reserva','Generación','Distribución','Factorización','Recolección'],ylabel='Mediana de proporciones por ejecución (%)',title='Dónde transcurre el tiempo: n=2048, P=6')
ax.legend();ax.grid(alpha=.2);fig.savefig(D/'fases.png',dpi=180);plt.close(fig)
for n in NS:
    for p in PS:
        print(n,p,[(m,round(lookup[n,p,m]['total_median_s']*1000,3)) for m in METHODS])
print('Shares 2048 P6', {m:{k:round(100*lookup[2048,6,m][k+'_share_median'],2) for k in PHASES} for m in METHODS})

