#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
out="${1:-resultados/cierre_local_$(date -u +%Y%m%dT%H%M%SZ)}"
mkdir -p "$(dirname "$out")";mkdir "$out"
make candidate test > "$out/build_tests.log" 2>&1
{ date -u; uname -a; lscpu; free -h; gcc --version; mpirun --version; } > "$out/entorno.txt"
mkdir "$out/tests" "$out/runs"
for n in 1 2 7 31 128; do
 ./build/cholesky_candidate_seq "$n" > "$out/tests/seq_n$n.csv"
 for p in 1 2 3 4 6; do
  timeout 60 mpirun --bind-to core --map-by core -np "$p" ./build/cholesky_candidate_mpi "$n" > "$out/tests/mpi_n${n}_p${p}.csv" 2>> "$out/tests/mpi.log"
 done
done
if ./build/cholesky_candidate_seq 0 > /dev/null 2>&1; then exit 1; fi
if timeout 30 mpirun -np 2 ./build/cholesky_candidate_mpi invalid > /dev/null 2>&1; then exit 1; fi
printf '%s\n' 'Candidate smoke tests: 30 valid configurations, invalid arguments rejected.' > "$out/tests/status.txt"
# Each observation is a fresh launch. rep=0 is discarded; rotating method order.
methods=(seq 1 2 3 4 6)
for rep in $(seq 0 7); do
 for n in 256 512 1024 2048; do
  for pos in 0 1 2 3 4 5; do
   method="${methods[$(((pos+rep)%6))]}"
   name="$out/runs/n${n}_r${rep}_m${method}"
   if [[ "$method" == seq ]]; then
    command=(taskset -c 0 ./build/cholesky_candidate_seq "$n")
   else
    command=(mpirun --bind-to core --map-by core -np "$method" ./build/cholesky_candidate_mpi "$n")
   fi
   timeout 120 ./build/measure_command "$name.time.csv" "${command[@]}" > "$name.csv" 2> "$name.log"
  done
 done
 printf 'Completed repetition %s of 7 (0 = warmup)\n' "$rep"
done
mkdir -p "$out/fuentes/src" "$out/fuentes/scripts"
cp src/implementacion_final/main_candidate.c src/experimentos/measure_command.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h "$out/fuentes/src/"
cp scripts/cierre_local.sh "$out/fuentes/scripts/";cp Makefile "$out/fuentes/"
(cd "$out/fuentes";find . -type f -print0 | sort -z | xargs -0 sha256sum) > "$out/fuentes.sha256"

