# Guía de Ejecución Física: De WSL al Clúster Real

> [!IMPORTANT]
> **Cambio de Paradigma:** Todos los datos generados a partir de este punto son **100% físicos y reales**. Se acabó la teoría.

## 1. Lo que ya aplicamos en tu computadora (WSL)

Acabamos de exprimir al máximo tu procesador local. Como un clúster de verdad tiene docenas de nodos, y tu computadora tiene recursos limitados, limitamos el estrés local a $N \le 2048$ y $P \le 4$ para evitar colgar la memoria RAM de tu máquina.

**¿Qué hicimos?**
1. Ejecutamos el script `run_local_benchmarks.sh` que invocó a `mpirun` con tu código nativo.
2. Los resultados se volcaron en el archivo `benchmark_real_wsl.csv`.
3. Ejecutamos `plot_real_data.py` para generar los gráficos reales.

**Resultados Físicos Locales:**
Al revisar tu `benchmark_real_wsl.csv`, confirmamos en la vida real todo el marco teórico:
* Para $N=256$, tu máquina tardó 0.004s en Secuencial y 0.045s con 4 procesos. ¡10 veces más lento! El *overhead* de red local superó al cálculo.
* Para $N=2048$, el Secuencial tardó 3.94s, pero con $P=2$ bajó a **2.87s**. ¡Aquí empezamos a ver Speedup real físico!

Los gráficos ya están en tu carpeta:
- ![Speedup Real WSL](C:/Users/Nicolas/.gemini/antigravity/brain/7839c84b-6f43-42cf-a7d7-64ddbe09dac7/real_speedup.png)
- ![Tiempo Real WSL](C:/Users/Nicolas/.gemini/antigravity/brain/7839c84b-6f43-42cf-a7d7-64ddbe09dac7/real_tiempo_vs_n.png)

---

## 2. Lo que debes hacer en el Clúster (Cuando te den acceso)

Tu código C ya está preparado para el clúster. Cuando inicies sesión en la supercomputadora de la facultad, sigue estos pasos exactos:

### Paso A: Preparar el Entorno
Sube tu archivo `cholesky_final_hpc.c`, el generador de gráficos `plot_real_data.py` y el script de la cola `cholesky_slurm.sh` a tu directorio del clúster.

### Paso B: Compilar para la Red Infiniband/Ethernet
En la consola del clúster, compila el archivo. (Asegúrate de tener cargado el módulo de MPI, ej. `module load openmpi`).
```bash
mpicc -O3 cholesky_final_hpc.c -o cholesky_final_hpc -lm
```

### Paso C: Generar el CSV Físico Masivo
Vas a reemplazar mi viejo script `run_local_benchmarks.sh` por uno adaptado a matrices bestiales. Crea un script en el clúster llamado `bench_cluster.sh` con esto:

```bash
#!/bin/bash
#SBATCH --nodes=4
#SBATCH --ntasks-per-node=16
#SBATCH --time=02:00:00

echo "N,P,estrategia,tiempo_total,tiempo_comp,tiempo_comm" > benchmark_real_cluster.csv

for N in 4096 8192 16384; do
    # Secuencial (Línea base)
    srun -n 1 ./cholesky_final_hpc $N 1 | grep "RESULT" >> benchmark_real_cluster.csv
    
    # Pruebas de escalabilidad masiva
    for P in 16 32 64; do
        srun -n $P ./cholesky_final_hpc $N 2 | grep "RESULT" >> benchmark_real_cluster.csv
    done
done
```
Mándalo a ejecutar con `sbatch bench_cluster.sh`.

### Paso D: Generar los Gráficos del Informe
Cuando el trabajo del clúster termine, tendrás el archivo de datos masivos `benchmark_real_cluster.csv`. 
Ejecuta tu script de Python para actualizar las imágenes:
```bash
python3 plot_real_data.py benchmark_real_cluster.csv
```

---

## 3. Modificaciones al Documento Final

Una vez que tengas esos últimos dos gráficos masivos de la red real, ve a tu **Documento Maestro Completo** (`Documentacion_Completa_Cholesky.md`). 
1. Reemplaza cualquier imagen de los "Bloques 1 al 6" con los `.png` que te acaba de generar el clúster.
2. Elimina la "Nota de Auditoría" en la Sección de Metodología, declarando oficialmente que los datos presentados son extraídos nativamente de los nodos de la FACET-UNT. 

**¡Y con eso, el proyecto queda en calidad de Tesis de Grado!**
