"""Recalcular evidencia original sin ejecutar binarios ni modificar data/raw.

Python >=3.10 y matplotlib. Cuartiles inclusivos, cocientes de medianas.
Cada observación conserva archivo original y número de fila CSV.
"""
from pathlib import Path
from collections import defaultdict
import csv, io, json, hashlib, math, re, statistics as st, tarfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'; OUT=ROOT/'data/processed'; FIG=ROOT/'figures'
OUT.mkdir(parents=True,exist_ok=True); FIG.mkdir(exist_ok=True)
ROWS=[]; AUDITS=[]; MEMBERS=[]; HASHES=[]
def write(name,rows):
    if not rows:return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with (OUT/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
def read(b):return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
def numeric(r):
    out={}
    for k,v in r.items():
        try:out[k]=float(v)
        except (ValueError,TypeError):out[k]=v
    return out
def check(r):
    for k,v in r.items():
        if isinstance(v,float):assert math.isfinite(v),(k,r)
        if k.endswith('_s') and isinstance(v,float):assert v>=0,(k,r)
    for k in ('relative_residual','projected_residual','factor_difference'):
        if k in r:assert 0<=r[k]<=1e-12,(k,r)
    if 'exact_residual' in r:assert r['exact_residual']==-1 or 0<=r['exact_residual']<=1e-12
    if 'valid' in r:assert r['valid']==1,r
    if 'exit_code' in r:assert r['exit_code']==0,r
    if 'identical' in r:assert r['identical']==1,r
    if 'application_s' in r:
        assert math.isclose(sum(r[k] for k in ('allocation_s','generation_s','factor_s','gather_s')),r['application_s'],rel_tol=1e-8,abs_tol=1e-8)
        if 'external_s' in r:
            assert r['external_s']>=r['application_s']+r['validation_s']
            r['other_external_s']=r['external_s']-r['application_s']-r['validation_s']
    # compare_mpi_total and compare_generation report maxima independently:
    # their phases need not sum to their maximum total.
    if 'allocation_s' in r and 'total_s' in r:
        phases=['allocation_s','generation_s','factor_s']+[k for k in ('distribution_s','gather_s') if k in r]
        assert math.isclose(sum(r[k] for k in phases),r['total_s'],rel_tol=1e-8,abs_tol=1e-8)
def add(r,campaign,method,origin,line,cohort='main',warmup=False):
    r=numeric(r);check(r)
    r.update(campaign=campaign,method=method,origin=origin,csv_line=line,cohort=cohort,warmup=int(warmup))
    ROWS.append(r)
def archive(path):
    with tarfile.open(path) as t:
        mm=t.getmembers(); assert len({m.name for m in mm})==len(mm)
        fs={m.name:t.extractfile(m).read() for m in mm if m.isfile()}
    for n,b in fs.items():MEMBERS.append(dict(archive=path.name,member=n,bytes=len(b),sha256=hashlib.sha256(b).hexdigest()))
    count=0
    for name,b in fs.items():
        if 'SHA256' not in Path(name).name:continue
        for h,target in re.findall(r'^([0-9a-f]{64})\s+\*?(.+)$',b.decode(),re.M):
            target=target.strip().removeprefix('./')
            matches=[n for n in fs if n==target or n.endswith('/'+target)]
            if not matches:matches=[n for n in fs if Path(n).name==Path(target).name]
            assert len(matches)==1,(name,target,matches)
            actual=hashlib.sha256(fs[matches[0]]).hexdigest();assert actual==h,(name,target)
            HASHES.append(dict(archive=path.name,manifest=name,member=matches[0],sha256=h));count+=1
    # LAPACK records hashes in entorno.txt, rather than a manifest file.
    if 'lapack_cluster' in path.name:
        env=next(b for n,b in fs.items() if n.endswith('/entorno.txt'))
        for h,target in re.findall(r'^([0-9a-f]{64})\s+(\S+)$',env.decode(),re.M):
            matches=[n for n in fs if n.endswith('/'+target)]
            assert len(matches)==1 and hashlib.sha256(fs[matches[0]]).hexdigest()==h
            HASHES.append(dict(archive=path.name,manifest='entorno.txt',member=matches[0],sha256=h));count+=1
    info=dict(archive=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),files=len(fs),verified_hash_entries=count)
    before=next((b for n,b in fs.items() if n.endswith('/cpu_stat_antes.txt')),None)
    after=next((b for n,b in fs.items() if n.endswith('/cpu_stat_despues.txt')),None)
    if before and after:
        a=dict(x.split() for x in before.decode().splitlines());b=dict(x.split() for x in after.decode().splitlines())
        info['cpu_stat_delta']={k:int(b[k])-int(v) for k,v in a.items()}
    source_matches={}; measured_matches={}
    for n,b in fs.items():
        if Path(n).suffix in ('.c','.h') and (ROOT/'src'/Path(n).name).exists():
            source_matches[Path(n).name]=b==(ROOT/'src'/Path(n).name).read_bytes()
            measured=ROOT/'archive/src_medidos_20260928'/Path(n).name
            measured_matches[Path(n).name]=b==measured.read_bytes()
    info['current_source_byte_matches']=source_matches
    info['measured_source_byte_matches']=measured_matches
    info['measured_source_directory']='archive/src_medidos_20260928'
    AUDITS.append(info)
    return fs

