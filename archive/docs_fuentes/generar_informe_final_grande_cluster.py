"""Etapa 19: recalcula desde originales y contrasta el análisis suministrado."""
from pathlib import Path
import csv,io,json,hashlib,tarfile,zipfile,re,math,statistics as st,sys
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader
D=ROOT/'desde_cero/resultados/final_grande_cluster_20260928';A=D/'campana_final_grande_20260928.tar.gz'
with tarfile.open(A) as t:
    mm=t.getmembers();assert len({m.name for m in mm})==len(mm)
    fs={m.name:t.extractfile(m).read() for m in mm if m.isfile()}
pfx='campana_final_grande_20260928/'
listed=[]
for line in fs[pfx+'SHA256SUMS.txt'].decode().splitlines():
    h,name=line.split(None,1)
    name=name if name in fs else pfx+name.removeprefix('./')
    assert hashlib.sha256(fs[name]).hexdigest()==h;listed.append(name)
assert len(listed)==43 and set(fs)-set(listed)=={pfx+'SHA256SUMS.txt'}
with tarfile.open(ROOT/'desde_cero/resultados/lapack_cluster_20260928/campana_lapack_cluster_20260928.tar.gz') as t:
    assert fs[pfx+'compare_lapack.c']==t.extractfile('campana_lapack_cluster_20260928/compare_lapack.c').read()
for name in ['main_candidate.c','cholesky.c','cholesky.h','cholesky_mpi.c','cholesky_mpi.h']:
    assert fs[pfx+name]==(ROOT/'desde_cero/resultados/cluster_exploratorio_20260928/fuentes'/name).read_bytes()
