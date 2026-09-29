# Scripts y bloques de ejecución enviados al clúster — 28/09/2026

> Proyecto: **Factorización de Cholesky HPC**
>
> Este documento reúne los **scripts y bloques de Bash enviados o pegados en el clúster durante la jornada del 28/09/2026**.
>
> **Fidelidad:**
> - **EXACTO**: bloque preservado en la conversación.
> - **RECONSTRUIDO**: el launcher exacto no quedó archivado, pero su protocolo sí; se reconstruye sin inventar resultados.
> - **BLOQUE DE TERMINAL**: comandos pegados directamente en shell, aunque no se guardaran como `.sh`.
>
> No se incluyen resultados ni análisis; sólo ejecución y reproducibilidad.

---

## 1. Diagnóstico inicial del clúster

**Tipo:** BLOQUE DE TERMINAL

```bash
cd ~/cholesky

nproc
lscpu

cat /sys/fs/cgroup/cpu.max
cat /sys/fs/cgroup/memory.max
cat /sys/fs/cgroup/cpuset.cpus.effective

gcc --version
mpicc --version
mpirun --version
python --version
```

---

## 2. Diagnóstico de binding MPI

**Tipo:** EXACTO

```bash
mpirun \
  --report-bindings \
  --bind-to core \
  --map-by core \
  -np 6 \
  /bin/true
```

---

## 3. Verificación de hashes de fuentes

**Tipo:** BLOQUE DE TERMINAL

```bash
cd ~/cholesky

sha256sum \
  main_candidate.c \
  cholesky.c \
  cholesky.h \
  cholesky_mpi.c \
  cholesky_mpi.h
```

---

## 4. Compilación del candidato secuencial

**Tipo:** EXACTO

```bash
cd ~/cholesky

gcc -O3 -std=c11 -Wall -Wextra -Wpedantic \
  main_candidate.c cholesky.c -lm \
  -o cholesky_candidate_seq \
  2>&1 | tee build_candidate_seq.log
```

---

## 5. Compilación del candidato MPI

**Tipo:** EXACTO

```bash
cd ~/cholesky

mpicc -O3 -std=c11 -Wall -Wextra -Wpedantic -DUSE_MPI \
  main_candidate.c cholesky.c cholesky_mpi.c -lm \
  -o cholesky_candidate_mpi \
  2>&1 | tee build_candidate_mpi.log
```

---

## 6. Validación inicial del candidato

**Tipo:** BLOQUE DE TERMINAL

### Secuencial

```bash
./cholesky_candidate_seq 128
```

### MPI P=6

```bash
mpirun \
  --bind-to core \
  --map-by core \
  -np 6 \
  ./cholesky_candidate_mpi 128
```

---

## 7. Pilotos iniciales

**Tipo:** BLOQUE DE TERMINAL

Patrón secuencial:

```bash
taskset -c 0 ./cholesky_candidate_seq N
```

Patrón MPI P=6:

```bash
mpirun \
  --bind-to core \
  --map-by core \
  -np 6 \
  ./cholesky_candidate_mpi N
```

Tamaños utilizados como pilotos:

```text
512
1024
2048
4096
```

---

## 8. Control repetido de N=4096

**Tipo:** BLOQUE DE TERMINAL

```bash
taskset -c 0 ./cholesky_candidate_seq 4096
```

```bash
mpirun \
  --bind-to core \
  --map-by core \
  -np 6 \
  ./cholesky_candidate_mpi 4096
```

---

## 9. Diagnóstico de throttling

**Tipo:** BLOQUE DE TERMINAL

```bash
echo "=== ANTES ==="
cat /sys/fs/cgroup/cpu.stat

mpirun \
  --bind-to core \
  --map-by core \
  -np 6 \
  ./cholesky_candidate_mpi 4096

echo "=== DESPUES ==="
cat /sys/fs/cgroup/cpu.stat
```

---

# 10. Campaña formal de cruce

**Tipo:** RECONSTRUIDO

El launcher exacto no quedó archivado. Sí quedó documentado el protocolo:

- `N=128,160,192,224,256`
- `SEQ`, `P=1,2,3,4,6`
- una ronda de warmup
- siete rondas útiles
- orden rotado
- `taskset -c 0` para secuencial
- `mpirun --bind-to core --map-by core` para MPI
- `.csv` y `.err` por ejecución

El script original tuvo un bug al usar `rep="$3"` sin `local` dentro de `run_case()`, modificando la variable exterior.

### Fragmento problemático documentado

```bash
run_case() {
    n="$1"
    method="$2"
    rep="$3"
    ...
}
```

