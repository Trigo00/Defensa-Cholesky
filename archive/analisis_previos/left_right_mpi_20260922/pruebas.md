# Experimento 6: left-looking MPI frente a right-looking MPI

## Pregunta

¿Cuál de las dos variantes nos conviene paralelizar en nuestra implementación?

## Comparación controlada

- Ambos algoritmos reciben la misma matriz SPD y usan distribución cíclica estática de columnas.
- Cada proceso guarda sus columnas en memoria local contigua.
- Right-looking utiliza el vector local introducido en el experimento 4.
- Left-looking calcula productos parciales con sus columnas anteriores, los combina mediante MPI_Reduce y difunde el pivote.
- Scatterv, Gatherv, reconstrucción y validación quedan fuera del cronómetro de factorización.
- Se alterna el orden left/right durante ocho repeticiones por configuración.

## Comprobaciones

- `make test-mpi-algorithms`: PASS con P=1,2,3,4.
- Casos SPD n=1,2,3,7,16,31, matriz 3x3 con factor conocido, pivote negativo y NaN.
- Incluye P mayor que n y tamaños no divisibles por P.
- AddressSanitizer y UndefinedBehaviorSanitizer: PASS con P=4. Se usa `--mca memory ^patcher` y `detect_leaks=0` por la incompatibilidad de MPI_Init documentada anteriormente.
- Las 320 observaciones cumplieron residuo relativo <=1e-12. Residuo máximo: 1,21308762262e-15.
- Diferencia relativa máxima del factor frente a right secuencial: 2,65779210291e-15.
- `sha256sum -c fuentes.sha256`: PASS después de la campaña.

## Alcance

Los resultados corresponden a versiones escalares, sin BLAS, en una máquina WSL. No demuestran que right-looking sea universalmente superior. Una versión por bloques, otro almacenamiento o menos colectivas podrían cambiar la comparación.
