# Guía paso a paso para ejecutar y defender el proyecto Cholesky

Esta guía convierte la historia completa del proyecto en un recorrido práctico. En cada etapa indica qué se quiso comprobar, qué archivo conviene abrir, cómo ejecutar una demostración corta y qué significa la salida.

Los nombres antiguos del documento histórico, como `desde_cero/src/cholesky.c`, corresponden en el repositorio actual a `src/implementacion_final/cholesky.c` o a un banco de `src/experimentos/`.

## Preparación

La ejecución requiere Linux o WSL, GCC, Make y Open MPI. LAPACKE/OpenBLAS solo se necesitan para la referencia LAPACK. Python 3 y `requirements.txt` permiten reconstruir tablas, figuras y PDF.

En WSL:

```bash
cd /mnt/c/Users/trigo/OneDrive/Escritorio/Defensa-Cholesky
sudo apt update
sudo apt install build-essential make openmpi-bin libopenmpi-dev liblapacke-dev libopenblas-dev python3 python3-venv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
make candidate test
```

Para comprobar toda la refactorización:

```bash
python3 scripts/verify_code_refactor.py
```

## Los cinco archivos de la implementación final

Si la profesora pide directamente la solución final, se muestran:

1. `src/implementacion_final/main_candidate.c`: entrada, selección secuencial/MPI, medición, reunión y CSV.
2. `src/implementacion_final/cholesky.c`: generación SPD, kernels secuenciales y validación.
3. `src/implementacion_final/cholesky_mpi.c`: reparto de columnas y right-looking MPI con vector local.
4. `src/implementacion_final/cholesky.h`: interfaz secuencial.
5. `src/implementacion_final/cholesky_mpi.h`: tipos e interfaz MPI.

Demostración mínima:

```bash
make candidate
./build/cholesky_candidate_seq 256
mpirun --bind-to core --map-by core -np 3 ./build/cholesky_candidate_mpi 256
```

---

# Etapa 1: decisiones secuenciales

## Experimento 1: Left-looking frente a Right-looking

### 1. ¿Qué queríamos probar?

Implementamos Cholesky, (A=LL^T), en C y en un solo proceso. Left-looking calcula la columna actual consultando columnas anteriores. Right-looking usa cada columna terminada para actualizar la región restante. La pregunta fue si dos órdenes matemáticamente equivalentes tenían el mismo rendimiento en memoria.

### 2. ¿Qué archivo se abre?

En `src/implementacion_final/cholesky.c`:

- `cholesky_left()`, cerca de la línea 154.
- `cholesky_right()`, cerca de la línea 195.

El cronómetro comparativo está en `src/experimentos/compare_seq.c`.

### 3. ¿Cómo se demuestra?

```bash
make all test
./build/compare_seq 256 7 2026
```

Los parámetros son N, repeticiones y semilla. Ambas variantes deben dar un residuo válido; la diferencia estudiada es el tiempo.

### 4. ¿Cómo se repite la campaña?

```bash
bash scripts/comparar_variantes.sh scratch/etapa1_left_right
```

## Experimento 2: Right-looking con columna contigua

### 1. ¿Qué queríamos probar?

El right-looking original relee la columna activa dando saltos de N elementos. La hipótesis fue copiarla a un vector contiguo. Copiar cuesta tiempo, pero puede mejorar la caché durante la actualización pesada.

### 2. ¿Qué archivo se abre?

En `src/implementacion_final/cholesky.c`:

- `cholesky_right()`, cerca de la línea 195.
- `cholesky_right_buffered()`, cerca de la línea 237.

`src/experimentos/compare_memory.c` compara Left, Right y Right con vector en seis órdenes equilibrados.

### 3. ¿Cómo se demuestra?

```bash
make all test
./build/compare_memory 256 12 2026
```

Las repeticiones deben ser múltiplo de seis.

### 4. ¿Cómo se repite la campaña?

```bash
bash scripts/comparar_memoria.sh scratch/etapa1_memoria
```


# Etapa 2: primer reparto MPI

## Experimento 3: columnas contiguas frente a cíclicas

### 1. ¿Qué queríamos probar?

