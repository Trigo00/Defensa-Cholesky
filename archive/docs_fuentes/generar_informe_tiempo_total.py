"""Etapa 6: tiempo completo de entrada, factorizacion y reunion."""
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

DATA=ROOT/'desde_cero/resultados/tiempo_total_20260922'
OUT=ROOT/'output/pdf/Cholesky_Etapa_6_Tiempo_total_MPI.pdf'
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
    p('CHOLESKY / ETAPA 6 / EXPERIMENTO 7 / '+number,'small');p(title,'title')
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
validation=json.loads((DATA/'validacion.json').read_text())
def ms(r,field='total'):return fmt(float(r[field+'_median_s'])*1000,3)

page('01','¿La mejora se mantiene al mover la matriz?')
p('Los experimentos anteriores medían el kernel de factorización. Sin embargo, una aplicación puede comenzar con la matriz A completa en un proceso y necesitar que el factor L vuelva completo al mismo proceso. En ese caso, repartir y reunir los datos también forman parte del costo útil.')
h('Caso de uso que medimos')
table([['Fase','MPI','Secuencial'],['Entrada','El rango 0 empaqueta las columnas cíclicas y ejecuta MPI_Scatterv.','Copia A al arreglo que se sobrescribirá.'],['Factorización','Right con vector local o left distribuido.','Right-looking con vector contiguo.'],['Salida','MPI_Gatherv y desempaquetado del factor completo en rango 0.','El factor ya está completo en el arreglo local.']],[90,222,185])
h('Qué queda fuera')
p('La reserva de memoria, la generación de A, la comprobación del resultado y el arranque de los procesos MPI quedan fuera. El lanzamiento puede pagarse una vez si una aplicación mantiene trabajadores activos, o en cada problema si crea un nuevo trabajo; por eso debe estudiarse por separado.')
h('Tiempo total observado')
eq(r'T_{\mathrm{total}}=T_{\mathrm{entrada}}+T_{\mathrm{factor}}+T_{\mathrm{salida}}')
p('Cada proceso registra marcas consecutivas. Para reportar cada fase y el total tomamos el máximo entre procesos. Debido a que los máximos de las fases podrían pertenecer a rangos distintos, la suma de los máximos por fase no tiene que coincidir exactamente con el máximo total.')
p('Esta definición representa un flujo centralizado de entrada y salida. No representa aplicaciones donde la matriz ya nace distribuida o el factor continúa utilizándose de forma distribuida.','small')

page('02','Protocolo de la comparación completa')
table([['Decisión','Valor'],['Algoritmos','Right MPI cíclico con vector local; left MPI cíclico; right secuencial con vector.'],['Tamaños y procesos','n=64,128,256,512,1024; P=1,2,3,4.'],['Repeticiones','Un calentamiento y 12 mediciones por algoritmo y configuración. Las seis permutaciones del orden se repiten dos veces.'],['Entrada','La misma matriz SPD, generada en C con semilla 2026, comienza completa en el rango 0.'],['Salida','El factor se reúne completo en rango 0 y se compara con la referencia secuencial.'],['Entorno','WSL2, Ryzen 5 2600, Open MPI 5.0.10, GCC 15.2.0, -O3, double, sin BLAS.']],[115,382])
h('Comparación contemporánea')
p('La referencia secuencial se ejecuta dentro del mismo lanzamiento y ocupa todas las posiciones posibles del orden. Para cada n y P comparamos MPI con esa referencia contemporánea. No dividimos por tiempos de PDF anteriores.')
h('Dos preguntas distintas')
eq(r'S_{\mathrm{kernel}}=\frac{\widetilde T_{\mathrm{factor,seq}}}{\widetilde T_{\mathrm{factor,MPI}}},\qquad S_{\mathrm{total}}=\frac{\widetilde T_{\mathrm{total,seq}}}{\widetilde T_{\mathrm{total,MPI}}}',14)
p('La primera indica cuánto acelera Cholesky una vez repartidos los datos. La segunda decide si conviene el flujo completo descrito. Una optimización puede mejorar el kernel y aun perder cuando la matriz es pequeña.')
p('Las barras de los gráficos muestran Q1-Q3 de 12 repeticiones. Son medidas descriptivas de dispersión, no intervalos de confianza.','small')

page('03','Resultado: el cruce práctico se desplaza')
fig('tiempo_total.png',450,290)
p('Figura 1. Tiempo completo: entrada, factorización y salida. Cada panel usa su propia escala. La referencia secuencial se repite para cada P porque se mide dentro del mismo lanzamiento.','small')
tr=[['n','Mejor P≥2','Sec. (ms)','Right total (ms)','Aceleración']]
for n in [64,128,256,512,1024]:
    best=min((R[n,q,'right'] for q in [2,3,4]),key=lambda r:float(r['total_median_s']))
    tr.append([str(n),str(best['P']),ms(R[n,int(best['P']),'sequential']),ms(best),fmt(best['total_speedup'])])
