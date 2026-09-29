"""Etapas 17 y 18: auditoría y estadísticas desde paquetes originales, sin ejecutar binarios."""
from pathlib import Path
import csv,io,json,re,math,hashlib,tarfile,statistics as st,sys
from xml.sax.saxutils import escape
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,PageBreak,Image,Table,TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from pypdf import PdfReader
ED=ROOT/'desde_cero/resultados/escalabilidad_cluster_20260928'
LD=ROOT/'desde_cero/resultados/lapack_cluster_20260928'
def archive(folder,name):
    a=folder/(name+'.tar.gz')
    with tarfile.open(a) as t:
        mm=t.getmembers();assert len(mm)==len({m.name for m in mm})
        fs={m.name:t.extractfile(m).read() for m in mm if m.isfile()}
    return fs,hashlib.sha256(a.read_bytes()).hexdigest()
ef,eh=archive(ED,'campana_escalabilidad_20260928');ep='campana_escalabilidad_20260928/'
lf,lh=archive(LD,'campana_lapack_cluster_20260928');lp='campana_lapack_cluster_20260928/'
def csvread(b):return list(csv.DictReader(io.StringIO(b.decode('utf-8-sig'))))
def csvout(d,name,rr):
    with (d/name).open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
def valid_numbers(r):assert all(math.isfinite(v) for v in r.values())
manifest=[]
for line in ef[ep+'provenance/SHA256_PROVENANCE.txt'].decode().splitlines():
    expected,name=line.split(None,1);assert hashlib.sha256(ef[name]).hexdigest()==expected
    manifest.append(name)
source_checks=[]
for name,b in ef.items():
    if name.endswith(('.c','.h')) and not name.endswith('measure_command.c'):
        assert b==(ROOT/'desde_cero/resultados/cluster_exploratorio_20260928/fuentes'/Path(name).name).read_bytes()
        source_checks.append(Path(name).name)
assert len(source_checks)==5
er=[];methods=['seq','p1','p2','p3','p4','p6'];sizes=[512,1024,2048,4096]
for name,b in ef.items():
    if not name.endswith('_internal.csv'):continue
    m=re.fullmatch(r'(warmup|rep([1-7]))_n(\d+)_(seq|p[12346])_internal.csv',Path(name).name);assert m,name
    tag,rep,n,method=m.groups();raw=csvread(b);assert len(raw)==1
    r={k:float(v) for k,v in raw[0].items()};valid_numbers(r)
    stem=name[:-len('_internal.csv')]
    ext=csvread(ef[stem+'_external.csv']);assert len(ext)==1
    r.update({k:float(v) for k,v in ext[0].items()});valid_numbers(r)
    assert int(n)==r['N'] and r['P']==(1 if method=='seq' else int(method[1:]))
    assert r['exit_code']==0 and r['valid']==1 and 0<=r['projected_residual']<=1e-12 and r['exact_residual']==-1
    assert all(v>=0 for k,v in r.items() if k.endswith('_s'))
    assert abs(sum(r[k] for k in ['allocation_s','generation_s','factor_s','gather_s'])-r['application_s'])<max(1e-11,r['application_s']*1e-10)
    r['other_external_s']=r['external_s']-r['application_s']-r['validation_s']
    assert r['other_external_s']>=0 and r['max_local_s']+1e-12>=r['application_s']
    assert ef[stem+'.err']==b''
    er.append(dict(original_file=name,round=int(rep or 0),method=method,**r))
assert len(er)==192
assert sum(n.endswith('_external.csv') for n in ef)==192
assert sum(n.endswith('.err') for n in ef)==192
for n in sizes:
    for method in methods:assert sorted(r['round'] for r in er if r['N']==n and r['method']==method)==list(range(8))
eu=[r for r in er if r['round']>0]
csvout(ED,'observaciones.csv',sorted(eu,key=lambda r:(r['round'],r['N'],r['method'])))
csvout(ED,'warmups.csv',[r for r in er if r['round']==0])
def summ(rows,keys,metrics):
    out=[]
    groups=sorted({tuple(r[k] for k in keys) for r in rows})
    for group in groups:
        selected=[r for r in rows if tuple(r[k] for k in keys)==group]
        for metric in metrics:
            vals=[r[metric] for r in selected];q1,_,q3=st.quantiles(vals,n=4,method='inclusive')
            out.append(dict(zip(keys,group),metric=metric,count=len(vals),q1= q1,median=st.median(vals),q3=q3,min=min(vals),max=max(vals)))
    return out
