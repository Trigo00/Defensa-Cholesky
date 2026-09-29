#!/bin/bash
#SBATCH --job-name=cholesky_bench
#SBATCH --output=resultado_cholesky_%j.out
#SBATCH --error=errores_cholesky_%j.err
#SBATCH --nodes=4                   # Cantidad de nodos (ajustar según el cluster)
#SBATCH --ntasks-per-node=16        # Procesos MPI por nodo (ajustar según CPU)
#SBATCH --time=01:00:00             # Tiempo máximo de ejecución
#SBATCH --partition=compute         # Nombre de la cola/partición (puede ser batch, normal, compute)

# Cargar módulos (ajustar según el cluster de la FACET-UNT)
# module load gcc openmpi

# Compilación (idealmente hacer esto fuera del script, pero se incluye por completitud)
# mpicc -O3 cholesky_final_hpc.c -o cholesky_final_hpc -lm

echo "Iniciando experimento Cholesky en el Cluster"
echo "Nodos asignados: $SLURM_JOB_NODELIST"
echo "Procesos totales: $SLURM_NTASKS"

# Parámetros: N=16384 (debe ser múltiplo de b=64)
N=16384

# Ejecución dejando al auto-tuner decidir
srun ./cholesky_final_hpc $N 0

# Ejecución forzando estrategias para comparar
echo "--- Ejecuciones Forzadas ---"
srun ./cholesky_final_hpc $N 2  # Fuerza 1D
srun ./cholesky_final_hpc $N 3  # Fuerza 2D
