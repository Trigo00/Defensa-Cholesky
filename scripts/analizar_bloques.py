from pathlib import Path
import csv,json,math,os,sys,statistics as st
if os.name=='nt':sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(sys.argv[1]);NS=(512,1024,2048);PS=(1,3,6);BS=(1,2,4,8,16,32,64)
summary=[];obs=0;maxres=0.;maxdiff=0.
for n in NS:
 for proc in PS:
    with (D/f'n{n}_p{proc}.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==49
    assert {(int(r['repetition']),int(r['order'])) for r in rows}=={(i,j) for i in range(1,8) for j in range(1,8)}
    for r in rows:
        assert int(r['N'])==n and int(r['P'])==proc
        assert int(r['block'])==BS[(int(r['order'])+int(r['repetition'])-2)%7]
        for k in ('allocation','generation','factor','gather','total'):
            assert math.isfinite(float(r[k+'_s'])) and float(r[k+'_s'])>=0
        assert math.isclose(sum(float(r[k+'_s']) for k in ('allocation','generation','factor','gather')),float(r['total_s']),rel_tol=1e-8,abs_tol=1e-9)
        for k in ('projected_residual','factor_difference'):
            assert math.isfinite(float(r[k])) and 0<=float(r[k])<=1e-12
        maxres=max(maxres,float(r['projected_residual']));maxdiff=max(maxdiff,float(r['factor_difference']))
    obs+=len(rows)
    for b in BS:
        rr=[r for r in rows if int(r['block'])==b];item=dict(N=n,P=proc,block=b)
        for k in ('allocation','generation','factor','gather','total'):
            v=[float(r[k+'_s']) for r in rr];q1,_,q3=st.quantiles(v,method='inclusive')
            item[k+'_median_s']=st.median(v);item[k+'_q1_s']=q1;item[k+'_q3_s']=q3
        # Independent enumeration of update ownership, not MPI index helpers.
        work=[0]*proc
        for col in range(n):work[(col//b)%proc]+=col*(n-col)
        ratio=max(work)*proc/sum(work)
        assert all(math.isclose(float(r['work_imbalance']),ratio,rel_tol=1e-9) for r in rr)
        item['work_imbalance']=ratio;summary.append(item)
R={(r['N'],r['P'],r['block']):r for r in summary}
for r in summary:r['total_ratio_vs_b1']=R[r['N'],r['P'],1]['total_median_s']/r['total_median_s']
with (D/'resumen.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
(D/'validacion.json').write_text(json.dumps(dict(observations=obs,max_projected=maxres,max_difference=maxdiff),indent=2))
for field,title in [('total','Flujo completo'),('factor','Factorización observada en rango 0')]:
    fig,axes=plt.subplots(3,3,figsize=(10,8),layout='constrained')
    for i,n in enumerate(NS):
        for j,proc in enumerate(PS):
            ax=axes[i,j];rr=[R[n,proc,b] for b in BS]
            med=[1000*r[field+'_median_s'] for r in rr]
            ax.errorbar(range(7),med,yerr=[[1000*(r[field+'_median_s']-r[field+'_q1_s']) for r in rr],[1000*(r[field+'_q3_s']-r[field+'_median_s']) for r in rr]],marker='o',capsize=3)
            ax.set(title=f'n={n}, P={proc}',xticks=range(7),xticklabels=BS,xlabel='Columnas por bloque',ylabel='ms');ax.grid(alpha=.2)
    fig.suptitle(title);fig.savefig(D/f'{field}.png',dpi=170);plt.close(fig)
for n in NS:
 for proc in PS:
    best=min((R[n,proc,b] for b in BS),key=lambda r:r['total_median_s'])
    base=R[n,proc,1]
    print(n,proc,'best',best['block'],'b1_ms',round(base['total_median_s']*1000,3),'best_ms',round(best['total_median_s']*1000,3),'ratio',round(best['total_ratio_vs_b1'],3),'IQR',base['total_q1_s'],base['total_q3_s'],best['total_q1_s'],best['total_q3_s'])

if (D/'repeticion/n2048_p6.csv').exists():
    confirmation=[]
    for n in (1024,2048):
        with (D/f'repeticion/n{n}_p6.csv').open() as f: rr=list(csv.DictReader(f))
        assert len(rr)==49
        assert {(int(r['repetition']),int(r['order'])) for r in rr}=={(i,j) for i in range(1,8) for j in range(1,8)}
        for r in rr:
            assert int(r['N'])==n and int(r['P'])==6
            assert int(r['block'])==BS[(int(r['order'])+int(r['repetition'])-2)%7]
            for k in ('projected_residual','factor_difference'):
                assert math.isfinite(float(r[k])) and 0<=float(r[k])<=1e-12
            assert math.isfinite(float(r['total_s'])) and float(r['total_s'])>0
        # b=4 selected before this follow-up; do not select another minimum.
        med={b:st.median(float(r['total_s']) for r in rr if int(r['block'])==b) for b in (1,4)}
        item=dict(N=n,P=6,baseline_ms=1000*med[1],block4_ms=1000*med[4],ratio=med[1]/med[4])
        confirmation.append(item);print('CONFIRMACION',item)
    (D/'confirmacion.json').write_text(json.dumps(confirmation,indent=2))

