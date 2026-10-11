"""Etapa 2: resultados medidos de la primera implementacion MPI en C."""
from pathlib import Path
import csv
import io
import json
import os
import sys
ROOT=Path(__file__).resolve().parents[2]
if os.name=='nt':sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
from matplotlib.mathtext import math_to_image
from matplotlib.font_manager import FontProperties
from svglib.svglib import svg2rlg
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Table,TableStyle,Image
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor,white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

DATA=ROOT/'desde_cero/resultados/mpi_20260921'
OUT=ROOT/'output/pdf/Cholesky_Etapa_2_MPI_y_distribuciones.pdf'
fonts=Path('C:/Windows/Fonts')
font_files=[('Body','calibri.ttf'),('Bold','calibrib.ttf')]
if not (fonts/'calibri.ttf').exists():
    fonts=Path(matplotlib.get_data_path())/'fonts/ttf'
    font_files=[('Body','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf')]
for name,file in font_files:pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold')
INK=HexColor('#172B3A'); BLUE=HexColor('#126F85')
styles={
    'title':ParagraphStyle('title',fontName='Bold',fontSize=23,leading=27,textColor=INK,spaceAfter=14),
    'h':ParagraphStyle('h',fontName='Bold',fontSize=14,leading=18,textColor=BLUE,spaceBefore=11,spaceAfter=7),
    'body':ParagraphStyle('body',fontName='Body',fontSize=11.2,leading=15.3,textColor=INK,spaceAfter=9),
    'small':ParagraphStyle('small',fontName='Body',fontSize=9,leading=12,textColor=HexColor('#536675'),spaceAfter=8),
    'cell':ParagraphStyle('cell',fontName='Body',fontSize=10,leading=13,textColor=INK),
}
story=[]
def p(text,style='body'):story.append(Paragraph(text,styles[style]))
def h(text):p(text,'h')
def page(number,title):
    if story:story.append(PageBreak())
    p('CHOLESKY / ETAPA 2 / EXPERIMENTO 3 / '+number,'small');p(title,'title')
def eq(formula,size=16):
    buf=io.BytesIO();math_to_image('$'+formula+'$',buf,prop=FontProperties(size=size),format='svg',color='#172B3A')
    buf.seek(0);d=svg2rlg(buf);d.hAlign='CENTER';story.extend([Spacer(1,3),d,Spacer(1,9)])
