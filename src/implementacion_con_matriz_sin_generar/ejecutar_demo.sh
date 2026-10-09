#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
input=${1:-MATRIZ.txt}
output=${2:-RESULTADO_L.txt}
if [ "$input" = "$output" ] || { [ -e "$input" ] && [ -e "$output" ] && [ "$input" -ef "$output" ]; }; then
    echo 'ERROR: entrada y salida deben ser archivos distintos.' >&2
    exit 2
fi
rm -f -- "$output"
trap 'rm -f -- "$output"' EXIT
trap 'exit 1' HUP INT TERM
make
# MPIEXEC permite seleccionar el lanzador y sus opciones en las pruebas.
${MPIEXEC:-mpirun --bind-to core --map-by core -np 2} ./cholesky_app "$input" "$output" --validate
test -s "$output"
trap - EXIT HUP INT TERM
echo "Factor validado: $output"
