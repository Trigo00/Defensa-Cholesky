"""Etapa 4: cruce observado entre secuencial y MPI."""
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

DATA=ROOT/'desde_cero/resultados/umbral_20260922'
OUT=ROOT/'output/pdf/Cholesky_Etapa_4_Cuando_conviene_MPI.pdf'
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
    p('CHOLESKY / ETAPA 4 / EXPERIMENTO 5 / '+number,'small');p(title,'title')
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
with (DATA/'umbral.csv').open() as f:focus=list(csv.DictReader(f))
with (DATA/'rondas.csv').open() as f:records=list(csv.DictReader(f))
F={(int(r['N']),int(r['P'])):r for r in focus}
R={(int(r['round']),int(r['N']),int(r['P']),r['distribution'],r['kernel']):r for r in records}
checks=json.loads((DATA/'conclusiones.json').read_text())
def span(n,p):
    r=F[n,p];return fmt(r['minimum_speedup'])+' - '+fmt(r['maximum_speedup'])

page('01','¿Cuándo empieza a compensar MPI?')
p('Después de mejorar el cíclico con un vector local, observamos que MPI podía ganar con matrices grandes y perder con pequeñas. Faltaba precisar la transición. Este experimento conserva el código C del anterior y cambia únicamente el plan de medición.')
h('La pregunta concreta')
p('Entre n=64 y n=256, ¿qué tamaños permiten al cíclico con vector superar al mejor secuencial de manera consistente con dos o tres procesos? Incluimos P=1 como control y conservamos las otras variantes MPI en los datos, sin usarlas para seleccionar el resultado que más nos favorezca.')
h('Protocolo fijado antes de medir')
table([['Decisión','Ejecución'],['Tamaños','64, 96, 128, 160, 192, 224 y 256.'],['Rondas','Tres rondas con lanzamientos separados en la misma sesión. Orden de tamaños ascendente, descendente y rotado; orden de P también rotado.'],['Repeticiones','Ocho tiempos por variante MPI y configuración, tras calentamiento. Doce tiempos por variante secuencial: seis antes y seis después.'],['Entradas','Mismo generador SPD en C, misma semilla 2026 y mismo n para todas las variantes.'],['Entorno','WSL2, AMD Ryzen 5 2600, GCC 15.2.0 y Open MPI 5.0.10. -O3; un proceso por núcleo distinto según WSL.']],[112,385])
h('Criterio conservador de mejora')
eq(r'S_r=\frac{\min_v\widetilde T_{v,\mathrm{seq},r}}{\widetilde T_{\mathrm{MPI},r}}')
eq(r'S_r>1.10\quad\mathrm{y}\quad Q_{3,\mathrm{MPI},r}<Q_{1,\mathrm{seq},r},\qquad r=1,2,3',14)
p('Exigimos aceleración superior a 1,10 y separación entre los cuartiles centrales en las tres rondas. Los cuartiles secuenciales corresponden a la variante con menor mediana en esa ronda. El margen del 10 % es una decisión práctica explícita, no una constante de Cholesky.')
p('Esta regla es descriptiva: Q1-Q3 no es un intervalo de confianza y su separación no demuestra significación estadística. Las tres rondas comparten equipo y sesión; no representan días, máquinas o condiciones independientes.','small')

page('02','La transición observada entre 64 y 256')
tr=[['n','S con P=2','Criterio','S con P=3','Criterio']]
for n in [64,96,128,160,192,224,256]:tr.append([str(n),span(n,2),F[n,2]['passes']+'/3',span(n,3),F[n,3]['passes']+'/3'])
table(tr,[42,143,84,143,85])
p('Cada intervalo muestra el mínimo y máximo de las tres aceleraciones calculadas por ronda. No es un intervalo de confianza. “Criterio” cuenta las rondas que cumplen simultáneamente ambas condiciones.','small')
fig('cruce.png',497,236)
p('Figura 1. Aceleración del cíclico con vector frente al mejor secuencial contemporáneo. Por encima de 1 gana MPI; por encima de 1,10 supera el margen elegido, aunque todavía debe cumplir la condición de cuartiles.','small')
h('Qué muestran las repeticiones')
p('<b>n≤192:</b> MPI con dos y tres procesos tuvo mayor mediana que el secuencial en las tres rondas.<br/><b>n=224:</b> tres procesos ganaron apenas en una ronda y perdieron en las otras dos.<br/><b>n=256:</b> ambos valores de P ganaron por mediana en las tres rondas; solo P=3 cumplió también el criterio completo en las tres.')
p('Por tanto, n=256 con P=3 es el <b>primer punto de la grilla probada</b> que satisface nuestra regla. No medimos un umbral exacto y no demostramos que todo n mayor que 256 tenga el mismo comportamiento.','small')

page('03','Por qué dos y tres procesos no reciben la misma conclusión')
tr=[['Ronda','Secuencial (ms)','MPI P=2 (ms)','MPI P=3 (ms)']]
for c in [1,2,3]:
    a=R[c,256,2,'cyclic','local'];b=R[c,256,3,'cyclic','local']
    tr.append([str(c),fmt(float(a['base_s'])*1000,3),fmt(float(a['median_s'])*1000,3),fmt(float(b['median_s'])*1000,3)])
