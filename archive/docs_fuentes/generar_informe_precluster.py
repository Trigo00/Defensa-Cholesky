"""Etapa 10: decisiones locales y preparación de ejecución entre nodos."""
from pathlib import Path
import csv,json,sys,io
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from matplotlib.mathtext import math_to_image
from svglib.svglib import svg2rlg
D=ROOT/'desde_cero/resultados/precluster_20260924'
OUT=ROOT/'output/pdf/Cholesky_Etapa_10_Preparacion_cluster.pdf'
with (D/'resumen.csv').open() as f:rows=list(csv.DictReader(f))
R={(r['experiment'],int(r['N']),r['method']):r for r in rows};V=json.loads((D/'validacion.json').read_text())
styles=getSampleStyleSheet();styles['BodyText'].leading=14;story=[]
def p(t):story.extend([Paragraph(t,styles['BodyText']),Spacer(1,8)])
def h(t):story.append(Paragraph(t,styles['Heading2']))
def page(t):
    if story:story.append(PageBreak())
    story.extend([Paragraph(t,styles['Title']),Spacer(1,10)])
def eq(t):
    b=io.BytesIO();math_to_image('$'+t+'$',b,format='svg');b.seek(0);d=svg2rlg(b);d.hAlign='CENTER';story.extend([d,Spacer(1,10)])
def table(data,widths):
    t=Table(data,colWidths=widths);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecf0')),('BOTTOMPADDING',(0,0),(-1,-1),8)]));story.extend([t,Spacer(1,10)])
