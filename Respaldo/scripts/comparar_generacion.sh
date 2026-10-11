#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make generation test
out="${1:-resultados/generacion_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$(dirname "$out")"
mkdir "$out"
{ date -u; uname -a; lscpu; gcc --version; mpirun --version; } > "$out/entorno.txt"
printf '%s\n' 'N=512,1024,2048; P=1..6; 6 repeticiones alternadas y un calentamiento.' 'Misma matriz seed=2026, igualdad bit a bit en cada repeticion.' 'Tiempo: generacion y distribucion hasta almacenamiento local; excluye reserva, inicio MPI y validacion.' 'Maximos de fases no son aditivos: procesos no sincronizan entre fases.' > "$out/protocolo.txt"
for n in 1 2 3 7 31; do
  mpirun --bind-to core --map-by core -np 6 ./build/compare_generation "$n" 2 > "$out/test_n${n}.csv"
done
index=0
for n in 512 1024 2048; do
  for off in 0 1 2 3 4 5; do
    p=$(( (index+off)%6+1 ))
    mpirun --bind-to core --map-by core --report-bindings -np "$p" ./build/compare_generation "$n" 6 > "$out/n${n}_p${p}.csv" 2>> "$out/placement.log"
  done
  index=$((index+1))
done
mkdir -p "$out/fuentes/src" "$out/fuentes/scripts"
cp src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h src/experimentos/compare_generation.c "$out/fuentes/src/"
cp Makefile "$out/fuentes/"
cp scripts/comparar_generacion.sh "$out/fuentes/scripts/"
sha256sum src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h src/experimentos/compare_generation.c src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h Makefile scripts/comparar_generacion.sh > "$out/fuentes.sha256"

