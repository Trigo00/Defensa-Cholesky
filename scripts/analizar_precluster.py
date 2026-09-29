from pathlib import Path
import csv,json,math,os,sys,statistics as st
if os.name=='nt':sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(sys.argv[1]);summary=[];observations=0;maxres=0.;maxdiff=0.
def read(path):
    with path.open() as f:return list(csv.DictReader(f))
def validate(rows,reps,labels,key,phases):
    global observations,maxres,maxdiff
    assert len(rows)==2*reps
    assert {(int(r['repetition']),int(r['order'])) for r in rows}=={(i,j) for i in range(1,reps+1) for j in (1,2)}
    for r in rows:
        assert r[key]==labels[(int(r['repetition'])+int(r['order'])-2)%2]
        for k in phases+('total',):assert math.isfinite(float(r[k+'_s'])) and float(r[k+'_s'])>=0
        assert float(r['total_s'])>0
        assert math.isclose(sum(float(r[k+'_s']) for k in phases),float(r['total_s']),rel_tol=1e-8,abs_tol=1e-8)
        for k in ('projected_residual','factor_difference'):
            assert math.isfinite(float(r[k])) and 0<=float(r[k])<=1e-12
        maxres=max(maxres,float(r['projected_residual']));maxdiff=max(maxdiff,float(r['factor_difference']))
    observations+=len(rows)
def record(rows,n,kind,key,labels):
    for label in labels:
        rr=[r for r in rows if r[key]==label];item=dict(N=n,experiment=kind,method=label,repetitions=len(rr))
        for field in ('factor','total'):
            v=[float(r[field+'_s']) for r in rr];q1,_,q3=st.quantiles(v,method='inclusive')
            item[field+'_median_s']=st.median(v);item[field+'_q1_s']=q1;item[field+'_q3_s']=q3
        summary.append(item)
for n in (1024,2048,3072):
    folder='mayor' if n==3072 else 'confirmacion';reps=2 if n==3072 else 8
    rows=read(D/f'{folder}/n{n}_p6.csv')
    assert all(int(r['N'])==n and r['P']=='6' for r in rows)
    validate(rows,reps,('1','4'),'block',('allocation','generation','factor','gather'))
    record(rows,n,'mpi','block',('1','4'))
for n in (512,1024,2048,3072):
    reps=2 if n==3072 else 6;rows=read(D/f'lapack/n{n}.csv')
    assert all(int(r['N'])==n for r in rows)
    assert 'threads=1 ' in (D/f'lapack/n{n}_library.log').read_text()
    validate(rows,reps,('own','lapack'),'method',('allocation','generation','factor'))
    record(rows,n,'lapack','method',('own','lapack'))
with (D/'resumen.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
(D/'validacion.json').write_text(json.dumps(dict(observations=observations,max_projected=maxres,max_difference=maxdiff),indent=2))
fig,axes=plt.subplots(1,2,figsize=(9,3.6),layout='constrained')
for ax,field in zip(axes,('factor','total')):
    for method,label in [('own','C propio'),('lapack','LAPACK / OpenBLAS 1 hilo')]:
        rr=[r for r in summary if r['experiment']=='lapack' and r['method']==method]
        ax.plot([r['N'] for r in rr],[r[field+'_median_s']*1000 for r in rr],marker='o',label=label)
    ax.set(xlabel='Orden n',ylabel='Mediana (ms), escala log',yscale='log',title='Factorización' if field=='factor' else 'Generación + reserva + factor')
    ax.grid(alpha=.2);ax.legend(fontsize=8)
fig.savefig(D/'lapack.png',dpi=180);plt.close(fig)
for r in summary:print(r['experiment'],r['N'],r['method'],'factor_ms',round(1000*r['factor_median_s'],3),'total_ms',round(1000*r['total_median_s'],3))
print('VALIDACION',observations,maxres,maxdiff)
