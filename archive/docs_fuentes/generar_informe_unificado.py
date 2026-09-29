"""Guía narrativa única más evidencia íntegra de diez etapas, con índice y marcadores."""
from pathlib import Path
import csv,io,json,sys,hashlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.mathtext import math_to_image
from svglib.svglib import svg2rlg
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pypdf import PdfReader,PdfWriter
TMP=ROOT/'tmp/pdfs/unificado';TMP.mkdir(parents=True,exist_ok=True)
OUT=ROOT/'output/pdf/Cholesky_Investigacion_Completa.pdf'
chapters=[
('1_Fundamentos_y_diseno','Fundamentos, left/right y memoria'),
('2_MPI_y_distribuciones','Primer MPI: contiguo y cíclico'),
('3_MPI_vector_local','Vector local y nuevo reparto preferido'),
('4_Cuando_conviene_MPI','Cuándo compensa MPI: kernel'),
('5_Left_vs_Right_MPI','Left MPI frente a right MPI'),
('6_Tiempo_total_MPI','Incluir distribución y recolección'),
('7_Generacion_distribuida','Generación distribuida y validación'),
('8_Flujo_con_generacion','Generación dentro del flujo completo'),
('9_Distribucion_bloque_ciclica','Bloques de columnas y repetición'),
('10_Preparacion_cluster','Nueva sesión, LAPACK y preparación'),
('11_Programa_candidato','Programa candidato y comprobaciones'),
('12_Speedup_candidato','Speedup y eficiencia del candidato'),
('13_Tiempo_externo_y_cierre','Tiempo externo y cierre local'),
('14_Repeticion_local','Repetición en otra sesión y referencia')]
sources=[ROOT/'output/pdf'/('Cholesky_Etapa_'+c[0]+'.pdf') for c in chapters]
readers=[PdfReader(p) for p in sources]
manifest=[];start=9
for p,r,(_,title) in zip(sources,readers,chapters):
    manifest.append(dict(file=p.name,title=title,start_page=start,pages=len(r.pages),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    start+=len(r.pages)
with (ROOT/'desde_cero/resultados/aplicacion_local_20260922/resumen.csv').open() as f:raw=list(csv.DictReader(f))
R={(int(r['N']),int(r['P']),r['method']):r for r in raw}
speed=[]
for n in (512,1024,2048):
 for proc in (1,3,6):
    s=float(R[n,proc,'sequential']['total_median_s']);t=float(R[n,proc,'distributed']['total_median_s'])
    speed.append(dict(N=n,P=proc,sequential_s=s,mpi_s=t,speedup=s/t,efficiency=s/t/proc))
fig,axes=plt.subplots(1,2,figsize=(8.8,3.2),layout='constrained')
for n in (512,1024,2048):
 rr=[r for r in speed if r['N']==n]
 axes[0].plot([r['P'] for r in rr],[r['speedup'] for r in rr],marker='o',label=f'n={n}')
 axes[1].plot([r['P'] for r in rr],[r['efficiency']*100 for r in rr],marker='o',label=f'n={n}')
axes[0].plot([1,3,6],[1,3,6],'k--',label='Ideal S=P');axes[0].axhline(1,color='gray',lw=.6)
axes[0].set(xlabel='Procesos',ylabel='Speedup útil del flujo',xticks=[1,3,6]);axes[0].legend(fontsize=7)
axes[1].set(xlabel='Procesos',ylabel='Eficiencia útil (%)',xticks=[1,3,6]);axes[1].legend(fontsize=7)
for a in axes:a.grid(alpha=.2)
fig.savefig(TMP/'speedup.png',dpi=180);plt.close(fig)
styles=getSampleStyleSheet();styles['BodyText'].leading=14;story=[]
def p(t):story.extend([Paragraph(t,styles['BodyText']),Spacer(1,8)])
def h(t):story.append(Paragraph(t,styles['Heading2']))
def page(t):
 if story:story.append(PageBreak())
 story.extend([Paragraph(t,styles['Title']),Spacer(1,10)])
def eq(t):
 b=io.BytesIO();math_to_image('$'+t+'$',b,format='svg');b.seek(0);d=svg2rlg(b);d.hAlign='CENTER';story.extend([d,Spacer(1,10)])
def table(data,widths):
 t=Table([[Paragraph(str(c),styles['BodyText']) for c in row] for row in data],colWidths=widths)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecf0')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),6)]));story.extend([t,Spacer(1,8)])
page('Cholesky paralelo: investigación completa')
p('Documento principal, actualizado al 27/09/2026. Reúne el recorrido y catorce informes íntegros. Las etapas 11-14 cierran el alcance local: candidato, speedup, reloj externo y repetición en otra sesión. C para algoritmos y medición; Python para análisis y documentos. Clúster pendiente.')
h('Cómo leerlo sin perder el hilo')
p('Las páginas 1-8 reconstruyen el camino y explican qué conservamos hoy. A partir de la página 9 están todos los capítulos experimentales, en orden, con sus pruebas, tablas, gráficos, ecuaciones y conclusiones originales. Los marcadores del PDF permiten saltar a cada etapa.')
p('Los capítulos históricos pueden decir "pendiente" o recomendar un siguiente paso que ya realizamos. Esas frases describen su momento: la decisión vigente está en esta guía. Se conserva toda su evidencia para no borrar los resultados que hicieron cambiar de postura. No se incluye la primera versión de fundamentos y validación, que fue sustituida por pedido del usuario.')
table([['Evidencia completa','Página global']]+[[m['title'],m['start_page']] for m in manifest],[420,65])
p('La numeración inferior "Unificado" es global. Los números de los capítulos conservados son locales. Los CSV individuales y las fuentes están en el proyecto y quedan identificados por campaña; no se vuelcan miles de filas crudas al cuerpo del informe.')
page('1. Entender qué se puede paralelizar')
p('El objetivo es construir un factor triangular inferior L para una matriz simétrica definida positiva A. Estudiamos matrices densas y double. La corrección se comprueba antes de interpretar los tiempos.')
eq(r'A=LL^T')
h('Left-looking: reunir contribuciones anteriores')
eq(r'L_{jj}=\sqrt{A_{jj}-\sum_{k<j}L_{jk}^2}')
eq(r'L_{ij}=\frac{A_{ij}-\sum_{k<j}L_{ik}L_{jk}}{L_{jj}},\quad i>j')
p('Cuando están disponibles los aportes anteriores y el pivote, distintos elementos debajo de la diagonal pueden calcularse simultáneamente. Nuestra versión MPI distribuye sumas parciales entre propietarios de columnas anteriores y las reúne mediante reducciones.')
h('Right-looking: propagar una columna terminada')
eq(r'S_{ik}\leftarrow S_{ik}-L_{ij}L_{kj},\quad i\geq k>j')
p('La columna j terminada se difunde; cada proceso actualiza destinos propios. Esos destinos son independientes dentro de esa etapa. Las columnas completas NO son independientes: la siguiente requiere sus actualizaciones previas. Ambas variantes pueden paralelizarse.')
h('Primera pregunta y primera respuesta')
p('¿Conviene right por ser naturalmente repartible? La teoría motiva probarlo, pero no decide el rendimiento. En el primer experimento secuencial n=1024, left tardó 137,69 ms y right original 1109,62 ms. Por tanto, aquella implementación original de right no era una buena base de rendimiento.')
h('Cómo construimos la entrada')
eq(r'A_{ii}=1+\sum_{j\ne i}|A_{ij}|')
p('Se generan pares simétricos con semilla fija y se completa la diagonal. La matriz resulta definida positiva por simetría y dominancia diagonal estricta con diagonal positiva. Es una familia reproducible; no representa todas las matrices ni estudia por sí sola problemas mal condicionados.')
page('2. Mejorar memoria antes de repartir')
h('¿Qué pasaría si la lectura de la columna fuera contigua?')
p('Copiamos la columna activa a un vector y contamos esa copia dentro del tiempo. Conservamos la aritmética y el orden de actualización. En una nueva campaña n=1024: left 144,79 ms, right original 1159,09 ms y right con vector 76,92 ms. Elegimos right con vector como base local.')
p('Eso respalda la importancia del acceso a datos; no aísla qué porcentaje se debe a caché o vectorización. Los números de las dos campañas no se mezclan para calcular cocientes.')
h('Primer MPI: ¿contiguo o cíclico?')
p('El dueño calcula la columna, ejecuta MPI_Bcast y todos actualizan columnas locales. El reparto contiguo entrega un intervalo a cada proceso. El cíclico alterna columnas entre ellos. Contar operaciones favorecía al cíclico, pero el primer código fue más lento con ese reparto.')
h('¿Equilibrar trabajo alcanza?')
p('No. El cíclico tenía lecturas e indexación costosas. Agregamos un vector local contiguo con los valores que cada proceso reutiliza. Para n=1024, P=3: cíclico original 72,04 ms, cíclico con vector 32,77 ms y contiguo con vector 39,66 ms. El secuencial contemporáneo fue 88,62 ms: speedup útil del kernel 2,70x.')
h('¿Y si left también funciona bien en MPI?')
p('Lo implementamos y comparamos directamente. En n=1024, P=3: left MPI 54,08 ms frente a right MPI 31,48 ms. Right tuvo menor mediana en las 20 configuraciones de esa campaña. Nuestra versión left requiere hasta 3n-1 colectivas y right n difusiones.')
p('La conclusión es sobre esas implementaciones y ese reparto. No demuestra que todos los left-looking sean inferiores. El perfil también incluye espera dentro de las colectivas.')
h('Decisión que conservamos')
p('Right-looking con vector local y distribución cíclica es la referencia principal. Las variantes anteriores siguen siendo evidencia y controles experimentales; no son todas "versiones finales" del programa.')
page('3. Del kernel al programa que entrega L')
h('¿Cuándo comienza a compensar MPI?')
p('En la campaña de tamaños pequeños, n=256 y P=3 fue el primer punto probado con mejora del kernel según la regla predefinida en tres rondas. No es un umbral universal y no incluye generación, distribución inicial ni reunión.')
h('¿Se mantiene al mover los datos?')
p('Añadimos empaquetado, distribución y recolección. En esa grilla la primera mejora clara apareció en n=512. Para n=1024, P=3, el flujo centralizado tardó 49,70 ms frente a 94,52 ms secuenciales: 1,90x. Aún faltaba generar A dentro del reloj.')
h('La consulta docente cambia la pregunta')
p('La profesora pidió considerar el proceso completo. Por eso estudiamos generación y fases, sin abandonar el speedup. Encontramos una forma de generar las mismas columnas directamente en cada proceso, idénticas bit a bit al generador original.')
p('En la prueba aislada n=2048, P=6, preparar la entrada pasó de 51,86 a 8,38 ms. Pero al integrar reserva, generación, kernel y salida, el total pasó de 874,60 a 837,39 ms: solo 4,3 % de reducción en esa campaña. La mejora de una fase no es la mejora del programa completo.')
h('Qué significa "total" en los informes')
p('Las etapas amplían el intervalo medido. Etapas 2-5: kernel. Etapa 6: entrada + kernel + salida. Etapa 7: preparación de entrada aislada. Etapas 8-10 MPI: reserva + generación + kernel + reunión. En las últimas, MPI ya está iniciado; lanzamiento, cierre, validación y liberación quedan fuera. No confundirlo con el tiempo externo del comando.')
h('Validar también cuesta')
p('Reconstruir LL transpuesta cuesta O(n³). Agregamos ocho comprobaciones con vectores de costo O(n²) por vector, junto con comparación contra el factor secuencial. El residuo completo permanece en casos pequeños. Las proyecciones solas no certifican corrección; las referencias grandes aún cuestan memoria y tiempo fuera del reloj principal.')
page('4. Sí medimos speedup: qué significa')
eq(r'S_{util}(n,P)=\frac{\operatorname{mediana}(T_{secuencial})}{\operatorname{mediana}(T_{MPI,P})},\qquad E_{util}=S_{util}/P')
p('También puede medirse escalabilidad interna como T_MPI,1/T_MPI,P. Es otra referencia. Un cociente entre dos repartos con el mismo P mide una optimización; no es el speedup por aumentar procesos. LAPACK frente a C propio tampoco es speedup MPI.')
story.append(Image(str(TMP/'speedup.png'),width=485,height=176))
p('Gráfico recuperado de la etapa 8, campaña aplicacion_local_20260922: ningún experimento nuevo. Medianas de seis repeticiones. Secuencial contemporáneo en rango 0 mientras otros rangos esperan; total con generación y L en rango 0. La referencia varía entre lanzamientos: limitación ya declarada. No son resultados del clúster.')
table([['n, P','Secuencial ms','MPI ms','S útil','E útil']]+[[f'{n}, 6',f'{1000*R0["sequential_s"]:.2f}',f'{1000*R0["mpi_s"]:.2f}',f'{R0["speedup"]:.2f}',f'{100*R0["efficiency"]:.1f} %'] for n in (512,1024,2048) for R0 in speed if R0['N']==n and R0['P']==6],[75,115,100,85,110])
h('Por qué no alcanza con mostrar S')
p('El speedup importa, pero depende de la calidad de la referencia y de qué incluye el reloj. Además mostramos tiempo absoluto, eficiencia, corrección, dispersión y recursos. Una base secuencial deliberadamente lenta puede producir un speedup grande y un programa lento.')
p('La mediana total sale de totales medidos directamente, no de sumar medianas de fases. Los cuartiles muestran dispersión, no intervalos de confianza. En el clúster volveremos a medir la referencia en el mismo hardware y sesión; nunca la tomaremos de WSL.')
page('5. Repetir puede cambiar una decisión')
h('¿Agrupar columnas mejora el reparto?')
p('Probamos grupos de 1,2,4,8,16,32,64 columnas. Todos siguen usando Cholesky escalar por columnas. b=1 reproduce el cíclico. El tiempo y el conteo de actualizaciones se compararon por separado.')
p('El 22/09 b=4 pareció favorable para n=1024, P=6: en una repetición 48,93 ms con b=1 frente a 44,02 ms con b=4. Para n=2048 la diferencia quedó en 0,2 %. El 24/09, nueva sesión: n=1024 dio 42,34 frente a 43,36 ms; n=2048 dio 767,99 frente a 798,87 ms. La mejora no se sostuvo.')
h('Decisión vigente')
p('Conservamos una columna como referencia principal. Cuatro columnas permanece como variante experimental. No cambiamos permanentemente el programa por cada mínimo observado; las pruebas también sirven para descartar una mejora como regla.')
h('¿Cuánto margen queda en el cálculo local?')
p('Incorporamos LAPACK como referencia externa desde C, sin MPI y con OpenBLAS de un hilo comprobado. Para n=2048: nuestro factor tardó 1484,35 ms y LAPACK 116,30 ms; los totales con generación fueron 1527,24 y 156,85 ms. No mezclamos estos datos con los de los lanzamientos MPI.')
p('La biblioteca combina organización del cálculo y kernels optimizados. Eso evidencia margen de mejora, pero no mide el aporte aislado de bloques, vectorización o caché. No reemplazamos nuestra implementación MPI con LAPACK.')
h('¿Hace falta implementar todo antes del clúster?')
p('No. Acordamos cerrar la preparación local, probar un tamaño mayor y dejar disponibles scripts y referencias. n=3072 fue un piloto con dos repeticiones: prueba factibilidad, no estabilidad estadística. Cholesky por bloques, OpenMP, almacenamiento triangular y reparto 2D quedan como extensiones.')
p('Próxima pregunta principal: ¿qué cambia al usar procesos dentro de un nodo y entre nodos distintos, con matrices que justifiquen esos recursos?')
page('6. En qué arquitectura estamos')
h('Seguimos en 1D')
p('1D describe el reparto de la matriz: distribuimos columnas entre procesos. Agrupar columnas no añade una segunda dimensión. Un reparto 2D asignaría bloques según filas y columnas sobre una malla de procesos. No lo implementamos.')
table([['Concepto','Qué significa aquí'],['MPI','Procesos con memoria distribuida; nuestro algoritmo principal.'],['LAPACK / OpenBLAS','Biblioteca de factorización y operaciones numéricas; referencia local con un hilo.'],['OpenMP','Paralelismo con hilos; habría que decidir regiones paralelas y sincronización. No está incorporado.'],['Bloques de reparto','Agrupan columnas para asignar propietarios; siguen siendo 1D.'],['Cholesky por bloques','Organiza el cálculo mediante submatrices; no se implementó en nuestro kernel.']],[125,360])
h('¿LAPACK es menos complejo que OpenMP?')
p('Usar una rutina probada como referencia demanda menos código propio que paralelizar y validar nuestro algoritmo con hilos. Pero comprender o reimplementar sus optimizaciones puede ser mucho más complejo. No son alternativas equivalentes: una biblioteca numérica y un modelo de paralelismo resuelven necesidades distintas.')
p('OpenMP requiere respetar dependencias y evitar carreras; sus implementaciones no están obligadas a detectar esos errores. LAPACKE ofrece la interfaz para llamar rutinas LAPACK desde C. Fuentes: <link href="https://www.openmp.org/spec-html/5.2/openmpse1.html" color="blue">OpenMP, alcance</link>; <link href="https://www.netlib.org/lapack/lapacke.html" color="blue">LAPACKE</link>.')
h('Qué no debemos concluir')
p('No demostramos superioridad universal de right, umbral universal para MPI, ventaja estable de b=4 ni escalabilidad entre nodos. Sí tenemos una implementación correcta en los casos probados, comparaciones trazables y decisiones locales revisables.')
page('7. Código de entrega y repositorio')
h('Una implementación elegida, varios experimentos')
p('El núcleo candidato está en src/cholesky_mpi.c, función cholesky_mpi_local. El generador y las comprobaciones están en src/cholesky.c. compare_application.c y compare_blocks.c son bancos de pruebas: no deben confundirse con varios algoritmos finales independientes.')
p('El candidato ya está consolidado en src/main_candidate.c: make candidate produce cholesky_candidate_mpi y la referencia secuencial autónoma. Recibe N, genera, factoriza, reúne L en memoria, valida y emite métricas CSV. No escribe el factor a disco. La configuración final depende del clúster.')
h('Versión candidata actual')
p('El archivo cholesky_final_hpc.c de la raíz pertenece al trabajo anterior al reinicio en desde_cero. Pese a su nombre, no es la entrega vigente. Ese informe anterior y la primera versión sustituida no integran la evidencia de este documento.')
p('Right-looking escalar, reparto 1D cíclico b=1, vector local, generación distribuida y salida completa en rango 0 para el escenario principal. Las comparaciones centralizadas, left, b=4 y LAPACK permanecen como evidencia. No se incorporan automáticamente todas al programa final.')
h('Cómo versionar la investigación')
p('Un repositorio Git conserva cambios mediante commits con el motivo y validación. Las etapas experimentales conservan CSV, protocolo y fuentes congeladas. Una etiqueta puede señalar una versión validada. No necesitamos archivos final2.c, final3.c ni inventar commits históricos: el primer commit registra el estado reunido hoy, y los snapshots conservan lo anterior.')
p('El repositorio se prepara localmente. Publicar en GitHub u otro servicio requiere elegir destino y visibilidad; no se publica por defecto. No se incluyen ejecutables, cachés, bibliotecas instaladas ni carpetas temporales.')
h('Próximos pasos, sin agregar ramas nuevas')
latest=json.loads((ROOT/'desde_cero/resultados/cierre_local_20260927/analisis.json').read_text())
latest6=next(r for r in latest['summary'] if r['N']==2048 and r['method']=='6')
p(f"Etapas 11-14 completadas: dos sesiones, cada una con 30 casos pequeños y 192 lanzamientos (168 medidos). N=2048/P=6: el 24/09 S app=1,83 y S externo=1,16; el 27/09 S app={latest6['application_s_speedup']:.2f} y S externo={latest6['external_s_speedup']:.2f}. No mezclamos las muestras. Lo próximo es configurar y probar el clúster.")
p('A continuación se conserva la evidencia completa en orden histórico. Los documentos originales no se reescriben para que parezca que siempre supimos qué variante elegir: los cambios de postura son parte de la investigación.')
def foot(c,d):c.setFont('Helvetica',8);c.drawString(48,28,'Guía de lectura | Decisiones actualizadas al 27/09/2026')
front=TMP/'guia.pdf';SimpleDocTemplate(str(front),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=42,bottomMargin=46).build(story,onFirstPage=foot,onLaterPages=foot)
fr=PdfReader(front);assert len(fr.pages)==8,f'La guia debe tener 8 paginas: {len(fr.pages)}'
writer=PdfWriter();writer.append(fr,import_outline=False)
for i,name in enumerate(['Inicio e índice','Fundamentos','Memoria y MPI','Evolución del reloj','Speedup y eficiencia','Bloques y LAPACK','1D y tecnologías','Código y repositorio']):writer.add_outline_item(name,i)
for reader,m in zip(readers,manifest):
    offset=len(writer.pages);writer.append(reader,import_outline=False);writer.add_outline_item(m['title'],offset)
total=len(writer.pages)
for i,pdfpage in enumerate(writer.pages):
    b=io.BytesIO();c=canvas.Canvas(b,pagesize=(float(pdfpage.mediabox.width),float(pdfpage.mediabox.height)))
    c.setFont('Helvetica',7);c.setFillColor(colors.HexColor('#526673'));c.drawRightString(float(pdfpage.mediabox.width)-30,12,f'Unificado | {i+1} / {total}');c.save();b.seek(0);pdfpage.merge_page(PdfReader(b).pages[0])
writer.add_metadata({'/Title':'Cholesky paralelo: investigación completa','/Subject':'Guía narrativa y evidencia integral, etapas 1 a 10'})
with OUT.open('wb') as f:writer.write(f)
check=PdfReader(OUT);assert len(check.pages)==8+sum(len(r.pages) for r in readers)
for i,p in enumerate(check.pages):assert p.extract_text().strip(),f'Pagina vacia {i+1}'
(TMP/'manifest.json').write_text(json.dumps(dict(pages=total,sources=manifest,speedup=speed),indent=2),encoding='utf-8')
print(OUT);print('Paginas:',total)
