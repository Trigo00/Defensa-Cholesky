# Verificación de la entrega

## Revisión del código del 29/09/2026

Todos los ejecutables se compilaron en WSL con `-O3 -std=c11 -Wall -Wextra -Wpedantic`. Pasaron las cuatro pruebas secuenciales y 89 comparaciones contra la versión anterior: bancos MPI con P=1,2,3,4,6, casos con N<P, candidato, generación idéntica, modos `profile`/`pair`, errores de argumentos y cronómetro externo. Los campos CSV no temporales coincidieron exactamente en los casos comparados. Pasó también la regresión del Layout nulo en left MPI.

Los registros de esta revisión son `refactor_build.log`, `refactor_equivalence.log` y `refactor_equivalence.json`; este último identifica los fuentes comprobados. `refactor_size.json` registra una reducción del 5,25 % de tokens en los archivos .c excluyendo comentarios y espacios. Los archivos tienen más líneas físicas por la explicación detallada. No se ejecutó una nueva campaña de rendimiento.

## Comprobaciones anteriores y documentación

Se ejecutaron en WSL los objetivos `make candidate test mpi-local test-mpi-local lapack test-lapack`. El registro conservado muestra las pruebas satisfactorias, incluidas las cuatro variantes MPI con P=1,2,3,4 y los controles de LAPACK. Las dos ejecuciones pequeñas del candidato con N=128 y P=1,2 devolvieron `valid=1`. Son controles locales de funcionamiento, no nuevas mediciones de rendimiento del clúster.

Todos los scripts shell pasaron `bash -n`. La consulta local `mpirun --version` no proporcionó una versión: emitió un diagnóstico de archivos de ayuda PMIx/PRRTE ausentes. No se infiere la versión a partir de esa consulta; las versiones históricas del clúster están en sus archivos originales. Las pruebas MPI anteriores sí finalizaron satisfactoriamente.

El 29/09/2026 se renderizaron y revisaron las 25 páginas del PDF rediseñado, incluidos portada, índice, fórmulas, 16 figuras, tablas y transiciones de página. La tabla del primer cruce se mantiene completa. La verificación automatizada complementaria está en `../verificacion_entrega.json`.
