#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make blocks test-blocks test-application
out="${1:-resultados/bloques_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$(dirname "$out")";mkdir "$out"
{ date -u; uname -a; lscpu; gcc --version; ompi_info --version; } > "$out/entorno.txt"
printf '%s\n' 'N=512,1024,2048 P=1,3,6 B=1,2,4,8,16,32,64' '7 repeticiones, orden rotado: cada bloque ocupa cada posicion una vez; un calentamiento por variante.' 'Total rank0: reserva+generacion distribuida+factorizacion+Gatherv y desempaquetado; excluye lanzamiento y validacion.' 'Fases rank0 incluyen espera; misma implementacion general de indices para B=1 y B>1.' 'Balance: max actualizaciones / media, conteo teorico k*(n-k) por columna; no mide balance por etapa ni comunicacion.' > "$out/protocolo.txt"
idx=0
for n in 512 1024 2048; do
  ps=(1 3 6)
  for off in 0 1 2; do
    p=${ps[$(( (idx+off)%3 ))]}
    mpirun --bind-to core --map-by core --report-bindings -np "$p" ./build/compare_blocks "$n" 7 > "$out/n${n}_p${p}.csv" 2>> "$out/placement.log"
  done
  idx=$((idx+1))
done
mkdir -p "$out/fuentes/src" "$out/fuentes/scripts"
cp src/experimentos/bench_utils.c src/experimentos/bench_utils.h src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h src/experimentos/compare_blocks.c "$out/fuentes/src/"
cp Makefile "$out/fuentes/";cp scripts/comparar_bloques.sh "$out/fuentes/scripts/"
sha256sum src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h src/experimentos/compare_blocks.c Makefile scripts/comparar_bloques.sh > "$out/fuentes.sha256"

