"""Verificación independiente de copias, cuantiles, enlaces y resultados publicados."""
from pathlib import Path
import csv,hashlib,json,math,re,sys,platform,importlib.metadata
from delivery_resources import inspect_resources
from datetime import datetime, timezone
from urllib.parse import unquote
import zipfile, tarfile
ROOT=Path(__file__).resolve().parents[2]
def read(path):return list(csv.DictReader(path.open(encoding='utf-8-sig')))
obs=read(ROOT/'data/processed/observations.csv');summary=read(ROOT/'data/processed/summary_all.csv')
# Independent inclusive percentile interpolation, rather than statistics.quantiles.
def percentile(v,p):
    x=sorted(v);at=(len(x)-1)*p;low=math.floor(at);high=math.ceil(at)
    return x[low]+(x[high]-x[low])*(at-low)
for s in summary:
    rr=[r for r in obs if r['campaign']==s['campaign'] and r['cohort']==s['cohort'] and int(float(r['N']))==int(s['N']) and int(float(r.get('P') or 1))==int(s['P']) and r['method']==s['method'] and r['warmup']=='0' and r.get(s['metric'])]
    vals=[float(r[s['metric']]) for r in rr]
    assert len(vals)==int(s['count']),(s,len(vals))
    for key,p in (('q1',.25),('median',.5),('q3',.75)):
        assert math.isclose(percentile(vals,p),float(s[key]),rel_tol=1e-12,abs_tol=1e-14),(s,key)
for file in ('summary_crossing.csv','summary_scalability.csv','summary_external.csv','summary_lapack.csv','summary_large_comparison.csv','summary_strong_scaling_8192.csv','summary_strong_application_8192.csv','summary_strong_pilots.csv'):
    rr=read(ROOT/'data/processed'/file)
    for r in rr:
        base=next(x for x in rr if x['N']==r['N'] and x['method']==r['ratio_reference'])
        assert math.isclose(float(base['median'])/float(r['median']),float(r['speedup']),rel_tol=1e-12)
        if r['method'].startswith('p'):assert math.isclose(float(r['speedup'])/int(r['P']),float(r['efficiency']),rel_tol=1e-12)
expected={'1':'none','2':'256','3':'192','4':'224','6':'256'}
assert {r['P']:r['first_tested_N'] for r in read(ROOT/'data/processed/first_crossing.csv')}==expected
formal={c:len([r for r in obs if r['campaign']==c and r['cohort']=='main' and r['warmup']=='0']) for c in ('cluster_crossing','cluster_scalability','cluster_lapack','cluster_large','cluster_strong_8192')}
assert list(formal.values())==[210,168,24,36,42]
strong=read(ROOT/'data/processed/summary_strong_scaling_8192.csv')
assert [int(r['P']) for r in strong]==[1,2,4,8,16,32]
assert all(int(r['count'])==7 for r in strong)
assert math.isclose(float(strong[-1]['speedup']),4.73358273475156,rel_tol=1e-12)
assert math.isclose(float(strong[-1]['efficiency']),.14792446046098624,rel_tol=1e-12)
assert float(strong[2]['maximum'])<float(strong[3]['minimum'])
audits=json.loads((ROOT/'data/processed/audit.json').read_text())
legacy={r['archive']:r for r in audits if not r['archive'].startswith('strong_scaling_')}
assert all(all(r['measured_source_byte_matches'].values()) for r in legacy.values())
measured=ROOT/'tests/fixtures/measured_sources'
for name,expected_hash in json.loads((measured/'sha256.json').read_text()).items():
    assert hashlib.sha256((measured/name).read_bytes()).hexdigest()==expected_hash,name

resources=inspect_resources(ROOT)
links=[]
for p in [ROOT/'README.md',ROOT/'MANIFEST.md',*(ROOT/'docs').glob('*.md'),*(ROOT/'src/experimentos/implementacion_con_matriz_sin_generar').glob('*.md')]:
    for target in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
        target=unquote(target.strip('<>')).split('#')[0]
        if not target or re.match(r'[a-zA-Z]+:',target):continue
        assert (p.parent/target).exists(),(p,target)
        links.append(target)
out=dict(status='PASS',verified_at_utc=datetime.now(timezone.utc).isoformat(),baseline_files_verified=len(json.loads((measured/'sha256.json').read_text())),summary_groups_verified=len(summary),formal_cluster_useful=formal,local_links_verified=len(links),resources=resources,scope='Cuantiles, cocientes, grillas, hashes históricos, archivos de paquetes, enlaces y correspondencia binaria de imágenes con el Word.',not_verified=['Ejecución o compilación C/MPI en esta verificación','Equivalencia funcional actual de fuentes refactorizados','Maquetación visual, paginación o exactitud narrativa del Word','Regeneración del Word o de sus imágenes'],python=sys.version)
(ROOT/'docs/verificacion_entrega.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
