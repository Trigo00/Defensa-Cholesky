# Experimento 4: MPI con vector local

Implementación y generación de entradas en C. Estadísticas y gráficos en Python.

## Comprobaciones ejecutadas

- `make mpi-local test-mpi-local`: PASS con P=1,2,3,4, las cuatro variantes (dos repartos por dos kernels), casos SPD n=1,2,7,16,31, factor 3x3 conocido y fallos colectivos por pivote negativo o NaN.
- El banco de pruebas inicializa el espacio de trabajo con NaN y verifica dos valores centinela, antes y después del vector local. Incluye P mayor que n y repartos con diferente número de columnas por proceso.
- AddressSanitizer y UndefinedBehaviorSanitizer: PASS con P=4, compilación `-O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer`. Ejecución con `ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 mpirun --mca memory ^patcher --bind-to core --map-by core -np 4 ./build/compare_mpi_local_sanitize --test`.
- Se mantiene la adaptación de la etapa 2 para la incompatibilidad ASan/MPI_Init: memory/patcher se desactiva solo en las pruebas, no en los tiempos. No se comprobó detección de fugas.
- Cada resultado medido se reúne y valida fuera del cronómetro: residuo relativo <=1e-12 y diferencia relativa por elemento del factor respecto a right secuencial <=1e-13. Los máximos se registran en `validacion.json`.

## Alcance del cambio

La función original `cholesky_mpi` se conserva. La nueva `cholesky_mpi_local` agrega un llenado del vector local por etapa y reemplaza la lectura `column[layout_global(d,c)]` por `local_column[c]`. La copia está incluida en el tiempo; la reserva del vector está fuera. No cambian los propietarios, el orden de las actualizaciones ni las llamadas a MPI_Bcast.

Las comparaciones usan tiempos de esta misma campaña, incluidas las referencias secuenciales medidas antes y después. El perfil se mide por separado. Las fuentes exactas y las huellas permiten conservar la referencia aunque la implementación continúe evolucionando.