Comparamos un reparto contiguo de columnas con uno cíclico, donde la columna k pertenece al proceso `k % P`. El cíclico buscaba equilibrar el trabajo decreciente, aunque comunicación y acceso local también influyen.

### 2. ¿Qué archivos se abren?

- `src/implementacion_final/cholesky_mpi.c`: `layout_create()`, `layout_owner()`, `layout_global()` y `cholesky_mpi()`.
- `src/experimentos/compare_mpi.c`: comparación y validación.
- `src/implementacion_final/cholesky_mpi.h`: definición de `Layout`.

### 3. ¿Cómo se demuestra?

```bash
make mpi test-mpi
mpirun --bind-to core --map-by core -np 3 ./build/compare_mpi 512 8
```

Perfil de fases:

```bash
mpirun --bind-to core --map-by core -np 3 ./build/compare_mpi 512 3 profile
```

### 4. ¿Cómo se repite la campaña?

```bash
bash scripts/comparar_mpi.sh scratch/etapa2_mpi
```

# Etapa 3: vector local dentro de MPI

## Experimento 4: cuatro combinaciones

### 1. ¿Qué queríamos probar?

Se cruzaron reparto contiguo/cíclico y kernel original/con vector local. Así se separó el efecto del reparto del efecto de la localidad de memoria.

### 2. ¿Qué archivos se abren?

- `src/implementacion_final/cholesky_mpi.c`: `cholesky_mpi()` y `cholesky_mpi_local()`, esta última cerca de la línea 220.
- `src/experimentos/compare_mpi_local.c`: cuatro variantes y orden equilibrado.
- `tests/test_buffered.c`: centinelas del vector auxiliar.

### 3. ¿Cómo se demuestra?

```bash
make mpi-local test-mpi-local
mpirun --bind-to core --map-by core -np 3 ./build/compare_mpi_local 512 8
mpirun --bind-to core --map-by core -np 3 ./build/compare_mpi_local 1024 4 profile
```

### 4. ¿Cómo se repite la campaña?

```bash
bash scripts/comparar_mpi_local.sh scratch/etapa3_mpi_local
```

# Etapa 4: umbral de utilidad de MPI

### 1. ¿Qué queríamos probar?

MPI agrega lanzamiento, comunicación y sincronización. Se recorrieron N=64..256, varios P y tres órdenes para localizar el primer tamaño con mejora repetible frente a una referencia secuencial contemporánea.

### 2. ¿Qué archivos se abren?

- `src/experimentos/compare_mpi_local.c`.
- `src/experimentos/compare_memory.c`.
- `scripts/medir_umbral.sh`: grilla y tres rondas.
- `scripts/analizar_umbral.py`: análisis histórico.

### 3. ¿Cómo se demuestra rápidamente?

```bash
make all mpi-local
./build/compare_memory 192 6 2026
mpirun --bind-to core --map-by core -np 3 ./build/compare_mpi_local 192 8
```

### 4. ¿Cómo se repite la campaña?

```bash
bash scripts/medir_umbral.sh scratch/etapa4_umbral
```

El cruce depende del equipo; no es una constante universal.


# Etapa 5: Left-looking MPI frente a Right-looking MPI

### 1. ¿Qué queríamos probar?

Con el mismo reparto cíclico comparamos dos coordinaciones. Right difunde una columna por paso. La implementación left acumula contribuciones, reduce resultados y difunde el pivote. La pregunta fue cuál funcionaba mejor en estas implementaciones.

### 2. ¿Qué archivos se abren?

- `src/experimentos/cholesky_left_mpi.c`.
- `src/implementacion_final/cholesky_mpi.c`.
- `src/experimentos/compare_mpi_algorithms.c`.

### 3. ¿Cómo se demuestra?

```bash
make mpi-algorithms test-mpi-algorithms
mpirun --bind-to core --map-by core -np 3 ./build/compare_mpi_algorithms 512 8
mpirun --bind-to core --map-by core -np 3 ./build/compare_mpi_algorithms 1024 4 profile
```

### 4. ¿Cómo se repite la campaña?

```bash
bash scripts/comparar_left_right_mpi.sh scratch/etapa5_algoritmos
```

