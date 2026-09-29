"""Estadisticas y figuras de mediciones C; no calcula factorizaciones."""
import argparse
from collections import defaultdict
import csv
import json
import math
import os
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
# Dependencias locales para graficos; tambien funciona con matplotlib instalado.
if os.name=='nt' and (ROOT/'tmp/pdf_deps').exists():
    sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('directory',type=Path)
    args=parser.parse_args()
    groups=defaultdict(list)
    for file in args.directory.glob('n[0-9]*.csv'):
        with file.open(newline='') as stream:
            for row in csv.DictReader(stream):
                groups[(int(row['N']),row['variant'])].append(row)
    if not groups: raise ValueError('No hay datos')
    sizes=sorted({n for n,_ in groups})
    stats={}
    for n in sizes:
        for variant in ('left','right'):
            rows=groups[(n,variant)]
            if len(rows)!=7 or {int(r['repetition']) for r in rows}!=set(range(1,8)):
                raise ValueError(f'Repeticiones incompletas: {n}, {variant}')
            if {int(r['seed']) for r in rows}!={2026}:
                raise ValueError('Semillas inconsistentes')
            times=[float(r['seconds']) for r in rows]
            residuals=[float(r['relative_residual']) for r in rows]
            if any(not math.isfinite(t) or t<=0 for t in times): raise ValueError('Tiempo invalido')
            if any(not math.isfinite(r) or r<0 or r>1e-12 for r in residuals): raise ValueError('Residuo invalido')
            q1,_,q3=statistics.quantiles(times,method='inclusive')
            stats[(n,variant)]={
                'N':n,'variant':variant,'repetitions':7,'median_s':statistics.median(times),
                'q1_s':q1,'q3_s':q3,'iqr_s':q3-q1,'max_residual':max(residuals)}
    with (args.directory/'resumen.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(next(iter(stats.values()))))
        writer.writeheader();writer.writerows(stats.values())
    ratios=[]
    for n in sizes:
        ratios.append({'N':n,'right_over_left':stats[n,'right']['median_s']/stats[n,'left']['median_s']})
    (args.directory/'comparacion.json').write_text(json.dumps(ratios,indent=2),encoding='utf-8')

    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(7.2,3.8),layout='constrained')
    for variant,color in [('left','#126f85'),('right','#b6532d')]:
        med=[stats[n,variant]['median_s']*1000 for n in sizes]
        lo=[(stats[n,variant]['median_s']-stats[n,variant]['q1_s'])*1000 for n in sizes]
        hi=[(stats[n,variant]['q3_s']-stats[n,variant]['median_s'])*1000 for n in sizes]
        ax.errorbar(sizes,med,yerr=[lo,hi],marker='o',capsize=4,color=color,label=variant+'-looking')
    ax.set(xscale='log',yscale='log',xlabel='Orden de la matriz n',ylabel='Tiempo de factorización (ms)')
    ax.set_xticks(sizes,labels=[str(n) for n in sizes]);ax.grid(alpha=.2,which='both');ax.legend()
    fig.savefig(args.directory/'left_right.png',dpi=180);plt.close(fig)

    # Conteo analitico del bucle right-looking, no benchmark ni simulacion temporal.
    n,p=12,3
    owners={
        'Contigua':[j//4 for j in range(n)],
        'Cíclica (round-robin)':[j%p for j in range(n)],
        'Bloque-cíclica (b=2)':[(j//2)%p for j in range(n)]}
    colors=['#126f85','#bc653b','#7062a0']
    fig,ax=plt.subplots(figsize=(7.2,2.8),layout='constrained')
    from matplotlib.patches import Rectangle
    distribution={}
    for y,(name,owner) in enumerate(owners.items()):
        for col,rank in enumerate(owner):
            ax.add_patch(Rectangle((col,y-.34),.94,.68,color=colors[rank]))
            ax.text(col+.47,y,str(rank),ha='center',va='center',color='white',weight='bold')
        counts=[sum(j*(n-j) for j in range(n) if owner[j]==rank) for rank in range(p)]
        distribution[name]={'owner':owner,'updates_by_rank':counts}
    ax.set(xlim=(-.1,12),ylim=(2.6,-.65),xlabel='Columna global (el número de cada celda indica su proceso)')
    ax.set_yticks(range(3),labels=list(owners));ax.set_xticks([j+.47 for j in range(n)],labels=range(n))
    ax.tick_params(axis='both',length=0);ax.spines['left'].set_visible(False);ax.spines['bottom'].set_visible(False)
    fig.savefig(args.directory/'distribuciones.png',dpi=180);plt.close(fig)
    (args.directory/'conteo_distribuciones.json').write_text(json.dumps(distribution,ensure_ascii=False,indent=2),encoding='utf-8')
    for row in ratios: print(row)


if __name__=='__main__': main()
