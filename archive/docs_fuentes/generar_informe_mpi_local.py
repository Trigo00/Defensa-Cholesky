"""Etapa 3: experimento del vector local MPI en C."""
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

DATA=ROOT/'desde_cero/resultados/mpi_local_20260921'
OUT=ROOT/'output/pdf/Cholesky_Etapa_3_MPI_vector_local.pdf'
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
    p('CHOLESKY / ETAPA 3 / EXPERIMENTO 4 / '+number,'small');p(title,'title')
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
with (DATA/'resumen.csv').open() as f:rows=list(csv.DictReader(f))
R={(int(r['N']),int(r['P']),r['distribution'],r['kernel']):r for r in rows}
validation=json.loads((DATA/'validacion.json').read_text())
def row(n,p,d,k='local'):return R[n,p,d,k]
def time(n,p,d,k='local'):return ms(row(n,p,d,k))
def ratio(n,p,d):return float(row(n,p,d)['original_over_local'])

page('01','¿Y si ambos repartos leyeran datos contiguos?')
p('En el experimento anterior, el cíclico equilibraba mejor el número de operaciones, pero tardaba más. Había una pista: incluso con un solo proceso, cuando ambos repartos poseen las mismas columnas, sus tiempos eran distintos. Antes de descartar el reparto cíclico, decidimos reducir el costo de acceso e indexación del cálculo local.')
h('Hipótesis')
p('Después de recibir la columna j, cada proceso copia los valores que necesita a un vector ordenado como sus columnas propias. Esperamos que reutilizar ese vector compense el costo de copiarlo, especialmente en el cíclico. La copia se incluye en el tiempo: no damos por hecho que sea beneficiosa.')
h('El cambio en C')
p('Sea g(c) la columna global correspondiente a la columna local c. En la versión original, el bucle interno consulta el vector difundido mediante ese índice global. En la nueva versión lo prepara una sola vez por etapa:')
eq(r'b_c=l_{g(c),j},\qquad g(c)>j')
eq(r'a^{\mathrm{local}}_{ic}\leftarrow a^{\mathrm{local}}_{ic}-l_{ij}b_c')
table([['Momento','Versión original','Con vector local'],['Antes de actualizar','Se usa la columna difundida.','local_column[c] = column[g(c)]'],['Dentro del bucle','lij * column[g(c)]','lij * local_column[c]']],[119,189,189])
p('Por ejemplo, con n=8 y P=3, el rango 1 cíclico posee las columnas globales 1, 4 y 7. En la etapa j=0 copia esos tres valores a posiciones locales consecutivas. Las filas que actualiza luego reutilizan esa copia.')
h('Cuánto cuesta y qué se conserva')
p('Cada proceso reserva tantos doubles adicionales como columnas propias: ocho bytes por columna local en este equipo. La memoria adicional máxima por proceso es:')
eq(r'M_{\mathrm{extra}}\leq 8\left\lceil\frac{n}{P}\right\rceil\ \mathrm{bytes}',15)
p('Durante toda la factorización se copian n(n−1)/2 valores entre todos los procesos. Es trabajo cuadrático adicional frente al cálculo cúbico de Cholesky; eso por sí solo no garantiza una mejora para tamaños pequeños.')
p('No cambian los propietarios, las dependencias, el orden de las operaciones aritméticas ni las llamadas a MPI_Bcast. El bucle interno accede ahora a datos consecutivos en ambos repartos. La asignación de índices fuera de ese bucle todavía difiere.','small')

