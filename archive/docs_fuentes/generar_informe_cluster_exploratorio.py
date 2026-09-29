"""Etapa 15 revisada: análisis de CSV originales y contraste con la bitácora.

No ejecuta benchmarks ni modifica fuentes. Conserva separadas las cohortes.
Ejecutar desde cualquier directorio con matplotlib, reportlab y pypdf.
"""
from pathlib import Path
import csv
import hashlib
import io
import json
import re
import statistics as st
import sys
import tarfile
import math
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader

DATA = ROOT / 'desde_cero/resultados/cluster_exploratorio_20260928'
SOURCE = DATA / 'bitacora_original.md'
text = SOURCE.read_text(encoding='utf-8-sig')
sections = {int(n): body for n, body in re.findall(r'^# (\d+)\. ([\s\S]*?)(?=^# \d+\. |\Z)', text, re.M)}

def tables(section):
    groups = re.findall(r'(?:^\|.*\|\s*\n)+', sections[section], re.M)
    return [[[v.strip().strip('`') for v in line.strip().strip('|').split('|')]
             for line in g.strip().splitlines() if not re.match(r'^\|[\s:|\-]+\|$', line)] for g in groups]

def number(s):
    return float(s.replace(' s', ''))

def write_csv(name, rows):
    with (DATA / name).open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

observations = []
scan = []
for section, cohort, affinity in [(14, 'scan_large', 'SEQ libre; MPI solicitado core'), (17, 'scan_small', 'SEQ CPU0; MPI solicitado core')]:
    table = tables(section)[0]
    assert len(table) == (5 if section == 14 else 3)
    for row in table[1:]:
        n = int(row[0]); seq = number(row[1])
        for method, value in zip(['seq', 'p1', 'p2', 'p3', 'p4', 'p6'], row[1:]):
            p = 1 if method == 'seq' else int(method[1:])
            r = dict(cohort=cohort, section=section, N=n, method=method, P=p, rep=1,
                     application_s=number(value), factor_s='', gather_s='', affinity=affinity,
                     evidence='tabla redondeada; validez declarada en bitácora')
            observations.append(r)
            scan.append(dict(cohort=cohort, N=n, method=method, P=p, application_s=number(value),
                             ratio_seq_mpi=seq/number(value), efficiency_pct=100*seq/number(value)/p))
for row in tables(12)[0][1:]:
    for method, pos in [('seq', 1), ('p6', 2)]:
        observations.append(dict(cohort='pilot',section=12,N=int(row[0]),method=method,P=1 if method=='seq' else 6,
            rep=1,application_s=number(row[pos]),factor_s='',gather_s='',affinity='SEQ libre; MPI solicitado core',
            evidence='tabla redondeada; valid=1 declarado'))
control = {}
for idx, method in enumerate(['seq', 'p6']):
    control[method] = []
    for row in tables(13)[idx][1:]:
        factor, app = number(row[1]), number(row[2 if method=='seq' else 3])
        gather = '' if method=='seq' else number(row[2])
        assert row[-1] == '1'
        r = dict(cohort='control_4096',section=13,N=4096,method=method,P=1 if method=='seq' else 6,
                 rep=int(row[0]),application_s=app,factor_s=factor,gather_s=gather,
                 affinity='SEQ libre; MPI solicitado core',evidence='tabla redondeada; valid=1 declarado')
        observations.append(r); control[method].append(r)
assert len(observations) == 50
assert all(r['application_s'] > 0 for r in observations)
write_csv('observaciones_tablas.csv', observations)
archive = DATA / 'evidencia_preformal_20260928.tar.gz'
with tarfile.open(archive) as tar:
    members = tar.getmembers()
    assert len({m.name for m in members}) == len(members)
    files = {m.name: tar.extractfile(m).read() for m in members if m.isfile()}
prefix = 'evidencia_preformal_20260928/'
hash_lines = files[prefix+'SHA256SUMS.txt'].decode().splitlines()
listed = set()
for line in hash_lines:
    expected, name = line.split(None, 1)
    assert hashlib.sha256(files[name]).hexdigest() == expected
    listed.add(name)
