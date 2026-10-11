"""Etapa 5: comparacion directa de left-looking y right-looking con MPI."""
from pathlib import Path
import csv,io,json,os,sys
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

DATA=ROOT/'desde_cero/resultados/left_right_mpi_20260922'
OUT=ROOT/'output/pdf/Cholesky_Etapa_5_Left_vs_Right_MPI.pdf'
fonts=Path('C:/Windows/Fonts');font_files=[('Body','calibri.ttf'),('Bold','calibrib.ttf')]
if not (fonts/'calibri.ttf').exists():
    fonts=Path(matplotlib.get_data_path())/'fonts/ttf';font_files=[('Body','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf')]
for name,file in font_files:pdfmetrics.registerFont(TTFont(name,str(fonts/file)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold')
INK=HexColor('#172B3A');BLUE=HexColor('#126F85')
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
    p('CHOLESKY / ETAPA 5 / EXPERIMENTO 6 / '+number,'small');p(title,'title')
def eq(formula,size=16):
    buf=io.BytesIO();math_to_image('$'+formula+'$',buf,prop=FontProperties(size=size),format='svg',color='#172B3A')
    buf.seek(0);d=svg2rlg(buf);d.hAlign='CENTER';story.extend([Spacer(1,3),d,Spacer(1,8)])
def table(rows,widths):
    t=Table([[Paragraph(str(c),styles['cell']) for c in r] for r in rows],colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#DCECF0')),('ROWBACKGROUNDS',(0,1),(-1,-1),[HexColor('#F1F6F8'),white]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    story.extend([t,Spacer(1,8)])
def fig(name,w,hgt):story.extend([Image(str(DATA/name),width=w,height=hgt),Spacer(1,5)])
def fmt(x,d=2):return f'{float(x):.{d}f}'.replace('.',',')
with (DATA/'resumen.csv').open() as f:rows=list(csv.DictReader(f))
R={(int(r['N']),int(r['P']),r['algorithm']):r for r in rows}
with (DATA/'perfil_resumen.csv').open() as f:profiles=list(csv.DictReader(f))
validation=json.loads((DATA/'validacion.json').read_text())
def ms(n,procs,alg):return fmt(float(R[n,procs,alg]['median_s'])*1000)

page('01','¿Cuál variante nos conviene paralelizar?')
p('Hasta ahora habíamos elegido right-looking por su organización natural de las actualizaciones, pero eso era una razón de diseño. Para responder con evidencia implementamos también left-looking con MPI y comparamos ambas variantes bajo las mismas condiciones.')
h('La dependencia que comparten')
p('En ambas variantes, la columna j solo puede finalizar cuando están disponibles las contribuciones que la afectan. Right-looking no elimina esa dependencia ni permite calcular arbitrariamente todas las columnas a la vez.')
h('Dónde aparece el trabajo paralelo')
table([['Variante','Antes de calcular j','Trabajo repartido después'],['Left-looking','Reúne desde las columnas 0,...,j-1 las contribuciones necesarias para j.','Con el pivote listo, calcula en paralelo distintos elementos Lij de la columna actual.'],['Right-looking','Las columnas anteriores ya aplicaron sus aportes sobre la matriz de trabajo.','Con j lista, actualiza en paralelo muchas posiciones de las columnas futuras.']],[105,195,197])
eq(r'l_{ij}=\frac{a_{ij}-\sum_{k<j}l_{ik}l_{jk}}{l_{jj}}\quad\mathrm{(left)}',15)
eq(r's_{ik}\leftarrow s_{ik}-l_{ij}l_{kj},\quad i\geq k>j\quad\mathrm{(right)}',15)
h('Una formulación precisa')
p('<b>Left-looking reúne el pasado para construir la columna actual. Right-looking propaga la columna actual hacia el futuro.</b> Ambos admiten paralelismo; right-looking expone un conjunto amplio de actualizaciones sobre la región restante. En versiones por tareas se puede priorizar la próxima columna y continuar otras actualizaciones como look-ahead.')
p('Nuestra versión right-looking es sincronizada por columnas: difunde j y cada proceso actualiza sus columnas propias antes de la etapa siguiente. Por eso esta comparación evalúa dos implementaciones concretas, no el máximo paralelismo teórico posible de cada familia.','small')

page('02','Cómo hicimos comparable el experimento')
h('La misma propiedad de datos')
p('Ambas variantes usan distribución cíclica estática. Cada proceso almacena sus columnas en memoria local contigua y recibe exactamente la misma matriz SPD. La distribución inicial y la reunión final son idénticas y quedan fuera del cronómetro del kernel.')
table([['Left-looking MPI','Right-looking MPI'],['Cada proceso calcula sumas parciales con sus columnas anteriores.','El propietario calcula la columna j.'],['MPI_Reduce reúne el pivote y los elementos inferiores en el propietario de j.','MPI_Bcast difunde el tramo terminado de j.'],['El propietario guarda la nueva columna; se difunde el pivote.','Cada proceso actualiza sus columnas futuras con vector local contiguo.']],[249,248])
h('Diferencia de coordinación')
p('Por columna, left usa una reducción escalar, una reducción vectorial -salvo en la última columna- y una difusión escalar: hasta 3n-1 colectivas. Right usa una difusión vectorial por columna: n colectivas. Los volúmenes exactos dependen de la implementación de MPI, pero left introduce más puntos de coordinación.')
h('Protocolo')
table([['Decisión','Valor'],['Tamaños y procesos','n=64,128,256,512,1024; P=1,2,3,4.'],['Repeticiones','Un calentamiento y ocho mediciones por algoritmo y configuración. Orden left/right alternado.'],['Entorno','WSL2, AMD Ryzen 5 2600, Open MPI 5.0.10, GCC 15.2.0, -O3, double, sin BLAS.'],['Tiempo','Máximo de las duraciones locales tras una barrera. Incluye cálculo y colectivas; excluye Scatterv, Gatherv y validación.'],['Correctitud','Residuo relativo <=10^-12 y comparación con el factor right secuencial.']],[114,383])
p('También ejecutamos un perfil separado para n=1024 y P=3. Sus cronómetros internos alteran el tiempo total; se usan para interpretar componentes, no para sustituir las medianas principales.','small')

page('03','Resultado: right fue más rápido en todos los casos')
fig('tiempos.png',497,321)
p('Figura 1. Medianas de ocho repeticiones; barras Q1-Q3. Se usa una escala propia por panel.','small')
tr=[['n','P','Left (ms)','Right (ms)','Left / Right']]
for n in [64,128,256,512,1024]:
    best=min(range(1,5),key=lambda q:float(R[n,q,'right']['median_s']))
    tr.append([str(n),str(best),ms(n,best,'left'),ms(n,best,'right'),fmt(float(R[n,best,'left']['median_s'])/float(R[n,best,'right']['median_s']))])
table(tr,[42,38,112,112,104])
p('La tabla usa, para cada n, el P que minimizó la mediana de right. No selecciona P por separado para favorecer a left. En las 20 configuraciones completas, right tuvo menor mediana.')
h('Caso principal: n=1024')
p('Con tres procesos, left tardó '+ms(1024,3,'left')+' ms y right '+ms(1024,3,'right')+' ms: left fue '+fmt(float(R[1024,3,'left']['median_s'])/float(R[1024,3,'right']['median_s']))+' veces más lento. Respecto de su propio P=1, left alcanzó '+fmt(R[1024,3,'left']['speedup'])+'x y right '+fmt(R[1024,3,'right']['speedup'])+'x. Ambos mejoraron al paralelizar y ambos empeoraron al pasar de tres a cuatro procesos.')

page('04','Por qué right ganó en nuestra implementación')
fig('perfil.png',497,205)
p('Figura 2. Perfil separado de n=1024, P=3, cuatro repeticiones por algoritmo. Se apilan medianas de componentes; su suma no tiene por qué coincidir exactamente con la mediana del total. Las colectivas incluyen espera.','small')
h('La comunicación de left es más fragmentada')
p('Left necesita reunir sumas parciales en cada columna. Aunque reparte bien los productos locales, paga reducciones vectoriales y escalares además de difundir cada pivote. Right difunde la columna terminada una vez y realiza actualizaciones locales sobre los datos que cada proceso posee.')
p('En el perfil, los tres rangos de left acumulan aproximadamente entre 10,80 y 14,29 ms dentro de MPI_Reduce, además de sus difusiones. Right no usa reducciones en el kernel. Esta observación explica parte de la diferencia, pero el tiempo dentro de una colectiva mezcla transferencia y espera.')
h('No es una prueba universal')
p('La conclusión válida es: <b>para nuestra implementación escalar, almacenamiento por filas, distribución cíclica, Open MPI local y tamaños probados, conviene continuar paralelizando right-looking con vector local.</b> No demostramos que toda implementación right sea superior a toda left.')
p('Una versión left por bloques, con BLAS, menos reducciones o comunicación no bloqueante podría cambiar el resultado. Una versión right con look-ahead también podría mejorar. Esas comparaciones requieren otra etapa y no deben darse por realizadas.')
h('Validación')
p('Se aceptaron '+str(validation['observations'])+' tiempos del experimento y '+str(validation['profile_rank_observations'])+' registros de perfil. El residuo máximo fue 1,2131×10^-15. La máxima diferencia relativa elemento a elemento frente al factor secuencial fue 2,6578×10^-15. Las pruebas con P=1,2,3,4 y los sanitizadores con P=4 finalizaron correctamente.')

page('05','Decisión y explicación para la consulta')
h('Qué elegimos')
p('Continuamos con right-looking MPI cíclico y vector local. La elección tiene ahora dos fundamentos: su estructura permite repartir las actualizaciones futuras entre propietarios de columnas, y la comparación directa mostró menor tiempo que el left-looking MPI implementado con el mismo reparto.')
h('Cómo explicarlo oralmente')
p('“Left-looking también puede paralelizarse: cada proceso forma contribuciones con las columnas anteriores y estas se combinan para calcular la columna actual. Right-looking calcula una columna y reparte las actualizaciones de la matriz restante. Implementé ambas con la misma distribución cíclica. En mis pruebas, right fue más rápido en todas las configuraciones; con n=1024 y tres procesos tardó 31,48 ms frente a 54,08 ms de left. El perfil muestra que left necesita más colectivas de reducción. Por eso elijo right para continuar, aclarando que es una conclusión sobre estas implementaciones.”')
h('Qué sigue pendiente')
p('Todavía medimos el kernel de factorización. El siguiente paso práctico es incluir distribución inicial y reunión final para comprobar si la ventaja se mantiene en el tiempo completo. Luego corresponde repetir dentro de un nodo y entre nodos del clúster.')
table([['Archivo en desde_cero','Contenido'],['src/cholesky_left_mpi.c','Left-looking distribuido y perfil de reducciones.'],['src/compare_mpi_algorithms.c','Comparación controlada, reunión y validación.'],['scripts/comparar_left_right_mpi.sh','Campaña reproducible.'],['scripts/analizar_left_right_mpi.py','Estadísticas, validación y gráficos.'],['resultados/left_right_mpi_20260922/','CSV, protocolo, perfil, huellas y fuentes.']],[222,275])

def footer(c,doc):
    w,height=A4;c.setStrokeColor(HexColor('#CFDDE3'));c.line(48,height-36,w-48,height-36)
    c.setFont('Body',8);c.setFillColor(HexColor('#536675'))
    c.drawString(48,28,'HPC · Cholesky | MPI en C · Estadísticas en Python | 22/09/2026')
    c.drawRightString(w-48,28,str(doc.page))
OUT.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=49,bottomMargin=48,title='Cholesky, etapa 5: left-looking vs right-looking MPI',author='Proyecto Cholesky HPC 2026').build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