es=summ(eu,['N','method'],['application_s','external_s','factor_s','generation_s','gather_s','validation_s','other_external_s'])
E={(int(r['N']),r['method'],r['metric']):r for r in es}
for r in es:
    r['ratio_vs_seq']=E[int(r['N']),'seq',r['metric']]['median']/r['median']
    r['efficiency_pct']=100*r['ratio_vs_seq']/(1 if r['method']=='seq' else int(r['method'][1:]))
csvout(ED,'resumen.csv',es)
def delta(fs,prefix):
    a={k:int(v) for k,v in (s.split() for s in fs[prefix+'cpu_stat_antes.txt'].decode().splitlines())}
    b={k:int(v) for k,v in (s.split() for s in fs[prefix+'cpu_stat_despues.txt'].decode().splitlines())}
    return {k:b[k]-v for k,v in a.items()}
edelta=delta(ef,ep)
ea=dict(files=len(ef),archive_sha256=eh,verified_provenance_hashes=len(manifest),global_measurement_manifest=False,
        measured=len(eu),warmups=24,all_exit_codes_zero=True,all_valid=True,empty_err_files=192,
        empty_build_logs=all(not b for n,b in ef.items() if n.endswith('.log')),
        max_projected_residual=max(r['projected_residual'] for r in er),same_candidate_sources=source_checks,cpu_stat_delta=edelta,
        script_in_archive=False,ordering_evidence='Nombres identifican rondas, pero no posiciones; script no archivado.')
(ED/'auditoria.json').write_text(json.dumps(ea,ensure_ascii=False,indent=2),encoding='utf-8')

lr=[]
for n in [2048,4096]:
    rr=csvread(lf[lp+f'n{n}.csv']);assert len(rr)==12
    for raw in rr:
        r={k:float(v) if k!='method' else v for k,v in raw.items()}
        valid_numbers({k:v for k,v in r.items() if k!='method'})
        assert r['N']==n and 0<=r['projected_residual']<=1e-12 and 0<=r['factor_difference']<=1e-12
        assert all(v>=0 for k,v in r.items() if k.endswith('_s'))
        assert abs(r['allocation_s']+r['generation_s']+r['factor_s']-r['total_s'])<max(1e-11,r['total_s']*1e-10)
        expected='own' if (int(r['order'])-1+int(r['repetition'])-1)%2==0 else 'lapack'
        assert r['method']==expected
        lr.append(dict(original_file=f'n{n}.csv',**r))
    for method in ['own','lapack']:assert sorted(int(r['repetition']) for r in lr if r['N']==n and r['method']==method)==list(range(1,7))
    assert lf[lp+f'n{n}.err'].decode().startswith('OpenBLAS threads=1 config=OpenBLAS 0.3.34')
assert 'LAPACK tests: PASS' in lf[lp+'compare_lapack_cluster_test.log'].decode()
hashes=re.findall(r'^([0-9a-f]{64})  (\S+)$',lf[lp+'entorno.txt'].decode(),re.M)
assert len(hashes)==4
for h,name in hashes:assert hashlib.sha256(lf[lp+name]).hexdigest()==h
for name in ['cholesky.c','cholesky.h']:assert lf[lp+name]==ef[ep+'provenance/'+name]
ls=summ(lr,['N','method'],['factor_s','total_s','generation_s'])
L={(int(r['N']),r['method'],r['metric']):r for r in ls}
for r in ls:r['ratio_own_over_method']=L[int(r['N']),'own',r['metric']]['median']/r['median']
csvout(LD,'observaciones.csv',lr);csvout(LD,'resumen.csv',ls)
control=csvread(lf[lp+'lapack_control_n512.log'].split(b'\n',1)[1]);assert len(control)==12
csvout(LD,'control_n512.csv',control)
la=dict(files=len(lf),archive_sha256=lh,verified_environment_hashes=len(hashes),global_measurement_manifest=False,
        measured_main=24,control_rows=12,main_repetitions_per_method=6,code_warmups_per_method_per_size=1,
        code_warmups_exported=False,threads=1,library='OpenBLAS 0.3.34 pthreads; LAPACKE_dpotrf_work',
        build_warning=lf[lp+'build_compare_lapack_cluster.log'].decode(errors='replace'),test_pass=True,
        max_projected_residual=max(r['projected_residual'] for r in lr),max_factor_difference=max(r['factor_difference'] for r in lr),
        exit_codes_archived=False,affinity_record_archived=False)