table(tr,[67,145,143,142])
p('Medianas para n=256. Right con vector fue la referencia secuencial elegida en estas tres comparaciones. No se mezclan rondas para calcular una aceleración única.','small')
h('Una mediana favorable puede convivir con dispersión')
a=R[1,256,2,'cyclic','local']
p('En la primera ronda, dos procesos tienen aceleración '+fmt(a['speedup'])+', superior a 1,10. Sin embargo, su Q3 es '+fmt(float(a['q3_s'])*1000,3)+' ms y el Q1 secuencial es '+fmt(float(a['base_q1_s'])*1000,3)+' ms. Los intervalos centrales se superponen y la configuración no pasa nuestra segunda condición.')
p('Con tres procesos, las tres rondas cumplen ambas condiciones. Sus aceleraciones son '+', '.join(fmt(R[c,256,3,'cyclic','local']['speedup']) for c in [1,2,3])+'. Eso respalda una mejora consistente dentro de esta sesión, pero no demuestra que tres procesos siempre sean mejores que dos: en la segunda ronda, P=2 tuvo menor mediana que P=3.')
h('Qué podemos decir sobre el cruce')
p('Hay un cambio de comportamiento entre los puntos probados n=224 y n=256. Es una zona candidata para investigar, no un intervalo matemáticamente garantizado del umbral. Tamaños, caché, compilador y carga del sistema pueden generar un comportamiento no monótono.')
p('Tampoco convertimos el dato en una regla automática “si n≥256, usar tres procesos”. Eso requeriría probar otros tamaños, repetir en otras sesiones y definir qué costo de ejecución queremos minimizar.')
h('Seguimos midiendo solo la factorización')
p('El tiempo incluye cálculo, copia del vector local, comunicación de columnas y esperas dentro de MPI. Excluye iniciar MPI, generar la matriz, distribuirla al principio, reunir el factor y validarlo. El cruce de una aplicación completa puede ser distinto al del kernel medido aquí.')

page('04','Resultado de esta etapa y siguiente problema')
h('Decisión provisional')
p('Para los tamaños ensayados hasta n=224, no tenemos evidencia consistente para elegir el cíclico MPI sobre el secuencial en este equipo. En n=256, tres procesos sí superan la regla prefijada. Conservamos ambos caminos; aún no introducimos selección automática ni trasladamos esta decisión al clúster.')
h('Validación de los datos')
p('Se verificaron '+str(checks['mpi_observations'])+' tiempos MPI y '+str(checks['sequential_observations'])+' tiempos secuenciales. Todas las observaciones cumplieron el límite de residuo relativo 10⁻¹². El máximo observado fue 5,7136×10⁻¹⁶; la diferencia máxima del factor MPI frente a right secuencial fue cero en estos casos.')
p('El análisis comprueba configuraciones, semilla, cantidad de repeticiones, orden equilibrado, tiempos finitos y resultados numéricos. Las huellas SHA-256 coinciden con las fuentes usadas. No se modificó el algoritmo: se reutilizaron los ejecutables y pruebas de la etapa anterior, y se validó cada nueva factorización fuera del cronómetro.')
h('¿Y si contamos también repartir y reunir la matriz?')
p('Ese es el próximo experimento útil: medir por separado la distribución inicial, la factorización y la reunión, además del total de esas fases. Con esa información podremos decidir si la aceleración del kernel se conserva cuando el programa debe entregar un resultado completo.')
p('El lanzamiento de procesos puede medirse aparte para aplicaciones que los crean por cada problema. En un programa que mantiene procesos MPI activos, ese costo no se paga en cada factorización. Debemos explicitar el caso de uso antes de elegir qué tiempo define la conveniencia.')
p('Después podremos repetir las mediciones en el clúster, primero dentro de un nodo y luego entre nodos. La comunicación local de WSL no estima el costo de su red. No hace falta añadir todavía bloques o planificación dinámica para responder estas preguntas.')
h('Cómo reproducirlo')
table([['Archivo en desde_cero','Uso'],['scripts/medir_umbral.sh','Ejecuta las tres rondas y registra el protocolo previo.'],['scripts/analizar_umbral.py','Valida datos y evalúa el mismo criterio en cada punto.'],['docs/generar_informe_umbral.py','Genera este capítulo desde la campaña registrada.'],['resultados/umbral_20260922/','CSV por ronda, resúmenes, gráfico, protocolo y fuentes.']],[227,270])
p('La fecha del experimento es 22/09/2026. Las etapas previas conservan sus resultados históricos; las conclusiones de esta etapa se basan solo en las nuevas rondas.','small')

def footer(c,doc):
    w,height=A4;c.setStrokeColor(HexColor('#CFDDE3'));c.line(48,height-36,w-48,height-36)
    c.setFont('Body',8);c.setFillColor(HexColor('#536675'))
    c.drawString(48,28,'HPC · Cholesky | MPI en C · Estadísticas en Python | 22/09/2026')
    c.drawRightString(w-48,28,str(doc.page))
OUT.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=49,bottomMargin=48,title='Cholesky, etapa 4: cuando conviene MPI',author='Proyecto Cholesky HPC 2026').build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
