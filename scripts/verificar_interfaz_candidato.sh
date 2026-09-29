#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
out="${1:?Output directory required}"
./build/cholesky_candidate_seq 0 >/dev/null 2>&1
seq_code=$?
mpirun -np 2 ./build/cholesky_candidate_mpi invalid > "$out/invalid_mpi.log" 2>&1
mpi_code=$?
./build/measure_command "$out/command_true.csv" /bin/true
true_code=$?
./build/measure_command "$out/command_false.csv" /bin/false
false_code=$?
printf 'sequential_invalid=%s mpi_invalid=%s command_true=%s command_false=%s\n' "$seq_code" "$mpi_code" "$true_code" "$false_code" > "$out/interface_status.txt"
ompi_info --version > "$out/mpi_version.txt" 2>&1
[[ "$seq_code" == 2 && "$mpi_code" == 2 && "$true_code" == 0 && "$false_code" == 1 ]]