page('Etapa 10: cerrar decisiones locales')
p('24 de septiembre de 2026. Completamos el alcance previo al clúster acordado: confirmar el reparto, incorporar una referencia LAPACK de un hilo, probar un tamaño mayor y preparar scripts configurables. Las conclusiones siguen siendo locales.')
h('¿Se mantiene la mejora de cuatro columnas?')
p('El 22 de septiembre b=4 pareció prometedor para n=1024 y P=6. Lo repetimos en esta nueva sesión con b=1 y b=4, ocho repeticiones por variante, orden alternado y el mismo resultado reunido en rango 0. El total contiene reserva, generación distribuida, kernel y recolección; MPI ya está iniciado.')
t=[['n','P','b=1 total (ms)','b=4 total (ms)']]
for n in (1024,2048,3072):t.append([str(n),'6',f'{1000*float(R["mpi",n,"1"]["total_median_s"]):.2f}',f'{1000*float(R["mpi",n,"4"]["total_median_s"]):.2f}'])
table(t,[70,45,180,180])
p('Para n=1024 y n=2048, b=4 no reduce la mediana total en esta sesión. No sostenemos la ventaja anterior como regla. Conservamos b=1 como referencia principal; b=4 queda disponible para comparar en el clúster.')
h('¿Podemos aumentar el tamaño local?')
p('n=3072 se ejecutó y validó con P=6. Solo hicimos dos repeticiones por bloque: es un piloto de factibilidad, no evidencia estadística suficiente para elegir reparto. El resultado no fija el tamaño adecuado del clúster.')
p('Se registraron entorno, afinidad, tiempos externos y uso máximo de memoria informado por time -v. El RSS de ese comando no representa la suma de memoria de todos los rangos. La estimación previa considera las copias de referencia y validación; no mide la memoria mínima del algoritmo.')
h('Qué cambió respecto del experimento anterior')
p('El banco admite seleccionar únicamente b=1 y b=4. Los mapas, el kernel y las condiciones numéricas son los mismos. Se registran los datos nuevos sin sobrescribir campañas anteriores. Una mejora observada una vez no obliga a adoptarla: repetir también puede justificar descartarla.')
page('¿Qué aporta LAPACK a la comparación?')
p('LAPACK proporciona rutinas de álgebra lineal. DPOTRF calcula Cholesky y organiza operaciones por bloques utilizando BLAS de nivel 3. LAPACKE es su interfaz C; OpenBLAS suministra rutinas optimizadas para el procesador. Esta referencia combina algoritmo e implementación optimizada: no aísla cuánto aporta cada técnica.')
h('La idea que debemos poder explicar')
eq(r'A=LL^T')
eq(r'L_{11}L_{11}^T=A_{11},\quad L_{21}L_{11}^T=A_{21}')
eq(r'A_{22}\leftarrow A_{22}-L_{21}L_{21}^T')
p('Esta identidad por bloques explica el trabajo: factorizar un bloque diagonal, resolver el panel inferior y actualizar una región con productos matriciales. Es un esquema conceptual right-looking; no afirmamos que reproduzca exactamente el orden interno de la biblioteca instalada. Las operaciones sobre submatrices permiten reutilizar datos y emplear kernels especializados.')
h('Comparación controlada desde C')
p('Nuestro right-looking con vector y LAPACK se ejecutan en el mismo programa, sin MPI, ligados a CPU 0 en esta PC. OpenBLAS se configura en un hilo y se comprueba con su API. Misma semilla 2026, precisión double, generador y política de reserva. Ambos reservan un vector n; LAPACK no necesita usarlo. Un calentamiento y seis repeticiones alternadas para n=512,1024,2048; dos para n=3072.')
p('Tiempo de factor: llamada de factorización. Total: reserva + generación + factor. Referencias, validación y liberación están fuera. No hay conversión de almacenamiento: A simétrica por filas se interpreta por columnas, DPOTRF produce U y el mismo arreglo representa L=U transpuesta por filas. Un caso con factor conocido comprueba esa interpretación.')
p('Usamos LAPACKE_dpotrf_work para evitar una transposición de la interfaz row-major y su barrido opcional de NaN. El dominio medido es entrada finita SPD generada; validamos resultados por separado. Los contratos de error de las implementaciones no son idénticos.')
h('Bibliotecas y fuentes consultadas')
p('LAPACKE 3.12.1; OpenBLAS 0.3.32, backend Zen, un hilo comprobado. Los logs incluyen dependencias dinámicas y configuración. La optimización interna de OpenBLAS no usa necesariamente las mismas opciones que nuestro código compilado con -O3.')
p('<link href="https://www.netlib.org/lapack/explore-html/d2/d09/group__potrf_ga84e90859b02139934b166e579dd211d4.html" color="blue">DPOTRF: contrato y algoritmo</link>; <link href="https://www.netlib.org/lapack/lapacke.html" color="blue">LAPACKE: interfaz C y almacenamiento</link>; <link href="https://www.openmathlib.org/OpenBLAS/docs/runtime_variables/" color="blue">OpenBLAS: configuración de ejecución</link>.')
page('Resultados: factor y tiempo completo')
story.append(Image(str(D/'lapack.png'),width=485,height=194))
p('Medianas; escala vertical logarítmica. n=3072 es exploratorio con dos repeticiones por método. No se mezclan tiempos de MPI con este experimento secuencial.')
t=[['n','C factor ms','LAPACK factor ms','C total ms','LAPACK total ms']]
for n in (512,1024,2048,3072):
    a=R['lapack',n,'own'];b=R['lapack',n,'lapack']
    t.append([str(n),f'{1000*float(a["factor_median_s"]):.2f}',f'{1000*float(b["factor_median_s"]):.2f}',f'{1000*float(a["total_median_s"]):.2f}',f'{1000*float(b["total_median_s"]):.2f}'])