for path in sorted((RAW/'cluster').glob('*.tar.gz')):
    fs=archive(path)
    campaign={'campana_cruce_20260928.tar.gz':'cluster_crossing','campana_escalabilidad_20260928.tar.gz':'cluster_scalability','campana_lapack_cluster_20260928.tar.gz':'cluster_lapack','campana_final_grande_20260928.tar.gz':'cluster_large','evidencia_preformal_20260928.tar.gz':'cluster_pilot'}[path.name]
    for name,b in sorted(fs.items()):
        if not name.endswith('.csv') or '_external.csv' in name:continue
        rr=read(b);base=Path(name).name
        if campaign=='cluster_lapack' or (campaign=='cluster_large' and rr and 'method' in rr[0]):
            for i,r in enumerate(rr,2):add(r,campaign,r['method'],path.name+'::'+name,i)
            continue
        assert len(rr)==1,name
        r=rr[0];m=re.search(r'(?:^|_)(seq|p\d+)(?:_|\.)',base)
        method='seq' if '_seq_' in base or '_seq.' in base else (m.group(1) if m else 'p'+r['P'])
        if campaign=='cluster_pilot' and 'seq' in base:method='seq'
        warm='warmup' in base
        rep=re.search(r'(?:rep)+(\d+)',base)
        r['repetition']=int(rep.group(1)) if rep else 0
        if campaign=='cluster_scalability':
            ext=read(fs[name.replace('_internal.csv','_external.csv')]);assert len(ext)==1
            r.update(ext[0])
        cohort='main' if campaign!='cluster_pilot' else base.split('_')[0]
        add(r,campaign,method,path.name+'::'+name,2,cohort,warm)
    if campaign=='cluster_lapack':
        b=next(v for k,v in fs.items() if k.endswith('/lapack_control_n512.log'))
        for i,r in enumerate(read(b.split(b'\n',1)[1]),3):add(r,campaign,r['method'],path.name+'::lapack_control_n512.log',i,'control')

