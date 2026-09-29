"""Genera el capítulo con ecuaciones vectoriales y resultados del CSV original."""
from pathlib import Path
import sys
import io
import csv

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tmp' / 'pdf_deps'))
import matplotlib
matplotlib.use('Agg')
from matplotlib.mathtext import math_to_image
from matplotlib.font_manager import FontProperties
from svglib.svglib import svg2rlg
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Flowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

OUT = ROOT / 'output' / 'pdf' / 'Cholesky_Etapa_1_Fundamentos_y_validacion.pdf'
OUT.parent.mkdir(parents=True, exist_ok=True)
for name, file in [('Body','calibri.ttf'), ('Bold','calibrib.ttf'), ('Italic','calibrii.ttf')]:
    pdfmetrics.registerFont(TTFont(name, 'C:/Windows/Fonts/' + file))
pdfmetrics.registerFontFamily('Body', normal='Body', bold='Bold', italic='Italic')
INK, BLUE, MUTED = HexColor('#172B3A'), HexColor('#126F85'), HexColor('#536675')
styles = {
    'title': ParagraphStyle('title', fontName='Bold', fontSize=25, leading=29, textColor=INK, spaceAfter=15),
    'h': ParagraphStyle('h', fontName='Bold', fontSize=14, leading=18, textColor=BLUE, spaceBefore=13, spaceAfter=7),
    'body': ParagraphStyle('body', fontName='Body', fontSize=11.2, leading=15.5, textColor=INK, spaceAfter=8),
    'small': ParagraphStyle('small', fontName='Body', fontSize=9, leading=12, textColor=MUTED, spaceAfter=6),
}
story = []
def p(text, style='body'):
    story.append(Paragraph(text, styles[style]))
def h(text): p(text, 'h')
def eq(text, size=17):
    stream = io.BytesIO()
    math_to_image('$' + text + '$', stream, prop=FontProperties(size=size), format='svg', color='#172B3A')
    stream.seek(0)
    drawing = svg2rlg(stream)
    drawing.hAlign = 'CENTER'
    story.extend([Spacer(1, 4), drawing, Spacer(1, 8)])
def newpage(k, title):
    if story: story.append(PageBreak())
    p('CHOLESKY / ETAPA 1 / ' + k, 'small')
    p(title, 'title')

class Matrices(Flowable):
    def __init__(self):
        super().__init__()
        self.width, self.height = 475, 92
    def draw(self):
        c = self.canv
        c.setFillColor(INK)
        for x, label, rows in [(27, 'A =', [[4,12,-16],[12,37,-43],[-16,-43,98]]),
                                (272, 'L =', [[2,0,0],[6,1,0],[-8,5,3]])]:
            c.setFont('Italic', 17); c.drawString(x-25, 41, label)
            left=x+22; right=left+130
            c.setStrokeColor(INK); c.setLineWidth(1)
            for side, direction in [(left,1),(right,-1)]:
                c.line(side, 12, side, 81)
                c.line(side, 81, side+direction*7, 81)
                c.line(side, 12, side+direction*7, 12)
            c.setFont('Body', 16)
            for i,row in enumerate(rows):
                for j,value in enumerate(row):
                    c.drawRightString(left+31+j*40, 62-i*22, str(value).replace('-', '−'))

newpage('01', 'Antes de acelerar,\n¿qué debemos calcular?')
p('Fundamentos, referencia secuencial y primeras mediciones', 'h')
p('Proyecto universitario de computación de alto rendimiento · 21 de septiembre de 2026', 'small')
p('El objetivo del proyecto es construir y evaluar una factorización de Cholesky paralela. Comenzamos por una versión secuencial cuyo resultado podamos verificar. Cada avance seguirá una pregunta, una hipótesis, una implementación y un experimento; los resultados decidirán la siguiente mejora.')
h('1. La pregunta inicial')
p('Dada una matriz real A, simétrica y definida positiva (SPD), buscamos una matriz triangular inferior L con diagonal positiva que cumpla:')
eq(r'A=LL^{T}')
p('Simétrica significa que A coincide con su transpuesta. Definida positiva significa que su forma cuadrática es positiva para cualquier vector real no nulo:')
eq(r'A=A^{T},\qquad x^{T}Ax>0\quad\mathrm{para}\ x\ne 0', 16)
p('La factorización sirve, por ejemplo, para resolver un sistema Ax = b: primero se resuelve Ly = b y después Lᵀx = y. En esta etapa implementamos solamente la factorización.')
h('2. Qué esperamos observar')
p('<b>Hipótesis:</b> si la matriz es SPD y respetamos las dependencias del algoritmo, el producto de L por su transpuesta reconstruirá A, salvo los errores de redondeo de la aritmética de punto flotante.')
p('En aritmética exacta, las condiciones SPD garantizan los pivotes positivos y la existencia de esta factorización. En una computadora verificaremos los pivotes y los resultados no finitos: una entrada mal condicionada puede presentar dificultades numéricas.')
h('3. Alcance de esta primera etapa')
p('Usamos Python como referencia didáctica porque permite relacionar directamente las ecuaciones con el código. No representa una implementación HPC optimizada. La referencia de rendimiento para MPI se construirá en C; no calcularemos speedup comparando Python con C.')

