"""Mostrar medianas de un CSV de Cholesky, separadas por configuracion."""
import argparse
import csv
import math
from collections import defaultdict
from statistics import median

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archivo", help="CSV generado por el programa")
parser.add_argument("campo", help="seconds, factor_s, application_s o total_s")
args = parser.parse_args()
groups = defaultdict(list)

with open(args.archivo, newline="", encoding="utf-8-sig") as source:
    reader = csv.DictReader(source)
    columns = reader.fieldnames or []
    if args.campo not in columns:
        parser.error(f"No existe {args.campo}. Campos: {', '.join(columns)}")
    keys = [k for k in ("N", "P", "variant", "distribution", "kernel",
                        "algorithm", "method", "block") if k in columns]
    for row in reader:
        if row.get("N") == "N":  # Encabezados repetidos del candidato.
            continue
        if "repetition" in columns and int(row["repetition"]) <= 0:
            continue  # Los bancos no siempre imprimen el calentamiento.
        if row.get("valid", "1") != "1" or row.get("identical", "1") != "1":
            parser.error("Hay resultados invalidos; revisalos antes de comparar tiempos.")
        value = float(row[args.campo])
        if not math.isfinite(value) or value < 0:
            parser.error("Hay tiempos negativos o no finitos.")
        groups[tuple(row[k] for k in keys)].append(value)

if not groups:
    parser.error("No hay mediciones utiles.")
for configuration, values in groups.items():
    label = " ".join(f"{k}={v}" for k, v in zip(keys, configuration))
    result = median(values)
    print(f"{label} | mediciones={len(values)} | "
          f"mediana {args.campo}={result:.9f} s ({result * 1000:.3f} ms)")