for folder in sorted((RAW/'local').iterdir()):
    if not folder.is_dir():continue
    for path in sorted(folder.rglob('*.csv')):
        rel=path.relative_to(folder)
        if 'fuentes' in rel.parts or path.name.endswith('.time.csv'):continue
        rr=read(path.read_bytes())
        if not rr or not any(k in rr[0] for k in ('seconds','factor_s','generation_s','application_s')):continue
        if any(k in rr[0] for k in ('median_s','repetitions')) or path.name=='observaciones.csv':continue
        for i,r in enumerate(rr,2):
            cohort=rel.parent.as_posix()
            if path.name.startswith('profile'):cohort+=':profile'
            if path.name.startswith('test') or cohort=='tests':cohort+=':test'
            method=':'.join(str(r[k]) for k in ('variant','algorithm','method','distribution','kernel','block') if k in r) or 'seq'
            warm=False
            match=re.fullmatch(r'n(\d+)_r(\d+)_m(seq|\d+)\.csv',path.name)
            if match:
                r.update(read(path.with_suffix('.time.csv').read_bytes())[0])
                r['repetition']=int(match[2]);warm=match[2]=='0';method='seq' if match[3]=='seq' else 'p'+match[3]
            if path.name.startswith('seq_before'):cohort+=':seq_before'
            if path.name.startswith('seq_after'):cohort+=':seq_after'
            add(r,folder.name,method,path.relative_to(ROOT).as_posix(),i,cohort,warm)

# Complete grids and unique round identities for the four formal cluster experiments.
for campaign,ns,methods,reps in [('cluster_crossing',[128,160,192,224,256],['seq','p1','p2','p3','p4','p6'],7),('cluster_scalability',[512,1024,2048,4096],['seq','p1','p2','p3','p4','p6'],7),('cluster_lapack',[2048,4096],['own','lapack'],6),('cluster_large',[6144,8192],['own','lapack','p6'],6)]:
    rr=[r for r in ROWS if r['campaign']==campaign and r['cohort']=='main' and not r['warmup']]
    assert len(rr)==len(ns)*len(methods)*reps,(campaign,len(rr))
    for n in ns:
        for method in methods:
            g=[r for r in rr if r['N']==n and r['method']==method]
            assert len(g)==reps and {int(r['repetition']) for r in g}==set(range(1,reps+1)),(campaign,n,method)
for camp in ('cierre_local_20260924','cierre_local_20260927'):
    assert len([r for r in ROWS if r['campaign']==camp and r['cohort']=='runs' and not r['warmup']])==168

SUMMARY=[];groups=defaultdict(list)
for r in ROWS:
    if r['warmup']:continue
    for metric,v in r.items():
        if (metric.endswith('_s') or metric=='seconds') and isinstance(v,float):
            groups[r['campaign'],r['cohort'],int(r['N']),int(r.get('P',1)),r['method'],metric].append((v,r))
for key,g in sorted(groups.items()):
    vals=[v for v,r in g];q1,_,q3=st.quantiles(vals,n=4,method='inclusive') if len(vals)>1 else [vals[0]]*3
    SUMMARY.append(dict(zip(('campaign','cohort','N','P','method','metric'),key),count=len(vals),q1=q1,median=st.median(vals),q3=q3,iqr=q3-q1,minimum=min(vals),maximum=max(vals),mean=st.mean(vals),sources=';'.join(sorted({r['origin'] for v,r in g}))))
def select(campaign,metric,cohort='main'):
    return [r for r in SUMMARY if r['campaign']==campaign and r['metric']==metric and r['cohort']==cohort]
def ratios(rr,base):
    ref={r['N']:r for r in rr if r['method']==base}
    for r in rr:
        if r['N'] in ref:
            r['ratio_reference']=base;r['speedup']=ref[r['N']]['median']/r['median'];r['efficiency']=r['speedup']/r['P'] if r['method'].startswith('p') else ''
    return rr
cross=ratios(select('cluster_crossing','application_s'),'seq')
for r in cross:r['clear_improvement']=int(r['method']!='seq' and r['speedup']>1.10 and r['q3']<next(s['q1'] for s in cross if s['N']==r['N'] and s['method']=='seq'))
scaling=ratios(select('cluster_scalability','application_s'),'seq')
external=ratios(select('cluster_scalability','external_s'),'seq')
lapack=ratios(select('cluster_lapack','factor_s'),'own')
large=ratios(select('cluster_large','factor_s'),'own')
for r in large:
    r['mpi_over_lapack']=next(x['median'] for x in large if x['N']==r['N'] and x['method']=='p6')/next(x['median'] for x in large if x['N']==r['N'] and x['method']=='lapack')