newpage('02', 'De las ecuaciones\na una columna de L')
p('Usamos índices desde 0, como en el programa. Al expandir el producto matricial, la triangularidad limita la suma:')
eq(r'a_{ij}=\sum_{k=0}^{\min(i,j)}l_{ik}l_{jk}')
h('4. Primero la diagonal; después, debajo de ella')
p('Para la columna j, los términos de las columnas anteriores ya son conocidos. Despejamos primero el elemento diagonal y luego cada elemento inferior:')
eq(r'l_{jj}=\sqrt{a_{jj}-\sum_{k=0}^{j-1}l_{jk}^{2}}', 19)
eq(r'l_{ij}=\frac{a_{ij}-\sum_{k=0}^{j-1}l_{ik}l_{jk}}{l_{jj}},\qquad i>j', 19)
p('Cuando j = 0, la suma vacía vale cero. Los elementos bajo la diagonal de una misma columna pueden calcularse de forma independiente una vez disponibles el pivote y las columnas anteriores. Esta observación será útil al estudiar paralelismo, aunque no determina por sí sola una estrategia eficiente.')
h('5. Un ejemplo que podemos resolver a mano')
story.append(Matrices())
eq(r'l_{00}=\sqrt{4}=2,\qquad l_{10}=12/2=6,\qquad l_{20}=-16/2=-8', 14)
eq(r'l_{11}=\sqrt{37-6^{2}}=1,\qquad l_{21}=\frac{-43-(-8)\cdot6}{1}=5', 16)
eq(r'l_{22}=\sqrt{98-(-8)^{2}-5^{2}}=3', 17)
p('El producto LLᵀ recupera la matriz A del ejemplo. El trabajo aritmético dominante de Cholesky denso es aproximadamente n³/3 operaciones de punto flotante; el almacenamiento denso crece como n². En Python también intervienen el intérprete y la representación de los objetos.', 'small')

newpage('03', 'Cómo comprobamos\nque el resultado es correcto')
h('6. Decisiones de implementación')
p('La función <b>cholesky()</b> conserva A y construye una L nueva, con ceros por encima de la diagonal. Esto facilita la comparación y evita factorizar una entrada modificada en la siguiente repetición. La referencia exige una matriz cuadrada, no vacía, finita y exactamente simétrica.')
p('En cada paso comprobamos que el pivote sea positivo y finito. También rechazamos resultados no finitos. Una ejecución que no supera estas comprobaciones no se acepta como medición válida.')
h('7. Generación reproducible de matrices SPD')
p('Generamos valores uniformes entre −1 y 1 fuera de la diagonal y los reflejamos para asegurar simetría. Luego fijamos:')
eq(r'a_{ii}=1+\sum_{j\ne i}|a_{ij}|')
p('La diagonal es positiva y estrictamente dominante. Por simetría, los autovalores son reales; los intervalos de Gershgorin quedan en el semieje positivo, por lo que la matriz es SPD. La semilla permite reproducir la entrada. Esta familia inicial no cubre todos los problemas ni matrices arbitrariamente mal condicionadas.')
h('8. Medida de reconstrucción')
eq(r'r=\frac{\|A-LL^{T}\|_{F}}{\|A\|_{F}},\qquad \|M\|_{F}=\sqrt{\sum_i\sum_j m_{ij}^{2}}', 17)
p('Usamos el residuo relativo para comparar el error con la magnitud de A. Para estas matrices pequeñas adoptamos r &lt; 10<super>−12</super> como criterio práctico. No es un umbral universal: un residuo pequeño tampoco asegura un error pequeño al resolver cualquier sistema mal condicionado.')
h('9. Pruebas realizadas')
p('<b>Resultado: cinco pruebas automatizadas aprobadas.</b> Comprueban el factor 3×3 conocido y que A se conserve; el caso escalar y la identidad; doce combinaciones generadas (tamaños 2, 7, 16 y 31 con semillas 0, 42 y 2026); entradas inválidas; y la detección de un factor deliberadamente incorrecto.')
p('Entre las entradas rechazadas están las matrices vacías, no cuadradas, asimétricas, indefinidas, semidefinidas sin positividad estricta y aquellas con NaN o infinito. El ejemplo conocido produjo exactamente el factor esperado.')