La conclusión vale para estas implementaciones, no para todo algoritmo Left o Right posible.

# Etapa 6: incluir distribución y reunión

### 1. ¿Qué queríamos probar?

Una mejora del kernel puede desaparecer al mover la matriz. Se midieron distribución, factorización y reunión del factor en rango 0.

### 2. ¿Qué archivos se abren?

- `src/experimentos/compare_mpi_total.c`.
- `src/implementacion_final/cholesky_mpi.c`.
- `src/experimentos/cholesky_left_mpi.c`.

### 3. ¿Cómo se demuestra?

```bash
make mpi-total test-mpi-total
mpirun --bind-to core --map-by core -np 3 ./build/compare_mpi_total 512 12
```

Las repeticiones deben ser múltiplo de seis. Los máximos de fases de ensayos distintos no se suman como un único tiempo.

### 4. ¿Cómo se repite la campaña?

```bash
bash scripts/comparar_tiempo_total.sh scratch/etapa6_tiempo_total
```

# Etapa 7: generación centralizada frente a distribuida

### 1. ¿Qué queríamos probar?

Cada proceso pasó a generar sus columnas locales, evitando que rango 0 construyera y repartiera toda A. Se exigió igualdad bit a bit con la generación centralizada.

### 2. ¿Qué archivos se abren?

- `src/implementacion_final/cholesky.c`: `generate_spd()`, `generate_spd_columns()` y `generate_spd_selected()`.
- `src/experimentos/compare_generation.c`.
- `tests/test_projected.c`.

### 3. ¿Cómo se demuestra?

```bash
make generation test
mpirun --bind-to core --map-by core -np 3 ./build/compare_generation 512 6
```

### 4. ¿Cómo se repite la campaña?

```bash
bash scripts/comparar_generacion.sh scratch/etapa7_generacion
```

# Etapa 8: aplicaciones completas

### 1. ¿Qué queríamos probar?

Se compararon MPI con generación centralizada, MPI con generación distribuida y referencia secuencial, incluyendo reserva, generación y el flujo necesario para obtener L.

### 2. ¿Qué archivo se abre?

`src/experimentos/compare_application.c`. Los kernels están en `src/implementacion_final/`.

### 3. ¿Cómo se demuestra?

```bash
make application test-application
mpirun --bind-to core --map-by core -np 3 ./build/compare_application 512 6
```

### 4. ¿Cómo se repite la campaña?

```bash
bash scripts/comparar_aplicacion.sh scratch/etapa8_aplicacion
```

La referencia secuencial vive en rango 0 mientras los demás procesos existen; representa este banco, no un proceso aislado.


# Etapa 9: grupos de columnas

### 1. ¿Qué queríamos probar?

Se ensayó propiedad por grupos b=1,2,4,8,16,32,64. Agrupar puede reducir cambios de propietario, pero también alterar el balance. Esto no es Cholesky bloqueado BLAS-3: solo cambia la propiedad de columnas.

### 2. ¿Qué archivos se abren?

- `src/implementacion_final/cholesky_mpi.c`: `layout_block_create()`.
- `src/experimentos/compare_blocks.c`.

### 3. ¿Cómo se demuestra?

```bash
make blocks test-blocks
mpirun --bind-to core --map-by core -np 3 ./build/compare_blocks 512 7
mpirun --bind-to core --map-by core -np 3 ./build/compare_blocks 512 6 pair
```

El modo `pair` compara b=1/b=4.

### 4. ¿Cómo se repite la campaña?

```bash
bash scripts/comparar_bloques.sh scratch/etapa9_bloques
```

# Etapa 10: cierre local y LAPACK

### 1. ¿Qué queríamos probar?

Se confirmó b=1/b=4 con tamaños mayores y se incorporó `LAPACKE_dpotrf_work` con OpenBLAS de un hilo. LAPACK indica cuánto falta frente a una biblioteca especializada.

### 2. ¿Qué archivos se abren?

- `src/experimentos/compare_lapack.c`.
- `src/experimentos/compare_blocks.c`.
- `scripts/precluster_local.sh`.