for name,rr in [('summary_crossing.csv',cross),('summary_scalability.csv',scaling),('summary_external.csv',external),('summary_lapack.csv',lapack),('summary_large_comparison.csv',large)]:write(name,rr)
write('first_crossing.csv',[dict(P=p,first_tested_N=min((r['N'] for r in cross if r['method']==f'p{p}' and r['clear_improvement']),default='none')) for p in (1,2,3,4,6)])
write('observations.csv',ROWS);write('summary_all.csv',SUMMARY);write('archive_members.csv',MEMBERS);write('verified_hashes.csv',HASHES)
validation=[]
for campaign in sorted({r['campaign'] for r in ROWS}):
    rr=[r for r in ROWS if r['campaign']==campaign]
    validation.append(dict(campaign=campaign,rows=len(rr),warmup_rows=sum(r['warmup'] for r in rr),**{k:max((r[k] for r in rr if k in r and r[k]>=0),default='not_exported') for k in ('relative_residual','projected_residual','exact_residual','factor_difference')}))
write('validation.csv',validation)
(OUT/'audit.json').write_text(json.dumps(AUDITS,indent=2),encoding='utf-8')

local_cross=[]
for round_ in (1,2,3):
    for n in (64,96,128,160,192,224,256):
        base_rows=[r for r in ROWS if r['campaign']=='umbral_20260922' and r['N']==n and r['cohort'] in (f'r{round_}:seq_before',f'r{round_}:seq_after')]
        bases={m:[r['seconds'] for r in base_rows if r['method']==m] for m in ('left','right','right_buffered')}
        best=min(bases,key=lambda m:st.median(bases[m]));q1=st.quantiles(bases[best],method='inclusive')[0]
        for p in (2,3):
            rr=[r for r in SUMMARY if r['campaign']=='umbral_20260922' and r['cohort']==f'r{round_}' and r['N']==n and r['P']==p and r['method']=='cyclic:local' and r['metric']=='seconds']
            assert len(rr)==1
            r=rr[0];speed=st.median(bases[best])/r['median']
            local_cross.append(dict(round=round_,N=n,P=p,base_variant=best,speedup=speed,clear_improvement=int(speed>1.1 and r['q3']<q1)))
write('summary_local_crossing.csv',local_cross)
closure=[]
for campaign in ('cierre_local_20260924','cierre_local_20260927'):
    for metric in ('application_s','external_s'):
        closure.extend(ratios(select(campaign,metric,'runs'),'seq'))
write('summary_local_closure.csv',closure)

from publication_visuals import configure, generate, COLORS, LABELS, MARKERS
configure()
def save(fig,name):
    for ext in ('png','svg'):fig.savefig(FIG/(name+'.'+ext),dpi=180)
    plt.close(fig)
def curves(rr,name,x='N',value='median',log=False,ylabel='Tiempo (s)',error=True):
    fig,ax=plt.subplots(figsize=(8,4.2),layout='constrained')
    for method in sorted({r['method'] for r in rr}):
        g=sorted((r for r in rr if r['method']==method),key=lambda r:r[x])
        kw=dict(marker=MARKERS.get(method,'o'),markersize=6,lw=1.8,label=LABELS.get(method,method),color=COLORS.get(method))
        if error:ax.errorbar([r[x] for r in g],[r[value] for r in g],yerr=[[r['median']-r['q1'] for r in g],[r['q3']-r['median'] for r in g]],capsize=3.5,**kw)
        else:ax.plot([r[x] for r in g],[r[value] for r in g],**kw)
    ax.set(xlabel='Orden de la matriz N' if x=='N' else x,ylabel=ylabel,yscale='log' if log else 'linear');ax.legend(ncol=3,fontsize=8.5);ax.grid(alpha=.2)
    if value=='speedup':ax.axhline(1,color='#546e7a',ls='--',lw=1.2)
    save(fig,name)
