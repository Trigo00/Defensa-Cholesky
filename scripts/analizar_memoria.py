"""Analiza el experimento de acceso a memoria: tres kernels C, 12 repeticiones."""
import argparse
from collections import defaultdict
import csv
import json
import math
import os
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[2]
if os.name=='nt' and (ROOT/'tmp/pdf_deps').exists():sys.path.insert(0,str(ROOT/'tmp/pdf_deps'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def main():
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);args=parser.parse_args()
    variants=('left','right','right_buffered')
    groups=defaultdict(list)
    orders={}
    expected=((0,1,2),(0,2,1),(1,0,2),(1,2,0),(2,0,1),(2,1,0))
    for path in args.directory.glob('n[0-9]*.csv'):
        with path.open(newline='') as stream:
            for row in csv.DictReader(stream):
                n=int(row['N']);rep=int(row['repetition']);variant=row['variant'];order=int(row['order'])
                if variant not in variants or not 1<=rep<=12 or not 1<=order<=3:
                    raise ValueError('Esquema de observaciones invalido')
                key=(n,rep,order)
                if key in orders:raise ValueError('Observacion duplicada')
                if variants.index(variant)!=expected[(rep-1)%6][order-1]:raise ValueError('Orden incorrecto')
                orders[key]=variant
                groups[n,variant].append(row)
    sizes=sorted({n for n,_ in groups})
    if not sizes:raise ValueError('Sin datos')
    stats={}
    for n in sizes:
        for variant in variants:
            rows=groups[n,variant]
            if len(rows)!=12 or {int(r['repetition']) for r in rows}!=set(range(1,13)):
                raise ValueError(f'Repeticiones incompletas: {n}, {variant}')
            if {int(r['seed']) for r in rows}!={2026}:raise ValueError('Semilla inconsistente')
            times=[float(r['seconds']) for r in rows];residuals=[float(r['relative_residual']) for r in rows]
            if any(not math.isfinite(x) or x<=0 for x in times):raise ValueError('Tiempo invalido')
            if any(not math.isfinite(x) or not 0<=x<=1e-12 for x in residuals):raise ValueError('Residuo invalido')
            q1,_,q3=statistics.quantiles(times,method='inclusive')
            stats[n,variant]={'N':n,'variant':variant,'repetitions':12,'median_s':statistics.median(times),'q1_s':q1,'q3_s':q3,'iqr_s':q3-q1,'max_residual':max(residuals)}
    with (args.directory/'resumen.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(next(iter(stats.values()))));writer.writeheader();writer.writerows(stats.values())
    comparisons=[]
    for n in sizes:
        left=stats[n,'left']['median_s'];direct=stats[n,'right']['median_s'];buffered=stats[n,'right_buffered']['median_s']
        comparisons.append({'N':n,'right_over_buffered':direct/buffered,'left_over_buffered':left/buffered,'buffer_bytes':8*n})
        print(f'N={n}: left={left*1000:.4f} ms; right={direct*1000:.4f} ms; vector={buffered*1000:.4f} ms; mejora/right={direct/buffered:.2f}x; mejora/left={left/buffered:.2f}x')
    (args.directory/'comparacion.json').write_text(json.dumps(comparisons,indent=2),encoding='utf-8')

    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(figsize=(7.2,3.3),layout='constrained')
    for pos,(variant,label,color) in enumerate(zip(variants,('Left','Right original','Right + vector'),('#126f85','#b6532d','#41834a'))):
        x=[i+(pos-1)*.19 for i in range(len(sizes))]
        median=[1000*stats[n,variant]['median_s'] for n in sizes]
        lo=[1000*(stats[n,variant]['median_s']-stats[n,variant]['q1_s']) for n in sizes]
        hi=[1000*(stats[n,variant]['q3_s']-stats[n,variant]['median_s']) for n in sizes]
        ax.errorbar(x,median,yerr=[lo,hi],fmt='o',capsize=3,color=color,label=label)
    ax.set(yscale='log',xlabel='Orden n (categorías)',ylabel='Factorización (ms, escala logarítmica)')
    ax.set_xticks(range(len(sizes)),labels=sizes);ax.grid(axis='y',which='major',alpha=.2);ax.legend(loc='upper left')
    fig.savefig(args.directory/'memoria.png',dpi=200);plt.close(fig)


if __name__=='__main__':main()
