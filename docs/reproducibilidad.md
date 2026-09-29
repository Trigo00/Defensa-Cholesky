# Reproducibilidad y trazabilidad

## Objetivo

Reproducir código, condiciones documentadas y análisis. No se promete reproducir exactamente tiempos en otra CPU, biblioteca, sesión o asignación. El análisis no ejecuta binarios procedentes de archivos comprimidos y no modifica los originales.

## Entornos medidos

| Entorno | CPU y recursos | Compilación/bibliotecas |
|---|---|---|
| WSL local | Ryzen5 2600; seis núcleos físicos, doce lógicos; sin aislamiento del anfitrión | GCC15.2.0, Open MPI5.0.10; LAPACKE3.12.1/OpenBLAS0.3.32 para referencia local |
| Clúster | AMD EPYC7B12; host visible de dos sockets, 128CPUs, dos NUMA; cpuset0-127; campañas principales cuota6CPUs, memoria24GiB | GCC13.3.0, Open MPI4.1.6; Python3.13.11 registrado en preparación |
| Biblioteca clúster | Un hilo OpenBLAS comprobado en código y logs | LAPACK/LAPACKE3.11.0, OpenBLAS0.3.34 pthreads, backend Zen |

CPU visible, cpuset y cuota no son equivalentes. Los archivos `entorno.txt`, los registros de binding y `cpu_stat_antes/despues.txt` están dentro de sus paquetes o en los directorios locales. El diagnóstico de binding no verifica por sí solo la afinidad de todas las observaciones ni la ubicación NUMA de memoria.

## Compilación del candidato

Desde el 29/09/2026, `src/implementacion_final/` y `src/experimentos/` forman la versión comentada y refactorizada. La copia exacta previa está en `archive/src_medidos_20260928`, con hashes de sus fuentes y Makefile. El análisis compara los fuentes de las campañas con esa copia medida; registra por separado que los fuentes actuales ya no coinciden byte a byte. La guía [del código](guia_codigo.md) describe los cambios y la regresión funcional, que se repite con `python3 scripts/verify_code_refactor.py`. No se atribuyen los tiempos históricos a una medición nueva de la refactorización.

Desde la raíz de esta entrega, en Linux/WSL:

```bash
make candidate test
```

El Makefile utiliza `-O3 -std=c11 -Wall -Wextra -Wpedantic`, las inclusiones `-Isrc/implementacion_final -Isrc/experimentos` y `-lm`. La versión MPI agrega `-DUSE_MPI` y usa `mpicc`; la referencia usa `gcc`. No se agregó `-ffast-math`, OpenMP ni BLAS al candidato. No se debe reemplazar una instantánea histórica por otra versión y seguir atribuyéndole sus mediciones.

Para una prueba breve:

```bash
./build/cholesky_candidate_seq 128
mpirun --bind-to core --map-by core -np 2 ./build/cholesky_candidate_mpi 128
mkdir -p scratch
./build/measure_command scratch/seq.time.csv ./build/cholesky_candidate_seq 128 > scratch/seq.csv
./build/measure_command scratch/mpi.time.csv mpirun --bind-to core --map-by core -np 2 ./build/cholesky_candidate_mpi 128 > scratch/mpi.csv
```

Estos comandos verifican el programa y el formato; no reproducen por sí solos una campaña completa. Ajustar binding y P a la asignación. El repositorio no solicita nodos ni contiene una configuración validada de Slurm para el servicio utilizado.

## Referencia LAPACK

En una instalación con headers y bibliotecas del sistema:

```bash
make lapack test-lapack
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ./build/compare_lapack 128 6
```

Si Conda proporciona las dependencias, verificar primero `$CONDA_PREFIX/include/lapacke.h`, `cblas.h` y las bibliotecas enlazadas. Ejemplo de compilación adaptada, sin instalar nada automáticamente:

```bash
gcc -O3 -std=c11 -Wall -Wextra -Wpedantic -Isrc/implementacion_final -Isrc/experimentos -I"$CONDA_PREFIX/include" \
  src/experimentos/compare_lapack.c src/implementacion_final/cholesky.c src/experimentos/bench_utils.c -L"$CONDA_PREFIX/lib" \
  -Wl,-rpath,"$CONDA_PREFIX/lib" -llapacke -lopenblas -lm -o build/compare_lapack
ldd build/compare_lapack
./build/compare_lapack --test
```

La presencia de paquetes Conda debe confirmarse en cada instancia. La información operativa recibida indica que hubo reinstalación de dependencias tras un reinicio y persistencia del directorio de trabajo; los paquetes no contienen todo el historial necesario para auditar esa secuencia. No se interpreta como garantía universal de persistencia del servicio. El warning `_Float16` de `openblas_config.h` se conserva como advertencia, no se oculta ni se confunde con un fallo numérico.

## Reproducir el análisis sin repetir los benchmarks

```bash
python -m pip install -r requirements.txt
python scripts/analyze_results.py
python scripts/build_documentation.py
python scripts/verify_delivery.py
```