curves(cross,'01_cruce_application_vs_n',ylabel='application_s: mediana y Q1-Q3 (s)')
curves([r for r in cross if r['method']!='seq'],'02_cruce_speedup',value='speedup',ylabel='SEQ / MPI (cociente de medianas)',error=False)
curves([r for r in scaling if r['method']!='seq'],'03_speedup_vs_n',value='speedup',ylabel='Speedup de aplicación frente a SEQ',error=False)
fig,axs=plt.subplots(1,2,figsize=(10,4),layout='constrained')
n_colors={512:'#2e7d32',1024:'#1e88e5',2048:'#e65100',4096:'#8e24aa'}
n_markers={512:'o',1024:'s',2048:'^',4096:'D'}
for n in (512,1024,2048,4096):
    g=sorted((r for r in scaling if r['N']==n and r['method']!='seq'),key=lambda r:r['P'])
    axs[0].errorbar([r['P'] for r in g],[r['median'] for r in g],yerr=[[r['median']-r['q1'] for r in g],[r['q3']-r['median'] for r in g]],marker=n_markers[n],markersize=6,lw=1.8,capsize=3,color=n_colors[n],label=f'N={n}')
    axs[1].plot([r['P'] for r in g],[100*r['efficiency'] for r in g],marker=n_markers[n],markersize=6,lw=1.8,color=n_colors[n],label=f'N={n}')
axs[0].set(yscale='log',ylabel='application_s (s, log)');axs[1].set(ylabel='Eficiencia S/P (%)')
for ax in axs:ax.set(xlabel='Procesos MPI',xticks=[1,2,3,4,6]);ax.legend(fontsize=8);ax.grid(alpha=.2)
save(fig,'04_escalabilidad_y_eficiencia')
fig,ax=plt.subplots(figsize=(8,4),layout='constrained')
g_app=[r for r in scaling if r['method']=='p6'];g_ext=[r for r in external if r['method']=='p6']
ax.plot([str(r['N']) for r in g_app],[r['speedup'] for r in g_app],marker='o',markersize=7,lw=2.2,color='#1e88e5',label='Aplicación (application_s)')
ax.plot([str(r['N']) for r in g_ext],[r['speedup'] for r in g_ext],marker='s',markersize=7,lw=2.2,color='#c62828',label='Comando completo (external_s)')
ax.axhline(1,ls='--',color='#546e7a',lw=1.3,label='S=1 (Igual tiempo)');ax.set(xlabel='N (categorías), P=6',ylabel='Speedup frente al SEQ del mismo reloj');ax.legend(fontsize=8.5);ax.grid(alpha=.2);save(fig,'05_interno_vs_externo')
fig,ax=plt.subplots(figsize=(8,4),layout='constrained');bottom=[0]*4
ns=[512,1024,2048,4096]
phase_colors={'allocation_s':'#90caf9','generation_s':'#80cbc4','factor_s':'#1565c0','gather_s':'#ffab91'}
for metric in ('allocation_s','generation_s','factor_s','gather_s'):
    values=[100*st.mean(r[metric]/r['application_s'] for r in ROWS if r['campaign']=='cluster_scalability' and not r['warmup'] and r['N']==n and r['method']=='p6') for n in ns]
    ax.bar([str(n) for n in ns],values,bottom=bottom,color=phase_colors[metric],edgecolor='white',linewidth=0.8,label={'allocation_s':'Reserva','generation_s':'Generación','factor_s':'Factorización','gather_s':'Reunión'}[metric]);bottom=[a+b for a,b in zip(bottom,values)]
