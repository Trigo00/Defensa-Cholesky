# Inventario técnico y evolución del código

`src/implementacion_final` contiene el candidato que se presenta; `src/experimentos` contiene bancos, variantes y utilidades. El Makefile conserva los mismos objetivos mediante ambas rutas de inclusión. Compartir un archivo no significa que todas sus funciones sean parte del camino ejecutado por el candidato.

La revisión didáctica del 29/09/2026 explica las instrucciones y extrae utilidades repetidas en `bench_utils.c`, además de dos auxiliares privados de generación/preparación de columnas. El mapa de lectura está en [guia_codigo.md](guia_codigo.md). Los originales medidos se preservan en `archive/src_medidos_20260928`; la comparación funcional reproducible se implementa en `scripts/verify_code_refactor.py`. El control de Layout nulo de left MPI se hace ahora antes de desreferenciarlo.

## Implementación seleccionada

| Archivo | Papel actual y origen de la decisión |
|---|---|
| `src/implementacion_final/main_candidate.c` | Entrada consolidada. Dos compilaciones: MPI y secuencial. Generación, factor, reunión, relojes y comprobación; reemplaza los bancos como programa de uso principal |
| `src/implementacion_final/cholesky.c` | Generación SPD reproducible centralizada/indexada; right con vector, variantes left/right y residuos. El candidato usa un subconjunto; las variantes se mantienen para contrastes |
| `src/implementacion_final/cholesky.h` | Contratos de representación, generación y validación. La entrada debe ser simétrica y el triángulo superior no es L |
| `src/implementacion_final/cholesky_mpi.c` | Mapas de propiedad y dos kernels right. El elegido es cholesky_mpi_local con layout cíclico b=1. El original y los mapas para grupos de columnas permanecen para experimentos |
| `src/implementacion_final/cholesky_mpi.h` | Layout, perfiles y contratos colectivos. No implica que el candidato active perfiles o todas las variantes |

La compilación MPI enlaza únicamente main_candidate, cholesky y cholesky_mpi. La secuencial enlaza main_candidate y cholesky. El ejecutable auxiliar de tiempo externo se construye por separado. No hay directivas OpenMP en el candidato ni dependencia LAPACK en sus reglas de compilación.

## Bancos y variantes experimentales

| Archivo | Experimento y estado |
|---|---|
| `main.c` | Primera interfaz de right escalar, siete repeticiones por defecto, residuo completo. Histórico; no es el candidato final |
| `compare_seq.c` | Left vs right original, orden alternado, kernel aislado. Identificó la desventaja inicial de right |
| `compare_memory.c` | Left/right/right_buffered, seis permutaciones. Sustentó la copia de columna como mejora |
| `compare_mpi.c` | Contiguo/cíclico del kernel original, con perfil opcional separado. No representa el kernel seleccionado |
| `compare_mpi_local.c` | Cruza dos repartos y dos kernels; incluye centinelas del workspace y orden balanceado. Verificó el vector local |
| `cholesky_left_mpi.c` | Alternativa con contribuciones parciales y reducciones. Conservada para contraste, no enlazada al candidato |
| `compare_mpi_algorithms.c` | Left/right MPI con mismo reparto, validación y máximo temporal de kernel |
| `compare_mpi_total.c` | Entrada centralizada, factor y retorno a rango0. Reserva y generación excluidas; sus máximos de fases no son aditivos |
| `compare_generation.c` | Centralizada/distribuida, igualdad bit a bit, sin factorización. Aísla generación y distribución |
| `compare_application.c` | Reserva, generación y flujo completo con referencias dentro del banco. La referencia secuencial vive en rank0 con otros procesos presentes |
| `compare_blocks.c` | Propiedad b=1,2,4,8,16,32,64 o pares b1/b4; no bloqueo BLAS-3. Incluye comprobación de mapas |
| `compare_lapack.c` | Referencia optimizada vigente: own vs LAPACKE_dpotrf_work, alternancia, un hilo comprobado y validación. No sustituye al MPI |
| `measure_command.c` | Benchmark auxiliar vigente de comando completo mediante fork/exec/waitpid; CSV de external_s y exit_code |

## Pruebas

`tests/test_cholesky.c` verifica factor conocido, escalar, identidad, generación y rechazo de entradas/pivotes inválidos. `test_variants.c` contrasta left/right. `test_buffered.c` verifica el vector con centinelas y memoria inicializada con NaN. `test_projected.c` comprueba generación por columnas, reproducibilidad de proyecciones, triángulo superior ignorado y detección de corrupción.