def table(rows,widths):
    t=Table([[Paragraph(str(c),styles['cell']) for c in r] for r in rows],colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#DCECF0')),('ROWBACKGROUNDS',(0,1),(-1,-1),[HexColor('#F1F6F8'),white]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.extend([t,Spacer(1,8)])
def fig(name,w,h):story.extend([Image(str(DATA/name),width=w,height=h),Spacer(1,5)])
def fmt(x,d=2):return f'{float(x):.{d}f}'.replace('.',',')
def ms(row):return fmt(float(row['median_s'])*1000)
with (DATA/'resumen_mpi.csv').open() as f:rows=list(csv.DictReader(f))
R={(int(r['N']),int(r['P']),r['distribution']):r for r in rows}
with (DATA/'perfil_resumen.csv').open() as f:profile=list(csv.DictReader(f))
seq=json.loads((DATA/'referencias.json').read_text())
validation=json.loads((DATA/'validacion.json').read_text())

page('01','¿Cuándo conviene repartir el trabajo?')
p('En la etapa anterior mejoramos el acceso a memoria de right-looking. Ahora damos el primer paso hacia memoria distribuida: implementamos MPI en C y comparamos propiedad estática contigua y cíclica. Python analiza los tiempos y prepara gráficos; no realiza la factorización.')
h('Hipótesis inicial')
p('Con matrices pequeñas, comunicar cada columna puede costar más que el cálculo ahorrado. Al crecer n, esperamos que varios procesos resulten útiles. El reparto cíclico debería equilibrar mejor las actualizaciones, pero eso <b>no garantiza</b> que sea el más rápido en esta implementación.')
h('Qué hace cada proceso')
p('<b>1. Asignar:</b> repartimos las columnas antes de factorizar. Cada proceso guarda solo las suyas, empaquetadas por filas.<br/><b>2. Calcular:</b> el dueño de la columna j calcula el pivote y los elementos inferiores de esa columna.<br/><b>3. Difundir:</b> todos llaman a MPI_Bcast; el dueño envía el tramo de la columna desde j hasta n−1.<br/><b>4. Actualizar:</b> cada proceso modifica las posiciones de sus columnas k &gt; j, usando el vector recibido. Luego avanzamos a j+1.')
eq(r'a_{ik}\leftarrow a_{ik}-l_{ij}l_{kj},\qquad i\geq k>j')
p('Los destinos pertenecen a procesos distintos: las actualizaciones de una etapa son independientes. Las columnas sucesivas siguen teniendo dependencias. Usamos comunicaciones bloqueantes y no incorporamos solapamiento ni tareas dinámicas.')
h('La misma matriz, dos propietarios posibles')
table([['n=8, P=3','Columnas de P0','Columnas de P1','Columnas de P2'],['Contiguo','0, 1, 2','3, 4, 5','6, 7'],['Cíclico','0, 3, 6','1, 4, 7','2, 5']],[95,134,134,134])
p('En contiguo, las primeras n mod P tareas reciben una columna adicional. En cíclico, owner(k)=k mod P. Incluso si P &gt; n, los procesos sin columnas participan en las comunicaciones. El reparto no cambia durante la factorización.','small')
p('MPI_Bcast distribuye un mensaje desde el dueño a todos los procesos del comunicador. Fuente: <link href="https://docs.open-mpi.org/en/main/man-openmpi/man3/MPI_Bcast.3.html" color="#126F85">documentación oficial de Open MPI</link>.','small')

page('02','Cómo medimos y qué comparamos')
table([['Decisión','Protocolo ejecutado'],['Equipo','Un equipo, WSL2 / Ubuntu 26.04, AMD Ryzen 5 2600; Open MPI 5.0.10 y GCC 15.2.0.'],['Compilación','-O3 -std=c11 -Wall -Wextra -Wpedantic; double, sin BLAS.'],['Tamaños y procesos','n = 64, 256, 512, 1024; P = 1, 2, 3, 4. Un proceso por núcleo distinto, según la topología expuesta por WSL.'],['Repeticiones MPI','Un calentamiento por reparto y 8 repeticiones medidas. Contiguo y cíclico alternan el orden. El orden de P rota entre tamaños.'],['Referencias secuenciales','Left, right original y right con vector. Seis repeticiones antes y seis después de MPI para cada tamaño; misma semilla 2026.']],[113,384])
h('El tiempo principal incluye cálculo y comunicación')
eq(r'T_P=\max_{r=0,\ldots,P-1}(t_{r,\mathrm{fin}}-t_{r,\mathrm{inicio}})')
p('Una barrera coordina el inicio. Cada proceso mide su duración con MPI_Wtime; al finalizar tomamos el máximo. No restamos marcas de reloj de procesos diferentes. El cronómetro incluye el armado del vector, las difusiones y las actualizaciones; excluye generación, reserva, distribución inicial, reunión del factor y comprobaciones. Tampoco incluye iniciar mpirun.')
p('<b>Por tanto, medimos el kernel de factorización, no el tiempo de la aplicación completa.</b> El proceso 0 genera y reúne matrices completas para este banco de pruebas; esa preparación también limita la escalabilidad futura.')
h('Dos aceleraciones responden preguntas distintas')
eq(r'S_{\mathrm{MPI}}=\frac{\widetilde T_{\mathrm{MPI},1}}{\widetilde T_{\mathrm{MPI},P}},\qquad S_{\mathrm{util}}=\frac{\min_v\widetilde T_{v,\mathrm{seq}}}{\widetilde T_{\mathrm{MPI},P}}',15)
p('La primera compara un reparto consigo mismo al aumentar P. La segunda comprueba si supera al mejor secuencial de esta campaña; esa es la relevante para decidir si nos conviene usar MPI. Reportamos medianas y cuartiles inclusivos. Los cuartiles describen dispersión; no son intervalos de confianza.','small')
p('MPI_Wtime mide tiempo local. Fuente: <link href="https://docs.open-mpi.org/en/main/man-openmpi/man3/MPI_Wtime.3.html" color="#126F85">documentación oficial de Open MPI</link>.','small')

page('03','Resultado: más procesos no siempre ayudan')
fig('tiempos_mpi.png',497,373)
p('Figura 1. Medianas de 8 repeticiones por configuración; barras Q1-Q3. La línea verde muestra la mejor mediana secuencial contemporánea. Cada panel tiene su propia escala vertical.','small')
h('Lo que vemos')
p('<b>n=64:</b> usar más de un proceso aumenta el tiempo en ambos repartos. Hay demasiado poco trabajo para amortizar la coordinación.<br/><b>n=256 y n=512:</b> el contiguo ya obtiene mejoras útiles; el cíclico presenta resultados cercanos al secuencial o más lentos en varias configuraciones.<br/><b>n=1024:</b> ambos repartos mejoran al pasar de 1 a 3 procesos. Agregar un cuarto no reduce la mediana en esta campaña.')
p('Contiguo y cíclico comparten el código de factorización y las operaciones matemáticas. Sin embargo, el reparto cambia los índices, los accesos al vector difundido y el código que puede optimizar el compilador. Esta prueba compara las implementaciones completas, no aísla exclusivamente el balance de carga.')

page('04','¿Cuándo empieza a convenir MPI?')
best_rows=[['n','Mejor sec. (ms)','Mejor MPI P≥2','MPI (ms)','S útil']]
for n in [64,256,512,1024]:
    best=min((R[n,p,d] for p in [2,3,4] for d in ['contiguous','cyclic']),key=lambda r:float(r['median_s']))
    best_rows.append([str(n),fmt(best['base_s'] and float(best['base_s'])*1000,3),('Contiguo' if best['distribution']=='contiguous' else 'Cíclico')+', P='+best['P'],fmt(float(best['median_s'])*1000,3),fmt(best['speedup_useful'])])
table(best_rows,[40,109,151,98,99])
p('Selección descriptiva de la menor mediana entre configuraciones probadas, no una garantía de que siempre sea la mejor. Right con vector fue la mejor referencia secuencial en los cuatro tamaños.','small')
h('Respuesta provisional para este equipo')
p('Con n=64 no conviene paralelizar este kernel. El primer tamaño probado con mejora clara del contiguo es n=256. Para n=1024 y P=3, el contiguo tarda '+ms(R[1024,3,'contiguous'])+' ms frente a '+fmt(float(R[1024,3,'contiguous']['base_s'])*1000)+' ms del secuencial: S útil = '+fmt(R[1024,3,'contiguous']['speedup_useful'])+'.')
p('<b>No encontramos un umbral exacto.</b> Faltan tamaños intermedios y campañas independientes. Tampoco suponemos que la conveniencia sea monótona: caché, reparto, sistema operativo y red pueden cambiar el resultado. P=3 y P=4 contiguos tienen cuartiles que se superponen en n=1024; no declaramos una superioridad concluyente de tres procesos.')
fig('speedup_util.png',497,242)
p('Figura 2. Aceleración útil del cíclico. Cerca de 1, una pequeña diferencia de medianas no basta para afirmar una mejora robusta. La evaluación entre nodos queda pendiente.','small')

page('05','¿Por qué no ganó el cíclico?')
p('La hipótesis de mejor reparto sí se cumple para el <b>número de actualizaciones</b>. Para n=1024 y P=3, los conteos exactos por proceso son:')
table([['Reparto','P0','P1','P2'],['Contiguo','46 434 993','86 086 814','46 434 993'],['Cíclico','59 652 153','59 652 153','59 652 494']],[107,130,130,130])
p('Pero el tiempo depende también de cuánto cuesta cada actualización y cuándo queda disponible. En el contiguo, el vector difundido se lee en posiciones consecutivas. En el cíclico, sus índices avanzan de P en P, aunque los destinos locales estén empaquetados. El cálculo de índices también difiere.')
fig('perfil_mpi.png',497,211)
p('Figura 3. Perfil separado para n=1024, P=3, con 3 repeticiones e instrumentación interna. Se apilan medianas de componentes; su suma no es necesariamente la mediana del total. Bcast incluye transferencia y espera por otros procesos: no mide únicamente red.','small')
h('Un control que impide una conclusión apresurada')
p('Con P=1, ambos repartos poseen las mismas columnas. Aun así, el contiguo tarda '+ms(R[1024,1,'contiguous'])+' ms y el cíclico '+ms(R[1024,1,'cyclic'])+' ms. Por tanto, <b>el desequilibrio entre procesos no explica toda la diferencia</b>. Los caminos de indexación y optimización local ya tienen un costo distinto.')
p('El informe de GCC registra versiones vectorizadas y no vectorizadas del bucle de actualización. Es una pista compatible con la diferencia de costo local, pero no cuantifica su causa. No medimos contadores de caché ni aislamos cada optimización del compilador.','small')

page('06','Qué aprendimos y cómo seguimos')
h('Decisión respaldada por esta campaña')
p('Ya tenemos una implementación MPI correcta con dos repartos estáticos. En los tamaños probados, el contiguo obtuvo menores medianas que el cíclico para cada P. Lo conservamos como referencia práctica; mantenemos el cíclico como candidato por su mejor equilibrio de operaciones. No elegimos una distribución de forma definitiva para el clúster.')
h('¿Y si ambos leyeran un vector local contiguo?')
p('Esa es la próxima pregunta. Después de recibir la columna, cada proceso podría copiar los valores que necesita a un vector ordenado como sus columnas locales. El bucle interno leería posiciones consecutivas tanto para contiguo como para cíclico. La copia costaría trabajo adicional: debemos incluirlo en el tiempo y comprobar si se amortiza.')
p('Este experimento permitiría reducir la diferencia de acceso e indexación antes de atribuir los resultados al reparto. Después repetiríamos el barrido de n y P en el clúster, distinguiendo un nodo de varios nodos. Todavía no incorporamos bloques, reparto dinámico ni comunicación solapada.')
h('Comprobaciones realizadas')
p('Ambos repartos pasaron casos SPD de tamaños 1, 2, 7, 16 y 31, un factor conocido 3×3 y rechazo colectivo de pivotes negativos y NaN, con P=1,2,3,4. Incluimos repartos desiguales y P &gt; n. Las '+str(validation['mpi_observations'])+' mediciones MPI tienen residuo relativo ≤ 10⁻¹² y coincidieron con el factor right secuencial dentro de 10⁻¹³; el residuo máximo observado fue 1,2131×10⁻¹⁵.')
p('UndefinedBehaviorSanitizer pasó con P=4. AddressSanitizer también pasó con P=4 al desactivar memory/patcher de Open MPI solo en la prueba. Con ese componente activo fallaba dentro de MPI_Init, incluso en un programa mínimo sin Cholesky. No se comprobó detección de fugas; las mediciones usaron compilación normal y la configuración MPI predeterminada.','small')
h('Archivos para reproducir y revisar')
table([['Archivo en desde_cero','Contenido'],['src/cholesky_mpi.c','Propietarios, índices y factorización distribuida.'],['src/compare_mpi.c','Banco de pruebas, validación, tiempo y perfil.'],['scripts/comparar_mpi.sh','Campaña con 1, 2, 3 y 4 procesos.'],['scripts/analizar_mpi.py','Estadísticas, aceleración, cuartiles y gráficos.'],['resultados/mpi_20260921/','CSV, entorno, afinidad, SHA-256 y resúmenes.']],[207,290])
p('Los 144 tiempos secuenciales, 256 tiempos MPI y 60 registros de perfil por rango se conservan por separado. Las etapas anteriores permanecen en el PDF de fundamentos; este capítulo continúa su análisis.','small')

def footer(c,doc):
    w,height=A4;c.setStrokeColor(HexColor('#CFDDE3'));c.line(48,height-36,w-48,height-36)
    c.setFont('Body',8);c.setFillColor(HexColor('#536675'))
    c.drawString(48,28,'HPC · Cholesky | MPI en C · Estadísticas en Python | 21/09/2026')
    c.drawRightString(w-48,28,str(doc.page))
OUT.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=49,bottomMargin=48,title='Cholesky, etapa 2: MPI y distribuciones',author='Proyecto Cholesky HPC 2026').build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