### Reconstrucción corregida

```bash
#!/usr/bin/env bash
set -euo pipefail

OUT="campana_cruce_20260928"
mkdir -p "$OUT"

SIZES=(128 160 192 224 256)
METHODS=(seq p1 p2 p3 p4 p6)

run_case() {
    local n="$1"
    local method="$2"
    local rep_tag="$3"

    local csv="$OUT/n${n}_${method}_${rep_tag}.csv"
    local err="$OUT/n${n}_${method}_${rep_tag}.err"

    if [[ "$method" == "seq" ]]; then
        taskset -c 0 \
            ./cholesky_candidate_seq "$n" \
            2>"$err" \
            | tee "$csv"
    else
        local p="${method#p}"

        mpirun \
            --bind-to core \
            --map-by core \
            -np "$p" \
            ./cholesky_candidate_mpi "$n" \
            2>"$err" \
            | tee "$csv"
    fi
}

for n in "${SIZES[@]}"; do
    for method in "${METHODS[@]}"; do
        run_case "$n" "$method" "warmup"
    done
done

for round in 1 2 3 4 5 6 7; do
    start=$(( (round - 1) % ${#METHODS[@]} ))

    for n in "${SIZES[@]}"; do
        for offset in 0 1 2 3 4 5; do
            idx=$(( (start + offset) % ${#METHODS[@]} ))
            method="${METHODS[$idx]}"
            run_case "$n" "$method" "rep${round}"
        done
    done
done
```

> Esta versión reproduce el protocolo y corrige el defecto de nombres; no es una copia byte por byte del launcher original.

---

## 11. Compilación de `measure_command.c`

**Tipo:** EXACTO

```bash
cd ~/cholesky

gcc -O3 -std=c11 -Wall -Wextra -Wpedantic \
  measure_command.c \
  -o measure_command \
  2>&1 | tee build_measure_command.log
```

---

## 12. Control del reloj externo

**Tipo:** BLOQUE DE TERMINAL

### Secuencial

```bash
./measure_command externo_seq_n128.csv \
  taskset -c 0 \
  ./cholesky_candidate_seq 128
```

### MPI P=6

```bash
./measure_command externo_mpi_n128_p6.csv \
  mpirun \
    --bind-to core \
    --map-by core \
    -np 6 \
    ./cholesky_candidate_mpi 128
```

---

# 13. Campaña formal de escalabilidad con dos relojes

**Tipo:** RECONSTRUIDO

Protocolo documentado:

- `N=512,1024,2048,4096`
- `SEQ`, `P=1,2,3,4,6`
- una ronda de warmup
- siete rondas útiles
- orden rotado
- afinidad secuencial con `taskset -c 0`
- MPI con binding por core
- reloj interno del candidato
- reloj externo mediante `measure_command`
- `.err` por ejecución

### Reconstrucción funcional

```bash
#!/usr/bin/env bash
set -euo pipefail

OUT="campana_escalabilidad_20260928"
mkdir -p "$OUT"

SIZES=(512 1024 2048 4096)
METHODS=(seq p1 p2 p3 p4 p6)

run_case() {
    local n="$1"
    local method="$2"
    local rep_tag="$3"

    local internal="$OUT/n${n}_${method}_${rep_tag}_internal.csv"
    local external="$OUT/n${n}_${method}_${rep_tag}_external.csv"
    local err="$OUT/n${n}_${method}_${rep_tag}.err"

    if [[ "$method" == "seq" ]]; then
        ./measure_command "$external" \
            taskset -c 0 \
            ./cholesky_candidate_seq "$n" \
            2>"$err" \
            | tee "$internal"
    else
        local p="${method#p}"

        ./measure_command "$external" \
            mpirun \
                --bind-to core \
                --map-by core \
                -np "$p" \
                ./cholesky_candidate_mpi "$n" \
            2>"$err" \
            | tee "$internal"
    fi
}

cp /sys/fs/cgroup/cpu.stat "$OUT/cpu_stat_antes.txt"

for n in "${SIZES[@]}"; do
    for method in "${METHODS[@]}"; do
        run_case "$n" "$method" "warmup"
    done
done

for round in 1 2 3 4 5 6 7; do
    start=$(( (round - 1) % ${#METHODS[@]} ))

    for n in "${SIZES[@]}"; do
        for offset in 0 1 2 3 4 5; do
            idx=$(( (start + offset) % ${#METHODS[@]} ))
            method="${METHODS[$idx]}"
            run_case "$n" "$method" "rep${round}"
        done
    done
done

cp /sys/fs/cgroup/cpu.stat "$OUT/cpu_stat_despues.txt"
```

