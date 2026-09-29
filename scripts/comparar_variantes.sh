#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make all test
out="${1:-resultados/left_right_$(date -u +%Y%m%dT%H%M%SZ)}"
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
    printf 'Dos variantes escalares, double, por filas, mismo generador y entrada\n'
    printf 'Semilla 2026; 1 calentamiento y 7 repeticiones por variante\n'
    printf 'Orden alternado left/right; copia y validacion fuera del timer\n'
} > "$out/entorno.txt"
sha256sum src/compare_seq.c src/cholesky.c src/cholesky.h tests/test_variants.c Makefile scripts/comparar_variantes.sh > "$out/fuentes.sha256"
for n in 64 128 256 512 1024; do
    taskset -c "$cpu" ./build/compare_seq "$n" 7 2026 > "$out/n${n}.csv"
done
printf 'Resultados: %s\n' "$out"