### 3. ¿Cómo se demuestra?

```bash
make lapack test-lapack
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ./build/compare_lapack 512 6
```

### 4. ¿Cómo se repite la campaña?

```bash
bash scripts/precluster_local.sh scratch/etapa10_precluster
```

Si no compila, instalar LAPACKE/OpenBLAS o adaptar las rutas de una instalación Conda.

# Etapa 11: programa candidato final

### 1. ¿Qué queríamos lograr?

Se consolidó una entrada con dos compilaciones comparables: secuencial y MPI right-looking, cíclico b=1, vector local y generación distribuida.

### 2. ¿Qué archivos se abren?

Los cinco archivos de `src/implementacion_final/`. El punto de entrada es `main_candidate.c`, con `main()` cerca de la línea 59. El Makefile muestra que el candidato MPI no enlaza LAPACK.

### 3. ¿Cómo se demuestra?

```bash
make candidate test
./build/cholesky_candidate_seq 512
mpirun --bind-to core --map-by core -np 3 ./build/cholesky_candidate_mpi 512
```

La salida CSV informa fases y controles numéricos. El factor se reúne en rango 0.

# Etapa 12: speedup hasta obtener L

### 1. ¿Qué queríamos probar?

Con el candidato congelado se comparó `factor_s`. Speedup es tiempo de referencia dividido por tiempo MPI; mayor que uno indica mejora en esa métrica y entorno.

### 2. ¿Qué archivos se abren?

- `src/implementacion_final/main_candidate.c`.
- `scripts/cierre_local.sh`.
- `scripts/analizar_cierre.py`.

### 3. ¿Cómo se demuestra?

```bash
mkdir -p scratch/etapa12
./build/cholesky_candidate_seq 1024 > scratch/etapa12/seq.csv
mpirun --bind-to core --map-by core -np 3 ./build/cholesky_candidate_mpi 1024 > scratch/etapa12/mpi.csv
```

Una ejecución sirve para mostrar el formato; la conclusión usa repeticiones y medianas.

# Etapa 13: comando completo

### 1. ¿Qué queríamos probar?

El usuario espera desde que lanza el comando hasta que termina. Este reloj agrega el arranque de `mpirun` y creación de procesos, por lo que puede reducir la ventaja observada dentro del kernel.

### 2. ¿Qué archivos se abren?

- `src/experimentos/measure_command.c`.
- `src/implementacion_final/main_candidate.c`.
- `scripts/verificar_interfaz_candidato.sh`.

### 3. ¿Cómo se demuestra?

```bash
make candidate
mkdir -p scratch/etapa13
./build/measure_command scratch/etapa13/seq.time.csv \
  ./build/cholesky_candidate_seq 512 > scratch/etapa13/seq.csv
./build/measure_command scratch/etapa13/mpi.time.csv \
  mpirun --bind-to core --map-by core -np 3 \
  ./build/cholesky_candidate_mpi 512 > scratch/etapa13/mpi.csv
```

Los `*.time.csv` contienen `external_s` y el código de salida; los otros CSV contienen relojes internos.

# Etapa 14: repetir en otra sesión

### 1. ¿Qué queríamos probar?

Se repitió el candidato sin cambiar el algoritmo para comprobar si la decisión sobrevivía a otra sesión. Se conservaron ambas campañas.

### 2. ¿Qué archivos se usan?

- `scripts/cierre_local.sh`.
- `data/raw/local/cierre_local_20260924/`.
- `data/raw/local/cierre_local_20260927/`.

### 3. ¿Cómo se repite?

Campaña completa:

```bash
bash scripts/cierre_local.sh scratch/etapa14_repeticion
```

Comprobación breve:

```bash
make candidate test
./build/cholesky_candidate_seq 256
mpirun --bind-to core --map-by core -np 3 ./build/cholesky_candidate_mpi 256
```

Cada repetición nueva debe guardarse como campaña nueva con fecha, entorno y hashes.


# Etapas 15–19: trabajo en el clúster

