"""Informe vigente: variantes, criterio MPI y distribuciones; datos reales de C."""
from pathlib import Path
import csv
import io
import json
import os
import sys

ROOT=Path(__file__).resolve().parents[2]
if os.name=='nt':
    sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
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

DATA=ROOT/'desde_cero/resultados/left_right_20260921'
MEMORY=ROOT/'desde_cero/resultados/memoria_20260921'
OUT=ROOT/'output/pdf/Cholesky_Etapa_1_Fundamentos_y_diseno.pdf'
font_dir=Path('C:/Windows/Fonts')
font_files=[('Body','calibri.ttf'),('Bold','calibrib.ttf')]
if not (font_dir/'calibri.ttf').exists():
    font_dir=Path(matplotlib.get_data_path())/'fonts/ttf'
    font_files=[('Body','DejaVuSans.ttf'),('Bold','DejaVuSans-Bold.ttf')]
for name,file in font_files:
    pdfmetrics.registerFont(TTFont(name,str(font_dir/file)))
pdfmetrics.registerFontFamily('Body',normal='Body',bold='Bold')
INK=HexColor('#172B3A'); BLUE=HexColor('#126F85')
styles={
    'title':ParagraphStyle('title',fontName='Bold',fontSize=24,leading=28,textColor=INK,spaceAfter=16),
    'h':ParagraphStyle('h',fontName='Bold',fontSize=14,leading=18,textColor=BLUE,spaceBefore=13,spaceAfter=7),
    'body':ParagraphStyle('body',fontName='Body',fontSize=11.3,leading=15.5,textColor=INK,spaceAfter=9),
    'small':ParagraphStyle('small',fontName='Body',fontSize=9,leading=12,textColor=HexColor('#536675'),spaceAfter=8),
    'cell':ParagraphStyle('cell',fontName='Body',fontSize=10.2,leading=13.5,textColor=INK),
}
story=[]
def p(text,style='body'):story.append(Paragraph(text,styles[style]))
def h(text):p(text,'h')
def page(number,title):
    if story:story.append(PageBreak())
    p('CHOLESKY / DECISIONES DE DISEÑO / '+number,'small');p(title,'title')
def eq(formula,size=17):
    buf=io.BytesIO();math_to_image('$'+formula+'$',buf,prop=FontProperties(size=size),format='svg',color='#172B3A')
    buf.seek(0);d=svg2rlg(buf);d.hAlign='CENTER'
    story.extend([Spacer(1,4),d,Spacer(1,9)])