(LD/'auditoria.json').write_text(json.dumps(la,ensure_ascii=False,indent=2),encoding='utf-8')

plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
palette=['#187d9d','#c77931','#27865d','#895aa4']
for metric,filename in [('application_s','aplicacion.png'),('external_s','externo.png')]:
    fig,axs=plt.subplots(1,2,figsize=(10,3.4),layout='constrained')
    for n,c in zip(sizes,palette):
        rr=[E[n,m,metric] for m in methods[1:]];ps=[1,2,3,4,6]
        axs[0].errorbar(ps,[r['median'] for r in rr],yerr=[[r['median']-r['q1'] for r in rr],[r['q3']-r['median'] for r in rr]],color=c,marker='o',capsize=3,label=f'N={n}')
        axs[1].plot(ps,[r['ratio_vs_seq'] for r in rr],'-o',color=c,label=f'N={n}')
    axs[0].set(yscale='log',ylabel='Mediana y Q1-Q3 (s, log)',xlabel='Procesos MPI',xticks=ps)
    axs[1].axhline(1,color='gray',ls='--');axs[1].set(ylabel='Speedup frente a SEQ',xlabel='Procesos MPI',xticks=ps)
    for a in axs:a.grid(alpha=.2);a.legend(fontsize=8)
    fig.savefig(ED/filename,dpi=180);plt.close(fig)
fig,ax=plt.subplots(figsize=(10,3.3),layout='constrained');labels=[];components=[[],[],[]]
for n in sizes:
    for method in ['seq','p6']:
        rr=[r for r in eu if r['N']==n and r['method']==method];labels.append(f'{n}\n{method.upper()}')
        for vals,k in zip(components,['application_s','validation_s','other_external_s']):vals.append(st.mean(r[k]/r['external_s']*100 for r in rr))
bottom=[0]*8
for vals,label,c in zip(components,['Aplicación','Validación','Resto externo'],['#187d9d','#87bb9c','#c77931']):
    ax.bar(labels,vals,bottom=bottom,label=label,color=c);bottom=[a+b for a,b in zip(bottom,vals)]
ax.set(ylabel='Media de fracciones por ejecución (%)',ylim=(0,100));ax.legend(loc='upper center',bbox_to_anchor=(.5,1.2),ncol=3,fontsize=8)
fig.savefig(ED/'composicion_externa.png',dpi=180);plt.close(fig)
fig,axs=plt.subplots(1,2,figsize=(10,3.4),layout='constrained')
for a,metric in zip(axs,['factor_s','total_s']):
    for off,method,c in [(-.18,'own','#187d9d'),(.18,'lapack','#c77931')]:
        rr=[L[n,method,metric] for n in [2048,4096]]
        a.bar([i+off for i in range(2)],[r['median'] for r in rr],width=.34,color=c,label=method)
        a.errorbar([i+off for i in range(2)],[r['median'] for r in rr],yerr=[[r['median']-r['q1'] for r in rr],[r['q3']-r['median'] for r in rr]],fmt='none',color='black',capsize=3)
    a.set(yscale='log',xticks=[0,1],xticklabels=['2048','4096'],xlabel='N',ylabel='Tiempo (s, log)',title='Factorización' if metric=='factor_s' else 'Reserva + generación + factor');a.legend();a.grid(axis='y',alpha=.2)
fig.savefig(LD/'lapack.png',dpi=180);plt.close(fig)

