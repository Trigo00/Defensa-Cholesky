"""Informe progresivo del flujo con generacion incluida."""
from pathlib import Path
import sys,csv,json,io
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from matplotlib.mathtext import math_to_image
from svglib.svglib import svg2rlg
D=ROOT/'desde_cero/resultados/aplicacion_local_20260922'
OUT=ROOT/'output/pdf/Cholesky_Etapa_8_Flujo_con_generacion.pdf'
with (D/'resumen.csv').open() as f:rows=list(csv.DictReader(f))
R={(int(r['N']),int(r['P']),r['method']):r for r in rows}
V=json.loads((D/'validacion.json').read_text())
styles=getSampleStyleSheet();styles['BodyText'].leading=15;story=[]
def p(t):story.extend([Paragraph(t,styles['BodyText']),Spacer(1,8)])
def h(t):story.append(Paragraph(t,styles['Heading2']))
def title(t):story.extend([Paragraph(t,styles['Title']),Spacer(1,12)])
def eq(t):
    b=io.BytesIO();math_to_image('$'+t+'$',b,format='svg');b.seek(0);d=svg2rlg(b);d.hAlign='CENTER';story.extend([d,Spacer(1,10)])
def ms(n,proc,m):return float(R[n,proc,m]['total_median_s'])*1000
title('Etapa 8: ¿mejora el tiempo completo?')
p('La generación distribuida redujo el tiempo de preparar la entrada en la etapa anterior. Ahora preguntamos si esa mejora se mantiene al incluir la factorización y devolver el resultado al proceso 0.')
h('Una comparación con el mismo resultado')
p('Centralizada: rango 0 genera A, empaqueta y distribuye columnas. Distribuida: cada proceso genera directamente sus columnas de la misma A. Ambas ejecutan right-looking MPI cíclico con vector local y reúnen L completa en rango 0. La referencia secuencial genera A y aplica right-looking con vector en rango 0.')
h('Qué llamamos total en este experimento')
eq(r'T=T_{reserva}+T_{generacion}+T_{distribucion}+T_{factorizacion}+T_{recoleccion}')
p('Medimos directamente el intervalo desde el comienzo de las reservas hasta que L queda completa en rango 0, con MPI ya iniciado. Las fases se registran consecutivamente en ese mismo proceso y suman su total por ejecución. También guardamos el máximo de las duraciones locales como control.')
p('Quedan fuera el lanzamiento y cierre de MPI, las referencias de prueba, la validación, la liberación de memoria y escribir resultados. Es el flujo de procesamiento, no el tiempo externo del comando mpirun. Las reservas se repiten; malloc no toca todas las páginas, por lo que parte del costo de memoria se paga al acceder a ellas en las fases posteriores.')
h('Por qué usar medianas')
p('Calculamos la mediana de los totales observados. No sumamos medianas de fases para obtenerla. Para conocer el peso de una fase, dividimos su duración por el total de esa misma ejecución y luego calculamos la mediana de esas proporciones. Estas medianas tampoco tienen que sumar exactamente 100 %.')
h('Protocolo')
p('n=512,1024,2048; P=1,3,6; un calentamiento y seis repeticiones por método y configuración, usando las seis permutaciones de los tres métodos. Son 162 observaciones en una sesión WSL. Tamaños y P se recorren en orden creciente. Ryzen 5 2600, afinidad por núcleo, GCC -O3; semilla 2026. El secuencial corre dentro del lanzamiento MPI con los otros procesos esperando, condición que debe tenerse presente al interpretar su referencia.')
story.append(PageBreak());title('Resultados del flujo integrado')
story.append(Image(str(D/'total.png'),width=490,height=152));p('Medianas y barras Q1-Q3. No son intervalos de confianza.')
data=[['n','P','Central (ms)','Distrib. (ms)','Secuencial (ms)']]
for n in (512,1024,2048):
    for proc in (3,6):data.append([str(n),str(proc),f'{ms(n,proc,"centralized"):.2f}',f'{ms(n,proc,"distributed"):.2f}',f'{ms(n,proc,"sequential"):.2f}'])
t=Table(data,colWidths=[55,35,125,125,140]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecf0')),('BOTTOMPADDING',(0,0),(-1,-1),8)]));story.extend([t,Spacer(1,12)])
a=ms(2048,6,'centralized');b=ms(2048,6,'distributed');s=ms(2048,6,'sequential')
p(f'Para n=2048 y P=6: cambiar la preparación centralizada por distribuida da un cociente de {a/b:.2f}x y una reducción de {(1-b/a)*100:.1f} % del tiempo mediano. Respecto del secuencial medido en esa configuración, el método distribuido alcanza {s/b:.2f}x.')
h('Lo que esta comparación permite afirmar')
p('Comparamos resultados completos equivalentes y datos idénticos, sin combinar tiempos de campañas diferentes. La velocidad de la generación aislada no se traslada automáticamente al total: la factorización, la salida y las interacciones con memoria siguen costando tiempo.')
p('No atribuimos diferencias de factorización exclusivamente al algoritmo, que es el mismo en ambas variantes MPI. La generación cambia el estado de caché, el primer acceso a memoria y cuándo llega cada proceso al kernel. Los tiempos de fases incluyen las esperas resultantes.')
story.append(PageBreak());title('¿Dónde conviene trabajar ahora?')
story.append(Image(str(D/'fases.png'),width=480,height=210))
rr=R[2048,6,'distributed'];share=100*float(rr['factor_share_median']);gather=100*float(rr['gather_share_median'])
p(f'En el flujo distribuido de n=2048, P=6, la factorización representa una mediana del {share:.1f} % del tiempo observado y la recolección del {gather:.1f} %. Estas proporciones sirven para priorizar el próximo experimento local; no predicen el comportamiento de la red del clúster.')
h('Validación')
p(f'Se aceptaron {V["observations"]} observaciones. Máximo residuo proyectado: {V["max_projected"]:.3e}; máxima diferencia relativa por elemento respecto del factor secuencial: {V["max_difference"]:.3e}. Se comprobó el factor completo contra una referencia secuencial en cada repetición. El residuo Frobenius completo se usa en las pruebas pequeñas (hasta n=128).')
p('La comprobación proyectada usa ocho vectores de signos y semilla 91827, fuera del tiempo útil, y su duración se registra por separado. No es un certificado ni el residuo Frobenius. Las pruebas incluyen n=1,2,3,7,31,128 y procesos sin columnas.')
h('Próxima hipótesis y límites')
p('Si el cálculo concentra el tiempo, el próximo cambio debe estudiar la factorización y el reparto, empezando por bloques de columnas cíclicos. Una distribución bloque-cíclica modifica propietarios; un algoritmo Cholesky por bloques modifica las operaciones. Debemos mantener esa distinción y cambiar una decisión por experimento.')
p('Una sola sesión y seis repeticiones no establecen un ganador universal. Falta confirmar configuraciones elegidas en sesiones independientes, ampliar tamaños y medir lanzamiento externo si la aplicación crea procesos por cada matriz. El banco conserva matrices de referencia fuera del cronómetro: su consumo de memoria no es el mínimo del algoritmo.')
p('Fuentes: src/compare_application.c; scripts/comparar_aplicacion.sh; scripts/analizar_aplicacion.py. Evidencia: resultados/aplicacion_local_20260922. Implementación y documentación con asistencia de IA, comprobadas mediante ejecución local.')
def footer(c,d):c.setFont('Helvetica',9);c.drawString(48,28,'Cholesky paralelo | Etapa 8 | Flujo de procesamiento');c.drawRightString(547,28,str(d.page))
SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=42,bottomMargin=46).build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