def table(rows,widths):
    content=[[Paragraph(str(c),styles['cell']) for c in r] for r in rows]
    t=Table(content,colWidths=widths,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#DCECF0')),('ROWBACKGROUNDS',(0,1),(-1,-1),[HexColor('#F1F6F8'),white]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8)]))
    story.extend([t,Spacer(1,9)])
def figure(name,width,height):story.extend([Image(str(DATA/name),width=width,height=height),Spacer(1,6)])
def ref(number,title,url):p(f'[{number}] <link href="{url}" color="#126F85">{title}</link>.','small')
with (DATA/'resumen.csv').open() as f:records=list(csv.DictReader(f))
stats={(int(r['N']),r['variant']):r for r in records}
sizes=sorted({n for n,_ in stats})
with (MEMORY/'resumen.csv').open() as f:memory_records=list(csv.DictReader(f))
memory_stats={(int(r['N']),r['variant']):r for r in memory_records}
memory_sizes=sorted({n for n,_ in memory_stats})

page('01','Cholesky: el problema que vamos a resolver')
p('Queremos factorizar una matriz real A, simétrica y definida positiva, como el producto de una matriz triangular inferior L y su transpuesta:')
eq(r'A=LL^{T}')
p('Por encima de la diagonal de L todos los elementos son cero. Elegimos su diagonal positiva; con esa condición el factor es único. Esta factorización permite resolver Ax = b mediante los sistemas triangulares Ly = b y Lᵀx = y.')
h('Condiciones de entrada')
eq(r'A=A^{T},\qquad x^{T}Ax>0\quad\mathrm{para\ todo}\ x\ne 0',16)
p('La primera condición es simetría; la segunda es definición positiva. En aritmética exacta garantizan que los pivotes de Cholesky sean positivos, sin necesidad de intercambiar filas. El código comprueba los pivotes para detectar entradas o resultados inválidos.')
h('De dónde salen las dependencias')
p('Al desarrollar el producto matricial, con índices desde cero, obtenemos:')
eq(r'a_{ij}=\sum_{k=0}^{\min(i,j)}l_{ik}l_{jk}')
p('Una columna nueva utiliza contribuciones de las anteriores. Left-looking y right-looking cambian cuándo se aplican esas contribuciones, no el problema matemático. Ambas variantes escalares realizan aproximadamente n³/3 operaciones de punto flotante.')
h('Las tres decisiones del trabajo')
p('<b>Primera:</b> qué variante conviene estudiar y qué muestran sus tiempos. <b>Segunda:</b> cuándo el ahorro de cálculo justifica usar más procesos. <b>Tercera:</b> cómo repartir los datos para mantener trabajo útil en esos procesos.')
p('Todo el cálculo, la generación de matrices y la futura implementación MPI se realizan en C. Python procesa los CSV y genera estadísticas y gráficos. En este informe se distingue entre mediciones ejecutadas, conteos analíticos y experimentos MPI todavía pendientes.','small')
ref(1,'Ballard et al. (2009), Communication-optimal Parallel and Sequential Cholesky Decomposition','https://www.netlib.org/lapack/lawnspdf/lawn215.pdf')

page('02','Left-looking y right-looking: ¿dónde está el paralelismo?')
h('Left-looking: actualizar la columna que necesitamos')
p('Al llegar a la columna j, recuperamos los aportes de las columnas ya calculadas. Primero obtenemos el pivote y luego los elementos debajo de él:')
eq(r'l_{jj}=\sqrt{a_{jj}-\sum_{k=0}^{j-1}l_{jk}^{2}}')
eq(r'l_{ij}=\frac{a_{ij}-\sum_{k=0}^{j-1}l_{ik}l_{jk}}{l_{jj}},\qquad i>j')
p('<b>También permite paralelismo:</b> conocido el pivote y disponibles los datos anteriores, distintos elementos lᵢⱼ pueden calcularse simultáneamente. Incluso una suma interna puede repartirse si luego se combinan correctamente sus resultados. En memoria distribuida debemos decidir dónde están esos datos y cuánto cuesta reunirlos.')
h('Right-looking: actualizar la región que todavía falta')
p('Usamos una matriz de trabajo S, inicialmente igual a A. Al llegar a j, las contribuciones anteriores ya se aplicaron:')
eq(r'l_{jj}=\sqrt{s_{jj}},\qquad l_{ij}=s_{ij}/l_{jj}\quad(i>j)')
p('Luego la columna calculada actualiza la submatriz restante:')
eq(r's_{ik}\leftarrow s_{ik}-l_{ij}l_{kj},\qquad i\geq k>j')
p('<b>El paralelismo aparece en esas actualizaciones:</b> cada pareja (i, k) modifica una posición diferente y lee una columna ya terminada. Las actualizaciones de la siguiente columna deben completarse antes de factorizarla.')
p('Ambas variantes tienen dependencias entre columnas y admiten versiones por bloques. En right-looking nos interesa repartir las actualizaciones; no ejecutar arbitrariamente todas las columnas a la vez. [1]','small')

page('03','Experimento 1: comparar las dos variantes en C')
h('La pregunta y el experimento')
p('<b>¿Right-looking es más rápido que left-looking en nuestra implementación secuencial?</b> Implementamos ambas variantes escalares en el mismo archivo C, con double, almacenamiento por filas y el mismo compilador. No usamos BLAS ni MPI en esta comparación.')
h('Matrices iguales para las dos variantes')
p('El generador C, con semilla 2026, crea valores simétricos fuera de la diagonal en [−1, 1). La diagonal se define como:')
eq(r'a_{ii}=1+\sum_{j\ne i}|a_{ij}|')
p('Esto produce una matriz simétrica con diagonal positiva y estrictamente dominante; por tanto es definida positiva. Cada llamada recibe una copia nueva de la misma matriz. Se exige un residuo relativo de reconstrucción no mayor que 10⁻¹².')
h('Condiciones de medición')
p('WSL / Ubuntu 26.04, AMD Ryzen 5 2600, GCC 15.2.0 y opciones -O3 -std=c11 -Wall -Wextra -Wpedantic. Ambas variantes se fijan a la misma CPU lógica. Para cada tamaño hacemos un calentamiento por variante y siete repeticiones, alternando cuál se ejecuta primero.')
p('El tiempo incluye solo la factorización. Generación, copia y residuo quedan fuera. Conservamos las observaciones individuales y calculamos medianas y cuartiles inclusivos. La copia y validación siguen el mismo protocolo para ambas variantes, pero no garantizan un estado idéntico de caché.')
rows=[['n','Left (ms)','Right (ms)','Right / Left']]
for n in sizes:
    l=float(stats[n,'left']['median_s']);r=float(stats[n,'right']['median_s'])
    rows.append([n,f'{l*1000:.4f}',f'{r*1000:.4f}',f'{r/l:.2f}'])
table(rows,[49,150,150,150])
p('Medianas de siete repeticiones por variante y tamaño. Un cociente Right / Left mayor que 1 indica que right-looking tarda más. No es un speedup MPI. Datos nuevos: resultados/left_right_20260921/.','small')

page('04','Qué dicen los datos y qué no demuestran')
figure('left_right.png',493,260)
p('Figura 1. Comparación secuencial. Ambos ejes son logarítmicos. Los puntos indican la mediana y las barras abarcan Q1 a Q3; algunas barras son pequeñas a esta escala.','small')
h('Resultado observado')
p('En esta primera campaña, right-looking tiene una mediana ligeramente menor para n = 64. Left-looking es más rápido en los otros cuatro tamaños ensayados. Para n = 1024, right-looking tarda aproximadamente 8,06 veces más. Por lo tanto, <b>estos resultados no justifican elegir la versión original de right-looking por velocidad secuencial</b>.')
h('Una explicación que debemos investigar')
p('El código de left-looking calcula productos escalares recorriendo filas contiguas. El de right-looking relee elementos de una columna con saltos de n posiciones. La inspección del código muestra esa diferencia de acceso; el experimento no aísla cuánto explica del tiempo. Haría falta variar almacenamiento o implementar bloques para comprobarlo.')
p('La conclusión corresponde a estas versiones escalares y a este equipo. No prueba que todas las implementaciones de left-looking superen a todas las de right-looking, ni que MPI vaya a invertir el resultado.')
h('La pregunta siguiente')
p('<b>¿Qué pasaría si copiamos la columna activa a un vector contiguo antes de reutilizarla?</b> Esa pregunta abre el experimento 2. Antes de agregar comunicación con MPI, comprobamos si un cambio pequeño en los accesos a datos mejora el cálculo local.')

page('05','Experimento 2: cambiar el acceso, conservar el algoritmo')
h('Hipótesis')
p('El kernel right-looking original recorre la matriz por filas, pero lee la columna activa con saltos. Proponemos copiar esa columna a un vector contiguo y reutilizarlo durante la actualización. La hipótesis es que el ahorro en esas lecturas repetidas compense el costo de copiar.')
table([
    ['Versión','Lectura dentro del bucle sobre k'],
    ['Right original','a[k*n+j]: al aumentar k, la dirección avanza n valores.'],
    ['Right + vector','column[k]: al aumentar k, la dirección avanza un valor.'],
],[145,354])
eq(r'c_k\leftarrow l_{kj},\qquad s_{ik}\leftarrow s_{ik}-l_{ij}c_k',17)
p('Mantenemos los bucles en el orden j, i, k, los mismos destinos y las mismas multiplicaciones y restas. El pivote y el cálculo de la columna no cambian. Esto sigue siendo Cholesky right-looking; no es aún una versión por bloques ni una implementación MPI.')
h('Costo de la modificación')
eq(r'\mathrm{memoria\ extra}=8n\ \mathrm{bytes},\qquad\mathrm{copias}=\frac{n(n-1)}{2}',17)
p('El vector reserva n valores double y se reutiliza. Para n = 1024 ocupa 8 KiB. El total de valores copiados crece como n², mientras que las actualizaciones mantienen su trabajo cúbico. Reservamos el vector antes del cronómetro, pero <b>todas las copias de columnas se incluyen en el tiempo medido</b>.')
h('Comparación controlada')
p('Volvemos a medir left, right original y right con vector en la misma campaña, sobre las mismas matrices y la misma CPU lógica. Hacemos un calentamiento por variante y doce repeticiones: las seis permutaciones del orden de ejecución se usan dos veces. Así cada variante aparece igual cantidad de veces en cada posición.')
p('Conservamos el equipo, GCC 15.2.0 y las opciones -O3 del experimento anterior. Medimos n = 64, 128, 256, 512, 1000 y 1024; n = 1000 evita limitar la muestra a potencias de dos. Las reservas, la copia de entrada y la validación quedan fuera del tiempo en las tres variantes.','small')

page('06','Resultados: ¿compensa copiar la columna?')
rows=[['n','Left (ms)','Right (ms)','Vector (ms)','Right / vector','Left / vector']]
for n in memory_sizes:
    left=float(memory_stats[n,'left']['median_s']);right=float(memory_stats[n,'right']['median_s']);vector=float(memory_stats[n,'right_buffered']['median_s'])
    rows.append([n,f'{left*1000:.4f}',f'{right*1000:.4f}',f'{vector*1000:.4f}',f'{right/vector:.2f}',f'{left/vector:.2f}'])
table(rows,[37,88,97,97,90,90])
p('Medianas de doce repeticiones por variante y tamaño. Un cociente mayor que 1 favorece a right con vector. Cada comparación usa exclusivamente observaciones de esta segunda campaña; no mezclamos tiempos nuevos con los del experimento 1.','small')
story.extend([Image(str(MEMORY/'memoria.png'),width=493,height=226),Spacer(1,6)])
p('Figura 2. Medianas y barras Q1–Q3. El eje vertical es logarítmico; el horizontal muestra tamaños como categorías. Las barras representan dispersión, no intervalos de confianza.','small')
h('El resultado que cambia nuestra decisión')
p('La variante con vector obtiene menor mediana en los seis tamaños probados. Para n = 1024, pasa de 1159,09 ms a 76,92 ms frente a right original: una mejora de 15,07 veces. En la misma campaña supera a left, que tarda 144,79 ms, por un factor de 1,88.')
p('La comparación conserva y contabiliza el costo del empaquetado. El trabajo adicional de copia se compensa en estas condiciones. Son mediciones secuenciales locales; todavía no representan un speedup MPI.','small')

page('07','Interpretación y decisión después del experimento')
h('¿Se conserva la corrección?')
p('Sí en los casos ensayados. La variante con vector produce el factor esperado para el ejemplo conocido y supera quince matrices generadas de distintos tamaños y semillas. Se compara su factor con right original, se comprueban pivotes inválidos y se prueba que no lea zonas del vector todavía sin inicializar ni escriba fuera de él.')
p('Las pruebas con AddressSanitizer y UndefinedBehaviorSanitizer pasaron. En la campaña se aceptaron 216 observaciones: seis tamaños, tres variantes y doce repeticiones. Todas cumplieron el criterio de residuo relativo no mayor que 10⁻¹²; el máximo registrado fue aproximadamente 1,21 × 10⁻¹⁵.')
h('Qué respalda y qué no aísla esta evidencia')
p('Mantener el algoritmo y cambiar el acceso a la columna produjo una reducción clara del tiempo. Esto respalda que la organización de esos accesos era una limitación importante de esta implementación. Sin contadores de hardware ni análisis adicional no atribuimos un porcentaje específico a fallos de caché: también pueden cambiar la vectorización y otras decisiones del compilador.')
p('Hay una señal útil: right original tarda 95,74 ms para n = 1000 y 1159,09 ms para n = 1024, aunque los tamaños son cercanos. La nueva versión tarda 59,85 y 76,92 ms. La sensibilidad al tamaño se reduce, pero no afirmamos haber identificado el mecanismo exacto que causó el salto.')
h('Qué conservamos')
p('<b>Adoptamos right-looking con vector como referencia local para el siguiente experimento MPI.</b> Ahora la decisión combina una organización clara para repartir actualizaciones con una mejora secuencial medida. Mantenemos left y right original como referencias y preservamos los resultados anteriores: pertenecen a implementaciones distintas.')
p('No concluimos que right-looking sea universalmente superior. La selección vale para estas versiones, matrices y máquina, y debe revisarse en el clúster. Para evaluar MPI volveremos a medir la mejor referencia secuencial en el mismo entorno.')
h('La pregunta siguiente')
p('<b>¿La ganancia de repartir estas actualizaciones alcanza para pagar el envío de columnas?</b> Esa será la prueba MPI. Un kernel local más rápido puede hacer que necesitemos matrices más grandes para que la comunicación se amortice; mejorar lo secuencial no garantiza más speedup paralelo.')
p('Trazabilidad: src/compare_memory.c, scripts/comparar_memoria.sh y resultados/memoria_20260921/. Python produce resumen.csv y memoria.png a partir de los CSV individuales.','small')

page('08','La razón para estudiar right-looking con MPI')
h('Partimos de una propiedad fija de las columnas')
p('Supongamos que cada columna tiene un proceso propietario. Queremos que los datos permanezcan en ese proceso y que el trabajo importante pueda repartirse sin migrar continuamente la matriz.')
table([
    ['Con ese reparto','Left-looking','Right-looking'],
    ['Columna j','Su dueño necesita aportes de columnas anteriores que pueden estar en otros procesos.','Su dueño encuentra la columna ya actualizada, calcula el pivote y los valores inferiores.'],
    ['Trabajo repartido','Para repartir el cálculo de esa columna habría que distribuir sumas o filas y reunir resultados, o usar otra planificación.','La columna calculada se comunica; cada proceso actualiza las columnas futuras de las que ya es dueño.'],
    ['Dependencias','Los aportes y el pivote deben estar disponibles.','La columna debe estar lista antes de actualizar; las actualizaciones necesarias preceden al siguiente pivote.'],
],[91,204,204])
p('La tabla describe una primera organización sencilla con columnas de dueño fijo. No afirma que todas las implementaciones left-looking necesiten esa misma comunicación ni que no puedan ser competitivas.')
h('Dónde encontramos trabajo independiente')
p('Con right-looking, terminada la columna j, dos procesos pueden actualizar destinos diferentes usando los mismos valores recibidos. La región activa contiene muchas actualizaciones, mientras que el pivote sigue siendo parte de la cadena de dependencias. Esta secuencia tiene una traducción directa a MPI: propietario → difusión de columna → actualizaciones locales. [2]')
h('Decisión defendible en el informe')
p('<b>Elegimos right-looking con vector para la primera implementación MPI por su correspondencia con un reparto estático de columnas, sus actualizaciones independientes y la mejora local medida en el experimento 2.</b> Conservaremos left y el mejor secuencial disponible al evaluar la utilidad real de MPI.')
p('La ventaja secuencial observada no demuestra escalabilidad distribuida. La adopción de MPI por rendimiento queda condicionada a medir su costo completo de factorización, incluidas comunicaciones y esperas.')
ref(2,'Netlib, Cholesky Factorization: panel y actualización distribuida right-looking','https://www.netlib.org/utk/papers/factor/node9.html')

page('09','¿Cuándo conviene usar más procesos?')
p('Repartir trabajo ahorra cálculo por proceso, pero agrega comunicación, coordinación y posibles esperas. Un modelo orientativo, sin solapamiento, es:')
eq(r'T_P\approx T_{\mathrm{dep}}+\frac{T_{\mathrm{upd}}}{P}+T_{\mathrm{comm}}+T_{\mathrm{espera}}',16)
p('Tdep representa trabajo dependiente no repartido; Tupd, las actualizaciones repartibles. En este modelo, usar P procesos compensa frente al mismo algoritmo secuencial cuando:')
eq(r'T_{\mathrm{upd}}\left(1-\frac{1}{P}\right)>T_{\mathrm{comm}}+T_{\mathrm{espera}}',17)
p('Para un mensaje de m bytes, el modelo α + βm distingue el costo de iniciar el envío y el costo por volumen. Un broadcast depende además de P y de la implementación MPI; no lo deduciremos únicamente de un ping-pong. [1]')
h('La comparación que realmente decide')
eq(r'T_{\mathrm{base}}(n)=\min(T_{L,1}(n),T_{R,1}(n),T_{R_v,1}(n))',15)
eq(r'S_{\mathrm{util}}(n,P)=\frac{T_{\mathrm{base}}(n)}{T_{R_v,P}(n)}',17)
p('Rv indica right con vector. Conviene MPI si reduce de forma repetible el tiempo frente a esa base. También compararemos el mismo kernel MPI con P = 1 y P mayor para aislar su escalabilidad. Si importa el tiempo completo de una tarea, debemos sumar arranque y distribución inicial.')
p('Para n = 1024, el experimento 2 deja una referencia local de 76,92 ms. Una versión MPI tendría que mejorar ese tiempo total de factorización en condiciones comparables. No usaremos los 1159,09 ms de right original para presentar un speedup artificialmente favorable.')
h('Cómo obtendremos el umbral')
p('Para cada n probaremos P = 1, 2, 3, 4 y otros valores permitidos, con varias ejecuciones. Elegiremos el menor tiempo estable; si la diferencia es pequeña frente a la dispersión, preferiremos menos recursos. El primer n favorable será un cruce observado para esa configuración, no una constante universal.')
p('<b>Pendiente:</b> aún no ejecutamos MPI en esta etapa ni tenemos resultados entre nodos. WSL no mide la red del clúster. Separaremos ensayos dentro de un nodo y entre nodos, manteniendo explícitos procesos, núcleos y afinidad.','small')

page('10','Repartos estáticos: contiguo, cíclico y por bloques')
p('En un reparto estático, el propietario de cada columna se fija antes de factorizar. <b>Round-robin por columnas es exactamente el reparto cíclico</b>: se asignan por turnos a los procesos 0, 1, …, P−1 y se repite.')
figure('distribuciones.png',493,192)
p('Figura 3. Ejemplo de asignación con n = 12 y P = 3. Los colores y números indican propietarios, no tiempos de ejecución.','small')
h('Contiguo: un intervalo de columnas por proceso')
p('P0 recibe 0–3, P1 recibe 4–7 y P2 recibe 8–11. La asignación es sencilla. El problema aparece cuando termina el primer intervalo: P0 deja de tener columnas futuras que actualizar mientras otros procesos siguen trabajando. Igual cantidad de columnas no implica igual cantidad de operaciones.')
h('Cíclico: columnas alternadas')
eq(r'\operatorname{owner}(j)=j\ \mathrm{mod}\ P',17)
p('P0 recibe 0, 3, 6 y 9; P1 recibe 1, 4, 7 y 10; P2 recibe 2, 5, 8 y 11. Al reducirse la región activa, sus columnas quedan repartidas entre varios procesos durante más etapas. No elimina el desequilibrio ni la escasez de trabajo al final. [3]')
h('Bloque-cíclico: repartir grupos de columnas')
eq(r'\operatorname{owner}(j)=\lfloor j/b\rfloor\ \mathrm{mod}\ P',17)
p('Agrupa b columnas consecutivas antes de pasar al siguiente proceso. Con b = 1 recuperamos el cíclico. Con bloques mayores se busca combinar reparto y operaciones locales más grandes; el tamaño b se elegirá midiendo. Cambiar el reparto por sí solo no convierte el kernel escalar en BLAS-3.')
ref(3,'ScaLAPACK Users’ Guide, Two-dimensional Block-Cyclic Distribution','https://www.netlib.org/scalapack/slug/node75.html')

page('11','Por qué el cíclico es nuestra primera hipótesis')
h('Contemos el trabajo, sin inventar tiempos')
p('En el kernel escalar right-looking, una columna global k recibe una actualización por cada columna anterior j. Cada una modifica sus n−k elementos inferiores. El número de actualizaciones de esa columna durante toda la factorización es:')
eq(r'U(k)=k(n-k),\qquad k=0,\ldots,n-1',18)
p('Sumando U(k) según los propietarios de la figura anterior obtenemos este conteo exacto para n = 12 y P = 3:')
counts=json.loads((DATA/'conteo_distribuciones.json').read_text(encoding='utf-8'))
rows=[['Reparto','P0','P1','P2','Máx. / media']]
for name,record in counts.items():
    work=record['updates_by_rank'];ratio=max(work)/(sum(work)/3)
    rows.append([name,*work,f'{ratio:.2f}'])
table(rows,[203,60,60,60,116])
p('Se cuentan restas de productos sobre elementos, no pivotes, divisiones, bytes ni segundos. Un valor Máx./media cercano a 1 indica mejor equilibrio de este trabajo acumulado. No representa una medición de rendimiento ni captura todas las esperas entre etapas.','small')
h('Qué respalda este ejemplo')
p('El cíclico distribuye mejor las actualizaciones que el contiguo en este caso. Para matrices densas y procesos similares, eso motiva comenzar con <b>propiedad estática cíclica</b>. Después compararemos bloque-cíclico cuando agrupemos operaciones. La decisión final dependerá del tiempo y de la comunicación medidos, no solo del conteo.')
h('Distribución contigua no significa memoria contigua')
p('El reparto indica qué índices globales pertenecen a un proceso. El almacenamiento local indica cómo los guarda en su RAM. Un proceso con columnas cíclicas puede empaquetarlas en un arreglo local contiguo; no necesita reservar los huecos de las columnas ajenas. [5]')
h('Cuándo asignamos las columnas')
p('En el esquema estático las asignamos al inicio. Durante cada etapa se comunica la columna lista y se trabaja sobre datos locales. No esperamos a un número de columna mágico para empezar a delegar. Cerca del final hay menos destinos independientes; reducir procesos o migrar datos solo convendría si su ahorro supera ese costo adicional.')
ref(5,'ScaLAPACK Users’ Guide, Local Storage Scheme and Block-Cyclic Mapping','https://www.netlib.org/scalapack/slug/node76.html')

page('12','Reparto dinámico y criterio para continuar')
h('Qué decide una distribución dinámica')
p('Un planificador asigna tareas durante la ejecución según qué procesos están libres. En Cholesky no puede entregar cualquier columna sin más: solo puede despachar tareas cuyas dependencias estén resueltas. Una tarea podría actualizar un bloque usando un panel ya calculado. [4]')
p('Si el proceso elegido no tiene los datos, debe recibirlos o acceder a ellos. Además, dos tareas que modifican el mismo bloque deben respetar su dependencia o combinar sus resultados de forma segura. Por eso distinguimos la propiedad de datos de la planificación de tareas: es posible fijar una y hacer dinámica la otra.')
h('Cuándo podría ayudar y qué cuesta')
table([
    ['Aspecto','Estático cíclico','Dinámico'],
    ['Asignación','Se conoce de antemano; no consulta una cola por tarea.','Se decide al quedar libre un trabajador y estar lista una tarea.'],
    ['Desigualdad entre procesos','Un proceso lento puede retrasar etapas.','Puede asignar más tareas a trabajadores rápidos.'],
    ['Datos y coordinación','Propiedad fija; comunicación del panel predecible.','Colas, mensajes, dependencias y posibles transferencias de datos.'],
    ['Granularidad','Columnas o grupos con tamaño fijado.','Tareas pequeñas equilibran mejor, pero aumentan coordinación; tareas grandes reducen ese costo.'],
],[90,204,205])
p('No podemos descartar lo dinámico como siempre más lento: un planificador por tareas puede ser eficaz. Para nuestro primer MPI de matrices densas en recursos similares, el cíclico estático ofrece un punto de partida más sencillo. Lo dinámico se justificaría si medimos esperas importantes por heterogeneidad o trabajo irregular que compensen su costo.')
h('El siguiente experimento, en orden')
p('<b>1.</b> Conservar right con vector como referencia local, junto con left y right original.<br/><b>2.</b> Implementar MPI con propiedad estática, comparando cíclico y contiguo con el mismo kernel.<br/><b>3.</b> Medir por separado P y n dentro de un nodo y entre nodos; registrar tiempo total de factorización, cómputo por proceso y espera en MPI.<br/><b>4.</b> Incorporar bloques o planificación dinámica solo si los resultados explican qué problema resolverían.')
p('La medición paralela usará el máximo de los tiempos locales con inicio coordinado; excluirá validación y mantendrá el mismo criterio en todas las variantes. El tiempo dentro de MPI puede incluir espera, no solo transferencia. No se presentan tiempos de MPI ni de distribuciones como si ya se hubieran medido.','small')
ref(4,'Dorris et al., Task-Based Cholesky Decomposition: tareas listas y planificación dinámica','https://netlib.org/utk/people/JackDongarra/PAPERS/task-based-cholesky.pdf')

def footer(c,doc):
    w,h=A4;c.setStrokeColor(HexColor('#CFDDE3'));c.line(48,h-36,w-48,h-36)
    c.setFont('Body',8);c.setFillColor(HexColor('#536675'))
    c.drawString(48,28,'HPC · Cholesky | C para cómputo y MPI · Python para análisis | 21/09/2026')
    c.drawRightString(w-48,28,str(doc.page))

OUT.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=49,bottomMargin=48,title='Cholesky: variantes, costo de MPI y distribución',author='Proyecto Cholesky HPC 2026').build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
