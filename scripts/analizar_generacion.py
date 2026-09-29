"""Estadisticas de generacion; no calcula Cholesky en Python."""
from pathlib import Path
import csv, sys, statistics as st, math, json
import os
if os.name=='nt': sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
D=Path(sys.argv[1]); summary=[]; observations=0
for n in (512,1024,2048):
    for p in range(1,7):
        with (D/f'n{n}_p{p}.csv').open() as f: rows=list(csv.DictReader(f))
        assert len(rows)==12
        assert {(int(r['repetition']),r['method']) for r in rows}=={(i,m) for i in range(1,7) for m in ('centralized','distributed')}
        for r in rows:
            assert int(r['N'])==n and int(r['P'])==p and r['identical']=='1'
            assert all(math.isfinite(float(r[k])) and float(r[k])>=0 for k in ('generation_s','distribution_s','total_s'))
        observations+=len(rows)
        for method in ('centralized','distributed'):
            values=[float(r['total_s']) for r in rows if r['method']==method]
            q1,_,q3=st.quantiles(values,method='inclusive')
            summary.append(dict(N=n,P=p,method=method,median_s=st.median(values),q1_s=q1,q3_s=q3))
with (D/'resumen.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(summary[0]));w.writeheader();w.writerows(summary)
(D/'validacion.json').write_text(json.dumps(dict(observations=observations,all_bitwise_identical=True),indent=2))
fig,axes=plt.subplots(1,3,figsize=(11,3.4),layout='constrained')
for ax,n in zip(axes,(512,1024,2048)):
    for method in ('centralized','distributed'):
        rr=[r for r in summary if r['N']==n and r['method']==method]
        ax.errorbar([r['P'] for r in rr],[r['median_s']*1000 for r in rr],yerr=[[1000*(r['median_s']-r['q1_s']) for r in rr],[1000*(r['q3_s']-r['median_s']) for r in rr]],marker='o',capsize=3,label=method)
    ax.set(title=f'n={n}',xlabel='Procesos',ylabel='Generar y distribuir (ms)',xticks=range(1,7));ax.grid(alpha=.2)
axes[0].legend();fig.savefig(D/'generacion.png',dpi=180);plt.close(fig)
for n in (512,1024,2048):
    for p in (1,3,6):
        rr=[r for r in summary if r['N']==n and r['P']==p]
        print(n,p,[(r['method'],round(r['median_s']*1000,3)) for r in rr])

