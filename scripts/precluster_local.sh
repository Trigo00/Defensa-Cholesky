#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
out="${1:-resultados/precluster_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$(dirname "$out")";mkdir "$out"
make blocks lapack test test-blocks test-lapack > "$out/pruebas.log" 2>&1
{ date -u; uname -a; lscpu; free -h; gcc --version; ompi_info --version; dpkg-query -W liblapacke-dev libopenblas-dev; ldd build/compare_lapack; } > "$out/entorno.txt"
SIZES='1024 2048' PROCESSES=6 REPETITIONS=8 bash scripts/campana_cluster.sh "$out/confirmacion"
SIZES=3072 PROCESSES=6 REPETITIONS=2 bash scripts/campana_cluster.sh "$out/mayor"
mkdir "$out/lapack"
# CPU 0 is a single logical processor; both algorithms share this affinity.
for n in 512 1024 2048 3072; do
 reps=6; if ((n==3072));then reps=2;fi
 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 /usr/bin/time -v -o "$out/lapack/n${n}_resource.txt" taskset -c 0 ./build/compare_lapack "$n" "$reps" > "$out/lapack/n${n}.csv" 2> "$out/lapack/n${n}_library.log"
done
mkdir -p "$out/fuentes/src" "$out/fuentes/scripts"
cp src/experimentos/bench_utils.c src/experimentos/bench_utils.h src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h src/experimentos/compare_lapack.c "$out/fuentes/src/"
cp Makefile "$out/fuentes/";cp scripts/precluster_local.sh "$out/fuentes/scripts/"
sha256sum src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h src/experimentos/compare_lapack.c Makefile scripts/precluster_local.sh > "$out/fuentes.sha256"
printf '%s\n' 'Confirmacion independiente de fecha previa: B1/B4, n1024/2048 P6, 8 repeticiones.' 'Mayor: n3072 P6 dos repeticiones por bloque; exploratorio.' 'LAPACK: sin MPI, afinidad CPU0, OpenBLAS 1 hilo comprobado; 6 repeticiones n512/1024/2048, 2 n3072.' 'Generador y entrada identicos; alias column-major U equivale a L row-major, sin transposicion.' 'Total LAPACK: reserva+generacion+factorizacion; validacion/liberacion fuera; ambos algoritmos reservan workspace n.' 'time -v incluye referencias, validacion y calentamientos; no usarlo como speedup de una factorizacion. RSS no suma memoria de todos los rangos.' > "$out/protocolo.txt"