def read(b):return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
def write(name,rows):
    with (D/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
rows=[];warmups=[]
for n in [6144,8192]:
    rr=read(fs[pfx+f'n{n}_own_lapack.csv']);assert len(rr)==12
    for raw in rr:
        r={k:(v if k=='method' else float(v)) for k,v in raw.items()}
        assert all(math.isfinite(v) for k,v in r.items() if k!='method')
        assert r['N']==n
        assert r['method']==('own' if (int(r['order'])+int(r['repetition'])-2)%2==0 else 'lapack')
        assert 0<=r['projected_residual']<=1e-12 and 0<=r['factor_difference']<=1e-12
        assert abs(r['allocation_s']+r['generation_s']+r['factor_s']-r['total_s'])<=1e-8
        assert all(v>=0 for k,v in r.items() if k.endswith('_s'))
        rows.append(dict(source=f'n{n}_own_lapack.csv',N=n,method=r['method'],rep=int(r['repetition']),
            factor_s=r['factor_s'],generation_s=r['generation_s'],secondary_s=r['total_s'],secondary_clock='total_s',
            gather_s='',validation_s='',projected_residual=r['projected_residual'],factor_difference=r['factor_difference']))
    assert fs[pfx+f'n{n}_own_lapack.err'].decode().strip()=='OpenBLAS threads=1 config=OpenBLAS 0.3.34 DYNAMIC_ARCH NO_AFFINITY Zen MAX_THREADS=128'
    for rep in range(7):
        name=f'n{n}_p6_rep{rep}' if rep else f'warmup_n{n}_p6'
        rr=read(fs[pfx+name+'.csv']);assert len(rr)==1
        r={k:float(v) for k,v in rr[0].items()}
        assert all(math.isfinite(v) for v in r.values())
        assert r['N']==n and r['P']==6 and r['valid']==1 and r['exact_residual']==-1
        assert 0<=r['projected_residual']<=1e-12
        assert all(v>=0 for k,v in r.items() if k.endswith('_s'))
        assert abs(sum(r[k] for k in ['allocation_s','generation_s','factor_s','gather_s'])-r['application_s'])<=1e-8
        assert r['max_local_s']+1e-12>=r['application_s']
        assert fs[pfx+name+'.err']==b''
        item=dict(source=name+'.csv',N=n,method='mpi_p6',rep=rep,factor_s=r['factor_s'],generation_s=r['generation_s'],
            secondary_s=r['application_s'],secondary_clock='application_s',gather_s=r['gather_s'],validation_s=r['validation_s'],
            projected_residual=r['projected_residual'],factor_difference='')
        (rows if rep else warmups).append(item)
assert len(rows)==36 and len(warmups)==2
summary=[];context=[]
for n in [6144,8192]:
    for method in ['own','mpi_p6','lapack']:
        rr=[r for r in rows if r['N']==n and r['method']==method]
        assert sorted(r['rep'] for r in rr)==list(range(1,7))
        vals=[r['factor_s'] for r in rr];q1,_,q3=st.quantiles(vals,n=4,method='inclusive')
        summary.append(dict(N=n,method=method,count=6,q1_s=q1,median_s=st.median(vals),q3_s=q3,min_s=min(vals),max_s=max(vals),
            mean_s=st.mean(vals),cv_percent=100*st.stdev(vals)/st.mean(vals)))
        context.append(dict(N=n,method=method,generation_median_s=st.median(r['generation_s'] for r in rr),
            secondary_clock=rr[0]['secondary_clock'],secondary_median_s=st.median(r['secondary_s'] for r in rr)))
S={(r['N'],r['method']):r for r in summary}
ratios=[]
for n in [6144,8192]:
    own,mpi,lap=[S[n,m]['median_s'] for m in ['own','mpi_p6','lapack']]
    ratios.append(dict(N=n,own_over_mpi_speedup=own/mpi,mpi_efficiency_vs_own_P6=own/mpi/6,own_over_lapack_speedup=own/lap,mpi_over_lapack_time_ratio=mpi/lap))
def cpu(name):return {k:int(v) for k,v in (line.split() for line in fs[pfx+name].decode().splitlines())}
before=cpu('cpu_stat_antes.txt');after=cpu('cpu_stat_despues.txt');delta={k:after[k]-v for k,v in before.items()}
Z=D/'analisis_campana_final_grande_20260928.zip'
with zipfile.ZipFile(Z) as z:
    supplied=read(z.read('resumen_factor.csv'));sup_ratios=read(z.read('razones_principales.csv'))
    sa=json.loads(z.read('auditoria.json'))
for r in supplied:
    ours=S[int(r['N']),r['method']]
    for k in r:
        if k not in ['N','method']:assert math.isclose(float(r[k]),ours[k],rel_tol=1e-12,abs_tol=1e-12),(r,k)
assert len(supplied)==6 and len(sup_ratios)==2
for r in sup_ratios:
    ours=next(o for o in ratios if o['N']==int(r['N']))
    for k,v in r.items():assert math.isclose(float(v),ours[k],rel_tol=1e-12,abs_tol=1e-12)
assert delta==sa['cpu_stat_delta'] and hashlib.sha256(A.read_bytes()).hexdigest()==sa['archive_sha256']
audit=dict(archive_sha256=hashlib.sha256(A.read_bytes()).hexdigest(),files=len(fs),verified_manifest_entries=len(listed),
    useful_observations=len(rows),exported_mpi_warmups=len(warmups),own_lapack_warmups='Una por método/tamaño en código, no exportadas',
    original_sources_match=True,all_mpi_valid=True,all_exported_residuals_acceptable=True,
    supplied_statistics_match=True,source_script_in_archive=False,exit_codes_archived=False,affinity_log_archived=False,
    binaries_in_archive=False,cpu_stat_delta=delta,max_projected_residual=max(r['projected_residual'] for r in rows),
    max_factor_difference=max(float(r['factor_difference']) for r in rows if r['factor_difference']!=''))
(D/'auditoria_independiente.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
write('observaciones.csv',rows);write('warmups_mpi.csv',warmups);write('resumen_factor.csv',summary);write('razones.csv',ratios);write('contexto.csv',context)
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(figsize=(9.8,3.5),layout='constrained')
for j,(method,label,c) in enumerate([('own','C propio','#6c818a'),('mpi_p6','MPI P=6','#187d9d'),('lapack','LAPACK, 1 hilo','#c77931')]):
    rr=[S[n,method] for n in [6144,8192]];x=[i+(j-1)*.24 for i in [0,1]]
    ax.bar(x,[r['median_s'] for r in rr],width=.22,label=label,color=c)
    ax.errorbar(x,[r['median_s'] for r in rr],yerr=[[r['median_s']-r['q1_s'] for r in rr],[r['q3_s']-r['median_s'] for r in rr]],fmt='none',color='black',capsize=4)
ax.set(xticks=[0,1],xticklabels=['6144','8192'],xlabel='N',ylabel='Factorización: mediana y Q1-Q3 (s)');ax.legend();ax.grid(axis='y',alpha=.2)
fig.savefig(D/'factor_comparado.png',dpi=180);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(9.8,3.2),layout='constrained')
axs[0].bar(['6144','8192'],[r['own_over_mpi_speedup'] for r in ratios],color='#187d9d');axs[0].axhline(1,color='gray',ls='--');axs[0].set(ylabel='C propio / MPI: speedup',xlabel='N')
axs[1].bar(['6144','8192'],[r['mpi_over_lapack_time_ratio'] for r in ratios],color='#c77931');axs[1].axhline(1,color='gray',ls='--');axs[1].set(ylabel='MPI / LAPACK: razón de tiempos',xlabel='N')
for a in axs:a.grid(axis='y',alpha=.2)
fig.savefig(D/'razones.png',dpi=180);plt.close(fig)
styles=getSampleStyleSheet();styles['BodyText'].fontSize=10;styles['BodyText'].leading=14;styles['Title'].fontSize=21;styles['Title'].leading=25;styles['Title'].textColor=colors.HexColor('#174b60')
story=[];md=[]
def page(t):
    if story:story.append(PageBreak())
    story.extend([Paragraph(escape(t),styles['Title']),Spacer(1,10)]);md.append('\n# '+t+'\n')
def h(t):story.append(Paragraph(escape(t),styles['Heading2']));md.append('\n## '+t+'\n')
def p(t):story.extend([Paragraph(escape(t),styles['BodyText']),Spacer(1,8)]);md.append(t+'\n')
def table(rr,widths):
    t=Table([[Paragraph(escape(str(v)),styles['BodyText']) for v in r] for r in rr],colWidths=widths,repeatRows=1)
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecf0')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.extend([t,Spacer(1,8)])
    md.extend(['| '+' | '.join(map(str,rr[0]))+' |','| '+' | '.join(['---']*len(rr[0]))+' |']);md.extend('| '+' | '.join(map(str,r))+' |' for r in rr[1:]);md.append('')
def chart(name,height):story.extend([Image(str(D/name),width=500,height=height),Spacer(1,8)]);md.append(f'![{name}]({name})\n')
page('Etapa 19: MPI frente a LAPACK en matrices grandes')
p('Pregunta final: al crecer hasta N=6144 y N=8192, ¿MPI con seis procesos se acerca o supera a LAPACK/OpenBLAS con un hilo? Se analiza el paquete original del 28/09/2026 y se contrasta de forma independiente el ZIP de análisis recibido.')
h('Respuesta')
p('MPI reduce el tiempo frente al C propio secuencial, pero no alcanza a LAPACK en ninguno de los dos tamaños. La razón MPI/LAPACK disminuye de 8,58 a 6,25: hay acercamiento relativo entre esos dos puntos, sin evidencia de un cruce futuro. La diferencia absoluta en segundos, en cambio, aumenta.')
h('Diseño y trazabilidad')
table([['Aspecto','Evidencia'],['Métodos y tamaños','C propio, MPI P6 y LAPACK/OpenBLAS 1 hilo; N=6144 y 8192.'],['Repeticiones','Seis útiles por método y tamaño: 36 observaciones. Dos warmups MPI exportados; warmups own/LAPACK implementados dentro del banco, no exportados.'],['Integridad','44 archivos regulares; 43 hashes del manifiesto verificados, excluido el propio manifiesto.'],['Continuidad','Los cinco fuentes candidatos coinciden con las etapas anteriores; compare_lapack.c coincide con la Etapa 18.'],['Entorno','EPYC 7B12, Open MPI 4.1.6, OpenBLAS 0.3.34; cuota de 6 CPUs y 24 GiB. Inicio 19:38:51 UTC; fin 20:05:20 UTC.']],[135,365])
h('Qué hace comparable factor_s')
p('El reloj principal abarca la fase que factoriza la misma familia de matrices SPD generadas con semilla 2026. En C/LAPACK es la llamada al kernel; en MPI es el intervalo del rango 0 alrededor del kernel distribuido, que incluye comunicaciones y esperas. No es un máximo reducido por fase ni una comparación de aritmética pura.')
p('Generación y reunión quedan fuera de factor_s; los relojes secundarios tienen límites distintos. El banco C/LAPACK alterna métodos dentro de un proceso; MPI se lanza por separado. Por eso el cociente principal es descriptivo del costo de esa fase en los dos programas, no una prueba que aísle únicamente el efecto del paralelismo.')

page('Resultados de factorización y dispersión')
chart('factor_comparado.png',184)
p('Figura 1. Medianas y Q1-Q3 inclusivos, seis observaciones útiles por grupo. Barras de cuartiles descriptivas; no intervalos de confianza. Los warmups no se incluyen.')
table([['N','Método','Q1 s','Mediana s','Q3 s','CV %'],*[[r['N'],r['method'],f"{r['q1_s']:.4f}",f"{r['median_s']:.4f}",f"{r['q3_s']:.4f}",f"{r['cv_percent']:.3f}"] for r in summary]],[55,85,95,95,95,75])
p('CV usa desviación muestral dividida por la media. La variación MPI en N=6144 es mayor que la de los otros grupos, pero la separación respecto de LAPACK es amplia: incluso el menor tiempo MPI supera al mayor LAPACK en ambos tamaños. Esta observación no necesita transformarse en un test de significación para describir la diferencia de esta sesión.')
h('Corrección numérica')
p(f"Las 12 mediciones MPI y los dos warmups registran valid=1. Las 24 filas own/LAPACK cumplen los controles exportados: residuo proyectado y diferencia de factor <=1e-12. Máximo residuo útil: {audit['max_projected_residual']:.3e}; máxima diferencia de factor: {audit['max_factor_difference']:.3e}. No se calcula residuo completo para estos tamaños.")
p('El ZIP adjunto coincide con los seis grupos estadísticos y con las razones recalculadas desde los originales. No se utilizó su narrativa como sustituto de la verificación de datos.')

page('Acercamiento relativo, no cruce')
chart('razones.png',165)
p('Figura 2. Izquierda: valores mayores que uno indican mejora MPI frente al C propio. Derecha: valores mayores que uno indican que MPI tarda más que LAPACK. Los denominadores responden preguntas distintas.')
table([['N','C / MPI','E MPI %','C / LAPACK','MPI / LAPACK'],*[[r['N'],f"{r['own_over_mpi_speedup']:.3f}",f"{100*r['mpi_efficiency_vs_own_P6']:.1f}",f"{r['own_over_lapack_speedup']:.3f}",f"{r['mpi_over_lapack_time_ratio']:.3f}"] for r in ratios]],[60,100,100,120,120])
p('La eficiencia respecto del C propio es S/6: 27,9% y 32,5%. No equivale a utilización de CPU. LAPACK sigue por delante usando un hilo; no se ejecutó ScaLAPACK. La cuota de seis CPUs equivalentes no implica seis cores exclusivos.')
gaps=[S[n,'mpi_p6']['median_s']-S[n,'lapack']['median_s'] for n in [6144,8192]]
p(f"La diferencia absoluta MPI menos LAPACK pasa de {gaps[0]:.3f} s a {gaps[1]:.3f} s. Por tanto, 'se acerca' solo es correcto en la razón relativa entre estos tamaños. Dos puntos no permiten extrapolar un tamaño donde MPI alcance a la biblioteca ni establecer una tendencia monótona.")
h('Interpretación y límite causal')
p('Repartir el trabajo del kernel propio obtiene una mejora, pero no compensa la ventaja local de LAPACK/OpenBLAS en esta medición. La campaña no separa las contribuciones de localidad, vectorización, algoritmos internos de la biblioteca o comunicación. No hace falta identificar cada causa para responder la comparación experimental.')

page('Relojes secundarios y condiciones del entorno')
table([['N','Método','Generación s','Reloj secundario','Mediana s'],*[[r['N'],r['method'],f"{r['generation_median_s']:.4f}",r['secondary_clock'],f"{r['secondary_median_s']:.4f}"] for r in context]],[55,85,110,145,85])
p('Estas medianas se presentan como contexto: no se construyen cocientes entre application_s y total_s. MPI application_s incluye reserva, generación, factorización y reunión/reconstrucción; total_s del banco own/LAPACK incluye reserva, generación y factor. Ninguno es el tiempo externo del comando. No se suman medianas para reconstruir totales.')
h('Salto en la generación')
p('La generación secuencial pasa de aproximadamente 0,402 s a 3,98 s al cambiar N=6144 por N=8192. El salto es observado, pero su causa no se aisló. La hipótesis del stride de 65536 bytes por fila puede motivar trabajo futuro; no se presenta como explicación demostrada ni exige una nueva campaña para cerrar esta pregunta.')
p('Su duración no se suma a factor_s. Sin embargo, la generación previa puede afectar caché y colocación de memoria al entrar al kernel: separar cronómetros no elimina toda influencia indirecta. Esa salvedad delimita la comparación, sin borrar la amplia diferencia observada.')
h('Cuota y procedencia')
p(f"Entre lecturas de cpu.stat hubo {delta['nr_throttled']} períodos adicionales con throttling y {delta['throttled_usec']/1e6:.6f} s adicionales en throttled_usec. Son contadores de toda la sesión durante el intervalo, no tiempos perdidos atribuibles a una repetición. No se corrigen los resultados restando ese valor.")
p('El paquete conserva fuentes, CSV y entorno, pero no script, binarios, códigos de salida del shell ni binding por ejecución. Los hashes de binarios mencionados en entorno.txt no pueden cotejarse sin esos binarios. Los .err MPI están vacíos y los de own/LAPACK informan threads=1. El estado numérico MPI es explícito; en own/LAPACK se verifican los residuos y diferencias exportados.')

page('Conclusión final de la comparación')
h('Respuesta a la pregunta planteada')
p('En N=6144 y N=8192, con la sesión limitada a seis CPUs equivalentes, MPI P6 acelera el kernel propio 1,67 y 1,95 veces, respectivamente. Aun así, sus medianas de factorización son 8,58 y 6,25 veces las de LAPACK/OpenBLAS a un hilo. No se observó que MPI alcanzara ni superara a LAPACK en ninguno de los dos tamaños ensayados.')
h('Cómo completa el proyecto')
p('La investigación muestra cuatro resultados complementarios: hay un tamaño mínimo ensayado donde el MPI propio empieza a compensar; la escalabilidad depende de N y P; el comando completo conserva menos ganancia que el reloj interno; y una biblioteca optimizada puede superar al kernel propio aun cuando este usa varios procesos. No se mezclan clocks ni referencias para obtener esas conclusiones.')
p('La ganancia MPI es real respecto de la base propia medida, pero no demuestra superioridad frente a implementaciones especializadas. Esta distinción es un resultado valioso del proyecto, no una razón para seguir ampliando matrices hasta encontrar un resultado favorable.')
h('Mi recomendación de cierre')
p('Con esta campaña, la pregunta final queda respondida para el alcance acordado. Recomiendo cerrar la experimentación y consolidar la conclusión general y la defensa. No es necesario probar 96 cores, implementar OpenMP o investigar en detalle el salto del generador. Se pueden mencionar como extensiones, sin convertirlas en requisitos del trabajo universitario.')
p('El límite principal sigue siendo una familia de matrices SPD y una sesión bajo cuota compartida. La campaña no prueba comportamiento multinodo, ni ScaLAPACK, ni un cruce futuro. La diferencia relativa observada es amplia, aunque los bancos no comparten exactamente el mismo régimen de lanzamiento y calentamiento.')
h('Reproducibilidad')
p('Se conservan los dos paquetes recibidos. observaciones.csv contiene las 36 mediciones útiles; warmups_mpi.csv conserva las dos filas descartadas. resumen_factor.csv, razones.csv, contexto.csv y auditoria_independiente.json se regeneran con desde_cero/docs/generar_informe_final_grande_cluster.py. El proceso no ejecuta código ni binarios recibidos. Estadísticas independientes coincidentes con el análisis adjunto. Documentación asistida por IA.')
(D/'informe.md').write_text('\n'.join(md),encoding='utf-8')
out=ROOT/'output/pdf/Cholesky_Etapa_19_Comparacion_final_grande.pdf'
def footer(c,d):c.setFont('Helvetica',8);c.drawString(45,25,'Cholesky | Etapa 19 | Comparación final | 28/09/2026');c.drawRightString(550,25,str(d.page))
SimpleDocTemplate(str(out),pagesize=A4,leftMargin=45,rightMargin=45,topMargin=36,bottomMargin=43).build(story,onFirstPage=footer,onLaterPages=footer)
assert len(PdfReader(out).pages)==5
print(json.dumps(dict(pdf=str(out),audit=audit,ratios=ratios),indent=2))