Los bancos MPI y LAPACK incorporan además `--test`; no se deben confundir con muestras de rendimiento. `verificar_interfaz_candidato.sh` comprueba argumentos inválidos y propagación del estado del cronómetro.

## Scripts de campaña

| Script | Banco o campaña que permite reproducir |
|---|---|
| `medir_secuencial.sh` | Primer right escalar |
| `comparar_variantes.sh`, `comparar_memoria.sh` | Variantes secuenciales y vector |
| `comparar_mpi.sh`, `comparar_mpi_local.sh` | Repartos y vector MPI con referencias antes/después |
| `medir_umbral.sh` | Tres rondas locales del cruce de kernel |
| `comparar_left_right_mpi.sh` | Comparación de algoritmos MPI |
| `comparar_tiempo_total.sh` | Entrada/factor/salida |
| `comparar_generacion.sh`, `comparar_aplicacion.sh` | Generación aislada y flujo con generación |
| `comparar_bloques.sh` | Exploración de granularidad de propiedad |
| `campana_cluster.sh` | Banco configurable histórico de pares b1/b4; no genera las cuatro campañas formales finales |
| `precluster_local.sh` | Confirmación local b1/b4, piloto3072 y LAPACK local |
| `cierre_local.sh` | Candidato con lanzamientos nuevos, 24 preparaciones y 168 mediciones, ambos relojes |

Los scripts `.sh` se conservan con su contenido original. Requieren Linux/WSL, comandos disponibles y afinidad adaptada. Algunos fijan CPU0 porque así se midió localmente. No se ejecutan automáticamente al regenerar la documentación.

## Análisis y publicación

Los catorce `analizar_*.py` siguen las grillas de sus campañas y calculan estadísticos de CSV, no factorizaciones. `analizar_pares_cluster.py` admite tamaños del banco de pares; los demás tienen distintas restricciones de muestras, orden y formatos. Se conservan para reconstruir decisiones y contrastar el análisis nuevo. Como escriben en el directorio recibido, operarlos únicamente sobre copias de trabajo.

`scripts/analyze_results.py` es la entrada consolidada: abre originales, comprueba cifras/filas/validez, verifica manifiestos de tar, separa cohortes y publica tablas y dieciséis figuras PNG/SVG (trece gráficas de datos y tres esquemas conceptuales). `publication_visuals.py` define el estilo común y las nuevas figuras; `build_documentation.py` incorpora las tablas al relato y `publication_pdf.py` genera el PDF con portada, índice navegable y fórmulas. `verify_delivery.py` comprueba procedencia, resultados clave, enlaces y consistencia de la entrega.

Los generadores documentales anteriores se conservan en `archive/docs_fuentes`. Sus rutas y dependencias corresponden al árbol antiguo; no son la entrada de publicación actual. `generar_informe_unificado.py` concatenaba informes locales después de un relato inicial, mientras que el informe nuevo se redacta de forma continua. `generar_informe_*cluster*.py` y el generador final verificaban originales de campaña y se utilizaron como contraste histórico. Las figuras antiguas permanecen en `archive/analisis_previos`; las nuevas están en `figures`.

El inventario exacto de todos los archivos originales, tamaños y hashes es `inventario_original.csv`; `procedencia_copias.csv` registra destino y campaña. `inventario_herramientas.csv` añade una fila por fuente, script o generador, con huella y tamaño; los snapshots históricos se identifican también en el inventario general. Así se conserva una relación exhaustiva sin convertir el relato principal en un listado de archivos.

## Antecedentes excluidos de las conclusiones actuales

`archive/antecedentes/cholesky_final_hpc.c` es un prototipo previo distinto, pese a su nombre. `run_local_benchmarks.sh`, `cholesky_slurm.sh`, `benchmark_real_wsl.csv` y sus gráficas pertenecen a ese antecedente. El script Slurm contiene ejemplos de cuatro nodos y estrategias forzadas que no describen las campañas reales del servicio web ni una implementación 2D ejecutada.

`compile_docs.py` y `plot_real_data.py` de ese antecedente contienen rutas absolutas de otra estructura de trabajo. Se preservan para explicar procedencia, pero no se presentan como herramientas portables vigentes. El binario suelto anterior no se incorpora como ejecutable de la entrega. El ZIP de fuentes preparado antes del clúster se conserva como antecedente de preparación, no como fuente única del estado final.

