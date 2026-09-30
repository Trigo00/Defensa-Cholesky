# Aplicación MPI de Cholesky con entrada externa

Esta aplicación separa la entrada/salida del banco experimental. Compila y enlaza
directamente `../implementacion_final/cholesky_mpi.c` y `cholesky.c`; no contiene
otra implementación de Cholesky. La llamada seleccionada es
`cholesky_mpi_local` con `layout_create(n, 1, MPI_COMM_WORLD)`: right-looking,
columnas cíclicas 1D y vector local, igual que el candidato validado.

## Formato de matriz

Archivo de texto ASCII:

```text
filas columnas
a11 a12 ... a1n
a21 a22 ... a2n
...
```

Los saltos de línea no son significativos, pero debe haber exactamente
`filas*columnas` números después de las dimensiones. No se admiten `NaN`,
infinito, dimensiones nulas ni datos adicionales. Para conservar el contrato del
kernel validado, la simetría se exige exactamente: `A[i,j] == A[j,i]`.

El factor de salida usa el mismo formato. Contiene `L` en el triángulo inferior y
ceros en el superior.

## Compilación y uso

```sh
cd src/implementacion_con_matriz_sin_generar
make
mpirun -np 3 ./cholesky_app tests/spd_3x3.txt factor_L.txt --validate
```

## Demostracion rapida en Windows

Edita `MATRIZ_AQUI.txt` y ejecuta con doble clic `EJECUTAR_DEMO.bat`. El script
usa dos procesos MPI, valida el resultado y deja el factor en `RESULTADO_L.txt`.
Consulta `LEEME_PRESENTACION.md` para el formato y el guion breve de la demo.

`--validate` es opcional. Calcula fuera del kernel el residuo relativo Frobenius
`||A-LL^T||/||A||` y exige que sea finito y no mayor que `1e-12`.

El rango 0 lee y comprueba `A`, la empaqueta por propietarios cíclicos y usa
`MPI_Scatterv`. Después del kernel, `MPI_Gatherv` devuelve las columnas al rango
0, que reconstruye la matriz densa y escribe `L`.

## Errores

- `2`: uso incorrecto;
- `3`: archivo o formato de entrada inválido;
- `4`: matriz no cuadrada o incompatible con los conteos MPI;
- `5`: valor no finito;
- `6`: matriz no simétrica;
- `7`: pivote no positivo/no finito o validación fallida;
- `8`: fallo al escribir la salida;
- `9`: memoria insuficiente.

`make test` ejecuta una SPD conocida y comprueba el rechazo de una matriz
simétrica indefinida. Puede fijarse el lanzador con `MPIEXEC`, por ejemplo
`MPIEXEC='mpirun -np 2' make test`.