El registro completo está en [scripts_cluster_20260928.md](scripts_cluster_20260928.md). Sus bloques se clasifican como **EXACTO**, **BLOQUE DE TERMINAL** o **RECONSTRUIDO**. Esta distinción debe conservarse al exponer: las campañas de cruce y escalabilidad tienen reconstrucciones fieles al protocolo; el launcher final grande sí quedó preservado exactamente.

Históricamente, los archivos estaban planos en `~/cholesky`. En el repositorio actual, los fuentes están en `src/implementacion_final/` y `src/experimentos/`, y los ejecutables en `build/`.

# Etapa 15: exploración y diagnóstico inicial

### 1. ¿Qué queríamos comprobar?

Antes de medir se registraron CPU visibles, cuota, memoria, cpuset, versiones y binding. Después se validó el candidato y se hicieron pilotos N=512, 1024, 2048 y 4096. Las 128 CPU visibles por `lscpu` no equivalían a 128 CPU concedidas: las campañas principales tuvieron una cuota agregada de seis CPU y 24 GiB.

### 2. ¿Qué archivos se utilizan?

- Código: los cinco archivos de `src/implementacion_final/`.
- Evidencia: `data/raw/cluster/evidencia_preformal_20260928.tar.gz`.
- Comandos originales: secciones 1–9 de `docs/scripts_cluster_20260928.md`.

### 3. Diagnóstico inicial

```bash
nproc
lscpu
cat /sys/fs/cgroup/cpu.max
cat /sys/fs/cgroup/memory.max
cat /sys/fs/cgroup/cpuset.cpus.effective
gcc --version
mpicc --version
mpirun --version
python --version

mpirun --report-bindings --bind-to core --map-by core -np 6 /bin/true
```

Las rutas cgroup pueden cambiar en otro servicio; debe registrarse el mecanismo equivalente.

### 4. Compilación, hashes y validación actuales

```bash
make candidate test

sha256sum \
  src/implementacion_final/main_candidate.c \
  src/implementacion_final/cholesky.c \
  src/implementacion_final/cholesky.h \
  src/implementacion_final/cholesky_mpi.c \
  src/implementacion_final/cholesky_mpi.h

./build/cholesky_candidate_seq 128
mpirun --bind-to core --map-by core -np 6 \
  ./build/cholesky_candidate_mpi 128
```

### 5. Pilotos y control de throttling

```bash
for n in 512 1024 2048 4096; do
  taskset -c 0 ./build/cholesky_candidate_seq "$n"
  mpirun --bind-to core --map-by core -np 6 \
    ./build/cholesky_candidate_mpi "$n"
done

cat /sys/fs/cgroup/cpu.stat
mpirun --bind-to core --map-by core -np 6 \
  ./build/cholesky_candidate_mpi 4096
cat /sys/fs/cgroup/cpu.stat
```

El cambio de `nr_throttled` o `throttled_usec` ayuda a interpretar la cuota, pero no demuestra por sí solo la causa de cada variación.

### 6. Reanalizar la evidencia

```bash
python3 scripts/analyze_results.py
```

---

# Etapa 16: campaña formal de cruce

### 1. ¿Qué queríamos probar?

Se buscó el primer N ensayado con mejora clara de MPI. El protocolo documentado fue:

- N=128, 160, 192, 224 y 256.
- Métodos `seq`, P=1, 2, 3, 4 y 6.
- Un warmup y siete rondas útiles.
- Orden de métodos rotado.
- `taskset -c 0` para secuencial.
- Binding por núcleo para MPI.
- CSV y stderr separados.

### 2. ¿Qué archivos se utilizan?

- `build/cholesky_candidate_seq` y `build/cholesky_candidate_mpi`.
- `data/raw/cluster/campana_cruce_20260928.tar.gz`.
- `data/processed/first_crossing.csv` y `summary_crossing.csv`.
- `figures/01_cruce_application_vs_n.svg` y `02_cruce_speedup.svg`.
- Launcher reconstruido: sección 10 de `docs/scripts_cluster_20260928.md`.

### 3. Bug documentado y corrección

El launcher original asignó `rep="$3"` sin `local` dentro de `run_case()`, alterando la variable exterior y generando nombres anómalos. Los originales no se renombraron dentro del tar. La reconstrucción corrige:

