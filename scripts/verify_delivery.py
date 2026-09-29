"""Verificación independiente de copias, cuantiles, enlaces y resultados publicados."""
from pathlib import Path
import csv,hashlib,json,math,re,sys,platform,importlib.metadata
from pypdf import PdfReader
ROOT=Path(__file__).resolve().parents[1]
def read(path):return list(csv.DictReader(path.open(encoding='utf-8-sig')))
copies=read(ROOT/'docs/procedencia_copias.csv')
for r in copies:
    p=ROOT/r['path'];assert p.is_file(),p
    assert p.stat().st_size==int(r['bytes']) and hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256'],p
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
for file in ('summary_crossing.csv','summary_scalability.csv','summary_external.csv','summary_lapack.csv','summary_large_comparison.csv'):
    rr=read(ROOT/'data/processed'/file)
    for r in rr:
        base=next(x for x in rr if x['N']==r['N'] and x['method']==r['ratio_reference'])
        assert math.isclose(float(base['median'])/float(r['median']),float(r['speedup']),rel_tol=1e-12)
        if r['method'].startswith('p'):assert math.isclose(float(r['speedup'])/int(r['P']),float(r['efficiency']),rel_tol=1e-12)
expected={'1':'none','2':'256','3':'192','4':'224','6':'256'}
assert {r['P']:r['first_tested_N'] for r in read(ROOT/'data/processed/first_crossing.csv')}==expected
formal={c:len([r for r in obs if r['campaign']==c and r['cohort']=='main' and r['warmup']=='0']) for c in ('cluster_crossing','cluster_scalability','cluster_lapack','cluster_large')}
assert list(formal.values())==[210,168,24,36]
audits=json.loads((ROOT/'data/processed/audit.json').read_text())
assert all(all(r['measured_source_byte_matches'].values()) for r in audits)
measured=ROOT/'archive/src_medidos_20260928'
for name,expected_hash in json.loads((measured/'sha256.json').read_text()).items():
    assert hashlib.sha256((measured/name).read_bytes()).hexdigest()==expected_hash,name
refactor=json.loads((ROOT/'docs/checks/refactor_equivalence.json').read_text())
assert refactor['status']=='PASS'
assert refactor['source_hash_mode']=='SHA-256 after CRLF to LF normalization for Git portability'
for name,expected_hash in refactor['current_sources'].items():
    assert hashlib.sha256((ROOT/'src'/name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()==expected_hash,name
links=[]
for p in [ROOT/'README.md',ROOT/'MANIFEST.md',*(ROOT/'docs').glob('*.md')]:
    txt=p.read_text(encoding='utf-8')
    for target in re.findall(r'\]\(([^)]+)\)',txt):
        if target.startswith(('http:','https:','#')):continue
        assert (p.parent/target.split('#')[0]).exists(),(p,target)
        links.append(target)
text=(ROOT/'docs/investigacion_completa.md').read_text(encoding='utf-8')
assert '@@TABLE' not in text and '¿' not in text
assert not re.search(r'^#+\s+Etapa\b|ChatGPT|el agente|el usuario pregunt',text,re.M|re.I)
pdf=ROOT/'output/pdf/Cholesky_Investigacion_Integral.pdf'
reader=PdfReader(pdf);pdftext='\n'.join(p.extract_text() for p in reader.pages)
assert '\ufffd' not in pdftext and len(reader.pages)>=15
figs=list((ROOT/'figures').glob('*.png'));assert len(figs)==16
assert all(p.with_suffix('.svg').exists() for p in figs)
out=dict(copies_verified=len(copies),summary_groups_verified=len(summary),formal_cluster_useful=formal,measured_cluster_sources_match=True,current_cluster_sources_match=all(all(r['current_source_byte_matches'].values()) for r in audits),local_links_verified=len(links),png_figures=len(figs),svg_figures=len(figs),pdf_pages=len(reader.pages),narrative_words=len(text.split()),python=sys.version,platform=platform.platform(),packages={k:importlib.metadata.version(k) for k in ('matplotlib','reportlab','pypdf')},scope='Checks of original copies, independent quantiles, ratios, grids, links and PDF text; visual review and Linux compilation are recorded separately.')
(ROOT/'docs/verificacion_entrega.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False,indent=2))
