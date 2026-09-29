#!/bin/bash
# Script de Benchmarking Local (WSL)

# 1. Compilar el código real
mpicc -O3 cholesky_final_hpc.c -o cholesky_final_hpc -lm

# 2. Inicializar el CSV
echo "N,P,estrategia,tiempo_total,tiempo_comp,tiempo_comm" > benchmark_real_wsl.csv

echo "Iniciando pruebas físicas en WSL..."

# 3. Bucle de pruebas
for N in 256 512 1024 2048; do
    echo "Testeando N=$N..."
    
    # Estrategia 1: Secuencial (P=1)
    mpirun -n 1 ./cholesky_final_hpc $N 1 | grep "RESULT" | cut -d',' -f2- >> benchmark_real_wsl.csv
    
    # Estrategias en Paralelo (P=2 y P=4)
    for P in 2 4; do
        # Estrategia 2: 1D Block-Cyclic
        mpirun -n $P ./cholesky_final_hpc $N 2 | grep "RESULT" | cut -d',' -f2- >> benchmark_real_wsl.csv
    done
done

echo "¡Benchmarking local terminado! Datos guardados en benchmark_real_wsl.csv"