```bash
run_case() {
    local n="$1"
    local method="$2"
    local rep_tag="$3"
    # ...
}
```

La reconstrucción reproduce el protocolo, pero no es una copia byte por byte.

### 4. ¿Cómo se vuelve a medir?

```bash
make candidate
```

Usar el launcher completo de la sección 10 y sustituir:

```text
./cholesky_candidate_seq -> ./build/cholesky_candidate_seq
./cholesky_candidate_mpi -> ./build/cholesky_candidate_mpi
```

La salida debe ir a una carpeta nueva. Para reanalizar la campaña preservada:

```bash
python3 scripts/analyze_results.py
```

---

# Etapa 17: escalabilidad con dos relojes

### 1. ¿Qué queríamos probar?

Se midió N=512, 1024, 2048 y 4096 con `seq` y P=1,2,3,4,6. Hubo un warmup, siete rondas útiles y orden rotado. Cada caso guardó:

- Reloj interno del candidato.
- Reloj externo de `measure_command`.
- Stderr.
- `cpu.stat` antes y después de la campaña.

### 2. ¿Qué archivos se utilizan?

- `src/experimentos/measure_command.c`.
- `src/implementacion_final/main_candidate.c`.
- `data/raw/cluster/campana_escalabilidad_20260928.tar.gz`.
- `data/processed/summary_scalability.csv` y `summary_external.csv`.
- Figuras 03, 04, 05 y `figures/14_fronteras_medicion.svg`.
- Launcher reconstruido: sección 13 del registro.

### 3. Control breve del reloj externo

```bash
make candidate
mkdir -p scratch/control_externo

./build/measure_command scratch/control_externo/seq.csv \
  taskset -c 0 ./build/cholesky_candidate_seq 128

./build/measure_command scratch/control_externo/mpi.csv \
  mpirun --bind-to core --map-by core -np 6 \
  ./build/cholesky_candidate_mpi 128
```

### 4. ¿Cómo se vuelve a medir?

Usar la reconstrucción de la sección 13 y sustituir:

```text
./measure_command        -> ./build/measure_command
./cholesky_candidate_seq -> ./build/cholesky_candidate_seq
./cholesky_candidate_mpi -> ./build/cholesky_candidate_mpi
```

Debe describirse como reconstrucción fiel, no como script original exacto.

---

# Etapa 18: LAPACK/OpenBLAS en el clúster

### 1. ¿Qué queríamos probar?

Se comparó el kernel propio con `LAPACKE_dpotrf_work` usando OpenBLAS de un hilo. La campaña principal midió N=2048 y N=4096 con seis repeticiones equilibradas.

### 2. ¿Qué archivos se utilizan?

- `src/experimentos/compare_lapack.c`.
- `src/implementacion_final/cholesky.c`.
- `data/raw/cluster/campana_lapack_cluster_20260928.tar.gz`.
- `data/processed/summary_lapack.csv`.
- `figures/07_lapack_cluster.svg`.
- Secciones 14–21 de `docs/scripts_cluster_20260928.md`.

### 3. Diagnóstico de bibliotecas

```bash
ldconfig -p 2>/dev/null | grep -Ei 'lapacke|lapack|openblas' || true
pkg-config --list-all 2>/dev/null | grep -Ei 'lapacke|lapack|openblas' || true

echo "$CONDA_PREFIX"
conda list | grep -Ei 'lapack|lapacke|openblas|blas' || true
find "$CONDA_PREFIX" \
  \( -name 'lapacke.h' -o -name 'liblapacke.so*' \
     -o -name 'liblapack.so*' -o -name 'libopenblas.so*' \) \
  2>/dev/null | sort
```

### 4. Compilación actual con Conda

```bash
mkdir -p build
gcc -O3 -std=c11 -Wall -Wextra -Wpedantic \
  -Isrc/implementacion_final -Isrc/experimentos \
  -I"$CONDA_PREFIX/include" \
  src/experimentos/compare_lapack.c \
  src/implementacion_final/cholesky.c \
  src/experimentos/bench_utils.c \
  -L"$CONDA_PREFIX/lib" -Wl,-rpath,"$CONDA_PREFIX/lib" \
  -llapacke -lopenblas -lm \
  -o build/compare_lapack_cluster
```

