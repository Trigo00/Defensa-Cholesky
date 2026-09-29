"""Audita el tar original y documenta la campaña de cruce, sin ejecutar binarios."""
from pathlib import Path
import csv, io, json, hashlib, tarfile, re, math, statistics as st, sys
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader
D=ROOT/'desde_cero/resultados/cruce_cluster_20260928'
A=D/'campana_cruce_20260928.tar.gz'
with tarfile.open(A) as t:
    members=t.getmembers()
    assert len(set(m.name for m in members))==len(members)
    files={m.name:t.extractfile(m).read() for m in members if m.isfile()}
prefix='campana_cruce_20260928/'
checks=[]
for manifest in ['SHA256SUMS_ALL.txt','provenance/SHA256_PROVENANCE.txt']:
    listed=set()
    for line in files[prefix+manifest].decode().splitlines():
        h,name=line.split(None,1)
        assert hashlib.sha256(files[name]).hexdigest()==h,(manifest,name)
        listed.add(name)
    checks.append(dict(manifest=manifest,verified=len(listed)))
    if manifest=='SHA256SUMS_ALL.txt': assert set(files)-listed=={prefix+manifest}
assert len(files)==494 and checks[0]['verified']==493
sources=[]
for name,b in files.items():
    if name.endswith(('.c','.h')):
        assert b==(ROOT/'desde_cero/resultados/cluster_exploratorio_20260928/fuentes'/Path(name).name).read_bytes()
        sources.append(dict(file=Path(name).name,sha256=hashlib.sha256(b).hexdigest()))
assert len(sources)==5
methods=['seq','p1','p2','p3','p4','p6'];sizes=[128,160,192,224,256]
rows=[]
for name,b in files.items():
    if not name.endswith('.csv'):continue
    match=re.fullmatch(r'(?:(warmup)|((?:rep)+)([1-7]))_n(\d+)_(seq|p[12346])\.csv',Path(name).name)
    assert match,name
    warm,rep_prefix,rep,n,method=match.groups()
    rlist=list(csv.DictReader(io.StringIO(b.decode())))
    assert len(rlist)==1
    r={k:float(v) for k,v in rlist[0].items()}
    assert all(math.isfinite(v) for v in r.values())
    assert r['N']==int(n) and r['P']==(1 if method=='seq' else int(method[1:]))
    assert r['valid']==1 and 0<=r['projected_residual']<=1e-12
    assert (0<=r['exact_residual']<=1e-12) if int(n)<=128 else r['exact_residual']==-1
    assert all(v>=0 for k,v in r.items() if k.endswith('_s'))
    assert abs(sum(r[k] for k in ['allocation_s','generation_s','factor_s','gather_s'])-r['application_s'])<=max(1e-11,1e-10*r['application_s'])
    assert r['max_local_s']+1e-12>=r['application_s']
    assert files[name[:-4]+'.err']==b''
    rep=0 if warm else int(rep)
    position=0 if warm else len(rep_prefix)//3
    if not warm:
        expected=sizes.index(int(n))*6+(methods.index(method)-(rep-1)%6)%6+1
        assert position==expected,(name,position,expected)
    rows.append(dict(original_file=name,round=rep,method=method,position_from_name=position,
                     normalized_file=f"{'warmup' if warm else 'rep'+str(rep)}_n{n}_{method}.csv",**r))
assert len(rows)==240
assert len({r['normalized_file'] for r in rows})==240
for n in sizes:
    for method in methods:
        assert sorted(r['round'] for r in rows if r['N']==n and r['method']==method)==list(range(8))
use=[r for r in rows if r['round']>0]
assert len(use)==210
def csvout(name,rr):
    with (D/name).open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
csvout('observaciones_normalizadas.csv',sorted(use,key=lambda r:(r['round'],r['position_from_name'])))
csvout('warmups.csv',[r for r in rows if r['round']==0])
summary=[];phases=[]
for n in sizes:
    for method in methods:
        selected=[r for r in use if r['N']==n and r['method']==method]
        times=[r['application_s'] for r in selected]
        q1,_,q3=st.quantiles(times,n=4,method='inclusive')
        summary.append(dict(N=n,method=method,P=1 if method=='seq' else int(method[1:]),samples=7,
            q1_s=q1,median_s=st.median(times),q3_s=q3,min_s=min(times),max_s=max(times)))
        phases.append(dict(N=n,method=method,**{k:st.median(r[k] for r in selected) for k in ['allocation_s','generation_s','factor_s','gather_s','application_s','validation_s']},
            gather_fraction_median=st.median(r['gather_s']/r['application_s'] for r in selected)))