> Reconstrucción fiel al protocolo, no copia literal del launcher original.

---

## 14. Comprobación de LAPACK / OpenBLAS

**Tipo:** EXACTO

```bash
echo "=== LAPACKE / LAPACK / OPENBLAS ==="

ldconfig -p 2>/dev/null \
    | grep -Ei 'lapacke|lapack|openblas' \
    || true

echo
echo "=== PKG-CONFIG ==="

pkg-config --list-all 2>/dev/null \
    | grep -Ei 'lapacke|lapack|openblas' \
    || true
```

---

## 15. Comprobación de Conda

**Tipo:** EXACTO

```bash
echo "=== CONDA PREFIX ==="
echo "$CONDA_PREFIX"

echo
echo "=== PAQUETES CONDA ==="
conda list 2>/dev/null | grep -Ei 'lapack|lapacke|openblas|blas' || true

echo
echo "=== HEADERS / LIBRERIAS EN CONDA ==="
find "$CONDA_PREFIX" \
    \( -name 'lapacke.h' \
    -o -name 'liblapacke.so*' \
    -o -name 'liblapack.so*' \
    -o -name 'libopenblas.so*' \) \
    2>/dev/null | sort
```

También:

```bash
conda list | grep -Ei 'lapack|openblas|blas'

find "$CONDA_PREFIX" \
    \( -name 'lapacke.h' \
    -o -name 'liblapacke.so*' \
    -o -name 'liblapack.so*' \
    -o -name 'libopenblas.so*' \) \
    2>/dev/null | sort
```

---

## 16. Compilación de `compare_lapack_cluster`

**Tipo:** EXACTO

```bash
cd ~/cholesky

gcc -O3 -std=c11 -Wall -Wextra -Wpedantic \
    compare_lapack.c cholesky.c \
    -I"$CONDA_PREFIX/include" \
    -L"$CONDA_PREFIX/lib" \
    -Wl,-rpath,"$CONDA_PREFIX/lib" \
    -llapacke -lopenblas -lm \
    -o compare_lapack_cluster \
    2>&1 | tee build_compare_lapack_cluster.log
```

---

## 17. Forzar OpenBLAS a un hilo

**Tipo:** EXACTO

```bash
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
```

---

## 18. Test de LAPACK/OpenBLAS

**Tipo:** EXACTO

```bash
taskset -c 0 ./compare_lapack_cluster --test \
    2>&1 | tee compare_lapack_cluster_test.log
```

---

## 19. Control LAPACK N=512

**Tipo:** EXACTO

```bash
taskset -c 0 ./compare_lapack_cluster 512 6 \
    2>&1 | tee lapack_control_n512.log
```

---

# 20. Campaña LAPACK principal

**Tipo:** RECONSTRUIDO / BLOQUE DE TERMINAL

```bash
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1

mkdir -p campana_lapack_cluster_20260928

taskset -c 0 \
    ./compare_lapack_cluster 2048 6 \
    > campana_lapack_cluster_20260928/n2048.csv \
    2> campana_lapack_cluster_20260928/n2048.err

taskset -c 0 \
    ./compare_lapack_cluster 4096 6 \
    > campana_lapack_cluster_20260928/n4096.csv \
    2> campana_lapack_cluster_20260928/n4096.err
```

> El banco exacto `compare_lapack_cluster N 6` corresponde al utilizado. El wrapper/redirecciones se reconstruyen porque no quedó un `.sh` original archivado.

---

## 21. Diagnóstico tras reinicio del entorno Conda

**Tipo:** EXACTO

```bash
cd ~/cholesky

echo "=== CONDA ==="
conda list | grep -Ei 'blas|lapack|openblas' || true

echo
echo "=== LIBRERIAS ==="
ls -l /opt/conda/lib/libopenblas.so* \
      /opt/conda/lib/liblapacke.so* 2>/dev/null || true

echo
echo "=== DEPENDENCIAS DEL EJECUTABLE ==="
ldd ./compare_lapack_cluster | grep -Ei 'openblas|lapack|not found'
```

---

## 22. Piloto LAPACK N=6144

**Tipo:** EXACTO

```bash
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1

taskset -c 0 ./compare_lapack_cluster 6144 2 \
    2>&1 | tee lapack_pilot_n6144.log
```

---

## 23. Piloto MPI N=6144 P=6

**Tipo:** EXACTO

```bash
cd ~/cholesky

mpirun \
  --bind-to core \
  --map-by core \
  -np 6 \
  ./cholesky_candidate_mpi 6144 \
  2> mpi_pilot_n6144_p6.err \
  | tee mpi_pilot_n6144_p6.csv

cat mpi_pilot_n6144_p6.err
```

