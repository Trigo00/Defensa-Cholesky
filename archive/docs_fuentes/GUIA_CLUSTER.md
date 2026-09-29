# Protocolo operativo previo al clúster

Estado: preparado y probado localmente; no ejecutado entre nodos.

## Qué llevar

Copiar `src/`, `tests/`, `scripts/`, `Makefile` y esta guía. Compilar en el destino,
no copiar ejecutables de WSL. Conservar una copia con hash de cada versión medida.
El algoritmo principal sigue siendo right-looking MPI cíclico. Bloque 4 es candidato,
no decisión universal. LAPACK es una referencia externa, no nuestra implementación MPI.

## Confirmar con el administrador

- Planificador y comando de lanzamiento (mpirun o srun compatible con MPI instalado).
- Módulos/compilador/MPI disponibles, núcleos físicos, RAM por nodo y límites de trabajo.
- Número de nodos, procesos por nodo y afinidad; verificar que el lanzamiento no sobreasigne núcleos.
- Partición, tiempo y memoria solicitados en la asignación. No se inventan directivas de scheduler aquí.

## Compilar y verificar

```bash
make blocks
mpirun --bind-to core --map-by core -np 3 ./build/compare_blocks --test
# Si están disponibles LAPACKE y OpenBLAS:
make lapack test-lapack
```

En el clúster adaptar el lanzamiento dentro de la asignación recibida. La compilación
LAPACK actual requiere LAPACKE y OpenBLAS (consulta/verificación de un hilo mediante su API).
Otra BLAS exige adaptar esa consulta, no asumir que usa un hilo.

## Ejecutar una campaña MPI configurable

```bash
# Ejemplo dentro de UNA asignación; tamaños de ejemplo, aumentar tras el piloto.
SIZES='1024 2048 3072' PROCESSES='1 3 6' REPETITIONS=8 \
  bash scripts/campana_cluster.sh resultados/nodo_piloto
```

Variables: `SIZES`, `PROCESSES`, `REPETITIONS` (par 2..28), `MPI_LAUNCHER`,
`MPI_FLAGS`, `MPI_COUNT_FLAG`, `MEMORY_BUDGET_MIB`. No se usa eval. Para srun, si el
administrador confirma compatibilidad: launcher `srun`, count flag `-n`, flags apropiados
para su asignación. El script no solicita nodos ni envía trabajos.

La protección de memoria usa aproximadamente `40*n*n` bytes más 128 MiB, incluyendo
matrices de validación: es una estimación conservadora para un nodo, no memoria mínima.
El presupuesto predeterminado es 60 % de MemAvailable del host de lanzamiento; en una
asignación con límite de memoria debe fijarse explícitamente al presupuesto concedido.
N está limitado a 20000 por el ejecutable; tamaños mayores requieren revisar índices,
conteos MPI y validación. No aumentar el límite sin esos cambios.

## Qué medir y comparar

Primero un nodo, luego varios nodos con igual N y P cuando sea posible, cambiando
solo la ubicación. Después aumentar P para escalabilidad fuerte. Elegir matrices
grandes mediante pilotos: que el trabajo dure lo suficiente y quepa sin swap.
No declarar un tamaño universal que justifique el clúster desde las pruebas WSL.

Mantener semilla, algoritmo, reloj, salida centralizada y opciones de compilación.
Repetir en varias asignaciones/sesiones. Registrar nodos y afinidad real, no solo P.
Preservar CSV y logs, incluso resultados sin mejora.

El total principal empieza con MPI ya iniciado y termina con L completa en rango 0:
reserva/mapas + generación + factor + reunión. Fases rank0 incluyen esperas. Medianas
de totales directamente medidos; no sumar medianas. `time -v` abarca el banco completo,
referencias, calentamientos y validaciones: no equivale a tiempo de una factorización.
Su RSS no representa la suma de memoria de todos los procesos/nodos.

Para speedup contra secuencial, ejecutar referencia en el mismo hardware/sesión,
con la misma generación y salida. No formar cocientes con resultados WSL ni mezclar
la referencia LAPACK con nuestra referencia propia sin identificarlas. LAPACK sin MPI
se ejecuta con afinidad de un núcleo y un hilo; usar `taskset` solo con una CPU permitida
por el planificador, no asumir CPU 0 en el clúster.

## Validación y límites

Factores comparados contra referencia secuencial en C y ocho proyecciones; residuo
completo en tests pequeños. La referencia secuencial O(n³) y varias copias O(n²)
siguen teniendo costo aunque estén fuera del tiempo principal. No son un banco
de memoria mínima ni validación distribuida escalable sin límite.

Los análisis específicos de etapas tienen grillas fijas. Para las nuevas campañas
de pares usar `scripts/analizar_pares_cluster.py CARPETA`; produce estadísticas
del total y factor para los tamaños presentes. Todo cambio de protocolo se documenta.

## Criterio para cerrar

Concluir qué versión conviene en las configuraciones probadas, dónde deja de escalar,
y cuánto pesan cómputo, generación y comunicación observada. No son necesarias
implementaciones triangulares, híbridas o por bloques antes de esta prueba.
# Candidato consolidado después de la preparación inicial

Las etapas 11-13 agregan `src/main_candidate.c`. Compilar con `make candidate`.
Ejemplo dentro de una asignación autorizada por el administrador:

```bash
mpirun --bind-to core --map-by core -np 6 ./build/cholesky_candidate_mpi 2048
```

Adaptar lanzador y afinidad al clúster; el ejemplo no solicita recursos.
El programa recibe N, genera con semilla 2026 y reúne L en memoria del rango 0.
Medir la referencia `./build/cholesky_candidate_seq N` en el mismo entorno.
`build/measure_command salida.time.csv <comando y argumentos>` mide externamente
el comando, incluyendo validación y cierre; informar la cola aparte.
No trasladar los tiempos ni el umbral local como conclusiones del clúster.
La guía histórica que sigue conserva los bancos de comparación b=1/b=4.
