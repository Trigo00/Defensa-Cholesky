#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make all test
out="${1:-resultados/memoria_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$(dirname "$out")"
mkdir "$out"
cpu=$(python3 -c 'import os; print(min(os.sched_getaffinity(0)))')
{
    date -u
    uname -a
    gcc --version
    lscpu
    printf '\nCPU logica fijada: %s\n' "$cpu"
    printf 'Flags: -O3 -std=c11 -Wall -Wextra -Wpedantic\n'
    printf 'Semilla 2026; 1 calentamiento y 12 repeticiones por variante\n'
    printf 'Orden: seis permutaciones repetidas dos veces\n'
    printf 'Memoria por filas, double. Empaquetado de columna dentro del timer\n'
    printf 'Reserva de matrices/workspace, copia de entrada y residuo fuera del timer\n'
    printf 'N=1000 incluido para no probar solamente potencias de dos\n'
} > "$out/entorno.txt"
sha256sum src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h src/experimentos/compare_memory.c tests/test_buffered.c Makefile scripts/comparar_memoria.sh > "$out/fuentes.sha256"
for n in 64 128 256 512 1000 1024; do
    taskset -c "$cpu" ./build/compare_memory "$n" 12 2026 > "$out/n${n}.csv"
done
printf 'Resultados: %s\n' "$out"

