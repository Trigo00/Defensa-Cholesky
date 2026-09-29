#!/usr/bin/env bash
# Ejecutar DENTRO de una asignacion del administrador/planificador.
set -euo pipefail
cd "$(dirname "$0")/.."
out="${1:?Indicar carpeta nueva de resultados}"
read -r -a sizes <<< "${SIZES:-1024 2048}"
read -r -a processes <<< "${PROCESSES:-1 3 6}"
read -r -a launcher <<< "${MPI_LAUNCHER:-mpirun}"
read -r -a flags <<< "${MPI_FLAGS:---bind-to core --map-by core --report-bindings}"
countflag="${MPI_COUNT_FLAG:--np}"
reps="${REPETITIONS:-8}"
[[ $reps =~ ^[0-9]+$ ]] && ((reps>=2 && reps<=28 && reps%2==0)) || { echo 'Repeticiones: par entre 2 y 28' >&2;exit 2; }
available=$(awk '/MemAvailable:/ {print int($2*0.6/1024)}' /proc/meminfo)
limit="${MEMORY_BUDGET_MIB:-$available}"
[[ $limit =~ ^[0-9]+$ ]] || exit 2
for n in "${sizes[@]}"; do
  [[ $n =~ ^[0-9]+$ ]] && ((n>=1 && n<=20000)) || exit 2
  # Conservative sum for single-node benchmark with reference matrices.
  required=$(( (40*n*n+1048575)/1048576+128 ))
  ((required<=limit)) || { echo "N=$n requiere presupuesto aproximado $required MiB; limite $limit" >&2;exit 2; }
done
for p in "${processes[@]}"; do [[ $p =~ ^[0-9]+$ ]] && ((p>=1 && p<=20000)) || exit 2; done
make blocks
mkdir -p "$(dirname "$out")";mkdir "$out"
{ date -u; uname -a; lscpu; free -h; gcc --version; mpicc --show; env | sort | grep -E '^(SLURM_|OMP_|OPENBLAS_|MKL_)' || true; } > "$out/entorno.txt"
printf '%s\n' "SIZES=${sizes[*]} PROCESSES=${processes[*]} REPS=$reps" "LAUNCHER=${launcher[*]} FLAGS=${flags[*]}" "MEMORY_BUDGET_MIB=$limit" 'B=1,4; orden alternado; MPI ya iniciado; total hasta L en rango0; validacion fuera.' > "$out/protocolo.txt"
for n in "${sizes[@]}"; do
 for p in "${processes[@]}"; do
  /usr/bin/time -v -o "$out/n${n}_p${p}_resource.txt" "${launcher[@]}" "${flags[@]}" "$countflag" "$p" ./build/compare_blocks "$n" "$reps" pair > "$out/n${n}_p${p}.csv" 2> "$out/n${n}_p${p}_placement.log"
 done
done
mkdir -p "$out/fuentes/src" "$out/fuentes/scripts"
cp src/experimentos/bench_utils.c src/experimentos/bench_utils.h src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h src/experimentos/compare_blocks.c "$out/fuentes/src/"
cp Makefile "$out/fuentes/";cp scripts/campana_cluster.sh "$out/fuentes/scripts/"
sha256sum src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h src/experimentos/compare_blocks.c Makefile > "$out/fuentes.sha256"