page('02','Un experimento con cuatro variantes')
table([['Reparto','Lectura original','Vector local'],['Contiguo','Referencia anterior','Nueva variante'],['Cíclico','Referencia anterior','Nueva variante']],[119,189,189])
h('Cómo evitamos mezclar campañas')
p('Volvimos a medir las cuatro variantes en el mismo ejecutable y sobre las mismas matrices. Los cocientes de esta etapa usan únicamente tiempos nuevos; no dividimos tiempos actuales por los del PDF anterior. La generación y todas las factorizaciones están en C. Python valida los CSV y obtiene estadísticas y gráficos.')
table([['Configuración','Protocolo ejecutado'],['Entorno','WSL2 / Ubuntu 26.04, AMD Ryzen 5 2600, Open MPI 5.0.10, GCC 15.2.0; -O3, double, sin BLAS.'],['Tamaños y procesos','n=64,256,512,1024 y P=1,2,3,4. Un proceso por núcleo distinto según la topología expuesta por WSL.'],['Orden y repeticiones','Un calentamiento por variante; ocho repeticiones medidas. Cada variante ocupa cada posición dos veces. Se equilibran también las parejas consecutivas dentro de cada repetición.'],['Tiempo MPI','Máximo de las duraciones locales, con inicio coordinado por barrera. Incluye copia del vector, cálculo y difusión.'],['Fuera del cronómetro','Reserva de memoria, generación, distribución inicial, reunión, validación y arranque de MPI.'],['Referencia secuencial','Left, right original y right con vector: seis ejecuciones antes y seis después de MPI para cada n.']],[120,377])
h('Qué reportamos')
eq(r'G_{\mathrm{copia}}=\frac{\widetilde T_{\mathrm{original}}}{\widetilde T_{\mathrm{local}}},\qquad S_{\mathrm{util}}=\frac{\widetilde T_{\mathrm{mejor\ secuencial}}}{\widetilde T_{\mathrm{MPI}}}',15)
p('Un cociente mayor que 1 indica una mejora. Usamos medianas y cuartiles inclusivos Q1-Q3. Las barras de dispersión no son intervalos de confianza; ocho repeticiones en una campaña no sustituyen repeticiones independientes en otros momentos.')
p('Se conservaron 512 tiempos MPI, 144 tiempos secuenciales y un perfil separado de 48 registros por rango (n=1024, P=3, cuatro variantes y cuatro repeticiones). El perfil incorpora cronómetros internos y no se usa para calcular la aceleración principal.','small')

page('03','Resultado: la copia ayuda sobre todo al cíclico')
fig('tiempos.png',497,373)
p('Figura 1. Medianas de ocho repeticiones; barras Q1-Q3. Líneas discontinuas: acceso original. Líneas continuas: vector local. La referencia secuencial es la mejor mediana de las tres variantes secuenciales de esta campaña. Cada panel tiene su propia escala.','small')
h('La hipótesis se cumple con límites')
p('<b>n=64:</b> todos los casos con P&gt;1 son más lentos que el mejor secuencial; agregar una copia no resuelve la falta de trabajo útil.<br/><b>n≥256:</b> el cíclico con vector tiene menor mediana que el cíclico original en todos los P probados.<br/><b>Contiguo:</b> copiar no aporta una mejora sistemática; su lectura original ya era consecutiva y en varios casos la copia agrega costo.')
p('Entre las nuevas variantes, el cíclico presenta menor mediana que el contiguo para P=2,3,4 y n≥256. Sin embargo, varias distribuciones de tiempos se superponen: esto respalda una elección provisional, no una superioridad universal ni una prueba de significación estadística.')

page('04','El caso n=1024, explicado con números')
tr=[['P','Contiguo original','Contiguo + vector','Cíclico original','Cíclico + vector']]
for proc in [1,2,3,4]:tr.append([str(proc),time(1024,proc,'contiguous','original'),time(1024,proc,'contiguous'),time(1024,proc,'cyclic','original'),time(1024,proc,'cyclic')])
table(tr,[30,117,117,116,117])
p('Todos los tiempos están en milisegundos. Mediana del mejor secuencial: '+fmt(float(row(1024,3,'cyclic')['base_s'])*1000)+' ms, correspondiente a right con vector.','small')
h('¿Se amortizó la copia?')
p('Con P=3, el cíclico pasa de '+time(1024,3,'cyclic','original')+' ms a '+time(1024,3,'cyclic')+' ms: mejora '+fmt(ratio(1024,3,'cyclic'))+' veces respecto de su versión original, incluyendo el tiempo de copiar. Frente al mejor secuencial, la aceleración útil es '+fmt(row(1024,3,'cyclic')['speedup_useful'])+'.')
h('El control con un solo proceso')
p('Antes de copiar, P=1 da '+time(1024,1,'contiguous','original')+' ms en contiguo y '+time(1024,1,'cyclic','original')+' ms en cíclico. Con el vector local, quedan en '+time(1024,1,'contiguous')+' y '+time(1024,1,'cyclic')+' ms, con cuartiles superpuestos. La gran diferencia previa se redujo: el reparto entre procesos no podía explicar esa diferencia inicial.')
fig('speedup.png',497,221)
p('Figura 2. Aceleración útil de las nuevas variantes. Tres procesos cíclicos dieron la menor mediana para n=1024; sus cuartiles se superponen con los de cuatro procesos y con el contiguo de tres. Debemos repetir antes de afirmar cuál es la mejor configuración de forma estable.','small')