S={(r['N'],r['method']):r for r in summary}
for r in summary:
    seq=S[r['N'],'seq']
    r['speedup']=seq['median_s']/r['median_s']
    r['efficiency_pct']=100*r['speedup']/r['P']
    r['mpi1_ratio']=S[r['N'],'p1']['median_s']/r['median_s']
    r['clear_improvement']=r['method']!='seq' and r['speedup']>1.10 and r['q3_s']<seq['q1_s']
csvout('resumen.csv',summary);csvout('fases.csv',phases)
cross=[dict(P=p,first_tested_N=next((n for n in sizes if S[n,f'p{p}']['clear_improvement']),None)) for p in [1,2,3,4,6]]
csvout('primer_cruce.csv',cross)
def stats_file(name):return {k:int(v) for k,v in (s.split() for s in files[prefix+name].decode().splitlines())}
before=stats_file('cpu_stat_antes.txt');after=stats_file('cpu_stat_despues.txt')
delta={k:after[k]-v for k,v in before.items()}
csvout('cpu_stat_diferencias.csv',[dict(metric=k,before=before[k],after=after[k],delta=v) for k,v in delta.items()])
assert all(b==b'' for name,b in files.items() if name.endswith(('.err','.log')))
audit=dict(archive_sha256=hashlib.sha256(A.read_bytes()).hexdigest(),files=len(files),hash_manifests=checks,
    measured=210,warmups=30,source_hashes=sources,empty_err_files=240,empty_build_logs=2,
    max_projected_residual=max(r['projected_residual'] for r in use),cpu_stat_delta=delta,
    naming_order_consistent=True,script_in_archive=False,
    quantiles='Inclusivos, interpolación lineal; 7 valores por configuración; sin warmups',
    first_crossings=cross)