styles=getSampleStyleSheet();styles['BodyText'].fontSize=10;styles['BodyText'].leading=14
styles['Title'].fontSize=21;styles['Title'].leading=25;styles['Title'].textColor=colors.HexColor('#174b60')
class Report:
    def __init__(self,d):self.d=d;self.story=[];self.md=[]
    def page(self,t):
        if self.story:self.story.append(PageBreak())
        self.story.extend([Paragraph(escape(t),styles['Title']),Spacer(1,10)]);self.md.append('\n# '+t+'\n')
    def h(self,t):self.story.append(Paragraph(escape(t),styles['Heading2']));self.md.append('\n## '+t+'\n')
    def p(self,t):self.story.extend([Paragraph(escape(t),styles['BodyText']),Spacer(1,8)]);self.md.append(t+'\n')
    def table(self,rr,widths):
        t=Table([[Paragraph(escape(str(v)),styles['BodyText']) for v in r] for r in rr],colWidths=widths,repeatRows=1)
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#dcecf0')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),6)]));self.story.extend([t,Spacer(1,8)])
        self.md.extend(['| '+' | '.join(map(str,rr[0]))+' |','| '+' | '.join(['---']*len(rr[0]))+' |']);self.md.extend('| '+' | '.join(map(str,r))+' |' for r in rr[1:]);self.md.append('')
    def chart(self,name,height):self.story.extend([Image(str(self.d/name),width=500,height=height),Spacer(1,6)]);self.md.append(f'![{name}]({name})\n')
    def save(self,name,stage,pages):
        (self.d/'informe.md').write_text('\n'.join(self.md),encoding='utf-8')
        pdf=ROOT/'output/pdf'/name
        def footer(c,d):c.setFont('Helvetica',8);c.drawString(45,25,f'Cholesky | Etapa {stage} | Clúster | 28/09/2026');c.drawRightString(550,25,str(d.page))
        SimpleDocTemplate(str(pdf),pagesize=A4,leftMargin=45,rightMargin=45,topMargin=36,bottomMargin=43).build(self.story,onFirstPage=footer,onLaterPages=footer)
        assert len(PdfReader(pdf).pages)==pages,(name,len(PdfReader(pdf).pages))
        return str(pdf)

R=Report(ED)
R.page('Etapa 17: escalabilidad y comando completo')
R.p('Pregunta: cuando el trabajo aumenta, ¿cómo cambia el rendimiento al pasar de uno a seis procesos y cuánto de la mejora sobrevive al medir el comando completo? Campaña del 28/09/2026, posterior al cruce formal. Análisis desde el paquete original, sin incorporar pilotos ni muestras de otras sesiones.')
R.h('Protocolo y evidencia')
R.table([['Elemento','Verificación'],['Grilla','N=512,1024,2048,4096; SEQ y MPI P=1,2,3,4,6.'],['Muestras','192 lanzamientos: 24 warmups y 168 útiles. Siete útiles por configuración. Cada interno tiene su externo y archivo .err.'],['Integridad y código',f'{len(ef)} archivos; {len(manifest)} hashes de provenance coinciden. Las cinco fuentes candidatas coinciden con etapas previas. No hay manifiesto global de las mediciones.'],['Validez','192 valid=1 y exit_code=0; residuos aceptables; fases coherentes; errores y logs de compilación vacíos.'],['Entorno','EPYC 7B12, GCC 13.3, Open MPI 4.1.6; cuota 6 CPUs y 24 GiB. Entorno fechado 16:40:52 UTC.']],[135,365])
R.h('Dos relojes del mismo lanzamiento')
R.p('application_s mide desde reserva hasta L completo en rango 0, con generación, factor y reunión. external_s proviene de measure_command.c: reloj monotónico antes de fork hasta waitpid. Incluye arranque del comando, MPI, validación, salida, liberación y cierre; excluye la escritura del CSV del cronómetro. El tiempo de cola o inicio del servicio no pertenece a este reloj.')
R.p('Se verificó external_s >= application_s + validation_s. El resto se calcula por observación antes de resumirlo; no equivale a tiempo puro de arranque. Medianas y cuartiles inclusivos usan solo las siete rondas útiles. Q1-Q3 describen dispersión, no intervalos de confianza.')
R.p('Los nombres de rondas están corregidos. El paquete no incluye el script de lanzamiento ni registros de posición temporal por ejecución: la rotación y la afinidad secuencial no pueden auditarse desde esos nombres. El entorno sí contiene un diagnóstico de binding P6, todos en el socket 0. Esta limitación no se confunde con un fallo numérico.')

