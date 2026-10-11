"""Estilo común y figuras explicativas; sin mediciones nuevas."""
import csv
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

COLORS = {'seq':'#263238','own':'#263238','lapack':'#00897b','p1':'#78909c',
          'p2':'#1e88e5','p3':'#2e7d32','p4':'#8e24aa','p6':'#e65100',
          'left':'#1e88e5','right':'#c2185b','right_buffered':'#00897b'}
MARKERS = {'seq':'o','own':'o','lapack':'s','p1':'v','p2':'^','p3':'o','p4':'s','p6':'D',
           'left':'^','right':'v','right_buffered':'o'}
LABELS = {'seq':'C secuencial','own':'C secuencial','lapack':'LAPACK · 1 hilo',
          'left':'Left-looking','right':'Right original','right_buffered':'Right con vector',
          **{f'p{p}':f'MPI · P={p}' for p in (1,2,3,4,6)}}

def configure():
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10.5,
        'axes.labelsize':10.5,'legend.fontsize':8.5,'axes.spines.top':False,
        'axes.spines.right':False,'axes.titleweight':'bold','axes.titlecolor':'#163b50',
        'axes.prop_cycle':plt.cycler(color=['#1e88e5','#e65100','#2e7d32','#8e24aa','#00897b','#c2185b']),
        'svg.hashsalt':'cholesky-20260928'})

def generate(root, figure_dir=None):
    figure_dir = figure_dir or root / "output/analisis/figures"
    figure_dir.mkdir(parents=True, exist_ok=True)
    configure()
    def save(fig,name):
        for ext in ('png','svg'):fig.savefig(figure_dir/f'{name}.{ext}',dpi=200)
        plt.close(fig)
    def box(ax,x,y,w,h,label,color='#e8eff4',size=10):
        ax.add_patch(Rectangle((x,y),w,h,facecolor=color,edgecolor='white',linewidth=1.8))
        ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=size,color='#17384b')
    fig,axs=plt.subplots(2,1,figsize=(9,4.5),layout='constrained')
    palette=['#bbdefb','#c8e6c9','#ffe0b2']
    for ax,cyclic in zip(axs,(False,True)):
        ax.set(xlim=(-.3,12.3),ylim=(-.7,2));ax.axis('off')
        ax.text(0,1.65,'Cíclico: propietario = j módulo P' if cyclic else 'Contiguo: intervalos de columnas',weight='bold')
        for j in range(12):
            p=j%3 if cyclic else j//4
            box(ax,j,.1,1,1,f'j={j}\nP{p}',palette[p],9.5)
        ax.text(0,-.45,'Ejemplo didáctico: N=12, P=3. Los colores identifican propietarios.',fontsize=9.5)
    save(fig,'13_distribucion_mpi')
    fig,ax=plt.subplots(figsize=(9,4.1),layout='constrained');ax.set(xlim=(0,12),ylim=(0,4.4));ax.axis('off')
    stages=[('Inicio MPI\ny barrera',2),('Reserva',1.4),('Generación',1.6),('Factorización\n+ comunicación',2.4),('Reunión',1.4),('Validación\ny cierre',3.2)]
    x=0
    for label,w in stages:box(ax,x,1.6,w,.85,label,'#dce9f0',9.5);x+=w
    for x,w,y,label,color in [(0,12,3.6,'external_s · comando completo','#c62828'),(2,6.8,2.8,'application_s · flujo en rango 0','#1565c0'),(5,2.4,.85,'factor_s (kernel)','#e65100')]:
        ax.plot([x,x+w],[y,y],color=color,lw=4);ax.text(x+w/2,y+.13,label,ha='center',fontsize=10.5,color=color,weight='bold')
    ax.text(0,.15,'Esquema del candidato MPI; anchos ilustrativos, sin proporción temporal.\nEl total_s del banco LAPACK incluye reserva, generación y factor; es otra frontera.',fontsize=9.5)
    save(fig,'14_fronteras_medicion')
    fig,axs=plt.subplots(1,2,figsize=(9,4.4),layout='constrained')
    for ax in axs:ax.set(xlim=(-.2,6.4),ylim=(-1.2,6.8));ax.axis('off')
    axs[0].set_title('Columna en almacenamiento por filas (row-major)',fontsize=11,weight='bold',pad=10)
    for i in range(5):
        for j in range(5):
            is_col = (j == 1)
            box(axs[0],j,4-i,1,.85,f'a[{i},{j}]' if is_col else '', '#ffe0b2' if is_col else '#eceff1', size=8)
    axs[0].annotate('Salto de fila: N doubles\n(64 B de línea de caché cargados,\nsolo 8 B usados = 12.5% eficiencia)',
                    xy=(1.5, 2.5), xytext=(2.6, 2.3),
                    arrowprops=dict(arrowstyle="->", color="#c62828", lw=1.5),
                    fontsize=8.5, color='#c62828', bbox=dict(boxstyle="round,pad=0.3", fc="#ffebee", ec="#ef9a9a"))
    axs[0].text(0,-.95,'Patrón no contiguo: continuos fallos de caché de capacidad/conflicto.',fontsize=8.5,style='italic',color='#455a64')
    axs[1].set_title('Copia en buffer contiguo (local_column)',fontsize=11,weight='bold')
    for j in range(5):
        box(axs[1],j,3.6,1,.85,f'v[{j}]', '#b2dfdb', size=9)
    axs[1].annotate('100% uso de línea de caché (64 B)\nPrefetcher secuencial activado',
                    xy=(2.5, 3.6), xytext=(0.5, 2.0),
                    arrowprops=dict(arrowstyle="->", color="#00796b", lw=1.5),
                    fontsize=8.5, color='#00796b', bbox=dict(boxstyle="round,pad=0.3", fc="#e0f2f1", ec="#80cbc4"))
    axs[1].text(0,0.5,'Copia acumulada: O(N²) doubles.\nTrabajo aritmético de factorización: O(N³).\nEl costo de la copia se amortiza con creces.',fontsize=9.5,linespacing=1.5,color='#263238')
    axs[1].text(0,-.95,'Esquema conceptual de jerarquía de memoria; no sustituye contadores PAPI.',fontsize=8.5,style='italic',color='#455a64')
    save(fig,'15_acceso_memoria')
    with (root/'data/processed/summary_all.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
    g=[r for r in rows if r['campaign']=='mpi_local_20260921' and r['cohort']=='.' and r['N']=='1024' and r['P']=='3' and r['metric']=='seconds']
    order=['contiguous:original','contiguous:local','cyclic:original','cyclic:local']
    g=sorted(g,key=lambda r:order.index(r['method']));assert len(g)==4
    labels=['Contiguo · original','Contiguo · vector local','Cíclico · original','Cíclico · vector local']
    palette_local=['#78909c','#1e88e5','#d81b60','#00897b']
    fig,ax=plt.subplots(figsize=(9,4.2),layout='constrained')
    for i,r in enumerate(g):
        q1,m,q3=[float(r[k])*1000 for k in ('q1','median','q3')]
        ax.errorbar(m,i,xerr=[[m-q1],[q3-m]],fmt='o',capsize=5,color=palette_local[i],ms=8,lw=1.8)
        ax.text(q3+1.5,i,f'{m:.2f} ms',va='center',fontsize=9.5,weight='bold',color=palette_local[i])
    ax.set(yticks=range(4),yticklabels=labels,xlabel='Factorización (ms) · mediana y Q1-Q3',xlim=(0,96),title='El vector local cambia la comparación entre repartos')
    ax.invert_yaxis();ax.grid(axis='x',alpha=.15)
    save(fig,'16_variantes_mpi_local')

