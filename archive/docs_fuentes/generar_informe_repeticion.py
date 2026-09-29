"""Compare independent sessions without pooling observations or changing the candidate."""
from pathlib import Path
import sys,csv,json,hashlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader
base=ROOT/'desde_cero/resultados'
folders=[base/'cierre_local_20260924',base/'cierre_local_20260927']
reports=[json.loads((f/'analisis.json').read_text()) for f in folders]
maps=[{(r['N'],r['method']):r for r in a['summary']} for a in reports]
out=folders[1]
# Every frozen source, including protocol and Makefile, must be byte-identical.
checks=[]
for old in (folders[0]/'fuentes').rglob('*'):
 if old.is_file():
  rel=old.relative_to(folders[0]/'fuentes');new=folders[1]/'fuentes'/rel
  equal=old.read_bytes()==new.read_bytes();assert equal,rel
  checks.append({'file':rel.as_posix(),'sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'identical':equal})
(out/'comparacion_fuentes.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
rows=[]
for key,old in maps[0].items():
 new=maps[1][key]
 for clock in ('application_s','external_s'):
  rows.append(dict(N=key[0],method=key[1],clock=clock,old_s=old[clock],new_s=new[clock],change_pct=100*(new[clock]/old[clock]-1),old_speedup=old[clock+'_speedup'],new_speedup=new[clock+'_speedup'],new_efficiency=new[clock+'_efficiency']))
with (out/'comparacion_sesiones.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
fig,axs=plt.subplots(2,2,figsize=(9,6),layout='constrained')
for i,n in enumerate((1024,2048)):
 for j,clock in enumerate(('application_s','external_s')):
  ax=axs[i,j]
  for k,date in enumerate(('24/09','27/09')):
   rr=[maps[k][n,str(p)] for p in (1,2,3,4,6)]
   ax.plot([1,2,3,4,6],[r[clock+'_speedup'] for r in rr],'-o',label=date)
  ax.axhline(1,color='gray',ls='--');ax.set(title=f'N={n}: '+('hasta L' if j==0 else 'comando completo'),xlabel='Procesos',ylabel='Speedup útil',xticks=[1,2,3,4,6]);ax.grid(alpha=.2);ax.legend()
fig.savefig(out/'comparacion_sesiones.png',dpi=180);plt.close(fig)
styles=getSampleStyleSheet();styles['BodyText'].leading=13;styles['BodyText'].fontSize=10;story=[]
def p(t):story.extend([Paragraph(t,styles['BodyText']),Spacer(1,7)])
def h(t):story.append(Paragraph(t,styles['Heading2']))
def title(t):story.extend([Paragraph(t,styles['Title']),Spacer(1,9)])
def table(data,widths):
 t=Table([[Paragraph(str(v),styles['BodyText']) for v in row] for row in data],colWidths=widths)
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecf0')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),5)]));story.extend([t,Spacer(1,8)])
title('Etapa 14: repetir en otra sesión')
h('¿Se mantiene la conclusión local?')
p('El 24/09 el candidato logró S=1,83 hasta obtener L y S=1,16 para el comando completo en N=2048, P=6. La segunda ventaja era modesta. Repetimos el 27/09 para comprobar sensibilidad a otra sesión, sin buscar un resultado favorable ni modificar el algoritmo.')
p('Mismo código y script, fuentes congeladas idénticas byte por byte. N=256,512,1024,2048; secuencial autónomo y MPI P=1,2,3,4,6. Siete observaciones por configuración y una descartada: 192 lanzamientos, 168 medidos. Orden rotado por ronda y mismos dos relojes. Conservamos datos separados y calculamos cada speedup con el secuencial de su propia sesión.')
story.append(Image(str(out/'comparacion_sesiones.png'),width=490,height=327))
p('Cocientes de medianas por sesión, sin bandas de confianza. Los cuartiles de los tiempos están en resumen.csv de cada campaña. Dos sesiones permiten contrastar tendencias, pero no establecen estabilidad universal ni equivalen a 14 repeticiones bajo las mismas condiciones.')
table([['N, P=6','S app 24/09','S app 27/09','S ext 24/09','S ext 27/09']]+[[n,f"{maps[0][n,'6']['application_s_speedup']:.2f}",f"{maps[1][n,'6']['application_s_speedup']:.2f}",f"{maps[0][n,'6']['external_s_speedup']:.2f}",f"{maps[1][n,'6']['external_s_speedup']:.2f}"] for n in (256,512,1024,2048)],[80,105,105,105,105])
story.append(PageBreak());title('Interpretación y versión de referencia')
new=maps[1][2048,'6'];seq=maps[1][2048,'seq']
h('Resultado de la nueva sesión')
p(f"N=2048/P=6: hasta L, {seq['application_s']*1000:.2f} ms secuenciales frente a {new['application_s']*1000:.2f} ms MPI (S={new['application_s_speedup']:.2f}; eficiencia {100*new['application_s_efficiency']:.1f}%). Comando completo: {seq['external_s']*1000:.2f} frente a {new['external_s']*1000:.2f} ms (S={new['external_s_speedup']:.2f}; eficiencia {100*new['external_s_efficiency']:.1f}%).")
if new['external_s_speedup']>1:
 p('La mediana externa con seis procesos vuelve a mejorar frente al secuencial en N=2048. La dirección se repite, pero la magnitud debe citarse por sesión: no declaramos una aceleración fija ni un umbral universal.')
else:
 p('La ventaja externa de seis procesos NO se repite en N=2048. Conservamos ambos resultados: el 1,16 anterior era una observación de aquella sesión, no una ganancia robusta. Eso no implica un error numérico ni justifica retocar el algoritmo hasta obtener un número favorable.')
for n in (1024,2048):
 best=min([r for r in reports[1]['summary'] if r['N']==n and r['method']!='seq'],key=lambda r:r['external_s'])
 p(f"N={n}: el menor tiempo externo MPI observado en esta sesión fue con P={best['P']}, {1000*best['external_s']:.2f} ms (S={best['external_s_speedup']:.2f}). Elegir el mínimo entre configuraciones es descriptivo; no prueba que esa cantidad sea siempre la mejor.")
h('Corrección y límites')
p(f"No todas las configuraciones repiten su ventaja: N=2048/P=3 pasa de S externo={maps[0][2048,'3']['external_s_speedup']:.2f} a {maps[1][2048,'3']['external_s_speedup']:.2f}. Es un ejemplo de por qué una mejora pequeña en una sesión no basta para recomendar una cantidad de procesos.")
p(f"Las 192 ejecuciones de campaña pasaron validación; residuo proyectado máximo {reports[1]['max_projected_residual']:.3e}. También pasaron los 30 casos pequeños del programa y las pruebas numéricas previas. El análisis revisó fases, estados de salida, muestras y tiempos finitos. Matrices grandes: ocho proyecciones; pequeñas: además residuo completo.")
p('No aislamos frecuencia, temperatura, carga del sistema ni espera activa. No atribuimos las variaciones a una causa concreta. El reloj externo incluye validación y arranque/cierre; no mide solo comunicaciones. Todo ocurre en WSL local, sin comunicación entre nodos.')
h('Qué significa congelar el candidato')
p('Fijamos en Git una referencia identificable del programa que medimos. No significa dejar de trabajar ni prohibir correcciones. Podemos preparar defensa, documentación, scripts y configuración del clúster. Un cambio que afecte cálculo o medición crea una versión nueva y se valida antes de comparar. Los datos anteriores conservan sus fuentes originales.')
p('La referencia sigue siendo right-looking MPI 1D cíclico b=1, vector local y generación distribuida. Con esta repetición se completa el control local acordado. El paso siguiente es adaptar la ejecución a los recursos del clúster y repetir allí con referencias contemporáneas, tamaños mayores y separación entre uno y varios nodos.')
p('Trazabilidad: resultados/cierre_local_20260927, comparacion_sesiones.csv y comparacion_fuentes.json. C mide; Python analiza y documenta. Trabajo asistido por IA. No se descartan resultados desfavorables.')
def footer(c,d):c.setFont('Helvetica',8);c.drawString(45,25,'Cholesky | Etapa 14 | Repetición local | 27/09/2026');c.drawRightString(550,25,str(d.page))
pdf=ROOT/'output/pdf/Cholesky_Etapa_14_Repeticion_local.pdf'
SimpleDocTemplate(str(pdf),pagesize=A4,leftMargin=45,rightMargin=45,topMargin=40,bottomMargin=45).build(story,onFirstPage=footer,onLaterPages=footer)
assert len(PdfReader(pdf).pages)==2
print(pdf)
print('Identical frozen files:',len(checks))
