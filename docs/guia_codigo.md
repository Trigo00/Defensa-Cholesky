# Guía para entender y defender el código

## Qué versión estás leyendo

Los archivos `.c` de `src/implementacion_final/` contienen el programa que se presenta y evalúa. Los de `src/experimentos/` son bancos comparativos, el cronómetro y utilidades auxiliares. Todos contienen la versión didáctica del 29/09/2026: instrucciones separadas, comentarios en español y pequeñas funciones comunes. Los comentarios explican cada instrucción lógica; las llaves y las líneas que continúan una misma expresión comparten esa explicación. Las cabeceras de funciones describen su propósito. Los `.h` se mantienen breves: contienen las interfaces y los tipos necesarios para compilar.

Los fuentes exactos anteriores están en `archive/src_medidos_20260928/`, con su Makefile y `sha256.json`. Las cuatro copias que ya tenían un formato distinto se conservan además en `archive/formato_previo_20260929`, junto con sus hashes y la comprobación de igualdad de instrucciones. Los tiempos del informe corresponden a las campañas originales, no a una nueva campaña de la versión refactorizada. Las modificaciones mantienen los algoritmos, el orden de las operaciones numéricas, los argumentos, los CSV y las fronteras de medición; esto no implica tiempos idénticos tras recompilar.

Se compartieron la conversión de argumentos, la diferencia entre factores, la generación de una columna y la preparación de la columna MPI. Se corrigió además un acceso a `d->n` anterior al control de `d == NULL` en left MPI. La validación de punteros no sustituye el contrato colectivo: los procesos deben recibir argumentos compatibles y llamar las colectivas en el mismo orden.

## Orden recomendado de lectura

1. `src/implementacion_final/main_candidate.c`: qué recibe el programa y cómo organiza las fases.
2. `src/implementacion_final/cholesky.c`: generación de A, right-looking y right con vector; después left y residuos.
3. Las funciones `layout_*` de `src/implementacion_final/cholesky_mpi.c`: significado y cálculo del reparto.
4. `src/implementacion_final/cholesky_mpi.c`: mapeo de columnas, preparación, difusión y actualización local.
5. Volver a `main_candidate.c` para seguir los relojes y la reconstrucción de L.
6. `src/experimentos/cholesky_left_mpi.c`: alternativa experimental y sus reducciones.
7. Los `compare_*.c` de `src/experimentos/`: qué pregunta responde cada banco y cómo valida sus resultados.

No hace falta aprender todos los bancos antes de entender el candidato. Cada banco conserva un `main` independiente porque sus opciones, relojes y salidas son distintos.

## Mapa de todos los archivos de src

Los cinco primeros forman `src/implementacion_final/`; los restantes están en `src/experimentos/`.

| Archivo | Papel y puntos que debes poder explicar |
|---|---|
| `cholesky.h` | Contratos públicos: tamaños, buffers, triángulo inferior y significado del retorno. |
| `cholesky.c` | SplitMix64; generación SPD; kernels left, right y right con vector; residuos completo y proyectado. |
| `cholesky_mpi.h` | `Layout`, `Profile`, `LeftProfile` y contratos colectivos. |
| `cholesky_mpi.c` | Propiedad contigua, cíclica y por grupos; difusión de columnas; vector local opcional mediante dos funciones distintas. |
| `cholesky_left_mpi.c` | Productos con columnas anteriores propias; reducción al propietario; construcción y difusión del pivote. |
| `main_candidate.c` | Entrada N; mismo archivo compilado secuencial/MPI; reserva, generación, factor, reunión, validación y CSV. |
| `main.c` | Banco inicial de right secuencial: N, repeticiones y semilla; validación completa fuera del tiempo de factor. |
| `compare_seq.c` | Left contra right, alternando qué variante se ejecuta primero. |
| `compare_memory.c` | Añade right con vector; usa las seis permutaciones de tres variantes. |
| `compare_mpi.c` | Contiguo contra cíclico con kernel original; modo `profile` y pruebas de errores colectivos. |
| `compare_mpi_local.c` | Cuatro combinaciones reparto/kernel; orden Williams y centinelas del vector auxiliar. |
| `compare_mpi_algorithms.c` | Left contra right MPI en reparto cíclico, con perfiles separados. |
| `compare_mpi_total.c` | Incluye empaquetado/reparto y reunión; contrasta con copia y factor secuenciales. |
| `compare_generation.c` | Generación centralizada y distribuida; exige igualdad bit a bit mediante `memcmp`. |
| `compare_application.c` | Tres flujos completos: centralizado, distribuido y secuencial; reserva y generación dentro del reloj. |
| `compare_blocks.c` | Propiedad por b=1,2,4,8,16,32,64 columnas; modo `pair` para b=1/4; validación del mapa. |
| `compare_lapack.c` | DPOTRF contra right con vector propio; un hilo OpenBLAS comprobado por API. |
| `measure_command.c` | Ejecuta un proceso hijo y mide desde antes de `fork` hasta después de `waitpid`. |
| `bench_utils.c` | `parse_unsigned`, `parse_bounded` y `factor_difference`: utilidades compartidas y comentadas. |
| `bench_utils.h` | Solo declara esas tres funciones para poder enlazarlas desde los bancos. |

