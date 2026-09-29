"""Etapa 7: primer experimento de generacion distribuida."""
from pathlib import Path
import sys, csv, io
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from matplotlib.mathtext import math_to_image
from svglib.svglib import svg2rlg
D=ROOT/'desde_cero/resultados/generacion_local_20260922'
OUT=ROOT/'output/pdf/Cholesky_Etapa_7_Generacion_distribuida.pdf'
styles=getSampleStyleSheet();styles['BodyText'].leading=15
story=[]
def p(t): story.extend([Paragraph(t,styles['BodyText']),Spacer(1,9)])
def h(t): story.append(Paragraph(t,styles['Heading2']))
def title(t):story.extend([Paragraph(t,styles['Title']),Spacer(1,12)])
def eq(t):
    b=io.BytesIO();math_to_image('$'+t+'$',b,format='svg');b.seek(0)
    d=svg2rlg(b);d.hAlign='CENTER';story.extend([d,Spacer(1,12)])
title('Etapa 7: ¿quién genera la matriz?')
p('Primera etapa posterior a la consulta docente. Algoritmos y MPI en C; análisis y gráficos en Python. Esta campaña estudia la preparación de la entrada, no mide todavía toda la aplicación.')
h('Pregunta e hipótesis')
p('¿Podemos evitar que el proceso 0 genere y distribuya toda la matriz? Si cada proceso calcula sus columnas directamente, eliminamos el empaquetado central y Scatterv. A cambio, se recalculan los valores simétricos y aparecen accesos por columnas; la mejora debe medirse.')
h('Implementación: exactamente la misma matriz')
p('El generador original visita las parejas i&lt;j en orden. Identificamos la posición de cada pareja en esa secuencia y recuperamos el estado del generador entero sin recorrer los valores anteriores. La suma diagonal conserva el mismo orden que antes. Por ello, el resultado se puede comprobar bit a bit.')
eq(r'q(i,j)=i(2n-i-1)/2+(j-i-1),\quad i<j')
eq(r'a_{ii}=1+\sum_{j\ne i}|a_{ij}|')
p('La simetría y la dominancia diagonal estricta con diagonal positiva aseguran que la matriz sea definida positiva. Cada proceso guarda sus columnas cíclicas en el formato que ya utiliza nuestro Cholesky MPI.')
h('Protocolo')
p('WSL, Ryzen 5 2600; 6 núcleos físicos. Tamaños 512, 1024 y 2048; P=1 a 6; semilla 2026; un calentamiento y 6 repeticiones alternadas por método. Total: 216 observaciones. Centralizado: generación en rango 0, empaquetado y Scatterv. Distribuido: generación directa local. Ambos terminan con idéntica matriz distribuida.')
p('El cronómetro excluye reserva, arranque MPI, factorización y validación. Se toma el máximo del tiempo total entre procesos. Las fases no están sincronizadas: sus máximos incluyen esperas distintas y no deben sumarse para reconstruir el total.')
story.append(PageBreak());title('Resultados y decisión provisional')
story.append(Image(str(D/'generacion.png'),width=490,height=152))
p('Puntos: medianas. Barras: Q1-Q3; no son intervalos de confianza. Una campaña local con seis repeticiones por configuración.')
with (D/'resumen.csv').open() as f: rows=list(csv.DictReader(f))
lookup={(int(r['N']),int(r['P']),r['method']):float(r['median_s']) for r in rows}
table=[['n','P','Central (ms)','Distrib. (ms)','Cociente']]
for n in (512,1024,2048):
    for proc in (1,6):
        a=lookup[n,proc,'centralized'];b=lookup[n,proc,'distributed']
        table.append([str(n),str(proc),f'{a*1000:.3f}',f'{b*1000:.3f}',f'{a/b:.2f}x'])
t=Table(table,colWidths=[65,45,115,115,90]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecf0')),('BOTTOMPADDING',(0,0),(-1,-1),8)]));story.extend([t,Spacer(1,12)])
a=lookup[2048,6,'centralized'];b=lookup[2048,6,'distributed']
p(f'Para n=2048 y P=6, el cociente entre medianas de preparación es {a/b:.2f}. Este cociente compara dos métodos con el mismo P; no es el speedup de Cholesky ni el de la aplicación completa.')
h('Comprobaciones y límites')
p('Todas las repeticiones reprodujeron exactamente la matriz original. Se probaron también n=1,2,3,7,31 con seis procesos, incluidos procesos sin columnas. Las pruebas C y sanitizadores de las funciones nuevas pasaron. Falta repetir en sesiones independientes y medir el impacto junto con la factorización.')
p('La reserva del banco contiene matrices adicionales para verificar igualdad; no representa la memoria mínima de una aplicación distribuida. Este experimento aún no integra el nuevo generador en el banco de tiempo completo.')
story.append(PageBreak());title('¿Y si comprobar tarda demasiado?')
p('Reconstruir todo LL transpuesta cuesta O(n³). Agregamos una comprobación complementaria con vectores de signos, reproducibles mediante una semilla separada. Para cada vector calculamos Ax y L(L transpuesta x), sin formar el producto matricial completo.')
eq(r'r_x=\frac{\|Ax-L(L^T x)\|_2}{\|Ax\|_2}')
p('Con k vectores, el costo es O(kn²) y la memoria auxiliar es O(n). Esta magnitud NO es el residuo de Frobenius. Un conjunto finito de vectores puede dejar errores sin detectar: no constituye un certificado determinista ni sustituye las pruebas exhaustivas.')
p('Las pruebas usan ocho vectores con semilla 91827, factores correctos y deliberadamente alterados, valores no finitos y elementos del triángulo superior que no pertenecen a L. También comprueban repetibilidad. El método está implementado como función independiente; los bancos históricos siguen usando el residuo completo.')
h('Siguiente pregunta')
p('¿La mejora al preparar la entrada reduce el tiempo que espera el usuario? El siguiente banco debe incluir reserva, generación, movimiento, factorización y salida; mantener un caso con resultado centralizado y otro distribuido; y registrar la validación por separado. Un tiempo externo adicional podrá incluir el arranque y cierre de MPI.')
h('Ruta local pendiente')
p('1. Integrar el flujo completo y validación escalable. 2. Matrices mayores y P=1 a 6. 3. Distribución bloque-cíclica. 4. Almacenamiento triangular. 5. Compilador y vectorización. 6. Referencia LAPACK. 7. Decidir, según evidencia y alcance defendible, algoritmo por bloques y MPI+OpenMP.')
h('Trazabilidad y uso de IA')
p('Fuentes: src/cholesky.c, src/compare_generation.c y tests/test_projected.c. Campaña: resultados/generacion_local_20260922, con CSV, protocolo, entorno, afinidad y copia de fuentes. Código y texto elaborados con asistencia de IA; resultados obtenidos mediante ejecución local. La defensa debe explicar las decisiones, las pruebas y sus límites.')
def footer(canvas,doc):
    canvas.setFont('Helvetica',9);canvas.drawString(48,28,'Cholesky paralelo | Etapa 7 | Estudio local');canvas.drawRightString(547,28,str(doc.page))
SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=42,bottomMargin=46).build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
