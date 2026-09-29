"""Insertar tablas recalculadas y publicar Markdown/PDF del informe continuo."""
from pathlib import Path
import csv,re,json,hashlib
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,Table,TableStyle,PageBreak,KeepTogether
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import matplotlib

ROOT=Path(__file__).resolve().parents[1];D=ROOT/'data/processed'
def read(name):return list(csv.DictReader((D/name).open(encoding='utf-8')))
S=read('summary_all.csv');TABLES={};TRACE=[]
def rows(camp,metric,cohort='main',n=None,p=None,methods=None):
    return [r for r in S if r['campaign']==camp and r['metric']==metric and r['cohort']==cohort and (n is None or int(r['N'])==n) and (p is None or int(r['P'])==p) and (methods is None or r['method'] in methods)]
def one(camp,metric,n,method,cohort='main',p=None):
    rr=[r for r in rows(camp,metric,cohort,n,p) if r['method']==method];assert len(rr)==1,(camp,n,method,len(rr));return rr[0]
def num(r,key='median',scale=1,digits=3):return f'{float(r[key])*scale:.{digits}f}'
def record(name,headers,data,source_rows):
    TABLES[name]=[headers,*data]
    for r in source_rows:TRACE.append(dict(table=name,**r))
rr=rows('memoria_20260921','seconds','.')
record('memory',['N','Left (ms)','Right (ms)','Vector (ms)'],[[n,*[num(one('memoria_20260921','seconds',n,m,'.'),scale=1000,digits=3) for m in ('left','right','right_buffered')]] for n in (64,128,256,512,1000,1024)],rr)
rr=rows('mpi_local_20260921','seconds','.',1024,3)
record('mpi_local',['Reparto y kernel','Mediana (ms)','Q1 (ms)','Q3 (ms)'],[[r['method'],*[num(r,k,1000) for k in ('median','q1','q3')]] for r in rr],rr)
rr=rows('precluster_20260924','total_s','confirmacion',p=6)
record('blocks',['N','b=1 total (ms)','b=4 total (ms)'],[[n,*[num(one('precluster_20260924','total_s',n,m,'confirmacion',6),scale=1000) for m in ('1','4')]] for n in (1024,2048)],rr)
rr=read('summary_local_closure.csv');select=[r for r in rr if r['N']=='2048' and r['method']=='p6']
record('local_closure',['Sesión','Reloj','MPI P6 (s)','Speedup','E (%)'],[[r['campaign'][-8:],r['metric'],num(r),num(r,'speedup'),num(r,'efficiency',100,1)] for r in select],select)
rr=read('first_crossing.csv')
record('crossing_first',['P','Primer N ensayado que cumple'],[[r['P'],r['first_tested_N'].replace('none','ninguno')] for r in rr],[])
rr=[r for r in read('summary_crossing.csv') if r['N']=='256']
rr.sort(key=lambda r:0 if r['method']=='seq' else int(r['P']))
record('crossing_256',['Método','Mediana ms','Q1 ms','Q3 ms','S','E %'],[[r['method'],*[num(r,k,1000) for k in ('median','q1','q3')],num(r,'speedup'),num(r,'efficiency',100,1) if r['efficiency'] else '-'] for r in rr],rr)
a=read('summary_scalability.csv');e=read('summary_external.csv')
rr=[r for r in a if r['method']=='p6'];data=[]
for r in rr:
    ext=next(x for x in e if x['N']==r['N'] and x['method']=='p6')
    data.append([r['N'],num(r),num(r,'speedup'),num(r,'efficiency',100,1),num(ext),num(ext,'speedup')])
record('scaling_p6',['N','App P6 (s)','S app','E app %','Ext P6 (s)','S externo'],data,rr+[r for r in e if r['method']=='p6'])
rr=[r for r in S if r['campaign']=='cluster_lapack' and r['cohort']=='main' and r['metric'] in ('factor_s','total_s')]
data=[]
for n in (2048,4096):
    for metric in ('factor_s','total_s'):
        own=one('cluster_lapack',metric,n,'own');lap=one('cluster_lapack',metric,n,'lapack')
        data.append([n,metric,num(own,digits=6),num(lap,digits=6),f"{float(own['median'])/float(lap['median']):.3f}"])
record('lapack_cluster',['N','Reloj','C propio (s)','LAPACK (s)','Propio/LAPACK'],data,rr)
rr=read('summary_large_comparison.csv');rr.sort(key=lambda r:(int(r['N']),{'own':0,'p6':1,'lapack':2}[r['method']]))
record('large',['N','Método','n obs.','Q1 (s)','Mediana (s)','Q3 (s)'],[[r['N'],r['method'],r['count'],*[num(r,k,1,6) for k in ('q1','median','q3')]] for r in rr],rr)
data=[]
for n in (6144,8192):
    mpi=next(r for r in rr if r['N']==str(n) and r['method']=='p6');lap=next(r for r in rr if r['N']==str(n) and r['method']=='lapack')
    data.append([n,num(mpi,'speedup'),num(mpi,'efficiency',100,1),num(lap,'speedup'),num(mpi,'mpi_over_lapack')])
record('large_ratios',['N','C/MPI','E MPI %','C/LAPACK','MPI/LAPACK'],data,rr)
rr=rows('cluster_large','generation_s')
record('generation_large',['N','Método','Generación mediana (s)'],[[r['N'],r['method'],num(r,digits=6)] for r in rr],rr)
rr=[r for r in read('validation.csv') if r['campaign'] in ('memoria_20260921','left_right_mpi_20260922','cierre_local_20260924','cierre_local_20260927','cluster_crossing','cluster_scalability','cluster_lapack','cluster_large')]
def sci(v):return '-' if v=='not_exported' else f'{float(v):.3e}'
record('validation',['Campaña','Filas auditadas','Residuo completo máx.','Proyectado máx.','Diferencia máx.'],[[r['campaign'],r['rows'],sci(r['relative_residual'] if r['relative_residual']!='not_exported' else r['exact_residual']),sci(r['projected_residual']),sci(r['factor_difference'])] for r in rr],[])
aa=json.loads((D/'audit.json').read_text());rr=[r for r in aa if 'cpu_stat_delta' in r]
record('throttling',['Campaña','Delta períodos','Delta throttled','Delta throttled_usec'],[[r['archive'].replace('campana_','').replace('_20260928.tar.gz',''),r['cpu_stat_delta']['nr_periods'],r['cpu_stat_delta']['nr_throttled'],r['cpu_stat_delta']['throttled_usec']] for r in rr],[])
fields=list(dict.fromkeys(k for r in TRACE for k in r))
with (D/'document_table_trace.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(TRACE)
def mdtable(t):return '\n'.join(['| '+' | '.join(map(str,t[0]))+' |','| '+' | '.join(['---']*len(t[0]))+' |']+['| '+' | '.join(map(str,r))+' |' for r in t[1:]])
text=(ROOT/'docs/investigacion_completa.md.in').read_text(encoding='utf-8')
for name,t in TABLES.items():text=text.replace('@@TABLE:'+name+'@@',mdtable(t))
assert '@@TABLE' not in text
(ROOT/'docs/investigacion_completa.md').write_text(text,encoding='utf-8')

from publication_pdf import publish
pdf=publish(ROOT,text)
from pypdf import PdfReader
print(json.dumps(dict(pdf=str(pdf),pages=len(PdfReader(pdf).pages),tables=len(TABLES),words=len(text.split()))))