Con bibliotecas del sistema basta `make lapack test-lapack`.

### 5. Un hilo, test y campaña

```bash
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1

taskset -c 0 ./build/compare_lapack_cluster --test
taskset -c 0 ./build/compare_lapack_cluster 512 6

mkdir -p scratch/campana_lapack_nueva
for n in 2048 4096; do
  taskset -c 0 ./build/compare_lapack_cluster "$n" 6 \
    > "scratch/campana_lapack_nueva/n$n.csv" \
    2> "scratch/campana_lapack_nueva/n$n.err"
done
```

El mensaje de configuración OpenBLAS en stderr es informativo. Los CSV históricos no contienen `valid` ni exit code.

---

# Etapa 19: comparación final grande MPI frente a LAPACK

### 1. ¿Qué queríamos probar?

Se extendió la comparación a N=6144 y N=8192. Primero hubo pilotos LAPACK y MPI P=6. Luego se ejecutó `run_campana_final_grande.sh`, cuyo bloque sí se preservó exactamente.

El resultado histórico fue acercamiento relativo, no cruce: MPI mejoró frente al secuencial propio, pero LAPACK de un hilo siguió siendo más rápido.

### 2. ¿Qué archivos se utilizan?

- Candidato: `src/implementacion_final/`.
- Referencia: `src/experimentos/compare_lapack.c`.
- Evidencia: `data/raw/cluster/campana_final_grande_20260928.tar.gz`.
- Resumen: `data/processed/summary_large_comparison.csv`.
- Figuras 08 y 09.
- Script exacto: sección 27 de `docs/scripts_cluster_20260928.md`.

### 3. Pilotos documentados

```bash
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1

taskset -c 0 ./build/compare_lapack_cluster 6144 2
mpirun --bind-to core --map-by core -np 6 \
  ./build/cholesky_candidate_mpi 6144

taskset -c 0 ./build/compare_lapack_cluster 8192 2
mpirun --bind-to core --map-by core -np 6 \
  ./build/cholesky_candidate_mpi 8192
```

### 4. ¿Qué hizo el launcher final?

1. Rechazó sobrescribir una carpeta existente.
2. Fijó OpenBLAS y OMP en un hilo.
3. Registró fecha, host, cuota, memoria, cpuset, CPU, GCC, MPI, Conda, variables, `ldd` e hashes.
4. Guardó `cpu.stat` antes y después.
5. Para N=6144: banco propio/LAPACK, warmup MPI y seis MPI P=6.
6. Para N=8192: warmup MPI, seis MPI P=6 y luego banco propio/LAPACK.
7. Verificó conteos, `valid=1` y stderr MPI.
8. Generó hashes, tar.gz y hash del paquete.

El orden fue diferente para 6144 y 8192 de forma deliberada. Cambiarlo crea otra campaña.

### 5. ¿Cómo se vuelve a ejecutar desde la estructura actual?

```bash
make candidate
# Bibliotecas del sistema:
make lapack test-lapack
# Con Conda, compilar build/compare_lapack_cluster como en la Etapa 18.
```

Tomar el script exacto de la sección 27 y adaptar solo las rutas:

```text
./compare_lapack_cluster  -> ./build/compare_lapack_cluster
./cholesky_candidate_mpi -> ./build/cholesky_candidate_mpi
compare_lapack.c          -> src/experimentos/compare_lapack.c
cholesky.c/.h             -> src/implementacion_final/cholesky.c/.h
cholesky_mpi.c/.h         -> src/implementacion_final/cholesky_mpi.c/.h
main_candidate.c          -> src/implementacion_final/main_candidate.c
```

Elegir un nombre de salida nuevo. N=6144/8192 requieren memoria considerable y no son apropiados para una demostración oral.

### 6. Empaquetado e integridad

```bash
tar -czf NOMBRE_CAMPAÑA.tar.gz NOMBRE_CAMPAÑA/
sha256sum NOMBRE_CAMPAÑA.tar.gz > NOMBRE_CAMPAÑA.tar.gz.sha256
```