## Cómo se guarda una matriz

En secuencial, `a[i*n+j]` es A(i,j). El arreglo tiene n² elementos `double`, consecutivos por filas. El factor L ocupa el triángulo inferior, incluida la diagonal. El triángulo superior no se convierte en ceros y no debe leerse como parte de L.

En MPI, `a[i*m+c]` es la fila global i y la columna **local** c, con `m=d.cols`. El índice global de esa columna se obtiene con `layout_global`. Distribuir columnas no significa usar almacenamiento local por columnas: los datos locales también se guardan por filas.

Ejemplo N=8 y P=3, con índices desde cero:

| Rango | Columnas globales | cols |
|---|---|---|
| 0 | 0, 3, 6 | 3 |
| 1 | 1, 4, 7 | 3 |
| 2 | 2, 5 | 2 |

En rango 1, `local[6*3+1]` guarda A(6,4). La columna global 4 pertenece a `4%3=1`; `layout_before(&d,4)` vale 1 en ese propietario. Por eso puede utilizarse como índice local de la columna activa.

Si N<P, algunos rangos tienen cero columnas. Reservan un buffer mínimo y siguen participando en las colectivas: tener cero trabajo local no permite saltarse `MPI_Bcast`.

## Un paso de right-looking MPI

Para cada columna j:

1. `layout_owner(d,j)` identifica al propietario.
2. `prepare_column` se ejecuta en todos los rangos, pero solo el propietario lee su diagonal, obtiene la raíz y divide los elementos inferiores por el pivote.
3. `MPI_Bcast(column+j,n-j,...)` entrega ese segmento a todos. Su raíz es el propietario de j, que cambia entre columnas; no siempre es rango 0.
4. Todos comprueban el pivote recibido. Si el propietario encontró un pivote inválido, dejó `NAN` y todos retornan -1 después de la misma difusión.
5. Cada rango actualiza solo sus columnas futuras y solo el triángulo inferior: A(i,k) -= L(i,j)L(k,j), con j<k<=i.

`begin=layout_before(d,j+1)` excluye las columnas ya resueltas. `end=layout_before(d,i+1)` excluye la parte superior de la matriz. Los bucles usan `c<end` porque end es un límite exclusivo.

En la variante original, el bucle interno traduce c a k para leer `column[k]`. En la variante con vector local, esa traducción se hace antes, copiando `local_column[c]=column[layout_global(d,c)]`. La copia se paga dentro del kernel y luego se reutiliza en varias filas. Las dos funciones siguen separadas para que esta diferencia sea visible.

## Qué cambia en left-looking MPI

Cada rango calcula, con sus columnas anteriores, una parte de la suma de cuadrados del pivote y de los productos de las filas inferiores. `MPI_Reduce` con `MPI_SUM` entrega esas contribuciones al propietario de la columna j. Este resta las sumas globales, calcula la raíz y completa su columna.

La reducción escalar se hace N veces; la vectorial N-1, porque la última columna no tiene filas inferiores; la difusión del pivote N veces. Son 3N-1 colectivas en esta implementación, frente a N difusiones en right. No es una afirmación sobre todos los algoritmos left posibles.

En el perfil left conservado, el campo `broadcast` incluye la preparación del pivote/columna entre la reducción y el final de `MPI_Bcast`; en right corresponde al intervalo de la difusión. Los perfiles no deben interpretarse como una descomposición idéntica de ambos algoritmos.

## Por qué la generación distribuida produce la misma A

El generador secuencial visita cada entrada superior una vez y la refleja al triángulo inferior. `indexed_value` calcula la posición de ese par dentro de la misma secuencia pseudoaleatoria y salta a su estado. Intercambiar i y j no cambia el valor generado.

`generate_column` suma las magnitudes en el mismo orden de índices que la referencia y escribe una diagonal igual a la suma más uno. Esto conserva simetría y dominancia diagonal estricta con diagonal positiva. El generador trabaja con enteros unsigned: el desbordamiento módulo 2^64 de la secuencia es intencional.

La comparación de generación exige igualdad de bytes, no solo un residuo pequeño. El parámetro b cambia propietarios por grupos de columnas; no convierte el cálculo escalar en Cholesky bloqueado con BLAS-3.

## Qué hace el candidato completo

`USE_MPI` es una decisión de compilación. `make candidate` construye dos ejecutables a partir del mismo `main_candidate.c`:

| Frontera | Actividad |
|---|---|
| Antes de t0 | En MPI: inicialización, argumentos y barrera. |
| t0 → t1 | Reserva de buffers y metadatos. |
| t1 → t2 | Generación central en secuencial o local distribuida en MPI. |
| t2 → t3 | Factorización; el kernel MPI incluye comunicaciones y esperas. |
| t3 → t4 | Reunión y reconstrucción global en MPI; no hay reunión en secuencial. |
| Después de t4 | Reducciones auxiliares, validación, CSV, liberación y finalización. |