R.page('Ganancia hasta obtener L')
R.chart('aplicacion.png',182)
R.p('Figura 1. Tiempo de aplicación MPI y cociente mediana(SEQ)/mediana(MPI). Cada N usa su propio secuencial contemporáneo. P1 es la ruta MPI, no una copia del secuencial autónomo.')
R.table([['N','SEQ s','P mínimo','MPI s','S','E %'],*[[n,f"{E[n,'seq','application_s']['median']:.6f}",min(methods[1:],key=lambda m:E[n,m,'application_s']['median'])[1:],f"{min(E[n,m,'application_s']['median'] for m in methods[1:]):.6f}",f"{max(E[n,m,'application_s']['ratio_vs_seq'] for m in methods[1:]):.2f}",f"{E[n,min(methods[1:],key=lambda m:E[n,m,'application_s']['median']),'application_s']['efficiency_pct']:.1f}"] for n in sizes]],[50,105,75,105,80,85])
R.h('Interpretación')
R.p('La curva no es monótona: utilizar más procesos no garantiza terminar antes. El mínimo entre configuraciones es descriptivo y requiere contexto; la eficiencia S/P no es utilización de CPU. Un valor cercano o superior al ideal lineal tampoco identifica por sí solo una causa como caché o balance.')
R.p('En resumen.csv quedan los 24 grupos con sus medianas, cuartiles y cocientes, para ambos relojes y las fases. La grilla alcanza seis procesos bajo cuota; no permite extrapolar a 24 o 96 procesos ni a varios nodos.')
R.h('Pregunta siguiente')
R.p('¿El mínimo del tiempo interno sigue siendo útil para quien espera que termine el comando? La validación secuencial y el costo de lanzar MPI pueden cambiar la respuesta, especialmente en los tamaños menores.')

R.page('Cuánto sobrevive en el reloj externo')
R.chart('externo.png',182)
R.p('Figura 2. Tiempo del comando y speedup externo. Las barras representan Q1-Q3 del tiempo; no se transfieren las ganancias del reloj interno al externo.')
R.table([['N','SEQ ext s','P mínimo','MPI ext s','S externo'],*[[n,f"{E[n,'seq','external_s']['median']:.4f}",min(methods[1:],key=lambda m:E[n,m,'external_s']['median'])[1:],f"{min(E[n,m,'external_s']['median'] for m in methods[1:]):.4f}",f"{max(E[n,m,'external_s']['ratio_vs_seq'] for m in methods[1:]):.2f}"] for n in sizes]],[60,125,80,125,110])
R.h('Una comparación explícita con P=6')
R.table([['N','S aplicación','S externo','E externa %'],*[[n,f"{E[n,'p6','application_s']['ratio_vs_seq']:.2f}",f"{E[n,'p6','external_s']['ratio_vs_seq']:.2f}",f"{E[n,'p6','external_s']['efficiency_pct']:.1f}"] for n in sizes]],[80,140,140,140])
R.p('S externo mayor que uno indica que el comando terminó antes por mediana. Un speedup externo menor no contradice la aceleración del kernel: mide una tarea más amplia. El primer tamaño de esta grilla que mejora no es un umbral universal ni necesariamente el mismo que el cruce N=192 de application_s.')

R.page('Costos del flujo y conclusión de escalabilidad')
R.chart('composicion_externa.png',165)
R.p('Figura 3. Media de las fracciones calculadas por lanzamiento; cada barra suma 100%. El resto externo combina inicialización, coordinación, cierre y otros costos. No es comunicación pura ni se obtiene restando medianas.')
R.h('Cuota observada')
R.p(f"cpu.stat cambia en {edelta['nr_periods']} períodos, {edelta['nr_throttled']} con throttling adicional y {edelta['throttled_usec']/1e6:.6f} s del contador throttled_usec. Las lecturas rodean toda la campaña y procesos auxiliares: no asignan ese costo a una configuración ni autorizan a restarlo de sus tiempos.")
R.h('Respuesta experimental')
for n in [2048,4096]:
    a=E[n,'p6','application_s'];b=E[n,'p6','external_s']
    R.p(f"N={n}/P6: S interno={a['ratio_vs_seq']:.2f}; S externo={b['ratio_vs_seq']:.2f}. La comparación mide beneficio frente al programa secuencial propio en esta sesión. La validación permanece fuera del reloj interno y dentro del externo.")
R.p('La campaña ya permite distinguir paralelismo del algoritmo y beneficio de extremo a extremo. No hace falta ampliar recursos para responder la pregunta planteada. Una repetición selectiva puede reforzar estabilidad, pero no es necesario investigar cada anomalía para cerrar un trabajo universitario.')
R.p('Archivos: observaciones.csv, warmups.csv, resumen.csv, auditoria.json y el paquete intacto. Los hashes calculados al recibir el archivo permiten identificar esta copia; no reemplazan un manifiesto de mediciones que no se archivó. La siguiente etapa compara el secuencial propio con una biblioteca optimizada en un banco aparte.')
pdf17=R.save('Cholesky_Etapa_17_Escalabilidad_cluster.pdf',17,4)

