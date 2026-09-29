#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
make all mpi-local test-mpi-local
out="${1:-resultados/mpi_local_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$(dirname "$out")"
mkdir "$out"
{
    date -u
    uname -a
    gcc --version
    ompi_info --version
    lscpu
    printf '\nFlags: -O3 -std=c11 -Wall -Wextra -Wpedantic\n'
    printf 'MPI --bind-to core --map-by core; P=1,2,3,4; N=64,256,512,1024\n'
    printf 'Variantes 0=original contiguo,1=original ciclico,2=local contiguo,3=local ciclico\n'
    printf 'Orden Williams: 0,1,3,2 / 1,2,0,3 / 2,3,1,0 / 3,0,2,1; dos ciclos\n'
    printf 'Un calentamiento por variante y 8 repeticiones medidas\n'
    printf 'Copia al vector local incluida; reserva, distribucion inicial y validacion excluidas\n'
    printf 'P rota entre tamanos. Referencias secuenciales antes y despues (6+6 repeticiones)\n'
    printf 'Perfil separado N=1024 P=3, 4 repeticiones; Bcast incluye espera\n'
} > "$out/entorno.txt"
sha256sum src/cholesky.c src/cholesky.h src/cholesky_mpi.c src/cholesky_mpi.h src/compare_mpi_local.c src/compare_memory.c Makefile scripts/comparar_mpi_local.sh > "$out/fuentes.sha256"
index=0
for n in 64 256 512 1024; do
    mpirun --bind-to core --map-by core -np 1 ./build/compare_memory "$n" 6 2026 > "$out/seq_before_n${n}.csv" 2>> "$out/placement.log"
    for offset in 0 1 2 3; do
        p=$(( (index+offset)%4+1 ))
        echo "Midiendo vector local N=$n P=$p"
        mpirun --bind-to core --map-by core --report-bindings -np "$p" ./build/compare_mpi_local "$n" 8 > "$out/mpi_n${n}_p${p}.csv" 2>> "$out/placement.log"
    done
    mpirun --bind-to core --map-by core -np 1 ./build/compare_memory "$n" 6 2026 > "$out/seq_after_n${n}.csv" 2>> "$out/placement.log"
    index=$((index+1))
done
mpirun --bind-to core --map-by core -np 3 ./build/compare_mpi_local 1024 4 profile > "$out/profile_p3.csv" 2>> "$out/placement.log"
printf 'Resultados: %s\n' "$out"
