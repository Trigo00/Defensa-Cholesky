"""Etapa 9: reparto bloque-ciclico; no Cholesky por bloques."""
from pathlib import Path
import csv,json,sys,io
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from matplotlib.mathtext import math_to_image
from svglib.svglib import svg2rlg
D=ROOT/'desde_cero/resultados/bloques_local_20260922'
OUT=ROOT/'output/pdf/Cholesky_Etapa_9_Distribucion_bloque_ciclica.pdf'
with (D/'resumen.csv').open() as f:rows=list(csv.DictReader(f))
R={(int(r['N']),int(r['P']),int(r['block'])):r for r in rows};BS=(1,2,4,8,16,32,64)
V=json.loads((D/'validacion.json').read_text());styles=getSampleStyleSheet();styles['BodyText'].leading=14;story=[]
def p(t):story.extend([Paragraph(t,styles['BodyText']),Spacer(1,8)])
def h(t):story.append(Paragraph(t,styles['Heading2']))
def page(t):
    if story:story.append(PageBreak())
    story.extend([Paragraph(t,styles['Title']),Spacer(1,10)])
def eq(t):
    b=io.BytesIO();math_to_image('$'+t+'$',b,format='svg');b.seek(0);d=svg2rlg(b);d.hAlign='CENTER';story.extend([d,Spacer(1,10)])
page('Etapa 9: ¿agrupar columnas ayuda?')
p('La etapa anterior mostró que la factorización concentra gran parte del tiempo. Estudiamos ahora si cambiar la propiedad de las columnas mejora el flujo completo. Se mantiene right-looking escalar: cada columna se termina y difunde antes de continuar.')
h('Hipótesis')
p('Un bloque de b columnas consecutivas se asigna por turnos a cada proceso. Agrupar columnas puede modificar la localidad y las esperas, pero también el reparto del trabajo. Como las columnas locales ya estaban empaquetadas por filas, b mayor no garantiza mejor acceso a memoria.')
eq(r'\operatorname{propietario}(j)=\lfloor j/b\rfloor\;\mathrm{mod}\; P')
p('Con P=3 y b=2: proceso 0 recibe 0,1,6,7; proceso 1 recibe 2,3,8,9; proceso 2 recibe 4,5,10,11. b=1 reproduce los propietarios de la distribución cíclica previa.')
h('Qué cambia y qué se conserva')
p('Cambia el mapa global/local y la cantidad de columnas de cada proceso. Se conserva la matriz generada, el kernel de actualización con vector local, n difusiones por factorización y L reunida en rango 0. Todas las variantes usan el mismo código general de índices, incluido b=1. No comparamos contra cifras de campañas anteriores.')
p('Esto es distribución por bloques de columnas. No es Cholesky por bloques con operaciones matriz-matriz ni agrupa las comunicaciones: sigue habiendo una difusión por columna.')
h('Protocolo y reloj')
p('n=512,1024,2048; P=1,3,6; b=1,2,4,8,16,32,64. Un calentamiento por variante y siete repeticiones. El orden rota para que cada bloque ocupe cada posición una vez; no balancea todas las parejas de vecinos. Se rota P entre tamaños. Total: 441 observaciones en una sesión local WSL, afinidad por núcleo, GCC -O3, semilla 2026.')
p('Total principal: reloj de rango 0 desde reserva y preparación del reparto hasta generación distribuida, factorización y recolección completa. Excluye lanzamiento/cierre MPI, referencias, validación y liberación. Las fases incluyen esperas. Se compara la mediana de totales medidos directamente.')
h('Control con un proceso')
p('Con P=1, las columnas y operaciones son iguales para todos los tamaños de bloque. Diferencias grandes en ese control requieren cautela: no pueden atribuirse a balance entre procesos. El mapa general introduce aritmética distinta de las versiones históricas.')
page('Tiempo hasta obtener el resultado')
story.append(Image(str(D/'total.png'),width=485,height=388))
p('Puntos: medianas; barras: Q1-Q3, no intervalos de confianza. Cada panel tiene su propia escala vertical. Comparamos bloques dentro de cada configuración.')
h('Interpretación')
p('El total contempla los cambios de generación y desempaquetado provocados por el reparto, además del kernel. Una menor mediana aislada es un candidato para repetir, no una demostración de superioridad universal. Elegir el mínimo entre siete alternativas puede favorecer fluctuaciones de esta sesión.')
h('Reproducibilidad')
p('Campaña: resultados/bloques_local_20260922. Implementación: src/compare_blocks.c y mapas de src/cholesky_mpi.c. Ejecución: scripts/comparar_bloques.sh; análisis: scripts/analizar_bloques.py. Código, entorno y fuentes congeladas acompañan los resultados. Desarrollo y texto con asistencia de IA; datos obtenidos ejecutando el código localmente.')
page('Factorización y reparto del trabajo')
story.append(Image(str(D/'factor.png'),width=485,height=388))
p('Factorización observada por rango 0: incluye sus esperas de comunicación. No es una medición separada de cómputo puro ni del máximo de cada proceso.')
eq(r'W_r=\sum_{k\in C_r}k(n-k),\qquad I=\frac{\max_r W_r}{\sum_r W_r/P}')
p('Cada columna k recibe k actualizaciones sobre n-k elementos. I=1 indica igualdad en este conteo acumulado; no garantiza balance en cada etapa, ni incluye pivotes, indexación o comunicaciones.')
balance=', '.join(f'b={b}: {float(R[2048,6,b]["work_imbalance"]):.4f}' for b in BS)
p('n=2048, P=6: '+balance+'.')
page('Decisión provisional y siguiente pregunta')
table=[['n','P','Mejor b observado','b=1 (ms)','Mejor (ms)','Cociente']]
for n in (512,1024,2048):
 for proc in (3,6):
    best=min((R[n,proc,b] for b in BS),key=lambda r:float(r['total_median_s']))
    base=float(R[n,proc,1]['total_median_s']);v=float(best['total_median_s'])
    table.append([str(n),str(proc),best['block'],f'{base*1000:.2f}',f'{v*1000:.2f}',f'{base/v:.3f}x'])
