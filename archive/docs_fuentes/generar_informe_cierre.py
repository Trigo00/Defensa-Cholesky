"""Three progressive reports from the validated candidate campaign."""
from pathlib import Path
import sys,json,io
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from matplotlib.mathtext import math_to_image
from svglib.svglib import svg2rlg
from pypdf import PdfReader
DATA=ROOT/'desde_cero/resultados/cierre_local_20260924'
info=json.loads((DATA/'analisis.json').read_text());rs=info['summary']
S={(r['N'],r['method']):r for r in rs}
styles=getSampleStyleSheet();styles['BodyText'].fontSize=10;styles['BodyText'].leading=13
story=[]
def p(t):story.extend([Paragraph(t,styles['BodyText']),Spacer(1,7)])
def h(t):story.append(Paragraph(t,styles['Heading2']))
def page(t):
 if story:story.append(PageBreak())
 story.extend([Paragraph(t,styles['Title']),Spacer(1,8)])
def eq(t):
 b=io.BytesIO();math_to_image('$'+t+'$',b,format='svg');b.seek(0);d=svg2rlg(b);d.hAlign='CENTER';story.extend([d,Spacer(1,9)])
def table(data,widths):
 t=Table([[Paragraph(str(v),styles['BodyText']) for v in row] for row in data],colWidths=widths,repeatRows=1)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecf0')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([t,Spacer(1,7)])