table(t,[40,100,120,100,125])
a=R['lapack',2048,'own'];b=R['lapack',2048,'lapack']
p(f'Para n=2048, el cociente C/LAPACK es {float(a["factor_median_s"])/float(b["factor_median_s"]):.2f}x en factor y {float(a["total_median_s"])/float(b["total_median_s"]):.2f}x en total. Es una comparación de implementaciones con un hilo, no speedup MPI ni prueba de que un algoritmo sea siempre superior.')
h('Qué decidimos con estos datos')
p('Existe margen importante en el cálculo local frente a una biblioteca optimizada. Esto justifica presentar LAPACK como referencia y explicar bloques/BLAS como mejora futura. No obliga a reimplementar la biblioteca antes del clúster ni invalida el estudio educativo de MPI por columnas.')
h('Corrección y alcance')
p(f'{V["observations"]} observaciones nuevas aceptadas: 36 MPI y 40 secuenciales/LAPACK. Residuo proyectado máximo {V["max_projected"]:.3e}; diferencia máxima respecto del factor secuencial {V["max_difference"]:.3e}. Pruebas pequeñas con residuo completo, factor conocido y rechazo de una matriz indefinida. Pruebas C, MPI y sanitizadores de la interfaz propia pasaron; la biblioteca instalada no fue recompilada con sanitizadores.')
p('Ocho proyecciones y comparación de factores en matrices grandes; el residuo proyectado no es un certificado. La generación de referencia y el cálculo secuencial de referencia continúan fuera del reloj principal y cuestan memoria y tiempo.')
page('Preparados para probar en el clúster')
h('Archivos operativos')
p('scripts/campana_cluster.sh: tamaños, procesos, repeticiones, lanzador y presupuesto de memoria configurables; exporta CSV, entorno, afinidad y fuentes. scripts/analizar_pares_cluster.py: análisis con biblioteca estándar Python para grillas nuevas. docs/GUIA_CLUSTER.md: instrucciones de compilación, métricas, límites y coordinación con el administrador.')
h('Orden de ejecución')
p('1. Confirmar con el administrador módulos, MPI, RAM, núcleos físicos, asignación y lanzamiento. 2. Compilar en destino y ejecutar tests pequeños. 3. Pilotos en un nodo para elegir tamaños grandes que quepan y duren suficiente. 4. Comparar un nodo y varios nodos con el mismo n y P cuando sea posible. 5. Aumentar P y repetir en distintas asignaciones. Registrar ubicación real y no solo cantidad de procesos.')
h('Qué comparación debemos preservar')
p('Conservar datos, salida centralizada, compilación, algoritmo y definición del reloj. Medir una referencia secuencial contemporánea en el mismo hardware; identificar si es nuestra implementación o LAPACK. No calcular speedup del clúster usando tiempos WSL. La espera en MPI puede mezclar comunicación y desbalance; debe interpretarse como tiempo observado, no latencia pura de red.')
h('Límites que siguen abiertos')
p('No ejecutamos pruebas entre nodos. El script no solicita asignaciones ni inventa directivas del planificador. Está probado localmente con mpirun; su configuración real dependerá del administrador. El ejecutable admite n hasta 20000; tamaños mayores exigen revisar conteos MPI, índices y memoria antes de ampliar ese límite.')
p('El control de memoria por defecto usa 60 % de MemAvailable del host de lanzamiento. En el clúster debe fijarse al presupuesto de la asignación. Las referencias y copias extra limitan este banco; no es una implementación de memoria mínima.')
h('Conclusión local y próximo interrogante')
p('Se conserva right-looking MPI cíclico de una columna como referencia. Cuatro columnas no demostraron una mejora estable entre sesiones. LAPACK revela margen en cálculo local. Ahora la pregunta es cómo cambia el equilibrio entre cómputo y comunicación cuando participan nodos distintos. Almacenamiento triangular, híbrido MPI+OpenMP y Cholesky por bloques quedan como extensiones, no requisitos para comenzar.')
h('Trazabilidad y asistencia')
p('Campaña: resultados/precluster_20260924. Fuentes y comandos acompañan los CSV. Desarrollo, análisis y texto con asistencia de IA; mediciones obtenidas ejecutando C en la PC. Las conclusiones deben poder defenderse explicando las decisiones y sus límites.')
def footer(c,d):c.setFont('Helvetica',9);c.drawString(48,28,'Cholesky paralelo | Etapa 10 | Preparación previa al clúster');c.drawRightString(547,28,str(d.page))
SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=42,bottomMargin=46).build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