`application_s=t4-t0` del rango 0 es la suma de sus fases consecutivas. `max_local_s` se calcula aparte como máximo entre rangos. `factor_s` del candidato no es una reducción por máximo ni cómputo puro.

`counts[r]` indica cuántos doubles recibirá el rango r y `offsets[r]` dónde empieza su segmento en el buffer empaquetado. `MPI_Gatherv` concatena esos segmentos; los bucles siguientes reconstruyen su ubicación en la matriz global.

En `compare_mpi_total`, en cambio, se reduce el máximo de cada fase. Esos máximos pueden provenir de rangos distintos y no tienen por qué sumar el máximo total. En el banco LAPACK, `total_s` incluye reserva, generación y factor, con otra frontera. Los bancos mantienen estas diferencias deliberadamente.

## Cómo leer la sintaxis de C que aparece aquí

| Expresión | Significado en este proyecto |
|---|---|
| `double *a` | Dirección del primer elemento del buffer; no contiene por sí sola las dimensiones. |
| `const Layout *d` | Puntero a metadatos que esta función no modifica. |
| `&x` | Dirección de x: permite que MPI o una función escriban su resultado allí. |
| `d->cols` / `d.cols` | Campo de una estructura accedida mediante puntero / mediante valor. |
| `(size_t)i*n+j` | Calcula un índice con un tipo adecuado para tamaños; el cast ocurre antes del producto. |
| `sizeof(double)` | Bytes de cada elemento, para convertir un conteo en memoria a reservar. |
| `condición ? a : b` | Selecciona una de dos expresiones; solo se evalúa la rama elegida. |
| `failed |= condición` | Conserva cualquier fallo previo y añade el nuevo; no lo reinicia a cero. |
| `!rank` | Verdadero únicamente para rango 0. |
| `rep=0` | Preparación no exportada como medición útil en estos bancos. |
| `column[i] = a[...] /= column[j]` | Primero divide y actualiza a[...]; después copia ese nuevo valor al mensaje. |
| `static` | Función privada de este archivo/unidad de compilación. |
| Función declarada en `.h` e implementada en `.c` | El encabezado anuncia la interfaz; el archivo C contiene toda la lógica que debes explicar. |
| `NULL`, `NAN`, `INFINITY` | Sin buffer; dato no numérico; indicador de residuo inválido/infinito, respectivamente. |
| `free(NULL)` | Operación válida; simplifica liberar buffers reservados solo en rango 0. |

## Qué demuestran las validaciones

El residuo completo reconstruye LLᵀ con acumulación `long double` y calcula ||A-LLᵀ||F/||A||F. Su costo es cúbico. El proyectado prueba ocho vectores de signos, con costo cuadrático por vector; no comprueba todas las direcciones posibles. La diferencia de factores compara cada elemento inferior contra una referencia, con denominador `max(1,abs(referencia))`.

El umbral principal es 1e-12, con controles históricos de diferencia a 1e-13 en algunos bancos. Se conservaron esos umbrales. Los centinelas de `compare_mpi_local` y su inicialización con NaN ayudan a detectar desbordes y lecturas prematuras del vector.

LAPACK se llama como column-major, triángulo superior. Para una entrada simétrica, el mismo buffer row-major se ve transpuesto: Uᵀ coincide con el L que se interpreta en el triángulo inferior row-major. La función `_work` evita la conversión row-major y el escaneo opcional de NaN de la interfaz de alto nivel.

## Cómo repetir las comprobaciones de la refactorización

En Linux/WSL con GCC, Make, MPI, LAPACKE, OpenBLAS y Python 3:

```bash
python3 scripts/verify_code_refactor.py
```

El script verifica los hashes originales, compila una referencia temporal desde los fuentes conservados, compila la versión actual y compara códigos de salida, encabezados, número de filas y campos CSV no temporales. Ejecuta los bancos de prueba con P=1,2,3,4,6, el candidato con N=1,7,128, los modos `profile` y `pair`, argumentos inválidos y el cronómetro externo. Comprueba también el caso nuevo de Layout nulo. Los tiempos solo deben ser finitos y no negativos: no se exige igualdad temporal ni se infiere una aceleración.

Los registros están en `docs/checks/refactor_build.log`, `refactor_equivalence.log` y `refactor_equivalence.json`. El JSON contiene los hashes de los fuentes actuales normalizando CRLF a LF para portabilidad con Git a los que corresponde la prueba. El análisis de resultados históricos sigue contrastando sus fuentes con `archive/src_medidos_20260928`, sin cambiar los CSV originales.

## Preguntas que debes poder responder en la defensa

1. Qué representa `local[i*cols+c]` y cómo se recupera la columna global.
2. Por qué todos llaman a Bcast aunque solo el propietario complete la columna.
3. Cómo evita el marcador NaN que un solo rango abandone el kernel antes de la difusión.
4. Por qué el vector local puede ayudar sin cambiar la matemática ni reducir las colectivas.
5. Qué diferencia hay entre acelerar factor_s, application_s y el comando completo.
6. Por qué una biblioteca local optimizada puede superar al kernel propio distribuido.
7. Qué comprueban los tests y qué no demuestran sobre rendimiento o matrices mal condicionadas.