newpage('04', 'Qué medimos\ny qué podemos concluir')
h('10. Protocolo de medición')
p('Para cada tamaño n = 32, 64 y 128 usamos la semilla 2026, un calentamiento y siete repeticiones medidas sobre la misma entrada. El reloj monótono <b>perf_counter</b> mide la llamada completa a cholesky(): comprobaciones de entrada, reserva de L y factorización. Generación de A, validación y escritura de archivos quedan fuera del cronómetro.')
p('Reportamos mediana, primer y tercer cuartil (Q1 y Q3), y rango intercuartílico IQR = Q3 − Q1. Se usa el método de cuartiles inclusivo de Python. El IQR describe la dispersión observada; no es un intervalo de confianza. La validación entre repeticiones puede modificar la caché.')
h('11. Resultados locales observados')
p('Windows 11 · Python 3.12.14 · 21 de septiembre de 2026. Tiempos en milisegundos; siete observaciones por fila.', 'small')
source = ROOT / 'desde_cero/resultados/20260921T170357862059Z'
with (source / 'resumen.csv').open() as f: rows = list(csv.DictReader(f))
data = [['n', 'Mediana', 'Q1', 'Q3', 'IQR', 'Residuo máx.']]
for r in rows:
    data.append([r['N']] + [f'{float(r[k])*1000:.4f}' for k in ['median_s','q1_s','q3_s','iqr_s']] + [f'{float(r["max_residual"]):.2e}'])
t = Table(data, colWidths=[30,81,79,79,75,131-20], rowHeights=27)
t.setStyle(TableStyle([('FONTNAME',(0,0),(-1,0),'Bold'),('FONTNAME',(0,1),(-1,-1),'Body'),('FONTSIZE',(0,0),(-1,-1),10),('BACKGROUND',(0,0),(-1,0),BLUE),('TEXTCOLOR',(0,0),(-1,0),white),('TEXTCOLOR',(0,1),(-1,-1),INK),('ALIGN',(0,0),(-1,-1),'RIGHT'),('VALIGN',(0,0),(-1,-1),'MIDDLE'),('ROWBACKGROUNDS',(0,1),(-1,-1),[HexColor('#EDF4F6'),white]),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
story.extend([t, Spacer(1,10)])
p('Los residuos quedan muy por debajo del criterio establecido. Al duplicar n, las medianas aumentan aproximadamente 5,96 y 7,59 veces. Es compatible con la tendencia cúbica esperada, pero tres tamaños pequeños en Python no demuestran una ley de escalabilidad ni permiten predecir tiempos del clúster.')
h('12. Conclusión y siguiente pregunta')
p('La referencia reconstruye correctamente las matrices ensayadas y el protocolo conserva mediciones individuales y dispersión. Esto respalda los casos probados, no constituye una prueba exhaustiva de estabilidad. Todavía no hay una variante paralela comparable ni un speedup que reportar.')
p('<b>¿Qué pasaría si llevamos el mismo algoritmo a C y separamos los costos de reserva, generación, factorización y validación?</b> Esa pregunta abre la etapa 2. Después estudiaremos cómo agrupar operaciones por bloques y cuáles pueden ejecutarse simultáneamente.')
p('<b>Trazabilidad.</b> Código: desde_cero/cholesky.py; pruebas: test_cholesky.py; medición: benchmark.py. Datos: desde_cero/resultados/20260921T170357862059Z/ (mediciones.csv, resumen.csv y entorno.json). Esta edición utiliza los resultados existentes; no representa una nueva campaña de medición.', 'small')
p('<b>Referencia.</b> <link href="https://netlib.org/lapack/explore-html/d2/d09/group__potrf_ga84e90859b02139934b166e579dd211d4.html" color="#126F85">LAPACK: documentación de DPOTRF</link>. Describe la factorización SPD y una versión de producción por bloques con BLAS de nivel 3. Nuestra referencia es escalar.', 'small')

def chrome(c, doc):
    w,h=A4
    c.setStrokeColor(HexColor('#CFDDE3')); c.line(48,h-36,w-48,h-36)
    c.setFont('Body',8); c.setFillColor(MUTED)
    c.drawString(48,28,'HPC · Cholesky | Fundamentos y validación secuencial')
    c.drawRightString(w-48,28,str(doc.page))

doc=SimpleDocTemplate(str(OUT),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=49,bottomMargin=48,title='Cholesky - Etapa 1: fundamentos y validación',author='Proyecto Cholesky HPC 2026')
doc.build(story,onFirstPage=chrome,onLaterPages=chrome)
print(OUT)
