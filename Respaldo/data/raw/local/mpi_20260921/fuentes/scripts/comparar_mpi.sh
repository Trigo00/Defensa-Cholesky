#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make all mpi test test-mpi
out="${1:-resultados/mpi_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$(dirname "$out")"
mkdir "$out"
{
    date -u
    uname -a
    gcc --version
    mpirun --version
    lscpu
    printf '\nFlags: -O3 -std=c11 -Wall -Wextra -Wpedantic\n'
    printf 'MPI: --bind-to core --map-by core; P=1,2,3,4; N=64,256,512,1024\n'
    printf '8 repeticiones; calentamiento por reparto; orden alternado\n'
    printf 'P rota entre tamanos; secuenciales contemporaneas antes y despues\n'
    printf 'Tiempo principal: maximo de duraciones locales del kernel, sin instrumentacion interna\n'
    printf 'Generacion, distribucion inicial, reunion, validacion y arranque MPI excluidos\n'
    printf 'Perfil separado: 3 repeticiones por rango; Bcast incluye espera\n'
} > "$out/entorno.txt"
sha256sum src/cholesky.c src/cholesky.h src/cholesky_mpi.c src/cholesky_mpi.h src/compare_mpi.c src/compare_memory.c Makefile scripts/comparar_mpi.sh > "$out/fuentes.sha256"
index=0
for n in 64 256 512 1024; do
    mpirun --bind-to core --map-by core -np 1 ./build/compare_memory "$n" 6 2026 > "$out/seq_before_n${n}.csv" 2>> "$out/placement.log"
    for offset in 0 1 2 3; do
        p=$(( (index+offset)%4+1 ))
        echo "Midiendo N=$n P=$p"
        mpirun --bind-to core --map-by core --report-bindings -np "$p" ./build/compare_mpi "$n" 8 > "$out/mpi_n${n}_p${p}.csv" 2>> "$out/placement.log"
    done
    mpirun --bind-to core --map-by core -np 1 ./build/compare_memory "$n" 6 2026 > "$out/seq_after_n${n}.csv" 2>> "$out/placement.log"
    index=$((index+1))
done
for p in 1 2 3 4; do
    mpirun --bind-to core --map-by core -np "$p" ./build/compare_mpi 1024 3 profile > "$out/profile_p${p}.csv" 2>> "$out/placement.log"
done
printf 'Resultados: %s\n' "$out"