assert set(files)-listed == {prefix+'SHA256SUMS.txt'}
originals = {}
for name, content in files.items():
    if not name.endswith('.csv'):
        continue
    rr = list(csv.DictReader(io.StringIO(content.decode())))
    assert len(rr) == 1
    r = rr[0]
    assert all(math.isfinite(float(v)) for v in r.values())
    assert all(float(v) >= 0 for k,v in r.items() if k.endswith('_s'))
    assert r['valid'] == '1' and 0 <= float(r['projected_residual']) <= 1e-12
    assert (0 <= float(r['exact_residual']) <= 1e-12) if int(r['N']) <= 128 else float(r['exact_residual']) == -1
    assert float(r['max_local_s']) + 1e-12 >= float(r['application_s'])
    assert abs(sum(float(r[k]) for k in ['allocation_s','generation_s','factor_s','gather_s'])-float(r['application_s'])) <= max(1e-11, 1e-10*float(r['application_s']))
    assert name[:-4]+'.err' in files
    originals[Path(name).name] = r
assert len(originals) == 53
assert all(not b for n,b in files.items() if n.endswith(('.err','.log')))
differences = []
for r in observations:
    base = {'scan_large':'scan','scan_small':'scan_small','pilot':'piloto','control_4096':'control'}[r['cohort']]
    method = 'seq' if r['method']=='seq' else 'mpi'
    name = f"{base}_{method}_n{r['N']}" + (f"_p{r['P']}" if method=='mpi' else '')
    name += (f"_rep{r['rep']}" if base=='control' else '') + '.csv'
    raw = originals[name]
    differences.append(abs(float(raw['application_s'])-r['application_s'])/r['application_s'])
    assert differences[-1] < 1e-5
    for k in ['application_s','factor_s','gather_s']:
        r[k] = float(raw[k])
    r['evidence'] = 'CSV original del paquete; integridad y coherencia verificadas'
write_csv('observaciones_originales.csv', [dict(file=n,**r) for n,r in sorted(originals.items())])
for r in scan:
    matches = [o for o in observations if o['cohort']==r['cohort'] and o['N']==r['N']]
    r['application_s'] = next(o['application_s'] for o in matches if o['method']==r['method'])
    r['ratio_seq_mpi'] = next(o['application_s'] for o in matches if o['method']=='seq')/r['application_s']
    r['efficiency_pct'] = 100*r['ratio_seq_mpi']/r['P']
write_csv('cocientes_escaneo.csv', scan)
validation = []
for section, method in [(9, 'seq'), (10, 'p6')]:
    block = re.search(r'N,P,allocation_s[^\n]*\n128,[^\n]+', sections[section]).group()
    row = next(csv.DictReader(io.StringIO(block)))
    assert int(row['valid']) == 1
    for k in ['projected_residual', 'exact_residual']:
        assert 0 <= float(row[k]) <= 1e-12
    phases = sum(float(row[k]) for k in ['allocation_s','generation_s','factor_s','gather_s'])
    assert abs(phases-float(row['application_s'])) < 1e-12
    validation.append(dict(section=section,method=method,**row))
write_csv('validacion_transcrita.csv', validation)

summaries = []
for method, rows in control.items():
    vals = [r['application_s'] for r in rows]
    q1, _, q3 = st.quantiles(vals, n=4, method='inclusive')
    summaries.append(dict(method=method,n=3,median_s=st.median(vals),mean_s=st.mean(vals),
        min_s=min(vals),max_s=max(vals),q1_s=q1,q3_s=q3,sample_sd_s=st.stdev(vals),
        cv_pct=100*st.stdev(vals)/st.mean(vals),range_over_median_pct=100*(max(vals)-min(vals))/st.median(vals)))
write_csv('estadisticas_control.csv', summaries)
S = {r['method']:r for r in summaries}
speed = S['seq']['median_s']/S['p6']['median_s']
phase = [dict(rep=r['rep'],factor_pct=100*r['factor_s']/r['application_s'],
              gather_pct=100*r['gather_s']/r['application_s'],
              rest_pct=100*(r['application_s']-r['factor_s']-r['gather_s'])/r['application_s']) for r in control['p6']]
write_csv('fracciones_control.csv', phase)
throttle=[]
for metric,before,after,delta in tables(16)[0][1:]:
    before,after,delta=int(before),int(after),int(delta)
    assert after-before==delta
    throttle.append(dict(metric=metric,before=before,after=after,delta=delta))