ax.set(xlabel='N, MPI P=6',ylabel='Media de fracciones por ejecución (%)',ylim=(0,100));ax.legend(ncol=4,fontsize=8);save(fig,'06_fases_aplicacion')
curves(lapack,'07_lapack_cluster',log=True,ylabel='factor_s: mediana y Q1-Q3 (s, log)')
curves(large,'08_comparacion_final',log=True,ylabel='factor_s: mediana y Q1-Q3 (s, log)')
fig,ax=plt.subplots(figsize=(7,3.8),layout='constrained');g=[r for r in large if r['method']=='p6']
ax.bar([f'N = {r["N"]}' for r in g],[r['mpi_over_lapack'] for r in g],color='#e65100',width=0.42,edgecolor='#bf360c',linewidth=1.2,label='Ratio: factor_s MPI P=6 / LAPACK 1 hilo')
ax.axhline(1,color='#00897b',ls='--',lw=1.5,label='Línea de paridad (Ratio = 1.0: igual tiempo)');ax.legend(fontsize=8.5)
for i,r in enumerate(g):
    val=r['mpi_over_lapack']
    ax.text(i,val+0.22,f"{val:.2f}x\n(LAPACK es {val:.2f}x más rápido)",ha='center',fontsize=9,weight='bold',color='#163b50')
ax.set(xlabel='Dimensión de la matriz N (campaña clúster)',ylabel='Mediana MPI P6 / mediana LAPACK 1 hilo',ylim=(0,10.5));ax.grid(axis='y',alpha=.2);save(fig,'09_distancia_mpi_lapack')
memory=select('memoria_20260921','seconds','.')
fig,axs=plt.subplots(1,2,figsize=(10,4.3),layout='constrained',gridspec_kw={'width_ratios':[1.5,1]})
for method in ('left','right','right_buffered'):
    g=sorted((r for r in memory if r['method']==method),key=lambda r:r['N'])
    for ax,subset,detail in ((axs[0],g,False),(axs[1],[r for r in g if r['N'] in (1000,1024)],True)):
        ax.errorbar([str(r['N']) if detail else r['N'] for r in subset],[r['median'] for r in subset],yerr=[[r['median']-r['q1'] for r in subset],[r['q3']-r['median'] for r in subset]],marker=MARKERS.get(method,'o'),markersize=6,lw=1.8,capsize=4,color=COLORS[method],label=LABELS[method])
        ax.set(yscale='log',xlabel='N (categorías)' if detail else 'Orden de la matriz N',ylabel='Factorización (s)');ax.grid(alpha=.15)
axs[0].legend(fontsize=8.5);axs[1].set_title('Detalle: 1000 y 1024',fontsize=11,weight='bold')
save(fig,'10_memoria_local')
curves(select('precluster_20260924','factor_s','lapack'),'11_lapack_local',log=True,ylabel='factor_s local (s, log); N=3072 es piloto')
fig,axs=plt.subplots(1,2,figsize=(10,3.8),layout='constrained')
session_styles=[('bloques_local_20260922','22/09 repetición','repeticion','#1e88e5','o','--'),('precluster_20260924','24/09 confirmación','confirmacion','#e65100','s','-')]
for camp,label,cohort,col,m,ls in session_styles:
    for ax,n in zip(axs,(1024,2048)):
        g=[r for r in select(camp,'total_s',cohort) if r['N']==n and r['method'] in ('1','4')]
        ax.plot([int(r['method']) for r in g],[1000*r['median'] for r in g],marker=m,markersize=6,lw=2.0,ls=ls,color=col,label=label)
        ax.set(title=f'N={n}, P=6',xlabel='Columnas por propietario b',ylabel='Total (ms)',xticks=[1,4]);ax.legend(fontsize=8.5);ax.grid(alpha=.2)
save(fig,'12_propiedad_columnas_sesiones')
generate(ROOT)
print(json.dumps(dict(observations=len(ROWS),summary_rows=len(SUMMARY),figures=len(list(FIG.glob('*.png'))),formal_cluster_useful=210+168+24+36)))