def save(name,stage):
 def footer(c,d):c.setFont('Helvetica',8);c.drawString(45,25,f'Cholesky | Etapa {stage} | Local WSL | 24/09/2026');c.drawRightString(550,25,str(d.page))
 out=ROOT/'output/pdf'/name
 SimpleDocTemplate(str(out),pagesize=A4,leftMargin=45,rightMargin=45,topMargin=40,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
 assert len(PdfReader(out).pages)==2
 story.clear();print(out.name)
page('Etapa 11: un programa candidato completo')
h('Pregunta e hipótesis')
p('Ya elegimos una variante a partir de bancos experimentales. ¿Podemos reunirla en un programa claro, correcto y medible sin cambiar el algoritmo? La hipótesis es que la composición conserva la corrección; su rendimiento debe medirse nuevamente.')
h('Qué conservamos')
p('Cholesky right-looking escalar en C; MPI; propiedad 1D cíclica de columnas (b=1); vector local contiguo; generación distribuida y factor completo reunido en rango 0. No añadimos OpenMP, LAPACK ni un algoritmo por bloques.')
eq(r'\operatorname{owner}(j)=j\ \mathrm{mod}\ P,\qquad A=LL^T')
h('Un programa, dos compilaciones comparables')
p('src/main_candidate.c es la entrada. Con USE_MPI se enlaza con cholesky_mpi.c y cholesky.c. Sin USE_MPI produce una referencia secuencial autónoma con right-looking buffered. Así comparten generador, validación y definición de salida, pero el secuencial no inicia MPI ni deja procesos inactivos esperando.')
p('Entrada: N entre 1 y 20000; semilla fija 2026. Ese límite protege los conteos MPI, no garantiza memoria disponible. No hay lectura de matrices externas. El límite local probado con siete repeticiones es N=2048; N=3072 pertenece al piloto histórico.')
h('Cómo ejecutarlo desde desde_cero, en Linux/WSL')
p('<font face="Courier">make candidate<br/>./build/cholesky_candidate_seq 1024<br/>mpirun --bind-to core --map-by core -np 3<br/>./build/cholesky_candidate_mpi 1024</font>')
p('Las dos últimas líneas representan un solo comando. La salida CSV informa tiempos, residuos y validez. L queda completo en memoria del rango 0; no se escribe un archivo de matriz ni se incluye I/O de disco del factor. El triángulo inferior representa L; el superior no forma parte del factor.')
h('Próxima pregunta')
p('Si la integración es correcta, ¿cuántos procesos reducen el tiempo hasta obtener L y cuánto se pierde al medir el comando completo?')
page('Comprobaciones y contrato del reloj')
table([['Comprobación','Resultado'],['Programa: N=1,2,7,31,128; secuencial y P=1,2,3,4,6','30 configuraciones válidas; incluye N menor que P y repartos desiguales.'],['Residuos','Ocho proyecciones reproducibles; residuo completo para N menor o igual a 128. Límite 1e-12 y control de valores finitos y diagonal positiva.'],['Biblioteca numérica propia','Pruebas existentes: factor conocido, identidad, variantes, entradas inválidas y detección de corrupción.'],['Interfaz','Argumentos inválidos rechazados. Errores de reserva abortan el trabajo MPI.']],[190,310])
p('Los tamaños grandes usan proyecciones O(n²) por vector, no reconstrucción completa O(n³). Eso es evidencia numérica, no un certificado para cualquier entrada. Esta etapa no amplía la familia de matrices: conserva las SPD diagonalmente dominantes del proyecto.')
eq(r'T_{app}=T_{reserva}+T_{generacion}+T_{factor}+T_{reunion}')
p('T_app es el intervalo medido en rango 0, desde la reserva hasta que reúne el resultado. También se registra la máxima duración local. Las fases de rango 0 suman su total, pero no son tiempos puros: por ejemplo, factor incluye comunicaciones y esperas. No sumamos máximos de fases de rangos distintos.')
p('La comprobación regenera A en rango 0 y calcula residuos después de T_app. Es la misma operación matemática en ambas compilaciones. Se mide aparte y queda incluida en el reloj externo, junto con liberación, salida CSV y cierre. No se genera una referencia secuencial adicional en el MPI candidato.')
h('Decisión y alcance')
p('Consolidamos este ejecutable como candidato operativo; los compare_*.c quedan como evidencia histórica. El programa no elige P automáticamente. Tampoco sustituye el estudio de rendimiento en el clúster.')
p('Trazabilidad: resultados/cierre_local_20260924/tests, build_tests.log y fuentes congeladas. Generación y medición en C; ejecución en Bash; análisis y documentación en Python. Desarrollo asistido por IA, con pruebas ejecutadas.')
save('Cholesky_Etapa_11_Programa_candidato.pdf',11)
page('Etapa 12: speedup del candidato')
h('¿Cuánto ganamos hasta obtener L?')
p('Medimos el programa elegido frente al secuencial autónomo contemporáneo, sin reutilizar tiempos anteriores. El objetivo es observar aceleración útil y eficiencia, no solamente comparar dos optimizaciones con igual P.')
eq(r'S_{app}(n,P)=\frac{\operatorname{mediana}(T_{app,seq})}{\operatorname{mediana}(T_{app,MPI,P})},\qquad E_{app}=S_{app}/P')
p('Protocolo: N=256,512,1024,2048; MPI P=1,2,3,4,6 y secuencial. Siete repeticiones por configuración, más una descartada; 168 observaciones medidas y 24 de preparación. Cada observación es un lanzamiento nuevo. Rotamos el orden de los seis métodos entre rondas; los tamaños siguen un orden fijo. No es una aleatorización completa.')
p('WSL local, Ryzen 5 2600, seis núcleos físicos y doce procesadores lógicos. MPI solicita un proceso por núcleo con afinidad; secuencial usa taskset CPU 0. GCC -O3, double, sin BLAS. Una sola sesión: no inferimos estabilidad entre días ni entre nodos.')
story.append(Image(str(DATA/'application_s.png'),width=500,height=160))
p('Puntos: medianas. Barras en tiempos: Q1-Q3 inclusivos. Los cuartiles describen dispersión, no intervalos de confianza. Las curvas de speedup son cocientes de medianas, sin incertidumbre inferencial calculada.')
h('Lectura de la figura')
p('S mayor que 1 significa que MPI reduce el tiempo frente a nuestro secuencial; E muestra la fracción del ideal lineal respecto de esa referencia. MPI con P=1 no tiene por qué coincidir con el secuencial: cambia almacenamiento y agrega coordinación y reunión.')
page('Resultados y decisión local')
table([['N','P','MPI ms','S app','E app']]+[[r['N'],r['P'],f"{1000*r['application_s']:.2f}",f"{r['application_s_speedup']:.2f}",f"{100*r['application_s_efficiency']:.1f}%"] for r in rs if r['method']!='seq'],[65,45,130,130,130])
p('Referencia secuencial (ms): '+ '; '.join(f"N={n}: {1000*S[n,'seq']['application_s']:.2f}" for n in (256,512,1024,2048))+'.')
best=min([r for r in rs if r['N']==2048 and r['method']!='seq'],key=lambda r:r['application_s'])
p(f"En N=2048, el menor tiempo MPI observado fue con P={best['P']}: {1000*best['application_s']:.2f} ms y S={best['application_s_speedup']:.2f}. Es el mínimo de esta muestra, no una regla automática para elegir procesos.")
p('El CSV también conserva T_MPI,1/T_MPI,P como escalabilidad interna. No la confundimos con aceleración frente al secuencial. La siguiente pregunta cambia el reloj: ¿esa ganancia sobrevive al arranque, comprobación y cierre?')
save('Cholesky_Etapa_12_Speedup_candidato.pdf',12)
page('Etapa 13: el comando completo')
h('¿El usuario termina antes?')
p('El ejecutable measure_command, escrito en C, mide con reloj monotónico desde antes de fork hasta que termina el comando hijo. Para MPI el hijo es mpirun; para el secuencial, taskset. La escritura del CSV del cronómetro queda fuera. El arranque de WSL y la cola de un planificador no se miden.')
eq(r'S_{ext}(n,P)=\frac{\operatorname{mediana}(T_{ext,seq})}{\operatorname{mediana}(T_{ext,MPI,P})}')
p('T_ext incluye lanzamiento, reserva, generación, factorización, reunión, regeneración para validar, residuos, salida CSV, liberación y cierre. No contiene impresión o escritura del factor. Las mismas 168 observaciones proporcionan ambos relojes: no hay que sumar medianas ni unir campañas.')
story.append(Image(str(DATA/'external_s.png'),width=500,height=160))
table([['N','Seq ext ms','MPI P6 ext ms','S ext P6']]+[[n,f"{1000*S[n,'seq']['external_s']:.2f}",f"{1000*S[n,'6']['external_s']:.2f}",f"{S[n,'6']['external_s_speedup']:.2f}"] for n in (256,512,1024,2048)],[70,145,145,140])
h('Qué podemos atribuir y qué no')
p('external - application - validation se calcula por ejecución y después se resume. No es tiempo puro de arranque ni tiempo puro de red: combina inicialización, barreras, reducciones de medición, cierre, liberación y salida. Aislar cada causa necesitaría otro experimento.')
page('Cierre de la investigación local')
h('Respuesta a la pregunta completa')
extbest=min([r for r in rs if r['N']==2048 and r['method']!='seq'],key=lambda r:r['external_s'])
p(f"Para N=2048, el menor tiempo externo MPI de la muestra aparece con P={extbest['P']}: {1000*extbest['external_s']:.2f} ms, frente a {1000*S[2048,'seq']['external_s']:.2f} ms secuenciales; S externo={extbest['external_s_speedup']:.2f}. El veredicto del reloj externo puede diferir del tiempo hasta obtener L.")
p('La validación se hace en rango 0 mientras los demás esperan una difusión del estado final. Su duración puede variar entre ejecuciones MPI y secuenciales, aunque el cálculo sea el mismo. Contención, esperas activas y condiciones del equipo son hipótesis; esta campaña no aísla sus aportes.')
h('Corrección y evidencia')
p(f"Se verificaron {info['observations']} lanzamientos de campaña sin fallo (incluidos los descartados para rendimiento). Residuo proyectado máximo: {info['max_projected_residual']:.3e}. El analizador exige tiempos finitos, salidas válidas, cantidad esperada de muestras y coherencia entre reloj externo y fases. Los 30 casos pequeños son adicionales.")
h('Qué queda decidido')
p('Conservamos la implementación 1D right-looking cíclica b=1 como candidata. La campaña no compara nuevos algoritmos y no justifica cambiarla por el menor tiempo aislado. Conservamos como resultados principales ambos relojes, speedup, eficiencia y dispersión. No afirmamos que seis procesos sean siempre mejores.')
h('Hasta dónde llegamos y qué dejamos abierto')
p('Cerramos el alcance local acordado: programa integrado, comprobación, campaña con 1-6 procesos y medición externa. No agotamos toda optimización imaginable. Se mantienen como extensiones: validar otras familias SPD, estudiar las esperas durante validación, Cholesky por bloques, OpenMP, 2D y entrada/salida real de matrices.')
p('En el clúster: compilar el mismo candidato, verificar afinidad y memoria con el administrador, aumentar N con pilotos seguros, repetir dentro de un nodo y entre nodos, y medir una referencia secuencial del mismo entorno. La cola se informa aparte. Ningún tamaño ni número de procesos local se extrapola automáticamente.')
h('Reproducibilidad y siguiente pregunta')
p('scripts/cierre_local.sh ejecuta; scripts/analizar_cierre.py analiza; resultados/cierre_local_20260924 conserva CSV, entorno y fuentes. ¿Cómo cambian las ganancias al crecer N y pasar de comunicación local a comunicación entre nodos? Esa será la siguiente etapa de investigación.')
save('Cholesky_Etapa_13_Tiempo_externo_y_cierre.pdf',13)
