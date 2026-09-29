"""Mediciones locales de la referencia Python, sin extrapolación a C/MPI."""

import csv
import json
import math
import platform
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

from cholesky import cholesky, generate_spd, relative_residual


def main():
    # Una carpeta por ejecución evita sobrescribir mediciones anteriores.
    out = Path(__file__).parent / "resultados" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    out.mkdir(parents=True)
    metadata = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version, "platform": platform.platform(),
        "processor": platform.processor(),
        "variant": "python_sequential_reference", "sizes": [32, 64, 128],
        "seed": 2026, "warmups": 1, "repetitions": 7,
        "timed_scope": "cholesky(): input checks, L allocation and factorization",
        "excluded": "A generation, residual and file IO",
        "quartiles": "statistics.quantiles(method='inclusive')",
    }
    (out / "entorno.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    with (out / "mediciones.csv").open("w", newline="", encoding="utf-8") as raw, \
         (out / "resumen.csv").open("w", newline="", encoding="utf-8") as summary:
        raw_writer = csv.writer(raw)
        summary_writer = csv.writer(summary)
        raw_writer.writerow(["N", "repetition", "seconds", "relative_residual"])
        summary_writer.writerow(["N", "repetitions", "median_s", "q1_s", "q3_s", "iqr_s", "max_residual"])
        for n in metadata["sizes"]:
            a = generate_spd(n, metadata["seed"])
            cholesky(a)  # Calentamiento no registrado.
            times, residuals = [], []
            for rep in range(1, metadata["repetitions"] + 1):
                start = perf_counter()
                lower = cholesky(a)
                elapsed = perf_counter() - start
                residual = relative_residual(a, lower)
                if not math.isfinite(residual) or residual > 1e-12:
                    raise RuntimeError("Validación fallida; no se acepta esta medición")
                times.append(elapsed)
                residuals.append(residual)
                raw_writer.writerow([n, rep, elapsed, residual])
            q1, _, q3 = statistics.quantiles(times, method="inclusive")
            summary_writer.writerow([n, len(times), statistics.median(times), q1, q3, q3-q1, max(residuals)])
    print(out)


if __name__ == "__main__":
    main()