El analizador abre tar.gz en memoria, verifica manifiestos disponibles, normaliza nombres y recalcula medianas/cuartiles desde CSV. Produce tablas, observaciones con procedencia, auditoría y figuras. El documento se genera desde la plantilla narrativa y las tablas procesadas. No depende de acceder al escritorio original ni a una instalación particular de WSL. Las bibliotecas Python están declaradas por rangos compatibles; el entorno usado para construir esta entrega queda en `docs/verificacion_entrega.json`.

Los scripts anteriores se conservan por trazabilidad. Algunos contienen grillas fijas, rutas históricas o escriben resúmenes en la carpeta de entrada. Para ejecutarlos, copiar una campaña a `scratch` y operar allí. El analizador consolidado es la entrada recomendada para la entrega.

## Evidencia original y derivados

Los cinco tar.gz del clúster son la representación canónica de sus archivos originales. Se evita extraerlos permanentemente y duplicar cientos de archivos. `archive_members.csv` inventaría sus miembros y hashes; `verified_hashes.csv` registra comprobaciones de manifiestos originales. Los análisis ZIP externos son derivados y se conservan en el archivo histórico, no se usan como fuente primaria de tiempos.

Los CSV locales se copian sin cambiar bytes. Las fuentes congeladas de cada campaña permanecen junto a su evidencia incluso cuando coinciden con otras: son pequeñas y fijan qué se midió. Los duplicados detectados están listados por SHA-256. La entrega previa `output/entrega_precluster_20260924` no se presenta como una nueva campaña; sus archivos están inventariados y se conservan en la carpeta original, con la correspondencia de contenido descrita en el manifest.

No se copian dependencias temporales, caches ni binarios sueltos de compilaciones locales. Los ejecutables ya incluidos en tar.gz se preservan como parte de la evidencia. Ningún original se borra ni se corrige en silencio.

## Alcance de la integridad

| Paquete | Archivos | Comprobación disponible |
|---|---:|---|
| Preformal | 114 | 113 entradas de manifiesto, más el manifiesto |
| Cruce | 494 | 493 entradas del manifiesto global y nueve de procedencia |
| Escalabilidad | 592 | Doce hashes de procedencia; sin manifiesto global original de CSV |
| LAPACK | 12 | Cuatro hashes en entorno; sin manifiesto global original de CSV |
| Final grande | 44 | 43 entradas, más el manifiesto |

Los hashes fijan contenido; no certifican veracidad experimental o fecha por sí solos. Un hash calculado al recibir un paquete identifica esa copia, no crea evidencia histórica que faltaba. En el paquete final se registran hashes de ejecutables que no fueron incluidos: no es posible verificar esos binarios ausentes; los fuentes sí están presentes.

## Correcciones y discrepancias documentales

1. El README antiguo daba por pendiente el clúster. Se conserva como documento fechado; el informe nuevo incorpora las campañas ejecutadas.
2. La guía previa mencionaba b=4 como candidato. La confirmación de otra sesión no mantuvo su ventaja y el programa final usa b=1.
3. El prototipo anterior tiene otro protocolo; sus scripts anuncian selección forzada de estrategias que su interfaz no implementa. Sus resultados no se mezclan con los del candidato.
4. La evidencia preformal se recibió primero como transcripción/redondeo. El nuevo análisis usa los CSV originales y conserva la transcripción como contexto histórico.
5. En cruce, nombres con `reprep...` se normalizan sin renombrar dentro del tar. El patrón recupera la ronda 1..7 y N/P; se exige una observación por ronda/configuración. La explicación del bug de variable global se conserva como diagnóstico documentado. No está archivado el script para inspeccionarlo independientemente.
6. Escalabilidad tiene nombres normalizados; ello no prueba por sí solo que se haya aplicado exactamente una reparación de Bash ni que se cumpliera todo el orden anunciado. Los scripts finales no están incluidos. No se fabrica uno bajo el rótulo de original.
7. Los CSV de LAPACK no exportan `valid` o exit code. Sus residuos, diferencias y pruebas se informan; no se atribuye `exit_code=0` no registrado.
8. El PDF unificado antiguo figura eliminado en el estado Git inicial y no está en disco. No se restaura ni se sobrescribe esa eliminación. Se conservan los 21 PDF únicos existentes; la nueva publicación es independiente.

## Repetir campañas en el futuro

Registrar compilador, flags, fuentes con hashes, bibliotecas dinámicas, quota/memoria, cpuset, afinidad efectiva, fecha, orden real y salida de cada ejecución. Mantener warmups separados y capturar códigos de salida. Ejecutar referencias contemporáneas y conservar las salidas fallidas para auditoría, sin incorporarlas como tiempos válidos. Un cambio de fuente o de reloj exige identificar otra campaña.

No hace falta repetir toda la investigación para defender los resultados actuales. Una futura prueba de OpenMP, bloqueo o varios nodos debe formularse como una comparación nueva, con el mismo presupuesto de recursos cuando esa sea la variable controlada.

