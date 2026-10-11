"""Resumen portable (solo biblioteca estandar) de campana_cluster.sh."""
from pathlib import Path
import csv,sys,math,statistics as st
D=Path(sys.argv[1]);out=[]
for f in sorted(D.glob('n*_p*.csv')):
    with f.open() as stream:rows=list(csv.DictReader(stream))
    if not rows:raise ValueError(f'Archivo vacio: {f}')
    n=int(rows[0]['N']);p=int(rows[0]['P']);reps=len(rows)//2
    assert reps>=2 and reps%2==0 and len(rows)==2*reps
    assert {(int(r['repetition']),int(r['order'])) for r in rows}=={(i,j) for i in range(1,reps+1) for j in (1,2)}
    for r in rows:
        assert int(r['N'])==n and int(r['P'])==p
        assert r['block']==('1','4')[(int(r['repetition'])+int(r['order'])-2)%2]
        for k in ('projected_residual','factor_difference'):
            assert math.isfinite(float(r[k])) and 0<=float(r[k])<=1e-12
        for k in ('allocation','generation','factor','gather','total'):
            assert math.isfinite(float(r[k+'_s'])) and float(r[k+'_s'])>=0
        assert math.isclose(sum(float(r[k+'_s']) for k in ('allocation','generation','factor','gather')),float(r['total_s']),rel_tol=1e-8,abs_tol=1e-8)
    for b in ('1','4'):
        item=dict(N=n,P=p,block=b,repetitions=reps)
        for k in ('factor','total'):
            v=[float(r[k+'_s']) for r in rows if r['block']==b];q1,_,q3=st.quantiles(v,method='inclusive')
            item[k+'_median_s']=st.median(v);item[k+'_q1_s']=q1;item[k+'_q3_s']=q3
        out.append(item)
if not out:raise ValueError('No hay mediciones')
with (D/'resumen_pares.csv').open('w',newline='') as stream:
    w=csv.DictWriter(stream,fieldnames=list(out[0]));w.writeheader();w.writerows(out)
print(f'{len(out)} configuraciones resumidas en {D}/resumen_pares.csv')