page('05','Qué decidimos y cuál es la próxima pregunta')
h('Qué podemos concluir')
p('Conservar <b>right-looking MPI cíclico con vector local</b> como candidato principal está ahora respaldado por una mejora medida, no solo por el conteo de operaciones. También conservamos el contiguo original como referencia: la copia no lo mejora sistemáticamente. Para matrices pequeñas, mantenemos el secuencial como opción práctica.')
p('El informe del compilador registra vectorización del nuevo bucle interno. El perfil separado muestra menor tiempo de cálculo local en el cíclico con vector para los tres rangos de n=1024, P=3. Es evidencia compatible con la mejora del acceso y la indexación; no cuantifica cuánto proviene de caché, instrucciones vectoriales u otros efectos.')
p('El tiempo dentro de MPI_Bcast incluye esperas además de transferencia. El perfil tiene instrumentación y se ejecuta en otra pasada: sus tiempos no deben sustituir las medianas principales. No medimos comunicación entre nodos ni el tiempo completo de la aplicación.')
h('Validación y trazabilidad')
p('Las cuatro variantes pasaron los casos SPD, el factor conocido, repartos desiguales, P&gt;n y fallos colectivos con P=1,2,3,4. También verificamos los límites del vector local y ejecutamos AddressSanitizer/UndefinedBehaviorSanitizer con P=4. Se mantuvo la adaptación de Open MPI descrita en la etapa 2 solo para los sanitizadores, con detección de fugas desactivada.')
p('Las 512 observaciones MPI fueron aceptadas. El residuo máximo fue 1,2131×10⁻¹⁵, inferior al límite 10⁻¹². La máxima diferencia registrada del factor frente a right secuencial fue cero en esta campaña. Se conservaron entradas del protocolo, afinidad, CSV y huellas de las fuentes.')
h('¿En qué tamaño empieza a compensar esta versión?')
p('Para responder mejor, el próximo paso razonable es probar tamaños intermedios entre 64 y 256, repetir campañas independientes y comparar pocos valores de P. Así evitamos elegir un umbral por una sola mediana. Después repetiremos el protocolo en el clúster, separando un nodo de varios nodos; los bloques y la planificación dinámica quedan para cuando los datos justifiquen su complejidad.')
table([['Archivo en desde_cero','Función'],['src/cholesky_mpi.c','Conserva el kernel original y añade cholesky_mpi_local.'],['src/compare_mpi_local.c','Compara las cuatro variantes y valida sus factores.'],['scripts/comparar_mpi_local.sh','Ejecuta la campaña reproducible.'],['scripts/analizar_mpi_local.py','Valida observaciones y genera estadísticas y gráficos.'],['resultados/mpi_local_20260921/','Datos, perfil, fuentes y comprobaciones.']],[223,274])

def footer(c,doc):
    w,height=A4;c.setStrokeColor(HexColor('#CFDDE3'));c.line(48,height-36,w-48,height-36)
    c.setFont('Body',8);c.setFillColor(HexColor('#536675'))
    c.drawString(48,28,'HPC · Cholesky | MPI en C · Estadísticas en Python | 21/09/2026')
    c.drawRightString(w-48,28,str(doc.page))
OUT.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=49,bottomMargin=48,title='Cholesky, etapa 3: vector local MPI',author='Proyecto Cholesky HPC 2026').build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