t=Table(table,colWidths=[45,30,140,85,90,80]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecf0')),('BOTTOMPADDING',(0,0),(-1,-1),8)]));story.extend([t,Spacer(1,12)])
p('Estos mínimos son descriptivos y fueron elegidos después de medir. Seleccionamos b=4 para una repetición con P=6, manteniendo b=1 como referencia. No se selecciona un tamaño universal.')
h('Repetición del candidato')
confirmation=json.loads((D/'confirmacion.json').read_text())
for c in confirmation:
    p(f'n={c["N"]}, P=6: b=1 tarda {c["baseline_ms"]:.2f} ms y b=4 tarda {c["block4_ms"]:.2f} ms; cociente {c["ratio"]:.3f}x. Son nuevas ejecuciones, con siete repeticiones por bloque, en la misma sesión local.')
p('Esta repetición añade 98 observaciones. Para n=1024 se mantiene una reducción cercana al 10 % con b=4; para n=2048 la diferencia cae a aproximadamente 0,2 %, insuficiente para sostener una ventaja práctica estable. Conservamos b=1 como referencia y b=4 como candidato para n=1024, P=6. No adoptamos b=4 universalmente.')
h('Validación')
p(f'Se aceptaron {V["observations"]} observaciones. Máximo residuo proyectado: {V["max_projected"]:.3e}; máxima diferencia respecto del factor secuencial: {V["max_difference"]:.3e}. Se comprueban propietarios, cantidad de columnas, prefijos e índices; b=1 se compara con el mapa cíclico original. Casos pequeños: n=1,2,3,7,31,65 con P=1,3,6, incluyendo bloques incompletos y procesos vacíos.')
p('Las matrices grandes se contrastan elemento a elemento con el factor secuencial y con ocho proyecciones. Los casos pequeños también usan residuo Frobenius completo. El análisis Python verifica el conteo de trabajo mediante una enumeración independiente. El residuo proyectado por sí solo no es un certificado.')
h('Próxima pregunta')
p('¿La ventaja se mantiene en otras sesiones y matrices? Si la distribución aporta poco, corresponde investigar reutilización de datos dentro del cálculo, mediante una referencia LAPACK y, según el alcance, Cholesky por bloques. El reparto por bloques no sustituye esa optimización.')
def footer(c,d):c.setFont('Helvetica',9);c.drawString(48,28,'Cholesky paralelo | Etapa 9 | Reparto bloque-cíclico');c.drawRightString(547,28,str(d.page))
SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=42,bottomMargin=46).build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
