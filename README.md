# Cholesky en C: memoria, MPI y referencia LAPACK

Investigación universitaria sobre cuándo el paralelismo reduce el tiempo de Cholesky y cuánto depende esa ventaja del kernel local y del reloj elegido. Se conservan experimentos locales y cinco paquetes originales del clúster, sin mezclar sus referencias.

El candidato es **right-looking en double, vector local, columnas 1D cíclicas b=1, generación distribuida y reunión en rango 0**. Se compila también una referencia secuencial desde la misma entrada. LAPACK/OpenBLAS se usa en un banco de comparación separado, con un hilo. OpenMP y ScaLAPACK son propuestas futuras, no implementaciones medidas.

## Leer el trabajo

- [Investigación completa](docs/investigacion_completa.md): desarrollo continuo, resultados, conclusiones y límites.
- [Informe PDF](output/pdf/Cholesky_Investigacion_Integral.pdf): versión para lectura e impresión, con portada, índice navegable, síntesis de resultados y 16 figuras.
- [Metodología](docs/metodologia_experimental.md) y [reproducibilidad](docs/reproducibilidad.md).
- [Inventario técnico](docs/inventario_tecnico.md) y [manifest](MANIFEST.md).
- [Guía del código para la defensa](docs/guia_codigo.md): recorrido por todos los fuentes, índices MPI, relojes y sintaxis de C.
- [Guía paso a paso de los experimentos](docs/guia_paso_a_paso_experimentos.md): qué archivo mostrar, cómo ejecutar cada etapa y qué significa su salida.
- [Registro de scripts del clúster](docs/scripts_cluster_20260928.md): bloques exactos, comandos de terminal y launchers reconstruidos de las campañas del 28/09/2026.

## Versión comentada del código

Los `.c` de `src/implementacion_final/` contienen la implementación que se presenta y evalúa. `src/experimentos/` reúne los bancos de comparación, el cronómetro y sus utilidades. Ambos grupos pertenecen a la revisión didáctica del 29/09/2026, con comentarios por instrucción lógica. Los fuentes anteriores y su Makefile se preservan en `archive/src_medidos_20260928/`: los tiempos del informe pertenecen a las campañas originales. Las pruebas de regresión comparan ambas versiones; no afirman igualdad de rendimiento.

Para repetir la comparación funcional completa en Linux/WSL con MPI, LAPACKE, OpenBLAS y Python 3:

```bash
python3 scripts/verify_code_refactor.py
```

## Compilar y ejecutar una prueba breve

Linux o WSL, GCC compatible con C11, Make y una instalación MPI coherente entre compilador y lanzador:

```bash
make candidate test
./build/cholesky_candidate_seq 128
mpirun --bind-to core --map-by core -np 2 ./build/cholesky_candidate_mpi 128
```

El programa recibe N (1..20000), genera con semilla 2026 y exporta CSV con tiempos y validación. El límite de N no garantiza memoria disponible. Adaptar P y afinidad a la asignación real. El factor queda en memoria del rango 0; no se escribe una matriz a disco.

Con headers y bibliotecas LAPACKE/OpenBLAS instalados:

```bash
make lapack test-lapack
OPENBLAS_NUM_THREADS=1 ./build/compare_lapack 128 6
```

`compare_lapack` verifica por API que OpenBLAS utilice un hilo. La guía explica rutas de Conda cuando las bibliotecas no están en las rutas del sistema.

## Regenerar tablas, gráficos y documento

Python 3.10 o posterior:

```bash
python -m pip install -r requirements.txt
python scripts/analyze_results.py
python scripts/build_documentation.py
python scripts/verify_delivery.py
```

No se ejecutan benchmarks ni binarios archivados: el análisis lee evidencia original y escribe derivados. La plantilla narrativa editable está en `docs/investigacion_completa.md.in`; el constructor incorpora tablas calculadas y produce Markdown/PDF. Los scripts históricos `analizar_*.py` escriben dentro de la carpeta que reciben: usarlos solo sobre copias de trabajo, nunca sobre `data/raw`.

## Resultados principales

En el cruce formal, el primer N ensayado con mejora descriptiva clara de aplicación fue 192 con P=3. Con P=6, la campaña de escalabilidad mostró ventaja del comando completo para N=2048 y N=4096. En la campaña final, MPI mejoró al secuencial propio, pero tardó aproximadamente **8,58 veces LAPACK en N=6144 y 6,25 veces en N=8192** al comparar `factor_s`. No se observó cruce frente a LAPACK de un hilo.

Los resultados de rendimiento son específicos del hardware, software, afinidad y asignación utilizados. En el clúster se trabajó con cuota agregada de seis CPUs y 24 GiB; las 128 CPUs visibles no eran una concesión de 128 núcleos. No hay resultados multinodo ni prueba causal de las anomalías de escalado.

## Organización

| Ruta | Contenido |
|---|---|
| `src/implementacion_final/` | Programa final secuencial/MPI y sus interfaces |
| `src/experimentos/` | Bancos comparativos, cronómetro y utilidades compartidas |
| `tests/`, `Makefile` | Pruebas y reglas de compilación para ambos grupos |
| `scripts/` | Análisis consolidado, publicación y scripts históricos de campañas |
| `data/raw/local/` | CSV originales, registros y fuentes congeladas locales |
| `data/raw/cluster/` | Cinco tar.gz originales, leídos sin extraer durante el análisis |
| `data/processed/` | Observaciones normalizadas, cuartiles, cocientes y auditoría |
| `figures/` | Figuras nuevas en PNG y SVG |
| `docs/`, `output/pdf/` | Informe y guías finales |
| `archive/` | Documentación anterior, análisis previos y antecedentes |

La separación entre código principal y experimental también está expresada en las carpetas. El Makefile incorpora las dos rutas de cabeceras y conserva los mismos objetivos; `make candidate` selecciona únicamente la implementación final y el cronómetro. `campana_cluster.sh` es un banco histórico de propiedad b=1/b=4: su nombre no significa que reproduzca las campañas finales del clúster.

La entrega conserva originales y trazabilidad; no configura remotos, publica ni crea commits automáticamente. Los antecedentes no vigentes se identifican explícitamente y no aportan denominadores a los resultados actuales.

