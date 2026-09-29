# Experimento 7: tiempo completo de entrada, factorización y salida

## Caso de uso

La matriz A comienza completa en el rango 0 y el factor L debe terminar completo en el mismo rango.

- MPI entrada: empaquetado cíclico en rango 0 y MPI_Scatterv.
- MPI cálculo: right-looking con vector local o left-looking distribuido.
- MPI salida: MPI_Gatherv y desempaquetado en rango 0.
- Secuencial: copia de A, right-looking con vector y salida ya disponible.
- Fuera del tiempo: reserva, generación, validación y arranque de procesos.

## Protocolo y comprobaciones

- n=64,128,256,512,1024; P=1,2,3,4.
- 12 repeticiones por algoritmo y configuración; seis permutaciones repetidas dos veces.
- `make test-mpi-total`: PASS con P=1,2,3,4.
- Casos SPD n=1,2,3,7,16,31, factor conocido 3x3, pivote negativo y NaN.
- AddressSanitizer y UndefinedBehaviorSanitizer: PASS con P=4 usando la adaptación `--mca memory ^patcher`, `detect_leaks=0` ya documentada.
- 720 observaciones aceptadas; residuo máximo 1,21308762262e-15.
- Diferencia relativa máxima frente al factor secuencial: 2,65779210291e-15.
- Las huellas de `fuentes.sha256` coinciden después de la campaña.

## Interpretación

El máximo de cada fase se calcula entre procesos por separado. Como los máximos pueden corresponder a rangos distintos, la suma de medianas o máximos por fase no debe reemplazar al tiempo total medido directamente.

En esta grilla, right con P=3 obtiene aceleración total 1,08x en n=256, 1,60x en n=512 y 1,90x en n=1024 frente a la referencia secuencial contemporánea. Se considera 512 el primer tamaño probado con mejora total clara, no un umbral universal.