Paquetes preservados:

```text
evidencia_preformal_20260928.tar.gz
campana_cruce_20260928.tar.gz
campana_escalabilidad_20260928.tar.gz
campana_lapack_cluster_20260928.tar.gz
campana_final_grande_20260928.tar.gz
```

### 7. Reconstruir el informe

```bash
python3 scripts/analyze_results.py
python3 scripts/build_documentation.py
python3 scripts/verify_delivery.py
```

---

# Recorrido corto para la defensa

Si hay pocos minutos:

1. Abrir `src/implementacion_final/main_candidate.c` y explicar el flujo.
2. Abrir `src/implementacion_final/cholesky.c` y mostrar `cholesky_right_buffered()`.
3. Abrir `src/implementacion_final/cholesky_mpi.c` y mostrar `layout_owner()` y `cholesky_mpi_local()`.
4. Ejecutar:

```bash
make candidate test
./build/cholesky_candidate_seq 256
mpirun --bind-to core --map-by core -np 3 ./build/cholesky_candidate_mpi 256
```

5. Mostrar `figures/08_comparacion_final.svg`.
6. Explicar que `src/experimentos/` justifica decisiones, pero no todo se enlaza al candidato final.

## Tabla rápida

| Pregunta | Código | Compilación | Demostración |
|---|---|---|---|
| Left vs Right | `cholesky.c`, `compare_seq.c` | `make all` | `./build/compare_seq 256 7 2026` |
| Vector contiguo | `cholesky.c`, `compare_memory.c` | `make all` | `./build/compare_memory 256 12 2026` |
| Repartos MPI | `cholesky_mpi.c`, `compare_mpi.c` | `make mpi` | `mpirun -np 3 ./build/compare_mpi 512 8` |
| Vector local MPI | `compare_mpi_local.c` | `make mpi-local` | `mpirun -np 3 ./build/compare_mpi_local 512 8` |
| Left vs Right MPI | `compare_mpi_algorithms.c` | `make mpi-algorithms` | `mpirun -np 3 ./build/compare_mpi_algorithms 512 8` |
| Flujo MPI | `compare_mpi_total.c` | `make mpi-total` | `mpirun -np 3 ./build/compare_mpi_total 512 12` |
| Generación | `compare_generation.c` | `make generation` | `mpirun -np 3 ./build/compare_generation 512 6` |
| Aplicación | `compare_application.c` | `make application` | `mpirun -np 3 ./build/compare_application 512 6` |
| Grupos b | `compare_blocks.c` | `make blocks` | `mpirun -np 3 ./build/compare_blocks 512 7` |
| LAPACK | `compare_lapack.c` | `make lapack` | `OPENBLAS_NUM_THREADS=1 ./build/compare_lapack 512 6` |
| Candidato | `src/implementacion_final/` | `make candidate` | `mpirun -np 3 ./build/cholesky_candidate_mpi 512` |
| Análisis | `scripts/analyze_results.py` | Python | `python3 scripts/analyze_results.py` |

## Conclusiones defendibles

- Todas las variantes se validan numéricamente antes de usar sus tiempos.
- El vector contiguo mejoró la localidad de memoria del right-looking.
- El candidato usa right-looking, propiedad cíclica b=1, vector local y generación distribuida.
- MPI tiene un umbral: para matrices pequeñas dominan sus costos.
- El reloj externo muestra menos mejora cuando pesa el arranque de MPI.
- MPI superó al secuencial propio en ciertos tamaños, pero no a LAPACK/OpenBLAS de un hilo.
- Las conclusiones pertenecen al hardware, bibliotecas, cuota y protocolo registrados.

## Errores que conviene evitar

- No decir que b=4 es el candidato final: la confirmación posterior llevó a b=1.
- No llamar «bloqueado BLAS-3» a `compare_blocks.c`.
- No sumar máximos de fases de ejecuciones diferentes.
- No presentar una corrida en vivo como resultado estadístico.
- No confundir CPU visibles con CPU concedidas.
- No atribuir los tiempos históricos a los fuentes comentados actuales sin mencionar los snapshots y hashes de cada campaña.
