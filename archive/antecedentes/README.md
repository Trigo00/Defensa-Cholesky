# Cholesky paralelo: punto de entrada

Leer `output/pdf/Cholesky_Investigacion_Completa.pdf`: guía actual y evidencia de
las catorce etapas en un solo documento. Las primeras ocho páginas reconstruyen el
camino; después están íntegros los informes experimentales con índice y marcadores.

## Qué estamos construyendo

Un Cholesky denso en C con MPI, distribución **1D por columnas**. Referencia candidata:
right-looking, vector local, reparto cíclico b=1. LAPACK es una referencia externa;
no reemplazó nuestro MPI. OpenMP y reparto 2D no se implementaron.

## Dónde mirar

Los archivos de la raíz `cholesky_final_hpc.c`, `Documentacion_Completa_Cholesky.pdf`
y `GUIA_CLUSTER.md` son antecedentes anteriores al reinicio en `desde_cero`.
Pese a sus nombres, no son la entrega ni la guía vigentes; sus cifras no integran
la evidencia actual. Se conservan en disco sin incluirlos en este repositorio.

- `desde_cero/src/cholesky.c`: secuencial, generación y validación.
- `desde_cero/src/main_candidate.c`: entrada del programa candidato MPI y secuencial.
- `desde_cero/src/measure_command.c`: cronómetro externo del comando.
- `desde_cero/src/cholesky_mpi.c`: núcleo MPI candidato `cholesky_mpi_local`.
- `desde_cero/src/cholesky_left_mpi.c`: variante de comparación.
- `desde_cero/src/compare_*.c`: bancos experimentales, no programas finales distintos.
- `desde_cero/scripts/`: ejecución y estadísticas; C mide, Python analiza.
- `desde_cero/resultados/`: mediciones, protocolos y snapshots originales.
- `desde_cero/docs/GUIA_CLUSTER.md`: preparación operativa del clúster.
- `desde_cero/Makefile`: compilación y pruebas.

## Estado y siguiente paso

Pruebas locales realizadas hasta n=3072. Sin resultados entre nodos.
Se midió speedup anteriormente; las últimas etapas comparaban mejoras con igual P.
El documento único vuelve a mostrar speedup útil y eficiencia sin inventar datos nuevos.
El ejecutable candidato está consolidado y medido en las etapas 11-13.
Falta ejecutar el clúster y fijar la configuración final. Varios archivos C
pueden formar un solo programa; una entrega literalmente de un archivo requiere
confirmar ese formato con la profesora.

Campaña de cierre: 30 configuraciones pequeñas y 192 lanzamientos, de los cuales
168 aportan rendimiento (7 repeticiones). N=256,512,1024,2048; P=1,2,3,4,6.
Para N=2048/P=6: speedup interno 1,83; externo con validación 1,16.
Son resultados locales de una sesión, no umbrales universales.

Repetición del 27/09 (etapa 14), con las mismas fuentes: otros 192 lanzamientos,
168 medidos. Para N=2048/P=6: speedup interno 1,95 y externo 1,16.
Se mantiene la dirección de la ventaja en este caso; los tiempos y la magnitud
del speedup interno cambian. Ambas sesiones se conservan por separado.
La referencia local se identifica con la etiqueta Git `candidato-local-v1`.
Congelar identifica lo medido; permite seguir documentando y preparar el clúster.
Una corrección posterior requiere otra versión y sus pruebas.

Desde `desde_cero`, en WSL/Linux:

```bash
make candidate
./build/cholesky_candidate_seq 1024
mpirun --bind-to core --map-by core -np 3 ./build/cholesky_candidate_mpi 1024
bash scripts/cierre_local.sh resultados/nueva_campana
python3 scripts/analizar_cierre.py resultados/nueva_campana
```

El candidato genera la matriz con semilla 2026 y devuelve métricas CSV; el factor
se reúne en memoria del rango 0. No escribe una matriz a disco. El reloj externo
incluye validación, lanzamiento y cierre, pero no el arranque de WSL ni una cola.

## Cómo trabajar con Git

Primer commit: estado reunido hoy, sin fingir una historia previa de commits.
Las campañas conservan snapshots de lo que realmente se midió. De aquí en adelante:
un cambio con propósito, pruebas, mediciones si corresponde y un commit que explique
el resultado. Usar etiquetas para versiones validadas, no copias final2.c/final3.c.
La presencia de una variante experimental no implica adoptarla para la entrega.

El repositorio es local. No se publica ni configura un remoto automáticamente.
Se ignoran binarios, cachés y bibliotecas temporales. Código y documentación con
asistencia de IA; decisiones y resultados sustentados por pruebas ejecutadas.
