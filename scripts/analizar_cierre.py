"""Validate observations, compute medians/IQR and useful speedup from fresh launches."""
from pathlib import Path
import csv,json,math,statistics,sys
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
folder=Path(sys.argv[1])
rows=[]
for n in (256,512,1024,2048):
 for rep in range(8):
  for method in ('seq','1','2','3','4','6'):
   stem=folder/'runs'/f'n{n}_r{rep}_m{method}'
   with Path(str(stem)+'.csv').open() as f: data=list(csv.DictReader(f))
   with Path(str(stem)+'.time.csv').open() as f: timing=list(csv.DictReader(f))
   assert len(data)==len(timing)==1
   r={k:float(v) for k,v in data[0].items()};r.update({k:float(v) for k,v in timing[0].items()})
   assert r['N']==n and r['P']==(1 if method=='seq' else int(method))
   assert r['valid']==1 and r['exit_code']==0 and r['projected_residual']<=1e-12
   assert all(math.isfinite(v) for v in r.values())
   assert r['external_s']>=r['application_s']+r['validation_s']
   assert abs(sum(r[k] for k in ('allocation_s','generation_s','factor_s','gather_s'))-r['application_s'])<1e-7
   r.update(method=method,rep=rep)
   r['other_external_s']=r['external_s']-r['application_s']-r['validation_s']
   rows.append(r)
def write(name,rs):
 with (folder/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
write('observaciones.csv',rows)
summary=[]
metrics=('application_s','external_s','validation_s','other_external_s','generation_s','factor_s','gather_s')
for n in (256,512,1024,2048):
 for method in ('seq','1','2','3','4','6'):
  group=[r for r in rows if r['N']==n and r['method']==method and r['rep']>0]
  assert len(group)==7
  s=dict(N=n,method=method,P=1 if method=='seq' else int(method),count=len(group))
  for key in metrics:
   values=[r[key] for r in group];q=statistics.quantiles(values,n=4,method='inclusive')
   s[key]=statistics.median(values);s[key+'_q1']=q[0];s[key+'_q3']=q[2]
  summary.append(s)
for r in summary:
 base=next(s for s in summary if s['N']==r['N'] and s['method']=='seq')
 one=next(s for s in summary if s['N']==r['N'] and s['method']=='1')
 for clock in ('application_s','external_s'):
  r[clock+'_speedup']=base[clock]/r[clock]
  r[clock+'_efficiency']=r[clock+'_speedup']/r['P']
  r[clock+'_mpi_scaling']=one[clock]/r[clock]
write('resumen.csv',summary)
for clock,title in [('application_s','Hasta obtener L'),('external_s','Comando completo, con validación')]:
 fig,axs=plt.subplots(1,3,figsize=(11,3.4),layout='constrained')
 for n in (256,512,1024,2048):
  rr=[r for r in summary if r['N']==n and r['method']!='seq'];ps=[r['P'] for r in rr]
  vals=[r[clock]*1000 for r in rr]
  axs[0].errorbar(ps,vals,yerr=[[1000*(r[clock]-r[clock+'_q1']) for r in rr],[1000*(r[clock+'_q3']-r[clock]) for r in rr]],marker='o',capsize=2,label=f'n={n}')
  axs[1].plot(ps,[r[clock+'_speedup'] for r in rr],'-o',label=f'n={n}')
  axs[2].plot(ps,[100*r[clock+'_efficiency'] for r in rr],'-o',label=f'n={n}')
 axs[0].set(ylabel='Mediana (ms)',yscale='log');axs[1].set(ylabel='Speedup vs. secuencial');axs[2].set(ylabel='Eficiencia (%)')
 axs[1].axhline(1,color='gray',ls='--');axs[1].plot([1,6],[1,6],'k:',label='Ideal S=P')
 for ax in axs:ax.set(xlabel='Procesos MPI',xticks=[1,2,3,4,6]);ax.grid(alpha=.2)
 axs[0].legend(fontsize=7);fig.suptitle(title);fig.savefig(folder/(clock+'.png'),dpi=190);plt.close(fig)
report={'observations':len(rows),'measured':sum(r['rep']>0 for r in rows),'max_projected_residual':max(r['projected_residual'] for r in rows),'summary':summary}
(folder/'analisis.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('Valid observations:',len(rows),'measured:',report['measured'])
for r in summary:
 if r['method'] in ('seq','6'): print(r['N'],r['method'],'app ms',round(1000*r['application_s'],3),'external ms',round(1000*r['external_s'],3),'S app',round(r['application_s_speedup'],3),'S ext',round(r['external_s_speedup'],3))