---

## 24. Piloto LAPACK N=8192

**Tipo:** EXACTO

```bash
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1

taskset -c 0 ./compare_lapack_cluster 8192 2 \
    2>&1 | tee lapack_pilot_n8192.log
```

---

## 25. Piloto MPI N=8192 P=6

**Tipo:** EXACTO

```bash
cd ~/cholesky

mpirun \
  --bind-to core \
  --map-by core \
  -np 6 \
  ./cholesky_candidate_mpi 8192 \
  2> mpi_pilot_n8192_p6.err \
  | tee mpi_pilot_n8192_p6.csv

cat mpi_pilot_n8192_p6.err
```

---

## 26. Comprobación final del entorno

**Tipo:** EXACTO

```bash
cd ~/cholesky

echo "=== CPU QUOTA ==="
cat /sys/fs/cgroup/cpu.max

echo
echo "=== MEMORY LIMIT ==="
cat /sys/fs/cgroup/memory.max

echo
echo "=== CPUSET ==="
cat /sys/fs/cgroup/cpuset.cpus.effective

echo
echo "=== BINARIOS ==="
ls -lh \
    ./cholesky_candidate_seq \
    ./cholesky_candidate_mpi \
    ./compare_lapack_cluster

echo
echo "=== OPENBLAS ==="
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
taskset -c 0 ./compare_lapack_cluster --test
```

---

# 27. `run_campana_final_grande.sh`

**Tipo:** EXACTO

## Creación

```bash
cd ~/cholesky

cat > run_campana_final_grande.sh <<'SCRIPT_EOF'
#!/usr/bin/env bash
set -euo pipefail

OUT="campana_final_grande_20260928"

if [ -e "$OUT" ]; then
    echo "ERROR: ya existe $OUT"
    echo "No se sobrescribirá."
    exit 1
fi

mkdir -p "$OUT"

export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1

echo "=== INICIO ==="
date -Is

{
    echo "=== FECHA INICIO ==="
    date -Is

    echo
    echo "=== HOST ==="
    hostname

    echo
    echo "=== CPU.MAX ==="
    cat /sys/fs/cgroup/cpu.max

    echo
    echo "=== MEMORY.MAX ==="
    cat /sys/fs/cgroup/memory.max

    echo
    echo "=== CPUSET ==="
    cat /sys/fs/cgroup/cpuset.cpus.effective

    echo
    echo "=== LSCPU ==="
    lscpu

    echo
    echo "=== GCC ==="
    gcc --version | head -1

    echo
    echo "=== MPIRUN ==="
    mpirun --version | head -3

    echo
    echo "=== OPENBLAS/LAPACK CONDA ==="
    conda list 2>/dev/null | grep -Ei 'blas|lapack|openblas' || true

    echo
    echo "=== VARIABLES ==="
    echo "OPENBLAS_NUM_THREADS=$OPENBLAS_NUM_THREADS"
    echo "OMP_NUM_THREADS=$OMP_NUM_THREADS"

    echo
    echo "=== DEPENDENCIAS LAPACK ==="
    ldd ./compare_lapack_cluster

    echo
    echo "=== HASHES ==="
    sha256sum \
        compare_lapack.c \
        cholesky.c \
        cholesky.h \
        cholesky_mpi.c \
        cholesky_mpi.h \
        main_candidate.c \
        compare_lapack_cluster \
        cholesky_candidate_mpi

} > "$OUT/entorno.txt" 2>&1

cp /sys/fs/cgroup/cpu.stat "$OUT/cpu_stat_antes.txt"

cp compare_lapack.c \
   cholesky.c \
   cholesky.h \
   cholesky_mpi.c \
   cholesky_mpi.h \
   main_candidate.c \
   "$OUT/"

run_lapack_pair () {
    local n="$1"

    echo
    echo "=== C PROPIO + LAPACK: N=$n ==="
    date -Is

    taskset -c 0 \
        ./compare_lapack_cluster "$n" 6 \
        2> >(tee "$OUT/n${n}_own_lapack.err" >&2) \
        | tee "$OUT/n${n}_own_lapack.csv"
}

run_mpi_warmup () {
    local n="$1"

    echo
    echo "=== MPI WARMUP: N=$n P=6 ==="
    date -Is

    mpirun \
        --bind-to core \
        --map-by core \
        -np 6 \
        ./cholesky_candidate_mpi "$n" \
        2> >(tee "$OUT/warmup_n${n}_p6.err" >&2) \
        | tee "$OUT/warmup_n${n}_p6.csv"
}

run_mpi_measured () {
    local n="$1"

    for rep in 1 2 3 4 5 6; do
        echo
        echo "=== MPI: N=$n P=6 REP=$rep ==="
        date -Is

        mpirun \
            --bind-to core \
            --map-by core \
            -np 6 \
            ./cholesky_candidate_mpi "$n" \
            2> >(tee "$OUT/n${n}_p6_rep${rep}.err" >&2) \
            | tee "$OUT/n${n}_p6_rep${rep}.csv"
    done
}

run_lapack_pair 6144
run_mpi_warmup 6144
run_mpi_measured 6144

run_mpi_warmup 8192
run_mpi_measured 8192
run_lapack_pair 8192

cp /sys/fs/cgroup/cpu.stat "$OUT/cpu_stat_despues.txt"

date -Is > "$OUT/fecha_fin.txt"

{
    echo "=== INTEGRIDAD ==="

    for n in 6144 8192; do
        echo
        echo "--- N=$n OWN/LAPACK ---"

        awk -F, '
            NR > 1 && $4 == "own"    {own++}
            NR > 1 && $4 == "lapack" {lapack++}
            END {
                print "own =", own+0
                print "lapack =", lapack+0
            }
        ' "$OUT/n${n}_own_lapack.csv"

        echo
        echo "--- N=$n MPI MEDIDO ---"

        count=$(find "$OUT" \
            -maxdepth 1 \
            -name "n${n}_p6_rep*.csv" \
            -type f | wc -l)

        echo "CSV MPI medidos = $count"

        awk -F, '
            FNR > 1 {
                rows++
                if ($NF == 1) valid++
            }
            END {
                print "filas MPI =", rows+0
                print "valid=1 =", valid+0
            }
        ' "$OUT"/n${n}_p6_rep*.csv
    done

    echo
    echo "=== STDERR MPI NO VACIOS ==="
    find "$OUT" \
        -name '*p6*.err' \
        -type f \
        -size +0c \
        -print

    echo
    echo "NOTA: los .err de own_lapack contienen normalmente"
    echo "la línea informativa OpenBLAS threads/config."

} | tee "$OUT/integridad.txt"

(
    cd "$OUT"
    sha256sum * > SHA256SUMS.txt
)

tar -czf "${OUT}.tar.gz" "$OUT"

sha256sum "${OUT}.tar.gz" \
    | tee "${OUT}.tar.gz.sha256"

echo
echo "=== CAMPAÑA FINALIZADA ==="
date -Is
echo
echo "Archivo:"
ls -lh "${OUT}.tar.gz"
SCRIPT_EOF

chmod +x run_campana_final_grande.sh
```

