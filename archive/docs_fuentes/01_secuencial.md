# Etapa 1. ¿Qué calculamos y cómo sabemos que es correcto?

## Pregunta e hipótesis

Queremos factorizar una matriz real simétrica definida positiva (SPD) como A = LLᵀ, donde L es triangular inferior con diagonal positiva. Esta factorización permite, por ejemplo, resolver Ax = b mediante dos sistemas triangulares. Resolver sistemas queda fuera de esta primera implementación.

Hipótesis: si respetamos las dependencias del algoritmo y usamos matrices SPD, la reconstrucción LLᵀ coincidirá con A salvo errores de redondeo. Esta hipótesis se evalúa con casos conocidos, entradas inválidas y matrices generadas.

## Deducción antes del código

De A = LLᵀ obtenemos aᵢⱼ = Σₖ lᵢₖ lⱼₖ. Como L es triangular, al calcular la columna j solo necesitamos las columnas anteriores:

\[
l_{jj}=\sqrt{a_{jj}-\sum_{k=0}^{j-1}l_{jk}^2},\qquad
l_{ij}=\frac{a_{ij}-\sum_{k=0}^{j-1}l_{ik}l_{jk}}{l_{jj}},\quad i>j.
\]

Primero calculamos la diagonal; luego los elementos que están debajo. En aritmética exacta, ser SPD garantiza pivotes positivos. En punto flotante controlamos cada pivote: matrices muy mal condicionadas pueden dar problemas numéricos.

Ejemplo que podemos comprobar a mano:

```text
A = [  4  12 -16 ]       L = [  2  0  0 ]
    [ 12  37 -43 ]           [  6  1  0 ]
    [-16 -43  98 ]           [ -8  5  3 ]
```

Primera columna: √4 = 2, 12/2 = 6, −16/2 = −8.
Segunda: √(37 − 6²) = 1 y (−43 − (−8)·6)/1 = 5.
Último pivote: √(98 − (−8)² − 5²) = 3.

El término dominante del trabajo aritmético es n³/3 FLOPs; almacenar matrices densas requiere O(n²) elementos. La implementación Python agrega costos de interpretación y objetos: no representa el rendimiento de C ni una biblioteca numérica optimizada.

## Qué implementamos y por qué

`cholesky.py` mantiene A y construye una L nueva. Esto facilita comparar y evita que repetir una prueba factorice por accidente una matriz ya modificada. Los ceros superiores se conservan explícitamente.

Para generar SPD elegimos entradas simétricas fuera de la diagonal y fijamos aᵢᵢ = 1 + Σⱼ≠ᵢ |aᵢⱼ|. Los autovalores son reales por simetría y quedan en intervalos positivos por dominancia diagonal estricta. Por tanto la matriz es SPD. Es una familia inicial reproducible mediante semilla, no una representación de todos los problemas ni una prueba de robustez ante mal condicionamiento.

## Experimento de corrección

Probamos el factor conocido, escalares, identidad, tamaños no redondos y tres semillas por tamaño. También exigimos errores explícitos para entradas vacías, no cuadradas, asimétricas, indefinidas, semidefinidas y no finitas. Un factor deliberadamente erróneo debe producir residuo elevado.

La medida es r = ||A − LLᵀ||F / ||A||F. Para esta familia pequeña y bien condicionada usamos r < 10⁻¹² como criterio práctico; no es un umbral universal. El residuo pequeño verifica reconstrucción, no asegura por sí solo un error pequeño al resolver cualquier sistema mal condicionado.

## Primer protocolo estadístico

Para N = 32, 64 y 128: una ejecución de calentamiento y siete medidas. La entrada es la misma para las repeticiones de cada N. Se mide con reloj monótono `perf_counter`; la reconstrucción se hace después de detener el cronómetro. Conservamos observaciones individuales y reportamos mediana, cuartiles e IQR = Q3 − Q1. El IQR describe dispersión, no es un intervalo de confianza.

Estas mediciones sirven para verificar el procedimiento. No compararemos tiempos de Python con futuros tiempos MPI para calcular speedup. Tampoco atribuiremos variaciones a caché o CPU sin evidencia adicional. Las verificaciones entre repeticiones pueden modificar el estado de caché; el protocolo debe mantenerse explícito.

## Resultados

Ejecución local del 21 de septiembre de 2026, con Python 3.12.14 sobre Windows 11. Las cinco pruebas automatizadas pasaron; el caso generado recorre doce combinaciones de tamaño y semilla. El ejemplo 3×3 produjo exactamente el factor esperado.

Datos medidos en esta etapa (milisegundos; siete repeticiones por fila):

| N | Mediana (ms) | Q1 (ms) | Q3 (ms) | IQR (ms) | Residuo máximo |
|---:|---:|---:|---:|---:|---:|
| 32 | 1.2313 | 1.2255 | 1.2627 | 0.0372 | 1.08 × 10⁻¹⁶ |
| 64 | 7.3433 | 7.3293 | 7.4244 | 0.0951 | 9.68 × 10⁻¹⁷ |
| 128 | 55.7097 | 55.3702 | 55.9313 | 0.5611 | 1.19 × 10⁻¹⁶ |

Archivos originales: [mediciones individuales](../resultados/20260921T170357862059Z/mediciones.csv), [resumen](../resultados/20260921T170357862059Z/resumen.csv) y [entorno](../resultados/20260921T170357862059Z/entorno.json).

Interpretación: los casos ensayados reconstruyen A con residuo muy inferior al criterio propuesto. Al duplicar N, la mediana aumenta aproximadamente 5.96 y 7.59 veces. La tendencia es compatible con trabajo cúbico, pero tres tamaños pequeños en Python no demuestran una ley de escalabilidad ni permiten extrapolar tiempos al clúster. La evidencia apoya la corrección en los casos probados; no constituye una prueba exhaustiva de estabilidad numérica.

Por ahora una tabla permite ver todas las observaciones resumidas sin agregar un gráfico redundante. En las comparaciones de variantes y procesos se incorporarán curvas de tiempo y speedup con dispersión.

## Próxima pregunta

¿Cuánto cambia el costo al llevar el mismo algoritmo a C y separar reserva, generación, factorización y validación? Esa será la etapa 2. Después preguntaremos qué actualizaciones pueden agruparse por bloques y ejecutarse en paralelo sin violar dependencias.

Fuente para contrastar el objetivo matemático y una implementación de producción por bloques: [LAPACK DPOTRF](https://netlib.org/lapack/explore-html/d2/d09/group__potrf_ga84e90859b02139934b166e579dd211d4.html). Nuestra referencia escalar no reproduce su implementación optimizada.
