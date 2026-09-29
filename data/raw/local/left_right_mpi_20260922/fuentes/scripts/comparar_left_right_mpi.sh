#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make all mpi-algorithms test test-mpi-algorithms
out="${1:-resultados/left_right_mpi_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$(dirname "$out")";mkdir "$out"
{
  date -u;uname -a;gcc --version;ompi_info --version;lscpu
  printf '\nLeft-looking MPI vs right-looking MPI con vector local\n'
  printf 'Misma distribucion ciclica de columnas, matriz, afinidad y compilador\n'
  printf 'N=64,128,256,512,1024; P=1,2,3,4; 8 repeticiones; orden alternado\n'
  printf 'Tiempo del kernel: maximo por proceso; Scatterv, Gatherv y validacion fuera\n'
  printf 'Perfil separado N=1024 P=3, 4 repeticiones por algoritmo\n'
} > "$out/protocolo.txt"
sha256sum src/cholesky.c src/cholesky.h src/cholesky_mpi.c src/cholesky_mpi.h src/cholesky_left_mpi.c src/compare_mpi_algorithms.c Makefile scripts/comparar_left_right_mpi.sh > "$out/fuentes.sha256"
index=0
for n in 64 128 256 512 1024; do
  for offset in 0 1 2 3; do
    p=$(( (index+offset)%4+1 ));echo "Comparando left/right N=$n P=$p"
    mpirun --bind-to core --map-by core --report-bindings -np "$p" ./build/compare_mpi_algorithms "$n" 8 > "$out/n${n}_p${p}.csv" 2>> "$out/placement.log"
  done
  index=$((index+1))
done
mpirun --bind-to core --map-by core -np 3 ./build/compare_mpi_algorithms 1024 4 profile > "$out/profile_n1024_p3.csv" 2>> "$out/placement.log"
printf 'Resultados: %s\n' "$out"