## Ejecución

```bash
./run_campana_final_grande.sh \
    2>&1 | tee run_campana_final_grande.log
```

---

# 28. Empaquetado y hashes de campañas

**Tipo:** RECONSTRUIDO / BLOQUE DE TERMINAL

Patrón utilizado:

```bash
tar -czf NOMBRE_CAMPAÑA.tar.gz NOMBRE_CAMPAÑA/

sha256sum NOMBRE_CAMPAÑA.tar.gz \
    > NOMBRE_CAMPAÑA.tar.gz.sha256
```

Paquetes principales de la jornada:

```text
evidencia_preformal_20260928.tar.gz
campana_cruce_20260928.tar.gz
campana_escalabilidad_20260928.tar.gz
campana_lapack_cluster_20260928.tar.gz
campana_final_grande_20260928.tar.gz
```

---

# 29. Launchers principales

```text
Campaña formal de cruce
    launcher original no preservado
    reconstrucción incluida arriba

Campaña formal de escalabilidad
    launcher original no preservado
    reconstrucción incluida arriba

Campaña LAPACK
    wrapper exacto no preservado como .sh
    comandos de ejecución reconstruidos

run_campana_final_grande.sh
    preservado de forma exacta
```

Ejecutables utilizados por esos scripts:

```text
cholesky_candidate_seq
cholesky_candidate_mpi
measure_command
compare_lapack_cluster
```

---

## Nota final de reproducibilidad

No debe presentarse la reconstrucción de los launchers de **cruce** y **escalabilidad** como copia byte por byte del script ejecutado originalmente.

Sí están documentados y preservados sus parámetros esenciales: tamaños, procesos, warmups, repeticiones, orden rotado, binding, afinidad, ejecutables y estructura de salida.

`run_campana_final_grande.sh`, en cambio, sí está reproducido a partir del bloque exacto enviado durante la sesión.