(D/'auditoria.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
colorset=['#687781','#187d9d','#27865d','#c77931','#895aa4']
fig,ax=plt.subplots(1,2,figsize=(10,3.6),layout='constrained')
for i,method in enumerate(methods):
    rr=[S[n,method] for n in sizes]
    med=[r['median_s']*1000 for r in rr]
    ax[0].errorbar(sizes,med,yerr=[[1000*(r['median_s']-r['q1_s']) for r in rr],[1000*(r['q3_s']-r['median_s']) for r in rr]],marker='o',capsize=3,label=method.upper())
    if method!='seq':ax[1].plot(sizes,[r['speedup'] for r in rr],'-o',label=method.upper())
ax[0].set(xlabel='N',ylabel='Aplicación (ms)',xticks=sizes)
ax[1].axhline(1,color='gray',lw=.8);ax[1].axhline(1.10,color='black',ls='--',label='S=1,10')
ax[1].set(xlabel='N',ylabel='Speedup de medianas',xticks=sizes)
for a in ax:a.grid(alpha=.2);a.legend(fontsize=7)
fig.savefig(D/'cruce.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(1,2,figsize=(10,3.2),layout='constrained')
rs=[S[256,m] for m in methods[1:]]
for a,key,ylabel in zip(ax,['speedup','efficiency_pct'],['Speedup','Eficiencia (%)']):
    a.bar([str(r['P']) for r in rs],[r[key] for r in rs],color=colorset);a.set(xlabel='Procesos MPI',ylabel=ylabel);a.grid(axis='y',alpha=.2)
fig.savefig(D/'n256.png',dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(10,3.4),layout='constrained')
labels=[];components=[[],[],[],[]]
for n in [160,192]:
    for method in ['seq','p3']:
        rr=[r for r in use if r['N']==n and r['method']==method]
        labels.append(f'N={n}\n{method.upper()}')
        for vals,k in zip(components,['allocation_s','generation_s','factor_s','gather_s']):vals.append(st.mean(r[k] for r in rr)*1000)
bottom=[0]*4
for vals,label,c in zip(components,['Reserva','Generación','Factor (incluye MPI)','Reunión/reconstrucción'],['#8d9fa3','#87bb9c','#187d9d','#c77931']):
    ax.bar(labels,vals,bottom=bottom,label=label,color=c);bottom=[a+b for a,b in zip(bottom,vals)]
ax.set(ylabel='Media de fases (ms)');ax.legend(fontsize=8);ax.grid(axis='y',alpha=.2)
fig.savefig(D/'fases_cruce.png',dpi=180);plt.close(fig)

styles=getSampleStyleSheet();styles['BodyText'].fontSize=10;styles['BodyText'].leading=14
styles['Title'].fontSize=21;styles['Title'].leading=25;styles['Title'].textColor=colors.HexColor('#174b60')
story=[];md=[]
def page(t):
    if story:story.append(PageBreak())
    story.extend([Paragraph(escape(t),styles['Title']),Spacer(1,10)]);md.append('\n# '+t+'\n')
def h(t):story.append(Paragraph(escape(t),styles['Heading2']));md.append('\n## '+t+'\n')
def p(t):story.extend([Paragraph(escape(t),styles['BodyText']),Spacer(1,8)]);md.append(t+'\n')
def table(data,widths):
    obj=Table([[Paragraph(escape(str(c)),styles['BodyText']) for c in row] for row in data],colWidths=widths,repeatRows=1)
    obj.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecf0')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.extend([obj,Spacer(1,8)])
    md.extend(['| '+' | '.join(map(str,data[0]))+' |','| '+' | '.join(['---']*len(data[0]))+' |'])
    md.extend('| '+' | '.join(map(str,r))+' |' for r in data[1:]);md.append('')
def chart(name,height):story.extend([Image(str(D/name),width=500,height=height),Spacer(1,8)]);md.append(f'![{name}]({name})\n')
page('Etapa 16: campaña formal de cruce')
p('Clúster | 28/09/2026 | Candidato Cholesky right-looking MPI cíclico 1D. Continuación de la exploración de la Etapa 15. Análisis independiente del paquete original entregado por el usuario; los resultados pegados en el mensaje se contrastaron con los CSV.')
h('Pregunta y resultado')
p('¿En qué tamaños ensayados MPI reduce claramente el tiempo hasta disponer de L frente al secuencial propio? Bajo el criterio prefijado, P=3 presenta la primera mejora en N=192. P=4 la presenta en N=224; P=2 y P=6, en N=256. MPI P=1 no cumple el criterio en la grilla. Son cruces descriptivos de una sesión, no umbrales universales.')
table([['Control de evidencia','Resultado'],['Cantidad de muestras','210 útiles y 30 warmups; siete útiles por cada una de 30 configuraciones.'],['Integridad','494 archivos regulares; 493 hashes del manifiesto general verificados. El manifiesto no se incluye a sí mismo.'],['Errores y compilación','240 archivos .err y dos logs de compilación vacíos. No hay códigos de salida explícitos archivados.'],['Corrección numérica',f"240 filas con valid=1. Residuo proyectado máximo útil: {audit['max_projected_residual']:.3e}."],['Fuentes','Cinco fuentes idénticas a las de la Etapa 15. Se preservan también los dos ejecutables originales sin ejecutarlos.']],[145,355])
h('Protocolo')
p('N=128,160,192,224,256; SEQ y MPI P=1,2,3,4,6. Una ronda descartada y siete medidas. Orden de métodos rotado; tamaños en orden creciente. Afinidad prevista: SEQ con taskset CPU0; MPI --bind-to core --map-by core. El entorno conserva un diagnóstico de binding P6 en el socket 0, no un registro independiente de cada lanzamiento.')
p('AMD EPYC 7B12, GCC 13.3, Open MPI 4.1.6, cuota de seis CPUs equivalentes y 24 GiB. Fuente de entorno fechada 2026-09-28T16:06:20Z. No se interpreta la cuota como seis cores exclusivos ni como acceso a varios nodos.')

page('Resultado del criterio fijado antes de medir')
chart('cruce.png',180)
p('Figura 1. Medianas y barras Q1-Q3 inclusivos en tiempos, siete observaciones por punto. Los speedups son cocientes de medianas, sin intervalos de confianza. Las líneas unen únicamente los puntos medidos. Warmups y pilotos quedan excluidos.')
p('S=mediana(T_SEQ)/mediana(T_MPI). E=S/P. Mejora clara descriptiva si S>1,10 y Q3_MPI<Q1_SEQ, ambas desigualdades estrictas. Cuartiles por interpolación inclusiva. No es una prueba formal de significación y no demuestra monotonicidad para tamaños no ensayados.')
table([['N','P1','P2','P3','P4','P6'],*[[n,*['Sí' if S[n,f'p{v}']['clear_improvement'] else 'No' for v in [1,2,3,4,6]]] for n in sizes]],[65,87,87,87,87,87])
table([['Procesos','Primer N ensayado con mejora clara'],*[[r['P'],r['first_tested_N'] or 'Ninguno en la grilla'] for r in cross]],[100,400])
p('La campaña responde el cruce del reloj application_s para esta entrada, implementación y sesión. No responde aún si mpirun termina antes que el comando secuencial: el reloj excluye arranque, validación y cierre.')

page('N=256: rapidez y eficiencia son preguntas distintas')
chart('n256.png',160)
seq=S[256,'seq']
table([['Método','Q1 (ms)','Mediana (ms)','Q3 (ms)','S','E (%)'],*[[m.upper(),f"{S[256,m]['q1_s']*1000:.3f}",f"{S[256,m]['median_s']*1000:.3f}",f"{S[256,m]['q3_s']*1000:.3f}",f"{S[256,m]['speedup']:.2f}" if m!='seq' else '-',f"{S[256,m]['efficiency_pct']:.1f}" if m!='seq' else '-'] for m in methods]],[75,85,105,85,60,90])
p('P=3 tiene la menor mediana MPI observada. P=2 obtiene la mayor eficiencia entre las configuraciones que aceleran (P>=2). P=1 da 86,9% de eficiencia numérica, pero S=0,87: es más lento que SEQ. P=6 mejora frente a SEQ con eficiencia 24,4%. Son descripciones de esta campaña; no prueban que P=3 sea siempre óptimo ni que su diferencia frente a P=4 sea estadísticamente concluyente.')
h('Comparación justa')
p('La referencia es el secuencial autónomo medido aquí. MPI P1 no ejecuta exactamente la misma ruta: utiliza almacenamiento distribuido y reunión incluso con un proceso. Por eso se conserva también MPI1/MPIP en resumen.csv como escalabilidad interna, sin sustituir el speedup frente a SEQ.')
h('Conclusión parcial')
p('Aumentar procesos no asegura menor tiempo. En matrices pequeñas los costos adicionales compiten con el trabajo que se reparte; una configuración intermedia puede terminar antes que utilizar toda la cuota disponible.')

page('Cómo se amortizan los costos adicionales')
chart('fases_cruce.png',170)
p('Figura 3. Medias de fases en las siete repeticiones, desde el reloj del rango 0. Aquí se usan medias para que las barras apiladas sumen la media total. El criterio principal sigue usando medianas del total medido, no la suma de medianas.')
table([['N / método','Generación ms','Factor ms','Reunión ms','Total ms'],*[[f'{n} / {m.upper()}',*[f"{next(r for r in phases if r['N']==n and r['method']==m)[k]*1000:.4f}" for k in ['generation_s','factor_s','gather_s','application_s']]] for n in [160,192] for m in ['seq','p3']]],[100,100,100,100,100])
p('Tabla: medianas de cada campo por separado. En N=160/P3, generación y factor disminuyen respecto de SEQ, pero el costo de reunión/reconstrucción impide mejorar el total. En N=192/P3 el ahorro compensa esos costos y se cumplen las dos condiciones de mejora. Esto describe los intervalos medidos; no aísla causas de hardware.')
p('factor_s incluye cálculo, colectivas y esperas. gather_s incluye MPI_Gatherv y reconstrucción serial. Las fases no son máximos por proceso. La comparación de las fases sirve para interpretar el cruce; no demuestra cuánto tiempo puro de red o de aritmética se consumió.')
h('Cuota durante esta campaña')
p(f"Los registros antes/después muestran incrementos de nr_throttled={delta['nr_throttled']} y throttled_usec={delta['throttled_usec']}; nr_periods aumenta {delta['nr_periods']}. No se registró throttling adicional en ese intervalo. Esto no demuestra ausencia de interferencia, migraciones o variación de frecuencia. El diagnóstico previo con N=4096 sigue siendo otro experimento y no se contradice con este resultado.")

page('Auditoría de nombres y alcance de la evidencia')
h('Qué se recuperó sin cambiar los originales')
p('Los nombres contienen uno o varios prefijos rep seguidos del número de ronda. Se extrajeron ronda, N y método; se contrastaron N/P con el contenido. Cada configuración tiene exactamente rondas 1..7 y un warmup. No hay colisiones en los 240 nombres normalizados. El número de prefijos coincide con las posiciones 1..30 de cada ronda bajo el orden rotado previsto.')
p('Esto respalda la recuperación inequívoca de la grilla y la coherencia del orden codificado. No reemplaza un registro temporal de los comandos: el script ejecutado no está incluido en el paquete. No se renombraron ni sobrescribieron archivos originales; observaciones_normalizadas.csv conserva el nombre original y el normalizado.')
h('Causa compatible con el script documentado')
p('La función de la bitácora asigna rep="$3" sin local, y el bucle la llama con "rep${rep}". La asignación modifica la variable exterior y acumula prefijos. El orden de métodos se calcula con start antes de esas llamadas; el bucle exterior asigna el siguiente número al comenzar otra ronda. Este mecanismo explica los nombres sin implicar pérdida de muestras.')
p('Para el próximo script: declarar local n="$1", local method="$2" y local rep_tag="$3" dentro de run_case; usar rep_tag al formar nombres. Mantener una variable distinta para la ronda exterior. Usar una carpeta nueva, registrar estados de salida y probar primero la generación de nombres y órdenes sin lanzar benchmarks.')
h('Integridad y trazabilidad')
p('El manifiesto general verificó 493 entradas; el manifiesto de provenance verificó nueve. Son comprobaciones de integridad del contenido recibido, no certificaciones independientes de las condiciones de ejecución. Los logs vacíos indican ausencia de mensajes capturados. valid=1, los residuos y la coherencia de fases respaldan la validez numérica de los resultados archivados.')
p('Archivos derivados: observaciones_normalizadas.csv (210 filas), warmups.csv (30), resumen.csv (30 configuraciones), fases.csv, primer_cruce.csv, cpu_stat_diferencias.csv y auditoria.json. El tar original queda archivado íntegro; no se ejecutan los binarios recibidos.')

page('Conclusión y siguiente pregunta experimental')
h('Qué queda respondido')
p('Bajo el criterio descriptivo prefijado, la primera mejora del tiempo hasta L aparece en N=192 con P=3 entre los tamaños ensayados. Para N=256 mejoran P=2,3,4,6. Los datos formales confirman que los costos adicionales deben amortizarse antes de obtener una ganancia, y que seis procesos no son la opción más rápida en esta grilla.')
h('Mi evaluación')
p('Los cruces del resumen coinciden con el análisis independiente; la afirmación sobre eficiencia de P=2 requiere limitarse a las configuraciones que aceleran. La campaña es aprovechable pese al defecto de nombres: no hace falta repetirla por ese motivo. Tampoco hace falta explorar más tamaños pequeños ahora. Una confirmación selectiva en otra sesión puede reforzar la estabilidad alrededor del primer cruce, sin rehacer toda la grilla para avanzar.')
h('Siguiente bloque, de forma gradual')
table([['Paso','Acción y propósito'],['1. Preparar el lanzamiento','Corregir variables locales y evitar sobrescritura. Guardar script, fuentes, compilación, binding y estados de salida.'],['2. Verificar dos relojes','Probar una configuración con el cronómetro externo existente y revisar sus dos salidas antes de lanzar la campaña. El tiempo externo incluye validación y runtime.'],['3. Medir escalabilidad','N=512,1024,2048,4096; SEQ y MPI P=1,2,3,4,6. Una ronda descartada y siete útiles: 192 lanzamientos, 168 útiles.'],['4. Confirmar y cerrar','Repetir en otra sesión los casos decisivos. Separar velocidad hasta L, tiempo externo y eficiencia; mantener registrados resultados desfavorables.']],[110,390])
p('Mantener afinidad controlada, orden rotado, semilla 2026 y candidato sin cambios. Registrar cpu.stat antes/después de cada bloque; no convertir su delta directamente en tiempo perdido de Cholesky. Los dos relojes deben provenir del mismo lanzamiento. No lanzar aún toda la campaña sin verificar ese mecanismo.')
p('La siguiente pregunta es cuánto escala el candidato cuando crece el trabajo y si la ganancia sobrevive al comando completo. No se necesita agregar BLAS, OpenMP o una distribución 2D para responderla. Esta etapa conserva alcance de una sesión en un host bajo cuota; no establece resultados multinodo.')
p('Reproducción: desde_cero/docs/generar_informe_cruce_cluster.py. Esta Etapa 16 continúa la 15; sus frases históricas sobre campaña pendiente corresponden al estado anterior. Estadísticas recalculadas desde el paquete original. Documentación y análisis con asistencia de IA.')
(D/'informe.md').write_text('\n'.join(md),encoding='utf-8')
pdf=ROOT/'output/pdf/Cholesky_Etapa_16_Cruce_cluster.pdf'
def footer(c,d):
    c.setFont('Helvetica',8);c.drawString(45,25,'Cholesky | Etapa 16 | Cruce formal | 28/09/2026');c.drawRightString(550,25,str(d.page))
SimpleDocTemplate(str(pdf),pagesize=A4,leftMargin=45,rightMargin=45,topMargin=36,bottomMargin=43).build(story,onFirstPage=footer,onLaterPages=footer)
assert len(PdfReader(pdf).pages)==6
print(json.dumps(dict(pdf=str(pdf),audit=audit,n256=[r for r in summary if r['N']==256]),indent=2))
