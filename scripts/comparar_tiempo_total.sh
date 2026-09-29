#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make all mpi-total test test-mpi-total
out="${1:-resultados/tiempo_total_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$(dirname "$out")";mkdir "$out"
{
  date -u;uname -a;gcc --version;ompi_info --version;lscpu
  printf '\nEntrada A completa y salida L completa en rango 0\n'
  printf 'MPI: empaquetado + Scatterv; kernel; Gatherv + desempaquetado\n'
  printf 'Secuencial: copia de entrada; right con vector; salida ya completa\n'
  printf 'N=64,128,256,512,1024; P=1,2,3,4; 12 repeticiones\n'
  printf 'Tres algoritmos; seis permutaciones repetidas dos veces\n'
  printf 'Reserva, generacion, validacion y arranque de procesos fuera del tiempo\n'
} > "$out/protocolo.txt"
sha256sum src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h src/experimentos/cholesky_left_mpi.c src/experimentos/compare_mpi_total.c Makefile scripts/comparar_tiempo_total.sh > "$out/fuentes.sha256"
index=0
for n in 64 128 256 512 1024; do
  for offset in 0 1 2 3; do
    p=$(( (index+offset)%4+1 ));echo "Tiempo completo N=$n P=$p"
    mpirun --bind-to core --map-by core --report-bindings -np "$p" ./build/compare_mpi_total "$n" 12 > "$out/n${n}_p${p}.csv" 2>> "$out/placement.log"
  done
  index=$((index+1))
done
printf 'Resultados: %s\n' "$out"