R=Report(LD)
R.page('Etapa 18: referencia LAPACK en el clúster')
R.p('Pregunta: ¿cuánto margen de rendimiento local queda frente a una biblioteca numérica optimizada? Se comparan el kernel secuencial propio y LAPACKE_dpotrf_work, enlazado con OpenBLAS 0.3.34, dentro del mismo ejecutable y con la misma matriz. Es una comparación local de implementaciones; no es ScaLAPACK ni una prueba MPI de la biblioteca.')
R.h('Diseño comprobado en el código archivado')
R.table([['Aspecto','Implementación'],['Tamaños principales','N=2048 y 4096; seis repeticiones por método y tamaño: 24 filas. Control N=512: otras 12 filas, separado.'],['Orden','Alternancia own/lapack y lapack/own; tres posiciones iniciales para cada método. Una ronda inicial por método sin exportar.'],['Hilos','openblas_set_num_threads(1) y comprobación por API. Los logs informan threads=1. OpenBLAS pthreads, no OpenMP añadido al candidato.'],['Entrada y salida','Matriz SPD con semilla 2026. Mismo generador; factor triangular inferior interpretado en row-major.'],['Validación','Ocho proyecciones, comparación con factor propio de referencia y pruebas pequeñas con residuo completo.']],[130,370])
R.h('Qué mide cada campo')
R.p('factor_s mide únicamente la llamada al kernel. total_s incluye reserva del arreglo y workspace, generación y factorización. Excluye preparar la matriz original/referencia del banco, validación y liberación. No existe aquí un reloj externo. Cada tamaño se ejecuta en un proceso con repeticiones internas, a diferencia de los lanzamientos nuevos de la campaña MPI.')
R.p('LAPACK recibe la matriz simétrica como column-major y triángulo U: ese almacenamiento representa L en row-major. La variante _work evita la conversión row-major y el chequeo opcional de NaN de la interfaz. Se verifica un factor conocido en el test. La comparación conserva el mismo arreglo lógico sin cobrar una transposición adicional.')

R.page('Resultados: kernel y flujo completo del banco')
R.chart('lapack.png',180)
R.p('Figura 1. Medianas y Q1-Q3 inclusivos, seis muestras por método. Escala logarítmica. El total se resume directamente, sin sumar medianas de fases. La mejora es own/LAPACK dentro de este banco.')
R.table([['N','Reloj','Propio s','LAPACK s','Cociente'],*[[n,'Factor' if k=='factor_s' else 'Total',f"{L[n,'own',k]['median']:.6f}",f"{L[n,'lapack',k]['median']:.6f}",f"{L[n,'lapack',k]['ratio_own_over_method']:.2f}"] for n in [2048,4096] for k in ['factor_s','total_s']]],[60,80,120,120,120])
R.h('Qué responde la comparación')
R.p('La biblioteca reduce ampliamente el tiempo incluso con un único hilo. La mejora del total es menor que la del kernel porque la generación permanece en el flujo. Esto demuestra margen de optimización local del candidato; no demuestra que agregar procesos pueda alcanzar ese margen ni aísla qué parte corresponde a cada optimización de la biblioteca.')
R.p('Los residuos y diferencias de factor pasan el criterio 1e-12 en las 24 filas. La diferencia normalizada máxima entre factores es aproximadamente 6,595e-15: resultados numéricamente consistentes no requieren igualdad bit a bit. Los tests pequeños figuran PASS.')

