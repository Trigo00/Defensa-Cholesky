#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make all test
out="${1:-resultados/c_secuencial_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$(dirname "$out")"
mkdir "$out"
{
    date -u
    uname -a
    gcc --version
    lscpu
    printf '\nVariante: C right-looking escalar; P=1; double\n'
    printf 'Flags: -O3 -std=c11 -Wall -Wextra -Wpedantic\n'
    printf 'Semilla: 2026; calentamientos: 1; repeticiones: 7\n'
    printf 'Medicion: solo cholesky_right; copia y residuo excluidos\n'
} > "$out/entorno.txt"
find src -type f \( -name '*.c' -o -name '*.h' \) -print0 \
  | sort -z | xargs -0 sha256sum > "$out/fuentes.sha256"
sha256sum tests/*.c Makefile scripts/medir_secuencial.sh >> "$out/fuentes.sha256"
for n in 128 256 512; do
    ./build/cholesky_seq "$n" 7 2026 > "$out/n${n}.csv"
done
printf 'Resultados: %s\n' "$out"

