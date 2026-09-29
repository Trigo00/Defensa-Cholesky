#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make application test-application
out="${1:-resultados/aplicacion_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$(dirname "$out")"
mkdir "$out"
{ date -u; uname -a; lscpu; gcc --version; ompi_info --version; } > "$out/entorno.txt"
printf '%s\n' 'N=512,1024,2048; P=1,3,6; seis permutaciones de tres metodos, un calentamiento.' 'Semilla matriz 2026; proyectada 91827, ocho vectores; factor secuencial de referencia.' 'Total principal: reloj de rango 0, desde reserva hasta L completa en rango 0; fases consecutivas.' 'Incluye reserva, generacion, distribucion, factorizacion, recoleccion. MPI ya iniciado.' 'Excluye referencia/validacion, liberacion, lanzamiento MPI y cierre. malloc no fuerza paginas: primer acceso se cobra a la fase que lo realiza.' 'Secuencial en rango 0, otros procesos lanzados quedan esperando; no es ejecutable secuencial independiente.' 'Maximo local tambien registrado; fases rank0 incluyen espera, no son costos puros.' > "$out/protocolo.txt"
for n in 512 1024 2048; do
  for p in 1 3 6; do
    mpirun --bind-to core --map-by core --report-bindings -np "$p" ./build/compare_application "$n" 6 > "$out/n${n}_p${p}.csv" 2>> "$out/placement.log"
  done
done
mkdir -p "$out/fuentes/src" "$out/fuentes/scripts"
cp src/bench_utils.c src/bench_utils.h src/cholesky.c src/cholesky.h src/cholesky_mpi.c src/cholesky_mpi.h src/compare_application.c "$out/fuentes/src/"
cp Makefile "$out/fuentes/"
cp scripts/comparar_aplicacion.sh "$out/fuentes/scripts/"
sha256sum src/cholesky.c src/cholesky.h src/cholesky_mpi.c src/cholesky_mpi.h src/compare_application.c Makefile scripts/comparar_aplicacion.sh > "$out/fuentes.sha256"