R.page('Auditoría y límites de la referencia')
R.h('Lo que contiene el paquete')
R.p('Doce archivos: dos CSV principales, dos salidas .err, código C, headers, ejecutable, logs de prueba/compilación y entorno. Se verificaron los cuatro hashes de fuentes/ejecutable registrados en entorno.txt. No hay un manifiesto original que cubra todos los CSV; se conserva el tar íntegro y su SHA-256 de recepción.')
R.p('Los archivos .err contienen el mensaje informativo de OpenBLAS threads=1, no un error de cálculo. El log de compilación contiene una advertencia -Wpedantic sobre _Float16 en openblas_config.h. Debe conservarse como advertencia de un encabezado de la biblioteca; no equivale a fallo del test ni autoriza a decir que compiló sin warnings.')
R.p('El código acumula el estado de fallo y lo devuelve al finalizar. Las filas no incluyen valid ni el código de salida y el paquete no registra ese estado del shell. Las comprobaciones numéricas exportadas son satisfactorias y el log de tests dice PASS, pero no se inventa un exit_code para las corridas principales.')
R.h('Afinidad y condiciones')
R.p('El límite de un hilo está comprobado por código y logs. El paquete LAPACK no conserva el comando de ejecución ni un registro de afinidad CPU: no se afirma que corriera fijado a CPU0. El banco alterna ambos métodos en el mismo proceso, lo que fortalece su comparación interna. El entorno registra EPYC 7B12 y bibliotecas conda-forge, fechado 17:25:42 UTC.')
R.h('Comparación con la etapa MPI')
R.p('No se construye un speedup formal LAPACK/MPI mezclando estas campañas. Tienen distintos ejecutables, tratamiento de calentamiento, validaciones y sesiones de medición. La lectura conjunta sí es válida: nuestro MPI acelera una base propia y la biblioteca muestra que esa base conserva un margen local grande. Acelerar una implementación no demuestra que sea competitiva con una biblioteca especializada.')
R.p('El control N=512 se conserva separado en control_n512.csv. No se suma a la muestra principal ni se usa como repetición independiente. Los seis resultados por método provienen del mismo lanzamiento; no son seis sesiones del clúster.')

R.page('Conclusión integrada y cierre universitario')
R.h('Tres respuestas complementarias')
R.p('La Etapa 16 localizó el cruce de application_s: primera mejora clara ensayada en N=192/P3. La Etapa 17 midió cómo cambian las ganancias con N y P y cuánto sobrevive al comando completo. Esta Etapa 18 muestra el margen del kernel propio frente a LAPACK/OpenBLAS con un hilo. Cada resultado conserva su denominador y su reloj.')
for n in [2048,4096]:
    R.p(f"N={n}: LAPACK mejora el kernel propio {L[n,'lapack','factor_s']['ratio_own_over_method']:.2f} veces y el flujo interno del banco {L[n,'lapack','total_s']['ratio_own_over_method']:.2f} veces. Es evidencia de rendimiento local, sin MPI en la biblioteca.")
R.h('Mi recomendación')
R.p('Estas campañas cubren las preguntas centrales de un proyecto universitario: corrección, cruce, escalabilidad, costo completo y referencia optimizada. No abriría ahora una nueva implementación con OpenMP, bloques o distribución 2D ni una campaña hasta 96 cores. Priorizaría redactar la conclusión y preparar la defensa.')
R.p('Si se desea una confirmación adicional, bastaría una sesión corta con SEQ y una o dos configuraciones MPI decisivas para N=2048/4096. Es una mejora de robustez, no una obligación de repetir todo. Guardar el script y la afinidad real solucionaría las principales carencias de trazabilidad detectadas.')
R.h('Límite que debe quedar explícito')
R.p('La referencia aportada es LAPACK, no ScaLAPACK. Si la consigna docente exige explícitamente una biblioteca distribuida, esa parte sigue pendiente y requiere un experimento distinto. Si pide una referencia numérica optimizada, esta campaña ya aporta evidencia pertinente.')
R.p('Conclusión defendible: el diseño MPI propio puede reducir el tiempo respecto de su versión secuencial cuando hay suficiente trabajo, pero los costos externos reducen la ganancia percibida y más procesos no siempre convienen. La comparación con LAPACK muestra que la eficiencia del kernel local importa tanto como repartir el trabajo. Estas observaciones se limitan a las matrices, grillas y entorno medidos.')
R.p('Reproducción de ambas etapas: desde_cero/docs/generar_informes_escalabilidad_lapack_cluster.py. Paquetes originales preservados; CSV derivados y auditorías junto a cada campaña. Análisis y documentación con asistencia de IA.')
pdf18=R.save('Cholesky_Etapa_18_LAPACK_cluster.pdf',18,4)
print(json.dumps(dict(pdfs=[pdf17,pdf18],escalabilidad=ea,lapack=la,p6=[r for r in es if r['method']=='p6' and r['metric'] in ['application_s','external_s']],lapack_ratios=[r for r in ls if r['method']=='lapack']),ensure_ascii=False,indent=2))
