"""Resume tiempos producidos por C; no realiza factorizaciones."""
import argparse
import csv
import math
from pathlib import Path
import statistics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    rows = []
    for path in sorted(args.directory.glob('n[0-9]*.csv')):
        with path.open(newline='') as stream:
            samples = list(csv.DictReader(stream))
        if len(samples) != 7:
            raise ValueError(f'{path}: se esperaban siete repeticiones')
        times = [float(r['seconds']) for r in samples]
        residuals = [float(r['relative_residual']) for r in samples]
        if any(not math.isfinite(x) or x <= 0 for x in times):
            raise ValueError(f'{path}: tiempo invalido')
        if any(not math.isfinite(r) or r > 1e-12 for r in residuals):
            raise ValueError(f'{path}: validacion fallida')
        q1, _, q3 = statistics.quantiles(times, method='inclusive')
        rows.append([int(samples[0]['N']), 7, statistics.median(times), q1, q3, q3-q1, max(residuals)])
    if not rows:
        raise ValueError('No se encontraron mediciones de C')
    rows.sort()
    with (args.directory/'resumen.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['N','repetitions','median_s','q1_s','q3_s','iqr_s','max_residual'])
        writer.writerows(rows)
    for n, reps, median, _, _, iqr, residual in rows:
        print(f'N={n}: mediana={median*1000:.4f} ms; IQR={iqr*1000:.4f} ms; r_max={residual:.3e}')


if __name__ == '__main__':
    main()

