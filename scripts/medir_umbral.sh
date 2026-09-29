#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make all mpi-local
out="${1:-resultados/umbral_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$(dirname "$out")"
mkdir "$out"
{
    date -u
    uname -a
    gcc --version
    ompi_info --version
    lscpu
    printf '\nTres rondas en la misma sesion; lanzamientos separados, no dias independientes\n'
    printf 'N=64,96,128,160,192,224,256; P=1,2,3\n'
    printf 'Ronda 1 ascendente, ronda 2 descendente, ronda 3 rotada; P rota\n'
    printf '8 repeticiones MPI por variante; mismas cuatro variantes del experimento 4\n'
    printf 'Referencias: tres secuenciales, 6 repeticiones antes y 6 despues\n'
    printf 'Criterio previo: Sutil>1.10 y Q3MPI<Q1secuencial en las tres rondas\n'
    printf 'Criterio descriptivo conservador, no prueba de significacion ni intervalo de confianza\n'
    printf 'Foco: ciclico con vector, P=2 y P=3. Otros kernels quedan como controles\n'
    printf 'Tiempo del kernel; copia local incluida; distribucion inicial y validacion excluidas\n'
    printf 'Flags -O3 -std=c11 -Wall -Wextra -Wpedantic; afinidad --bind-to core --map-by core\n'
} > "$out/protocolo.txt"
sha256sum src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h src/experimentos/compare_mpi_local.c src/experimentos/compare_memory.c Makefile scripts/medir_umbral.sh > "$out/fuentes.sha256"
for round in 1 2 3; do
    mkdir "$out/r${round}"
    case "$round" in
        1) sizes=(64 96 128 160 192 224 256);;
        2) sizes=(256 224 192 160 128 96 64);;
        3) sizes=(160 192 224 256 64 96 128);;
    esac
    index=$((round-1))
    for n in "${sizes[@]}"; do
        echo "Ronda=$round N=$n"
        date -u >> "$out/r${round}/orden.log"
        echo "N=$n" >> "$out/r${round}/orden.log"
        mpirun --bind-to core --map-by core -np 1 ./build/compare_memory "$n" 6 2026 > "$out/r${round}/seq_before_n${n}.csv" 2>> "$out/placement.log"
        for offset in 0 1 2; do
            p=$(( (index+offset)%3+1 ))
            mpirun --bind-to core --map-by core --report-bindings -np "$p" ./build/compare_mpi_local "$n" 8 > "$out/r${round}/mpi_n${n}_p${p}.csv" 2>> "$out/placement.log"
        done
        mpirun --bind-to core --map-by core -np 1 ./build/compare_memory "$n" 6 2026 > "$out/r${round}/seq_after_n${n}.csv" 2>> "$out/placement.log"
        index=$((index+1))
    done
done
printf 'Resultados: %s\n' "$out"