write_csv('throttling_transcrito.csv', throttle)
hashes = dict(re.findall(r'(main_candidate\.c|cholesky(?:_mpi)?\.[ch])\s*\n([A-F0-9]{64})', sections[6]))
assert len(hashes)==5
checks=[]
for name, expected in hashes.items():
    actual=hashlib.sha256((DATA/'fuentes'/name).read_bytes()).hexdigest()
    assert actual.upper()==expected
    checks.append(dict(file=name,sha256=actual,match_recorded=True))
    assert files[prefix+name] == (DATA/'fuentes'/name).read_bytes()
manifest=dict(source=str(SOURCE.relative_to(ROOT)),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    evidence='CSV originales del clúster auditados; bitácora para contexto, afinidad y cpu.stat.',
    archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    verified_hash_entries=len(hash_lines),original_csv_count=len(originals),
    empty_error_files=sum(n.endswith('.err') for n in files),empty_build_logs=2,
    max_relative_table_difference=max(differences),
    table_observations=50,validation_rows=2,diagnostic_runs=1,reported_runs_total=53,
    formal_campaign_executed=False,code_hashes=checks,
    statistical_convention='Q1/Q3 inclusivos por interpolación lineal; desviación muestral ddof=1; cohortes separadas')
(DATA/'auditoria.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
palette=['#176b87','#c06425','#278264','#9355a0']
def save(fig,name):
    fig.savefig(DATA/name,dpi=180,bbox_inches='tight');plt.close(fig)
fig,ax=plt.subplots(1,2,figsize=(9.8,3.8),layout='constrained')
for n,col in zip([512,1024,2048,4096],palette):
    rs=[r for r in scan if r['N']==n and r['method']!='seq']
    ps=[r['P'] for r in rs]
    ax[0].plot(ps,[r['application_s'] for r in rs],'-o',color=col,label=f'N={n}')
    ax[1].plot(ps,[r['ratio_seq_mpi'] for r in rs],'-o',color=col,label=f'N={n}')
ax[0].set(yscale='log',ylabel='Aplicación MPI (s, escala log)',xlabel='Procesos',xticks=[1,2,3,4,6])
ax[1].plot([1,6],[1,6],'k--',lw=1,label='Referencia S=P')
ax[1].axhline(1,color='gray',lw=.8)
ax[1].set(ylabel='Cociente SEQ / MPI',xlabel='Procesos',xticks=[1,2,3,4,6])
for a in ax:a.grid(alpha=.2);a.legend(fontsize=8)
save(fig,'escaneo_mayor.png')
fig,ax=plt.subplots(1,2,figsize=(9.8,3.6),layout='constrained')
for a,n in zip(ax,[128,256]):
    rs=[r for r in scan if r['N']==n]
    a.bar(['SEQ','P1','P2','P3','P4','P6'],[r['application_s']*1000 for r in rs],color=['#637681']+['#176b87']*5)
    a.axhline(rs[0]['application_s']*1000,color='#c06425',ls='--')
    a.set(title=f'N={n}',ylabel='Aplicación (ms)');a.grid(axis='y',alpha=.2)
save(fig,'cruce_exploratorio.png')
fig,ax=plt.subplots(1,2,figsize=(9.8,3.5),layout='constrained')
for a,method in zip(ax,['seq','p6']):
    vals=[r['application_s'] for r in control[method]]
    a.plot([1,2,3],vals,'o-',color='#176b87')
    a.axhline(st.median(vals),ls='--',color='#c06425',label='Mediana')
    a.set(title='Secuencial' if method=='seq' else 'MPI P=6',xlabel='Repetición',ylabel='Aplicación (s)',xticks=[1,2,3])
    a.ticklabel_format(useOffset=False,axis='y');a.grid(alpha=.2);a.legend()
save(fig,'control_4096.png')
fig,ax=plt.subplots(figsize=(9.8,2.7),layout='constrained')
left=[0,0,0]
for key,label,col in [('factor_pct','Factor: cálculo + MPI + esperas','#176b87'),('gather_pct','Reunión + reconstrucción','#c06425'),('rest_pct','Reserva + generación','#91b8aa')]:
    vals=[r[key] for r in phase];ax.barh([1,2,3],vals,left=left,label=label,color=col)
    left=[x+y for x,y in zip(left,vals)]
ax.set(xlim=(0,100),xlabel='Porcentaje del tiempo de aplicación',ylabel='Repetición',yticks=[1,2,3])
ax.legend(loc='upper center',bbox_to_anchor=(.5,-.28),ncol=1,fontsize=8)
save(fig,'fases_4096.png')

styles=getSampleStyleSheet()
styles['BodyText'].fontSize=10;styles['BodyText'].leading=14
styles['Title'].fontSize=21;styles['Title'].leading=25;styles['Title'].textColor=colors.HexColor('#174b60')
styles['Heading2'].fontSize=12;styles['Heading2'].leading=15;styles['Heading2'].textColor=colors.HexColor('#174b60')
story=[];md=[]
def page(title):
    if story:story.append(PageBreak())
    story.extend([Paragraph(escape(title),styles['Title']),Spacer(1,10)])
    md.append('\n# '+title+'\n')
def h(title):
    story.append(Paragraph(escape(title),styles['Heading2']));md.append('\n## '+title+'\n')
def p(t):
    story.extend([Paragraph(escape(t),styles['BodyText']),Spacer(1,7)]);md.append(t+'\n')
def table(rows,widths):
    t=Table([[Paragraph(escape(str(c)),styles['BodyText']) for c in row] for row in rows],colWidths=widths,repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecf0')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,0),(-1,0),.5,colors.HexColor('#adc5cf'))]))
    story.extend([t,Spacer(1,8)])
    md.extend(['| '+' | '.join(map(str,rows[0]))+' |','| '+' | '.join(['---']*len(rows[0]))+' |'])
    md.extend('| '+' | '.join(map(str,r))+' |' for r in rows[1:]);md.append('')
def chart(name,height):
    story.extend([Image(str(DATA/name),width=500,height=height),Spacer(1,6)])
    md.append(f'![{name}]({name})\n')

page('Etapa 15: primeros resultados del clúster')
p('Cholesky en C y MPI | Experimentos del 28/09/2026. Edición revisada con archivos originales del clúster. Continuación de las catorce etapas locales. Estado: exploración completada; campaña formal de cruce no incluida en la evidencia recibida.')
h('Pregunta y respuesta provisional')
p('¿El candidato conserva corrección y obtiene ganancias en el nuevo entorno? Las ejecuciones documentadas pasan validación. El control repetido de N=4096 muestra un cociente de medianas de aproximadamente 2,50 frente al secuencial. El escaneo sugiere un cruce entre N=128 y N=256 y un comportamiento no monótono con P. Todavía no hay una curva de escalabilidad confirmada con repeticiones para cada configuración.')
h('Qué evidencia recibimos')
table([['Conjunto','Ejecuciones descritas','Uso'],['Validación N=128','2','Corrección secuencial y MPI P6'],['Piloto N=512..4096','8','Elegir tamaños'],['Control N=4096','6 (3 por método)','Dispersión dentro de la sesión'],['Escaneo mayor y pequeño','24 + 12','Localizar preguntas'],['Diagnóstico de cuota','1','Comprobar throttling'],['Campaña formal de cruce','0; 240 previstas','Plan, sin resultados todavía']],[175,125,200])
p('Se recibieron 53 CSV originales, sus 53 archivos de error, dos logs de compilación, cinco fuentes y un manifiesto SHA-256 en evidencia_preformal_20260928.tar.gz. Los 113 hashes del manifiesto coinciden. Los gráficos y las estadísticas de esta edición se recalculan desde los CSV originales, manteniendo separados los conjuntos. Las 50 observaciones de las tablas anteriores coinciden salvo redondeo; las conclusiones se mantienen.')
h('Continuidad del proyecto')
p('Conservamos right-looking, vector local, reparto cíclico 1D b=1, generación distribuida y L en rango 0. Los cinco SHA-256 de la bitácora coinciden con las fuentes actuales, cuya copia queda archivada con este análisis. No se cambiaron los algoritmos. Las decisiones previas explican el candidato; los tiempos de WSL no se usan para calcular ganancias en el clúster.')

page('Entorno, corrección y significado de los relojes')
p('La sesión declara AMD EPYC 7B12, GCC 13.3 y Open MPI 4.1.6. Ve 128 CPUs y dos nodos NUMA. cpu.max=600000 100000 limita la capacidad agregada a seis CPUs equivalentes; memory.max=25769803776 corresponde a 24 GiB. Esto no acredita exclusividad sobre seis núcleos.')
h('Pregunta: ¿se preservó la corrección?')
table([['N=128','Secuencial','MPI P=6'],['Residuo proyectado','3,8964e-16','3,8964e-16'],['Residuo completo','3,7903e-16','3,7903e-16'],['valid','1','1']],[170,165,165])
p('El máximo residuo proyectado informado en los tamaños explorados es 2,274918e-15, unas 440 veces menor que 1e-12. Para N>128, exact_residual=-1 indica que no se calculó el residuo completo. Ocho proyecciones son evidencia numérica, no una prueba exhaustiva. Residuos iguales no demuestran que los factores sean idénticos elemento a elemento. El alcance es la familia SPD diagonalmente dominante generada con semilla 2026.')
h('Contrato comprobado en main_candidate.c')
table([['Campo','Interpretación'],['application_s','Rango 0: reserva + generación + factor + reunión/reconstrucción. Excluye validación y arranque/cierre MPI.'],['factor_s','Tiempo de la fase de factor en rango 0; incluye MPI y esperas, no solo operaciones aritméticas.'],['gather_s','MPI_Gatherv y reconstrucción serial de L en rango 0; no es tiempo puro de red.'],['max_local_s','Máximo del intervalo local completo entre rangos; no son máximos por fase.'],['validation_s','Comprobación posterior al tiempo de aplicación. No sustituye una medición externa.']],[110,390])
p('Las fases consecutivas suman el total en cada ejecución. Debe resumirse application_s directamente: sumar medianas de fases no reconstruye necesariamente su mediana. Se verificó la suma en los 53 CSV originales dentro de su precisión impresa, además de tiempos finitos y no negativos, valid=1 y residuos dentro del criterio.')
h('Conclusión y próxima pregunta')
p('El traslado tiene evidencia de corrección para las entradas ensayadas. Falta medir de manera repetida cuánto cuesta producir L bajo una afinidad controlada y cuánto tarda el comando completo.')

page('Escaneo mayor: dónde aparecen las preguntas')
chart('escaneo_mayor.png',194)
p('Figura 1. Sección 14 de la bitácora: una observación por configuración, sin barras de dispersión. Las líneas conectan puntos medidos; no describen tamaños ni procesos intermedios. El secuencial de este escaneo no tenía afinidad fijada.')
table([['N','SEQ (s)','P del mínimo MPI','MPI (s)','SEQ/MPI'], *[[n,f"{next(r['application_s'] for r in scan if r['N']==n and r['method']=='seq'):.6f}", min([r for r in scan if r['N']==n and r['method']!='seq'],key=lambda x:x['application_s'])['P'],f"{min(r['application_s'] for r in scan if r['N']==n and r['method']!='seq'):.6f}",f"{max(r['ratio_seq_mpi'] for r in scan if r['N']==n and r['method']!='seq'):.2f}"] for n in [512,1024,2048,4096]]],[60,110,110,110,110])
h('Observaciones que merecen confirmación')
p('Para N=2048, P=4 tarda 43,1% más que P=3; pasar de P=4 a P=6 reduce el tiempo 67,4%. En N=4096, P=4 también empeora frente a P=3. P=6 produce el menor tiempo observado en tres de los cuatro tamaños, mientras N=512 favorece P=4. Son mínimos seleccionados de observaciones únicas, no recomendaciones definitivas.')
p('Al duplicar N de 2048 a 4096, el total secuencial crece 9,03 veces y MPI P=6 crece 21,52 veces dentro de este escaneo. El total contiene varias fases: no debe exigirse un factor ocho exacto. La diferencia justifica estudiar ambos tamaños; no demuestra por sí misma un problema de caché, NUMA, comunicación o cuota.')
h('Cómo leer el resultado cercano a seis')
p('N=2048/P=6 da 5,97 en el escaneo y 6,15 en el piloto separado. Se conservan ambos sin combinarlos. El cociente es aceleración frente al secuencial propio, que usa otra ruta de almacenamiento; no prueba escalabilidad lineal o superlineal sostenida. Comparar MPI P1/MPIP responde una pregunta distinta y también deberá informarse.')

page('N=4096: qué dicen las tres repeticiones')
chart('control_4096.png',179)
p('Figura 2. Tres pares consecutivos de la sección 13, con SEQ antes de MPI en todos ellos. Paneles con escalas verticales distintas para mostrar variación. Son repeticiones de una misma sesión, con el secuencial sin afinidad explícita.')
table([['Estadística (s)','SEQ','MPI P=6'], *[[label,f"{S['seq'][key]:.6f}",f"{S['p6'][key]:.6f}"] for key,label in [('median_s','Mediana'),('min_s','Mínimo'),('max_s','Máximo'),('q1_s','Q1 inclusivo'),('q3_s','Q3 inclusivo'),('sample_sd_s','Desvío muestral')]]],[180,160,160])
p(f"Cociente de medianas: {speed:.4f}. Reducción relativa del tiempo: {100*(1-1/speed):.2f}%. Eficiencia descriptiva S/6: {100*speed/6:.2f}%. Coeficiente de variación: SEQ {S['seq']['cv_pct']:.2f}% y MPI {S['p6']['cv_pct']:.2f}%. Q1 y Q3 se calculan con interpolación inclusiva; con tres datos su utilidad es descriptiva, sin inferencia de significación.")
h('Conclusión respaldada')
p('El tiempo MPI cercano a 4,12 s reaparece en los tres pares. No parece un valor aislado del primer piloto. La ganancia alrededor de 2,50 se sostiene en este control, pero no acredita estabilidad entre sesiones ni una configuración óptima. No se añaden el piloto, el escaneo o el diagnóstico de cuota a esta muestra para aumentar artificialmente n.')
h('Siguiente pregunta')
p('¿Se mantienen la ganancia y la no monotonía al fijar también el secuencial, rotar métodos y repetir P=1,2,3,4,6? Esa prueba es más informativa que aumentar ahora el número de variantes algorítmicas.')

page('Fases, afinidad y cuota: evidencia y límites')
chart('fases_4096.png',177)
p('Figura 3. Porcentajes calculados por ejecución desde los CSV originales de los tres controles MPI; el resto se obtiene como application-factor-gather y corresponde a reserva más generación.')
p(f"Mediana de la fracción de factor: {st.median(r['factor_pct'] for r in phase):.2f}%; reunión/reconstrucción: {st.median(r['gather_pct'] for r in phase):.2f}%. El mayor tiempo está dentro del kernel MPI, pero esta medición no separa cálculo, difusión y espera. Optimizar únicamente la reunión tendría un margen cercano al 2% del total en estos casos, aun suponiendo eliminarla por completo.")
h('Afinidad observada, no exclusividad')
p('El diagnóstico con /bin/true y P=6 informó seis cores distintos del socket 0. Es evidencia del mapeo de ese lanzamiento. No demuestra retrospectivamente el binding de cada benchmark ni que P=4 use exactamente la misma colocación. Compartir socket tampoco demuestra ubicación efectiva de páginas de memoria. Conviene guardar bindings por P en la campaña formal.')
h('Throttling comprobado, causalidad abierta')
table([['Contador','Incremento'],['usage_usec','37.260.596 (37,261 CPU-s agregados)'],['nr_periods','66'],['nr_throttled','28 (42,42% de los períodos observados)'],['throttled_usec','119.281 (0,119281 s del contador)']],[285,215])
p('Los contadores cubren el intervalo entre dos lecturas del cgroup, incluidos lanzamiento, validación y procesos auxiliares; application_s=4,127776 s solo cubre la aplicación en rango 0. El 42,42% NO es porcentaje de tiempo perdido. Tampoco corresponde restar 0,119281 s al factor ni dividir los CPU-s por application_s para inferir utilización. No hay un control equivalente sin cuota que permita atribuirle la pérdida de rendimiento.')
h('Decisión')
p('Mantener P<=6 y registrar cuota/contadores sin modificar el algoritmo. La evidencia todavía no permite escoger entre cuota, interferencia, localidad y colectivas como causa de la no monotonía.')

page('Cruce pequeño: hipótesis y campaña pendiente')
chart('cruce_exploratorio.png',181)
p('Figura 4. Sección 17: una observación por método, con SEQ fijado a CPU0. No se combina con el escaneo mayor ni con las validaciones anteriores.')
h('Qué se puede concluir ahora')
p('En N=128 todos los tiempos MPI superan el secuencial de esa prueba. En N=256, P=2,3,4,6 mejoran; el menor tiempo observado es P=3, con cociente 2,01. Esto localiza una región de interés entre dos tamaños ensayados. No demuestra que exista un único umbral ni que todos los tamaños posteriores mejoren.')
h('Protocolo que ya quedó definido')
p('N=128,160,192,224,256; SEQ y MPI P=1,2,3,4,6; una ronda descartada y siete rondas medidas. Son 30 configuraciones, 240 lanzamientos y 210 observaciones útiles. Se rota el orden de métodos; el orden de tamaños permanece fijo. Siete rondas no equilibran exactamente las seis posiciones posibles. Cada observación abre un proceso nuevo: la ronda descartada no convierte al programa en un benchmark de runtime persistente.')
p('Métrica primaria: application_s. S=mediana(SEQ)/mediana(MPI); E=S/P. Mejora clara descriptiva si S>1,10 y Q3(MPI)<Q1(SEQ). Fijar Q1/Q3 inclusivos antes del análisis. No es un test estadístico, y comparar muchas configuraciones hace especialmente necesaria una confirmación posterior de los puntos elegidos.')
h('Ajustes operativos antes de ejecutarla')
p('Usar una carpeta nueva y fallar si ya existe: mkdir -p y tee sobre nombres repetidos pueden sobrescribir una campaña. Guardar fuentes/hashes, entorno, bindings, errores y código de salida. Mantener una sola campaña activa. Si ya se ejecutó después de escribir la bitácora, conservarla como fue y analizarla antes de decidir si requiere repetición.')
h('Pregunta que seguirá abierta')
p('El cruce de application_s no es el cruce del comando completo. Un MPI rápido dentro del programa puede seguir siendo más lento cuando se incluyen arranque, validación y cierre. Falta medir ese segundo reloj en el clúster.')

page('Conclusión de etapa y camino al cierre')
h('Mi evaluación')
p('El avance es productivo: se confirmó el candidato, se identificó el entorno real y los pilotos descubrieron preguntas que una campaña automática podría haber ocultado. Ya hay evidencia suficiente para fijar las siguientes mediciones. Seguir acumulando ejecuciones aisladas aportaría menos que completar una grilla repetida y una confirmación en otra sesión.')
h('Orden recomendado')
table([['Paso','Pregunta y alcance'],['1. Evidencia resguardada','Completado: paquete original archivado; CSV, archivos de error, logs y fuentes contrastados. No hace falta repetir los pilotos para recuperar esta evidencia.'],['2. Completar el cruce','Ejecutar o recuperar la campaña N=128..256 fijada. Reportar medianas, Q1-Q3 y criterio descriptivo por N y P.'],['3. Escalabilidad mayor','N=512,1024,2048,4096; mismos seis métodos; siete repeticiones y una ronda descartada: 192 lanzamientos, 168 útiles. Afinidad controlada y orden rotado.'],['4. Segundo reloj','Medir aplicación y comando externo en los mismos lanzamientos, tras verificar el cronómetro. Priorizar esta incorporación para la campaña mayor; conservar validación aparte.'],['5. Confirmar y cerrar','Otra sesión para el cruce y configuraciones decisivas, especialmente N=2048/4096 con P=3,4,6 y SEQ. Explicar límites sin exigir resolver cada causa.']],[110,390])
p('La grilla mayor es una propuesta para el siguiente bloque, no un resultado ni una orden de ejecución inmediata. Si el costo es alto, hacer primero N=2048 y N=4096 y completar después los otros tamaños. Comparar sesiones por separado y medir el secuencial en cada una. No hace falta ampliar a 48/96 cores para responder el alcance actual.')
h('Conclusión que hoy puede defenderse')
p('En la sesión con cuota de seis CPUs equivalentes y 24 GiB, el candidato conserva la corrección reportada y muestra ganancias del tiempo hasta L en varios casos explorados. Para N=4096, tres repeticiones por método dan 10,327 s secuenciales y 4,123 s MPI P6 de mediana, con cociente 2,50. No se ha establecido aún el cruce reproducible, la curva completa de escalabilidad ni la ganancia del comando externo. Los resultados corresponden al entorno de un host; no acreditan ejecución entre nodos.')
p('No es necesario que MPI gane siempre para cerrar el proyecto. El cierre requiere describir dónde gana, dónde deja de convenir y qué costo agrega el flujo completo, con datos repetidos y límites explícitos. Bloques, BLAS, OpenMP y distribución 2D quedan como extensiones justificables después de esa respuesta.')

page('Trazabilidad y precisiones de la revisión')
h('Qué se verificó y qué permanece declarado')
p('Se auditaron los 53 CSV originales y los 113 hashes del paquete. Las cinco fuentes coinciden byte por byte con las copias archivadas. Los 53 archivos .err y ambos logs de compilación están vacíos: no contienen mensajes capturados, pero no sustituyen códigos de salida explícitos. No se ejecutaron nuevos benchmarks. Los diagnósticos de afinidad y cpu.stat siguen procediendo de la bitácora: el paquete no incluye esos logs completos.')
h('Precisiones frente a interpretaciones anteriores')
p('1. Coincidencia de residuos no equivale a igualdad de factores. 2. El binding observado para P=6 no descarta de forma general efectos NUMA ni acredita P=4. 3. La repetibilidad en una sesión no demuestra estabilidad entre fechas. 4. La fracción dominante de factor no equivale a cómputo puro. 5. La cuota de seis CPUs no es una reserva exclusiva. 6. El throttling observado no cuantifica la pérdida de tiempo de Cholesky.')
h('Archivos conservados con esta etapa')
table([['Archivo o carpeta','Contenido'],['evidencia_preformal_20260928.tar.gz','Paquete original íntegro del clúster.'],['bitacora_original.md','Contexto y protocolo experimental.'],['fuentes/ y auditoria.json','Fuentes, hashes y comprobaciones actualizadas.'],['observaciones_originales.csv','53 filas extraídas del paquete original.'],['observaciones_tablas.csv','Reconstrucción anterior conservada para contraste.'],['cocientes_escaneo.csv','Cocientes recalculados con los originales.'],['estadisticas_control.csv','Mediana, cuartiles, desvío y CV del control.'],['fracciones_control.csv','Porcentajes por ejecución desde originales.'],['throttling_transcrito.csv','Contadores de la bitácora; diferencias verificadas.'],['informe.md y cuatro PNG','Análisis y gráficos de esta edición revisada.']],[190,310])
p('Generador: desde_cero/docs/generar_informe_cluster_exploratorio.py. Verifica el paquete, contrasta la bitácora y recalcula desde los originales. Esta revisión reemplaza la edición que indicaba ausencia de CSV y logs. No añade repeticiones ni convierte los pilotos en una campaña formal. Análisis y documentación realizados con asistencia de IA.')

(DATA/'informe.md').write_text('\n'.join(md),encoding='utf-8')
pdf=ROOT/'output/pdf/Cholesky_Etapa_15_Exploracion_cluster.pdf'
pdf.parent.mkdir(parents=True,exist_ok=True)
def footer(c,d):
    c.setFont('Helvetica',8);c.setFillColor(colors.HexColor('#52646d'))
    c.drawString(45,25,'Cholesky | Etapa 15 | Exploración de clúster | 28/09/2026')
    c.drawRightString(550,25,str(d.page))
SimpleDocTemplate(str(pdf),pagesize=A4,leftMargin=45,rightMargin=45,topMargin=36,bottomMargin=43).build(story,onFirstPage=footer,onLaterPages=footer)
reader=PdfReader(pdf)
assert len(reader.pages)==8, f'Esperadas 8 páginas, obtenidas {len(reader.pages)}'
assert all(len(page.extract_text())>400 for page in reader.pages)
print(json.dumps(dict(pdf=str(pdf),pages=len(reader.pages),control_speedup=speed,statistics=summaries),indent=2))
