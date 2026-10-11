# Demostración: Cholesky MPI con una matriz externa

Durante la presentación sólo tenés que hacer dos cosas:

1. Editar `MATRIZ.txt` con la matriz que quieras probar.
2. Hacer doble clic en `EJECUTAR_DEMO.bat`.

El script compila la aplicación si detecta cambios, la ejecuta con dos procesos
MPI, valida el resultado y genera `RESULTADO_L.txt` en esta misma carpeta.

No hace falta ejecutar los scripts de benchmark ni proporcionar una semilla: la
matriz se lee directamente desde el archivo.

## Formato de `MATRIZ.txt`

La primera línea contiene las dimensiones. Luego van las filas de la matriz.

```text
3 3
4 12 -16
12 37 -43
-16 -43 98
```

Esta matriz ya viene cargada y es definida positiva. Su resultado esperado es:

```text
3 3
2 0 0
6 1 0
-8 5 3
```

La matriz debe cumplir estas condiciones:

- ser cuadrada;
- tener únicamente números finitos;
- ser exactamente simétrica;
- ser definida positiva.

Si no cumple alguna condición, la consola mostrará un error y no se generará un
nuevo factor válido.

## Qué muestra la salida

El script imprime una línea parecida a:

```text
Validacion: residuo relativo Frobenius = 0
```

Un valor cercano a cero confirma que `A ≈ L Lᵀ`. El archivo
`RESULTADO_L.txt` contiene `L` en su triángulo inferior y ceros arriba.

## Si querés cambiar la cantidad de procesos

No es necesario durante la presentación. Si hiciera falta, abrí
`ejecutar_demo.sh` y reemplazá sólo `-np 2` por `-np 3`, `-np 4`, etc. Para una
demostración breve, dos procesos alcanzan y mantienen la salida fácil de
explicar.

## Frase breve para la defensa

> En esta versión la matriz no se genera dentro del programa. El proceso 0 la
> lee, la valida y la distribuye según el mismo reparto cíclico usado en los
> experimentos. El kernel MPI right-looking no cambió; al finalizar se reúne y
> se guarda el factor L, verificando el residuo.

El lanzador de la demo elimina el resultado anterior antes de comenzar y limpia cualquier salida si ocurre un error. Solo anuncia éxito después de validar el factor. Las pruebas usan una carpeta temporal y no modifican MATRIZ.txt ni RESULTADO_L.txt.