table(tr,[43,75,111,154,114])
h('Qué cambia respecto del kernel')
p('<b>n=64:</b> la coordinación y las copias dominan.<br/><b>n=128:</b> la mejor configuración paralela apenas iguala al secuencial.<br/><b>n=256:</b> right con P=3 mejora solo 1,08x, por debajo del margen práctico de 10 % usado en la etapa 4.<br/><b>n=512 y n=1024:</b> la ventaja total ya es clara: 1,60x y 1,90x con P=3.')
p('En esta grilla, <b>512 es el primer tamaño con una mejora total clara</b>. Es una observación de esta campaña, no un umbral universal.')

page('04','Qué costo agregan la entrada y la salida')
fig('fases_1024.png',497,217)
p('Figura 2. Medianas de cada fase y del total para n=1024. Las líneas de fases no deben sumarse como si provinieran del mismo rango y repetición.','small')
h('Right con n=1024 y P=3')
r=R[1024,3,'right'];s=R[1024,3,'sequential'];l=R[1024,3,'left']
table([['Entrada','Factorización','Salida','Total'],[ms(r,'input')+' ms',ms(r,'factor')+' ms',ms(r,'gather')+' ms',ms(r)+' ms']],[124,124,124,125])
p('El kernel right mejora '+fmt(float(s['factor_median_s'])/float(r['factor_median_s']))+'x frente al secuencial. Al incluir entrada y salida, la aceleración queda en '+fmt(r['total_speedup'])+'x. Los movimientos de datos reducen la ganancia, pero no la eliminan en este tamaño.')
h('Right mantiene la ventaja frente a left')
p('Con n=1024 y P=3, left tarda '+ms(l)+' ms en total frente a '+ms(r)+' ms de right. Como ambos usan el mismo reparto y las mismas fases externas, la diferencia continúa concentrándose en la factorización: '+ms(l,'factor')+' ms para left y '+ms(r,'factor')+' ms para right.')
h('Una limitación visible')
p('La entrada y la salida permanecen alrededor de cinco a seis milisegundos cada una para n=1024 y no disminuyen al aumentar P en esta máquina. El rango 0 empaqueta y desempaqueta en forma secuencial; ese diseño se convertirá en cuello de botella al escalar.')
p('Una aplicación real podría evitar esas conversiones generando o leyendo directamente el formato distribuido, o conservar el factor distribuido. Eso cambiaría el caso de uso y debe medirse como otro experimento.','small')

page('05','Conclusión y siguiente etapa')
h('Decisión actual')
p('Right-looking MPI cíclico con vector local sigue siendo la variante elegida. Fue más rápido que left en el kernel y en el flujo completo. Con matrices pequeñas conviene la versión secuencial; para n=512 y n=1024, tres procesos dieron una mejora total clara en esta campaña.')
h('Qué afirmamos y qué no')
p('Afirmamos resultados sobre una entrada y salida centralizadas en WSL. No sabemos todavía cómo cambia el costo dentro de un nodo del clúster ni, especialmente, entre nodos. Tampoco medimos lectura desde archivo, escritura, lanzamiento del trabajo o varias factorizaciones consecutivas.')
h('Validación')
p('Se aceptaron '+str(validation['observations'])+' observaciones. El residuo relativo máximo fue 1,2131×10^-15 y la diferencia relativa máxima frente al factor secuencial fue 2,6578×10^-15. Las pruebas funcionales y los sanitizadores con P=4 terminaron correctamente; las huellas de las fuentes medidas coinciden.')
h('Siguiente experimento cuando tengamos el clúster')
p('Repetiremos right secuencial y right MPI con P=1,2,3,4 dentro de un nodo. Luego compararemos una asignación equivalente entre nodos, registrando nodos, procesos por nodo, afinidad, compilador y biblioteca MPI. Mediremos entrada, kernel, salida y total con el mismo criterio.')
p('Si la red hace dominar la comunicación, el siguiente cambio razonable será agrupar operaciones por bloques para reducir la frecuencia de mensajes y aprovechar BLAS. No conviene implementar esa complejidad antes de observar el problema en el clúster.')
table([['Archivo en desde_cero','Contenido'],['src/compare_mpi_total.c','Cronometra fases, reúne y valida.'],['scripts/comparar_tiempo_total.sh','Campaña completa reproducible.'],['scripts/analizar_tiempo_total.py','Estadísticas y gráficos por fase.'],['resultados/tiempo_total_20260922/','CSV, protocolo, afinidad, huellas y fuentes.']],[218,279])

def footer(c,doc):
    w,height=A4;c.setStrokeColor(HexColor('#CFDDE3'));c.line(48,height-36,w-48,height-36)
    c.setFont('Body',8);c.setFillColor(HexColor('#536675'))
    c.drawString(48,28,'HPC · Cholesky | MPI en C · Estadísticas en Python | 22/09/2026')
    c.drawRightString(w-48,28,str(doc.page))
OUT.parent.mkdir(parents=True,exist_ok=True)
SimpleDocTemplate(str(OUT),pagesize=A4,leftMargin=48,rightMargin=48,topMargin=49,bottomMargin=48,title='Cholesky, etapa 6: tiempo total MPI',author='Proyecto Cholesky HPC 2026').build(story,onFirstPage=footer,onLaterPages=footer)
print(OUT)
