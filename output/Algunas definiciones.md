# Cholesky HPC

## Conceptos clave, comparación con LAPACK/OpenBLAS y mejoras futuras

*Versión editorial del cuaderno `Cronologia.ipynb`*

> **Criterio de edición:** El contenido técnico se conserva, pero se reorganiza en formato de informe: títulos, listas, tablas, fórmulas y fragmentos de código se presentan sin marcas de Markdown ni diagramas ASCII difíciles de leer.

## Contenido

1. [Nuestra optimización frente a LAPACK/OpenBLAS](#1-nuestra-optimización-frente-a-lapackopenblas)
2. [La pila LAPACKE - LAPACK/DPOTRF - BLAS - OpenBLAS](#2-la-pila-lapacke---lapackdpotrf---blas---openblas)
3. [Qué es DPOTRF](#3-qué-es-dpotrf)
4. [Qué es BLAS y qué significa nivel 3](#4-qué-es-blas-y-qué-significa-nivel-3)
5. [Qué es OpenBLAS](#5-qué-es-openblas)
6. [Qué mostraron nuestros resultados](#6-qué-mostraron-nuestros-resultados)
7. [Qué aportaría OpenMP](#7-qué-aportaría-openmp)
8. [Qué generaría OpenMP en nuestro proyecto](#8-qué-generaría-openmp-en-nuestro-proyecto)
9. [OpenMP y Cholesky bloqueado](#9-openmp-y-cholesky-bloqueado)
10. [Distribución MPI 1D y 2D](#10-distribución-mpi-1d-y-2d)
11. [Hoja de ruta técnica posible](#11-hoja-de-ruta-técnica-posible)
12. [Resumen para recordar](#12-resumen-para-recordar)
13. [ScaLAPACK: qué es y cómo se diferencia de LAPACK](#13-scalapack-qué-es-y-cómo-se-diferencia-de-lapack)

## Introducción

Este documento organiza los conceptos que surgieron durante la investigación para distinguir qué optimizamos en nuestra implementación, qué aportan LAPACK y OpenBLAS, qué papel podría tener OpenMP y qué significa una distribución MPI bidimensional.

La discusión se ordena alrededor de tres dimensiones que conviene mantener separadas:

1. Cómo se organiza el algoritmo y el acceso a memoria.

2. Cómo se ejecuta eficientemente el cálculo dentro de un core o nodo.

3. Cómo se reparte el trabajo entre varios cores, procesos o nodos.

El proyecto exploró principalmente la organización propia del algoritmo y, sobre todo, la distribución del trabajo mediante MPI. La comparación con LAPACK/OpenBLAS permitió observar cuánto rendimiento adicional puede obtenerse mejorando el cálculo local.

# 1. Nuestra optimización frente a LAPACK/OpenBLAS

Nuestra implementación y LAPACK resuelven el mismo problema matemático de factorización de Cholesky:

$A = LL^T$

La diferencia principal no está en la definición matemática, sino en la forma en que se organiza y ejecuta el trabajo.

## Lo que optimizamos en nuestra implementación

- Comparación entre las variantes left-looking y right-looking.
- Selección del enfoque right-looking.
- Introducción de un vector auxiliar para favorecer accesos más contiguos.
- Estudio del patrón de acceso a memoria.
- Distribución MPI de columnas.
- Comparación entre distribuciones contigua y cíclica.
- Almacenamiento local de columnas.
- Generación distribuida.
- Recolección (gathering) del resultado.
- Análisis de distintos esquemas de propiedad de columnas.

Estas mejoras permitieron construir una implementación comprensible, correcta y paralelizable. Sin embargo, el núcleo numérico continúa expresado en gran medida mediante bucles propios en C que operan sobre elementos o columnas.

## Lo que representa LAPACK/OpenBLAS

LAPACK/OpenBLAS trabaja en un nivel de optimización distinto. En lugar de limitarse a mejorar recorridos de memoria puntuales, organiza una parte importante del cálculo como operaciones grandes sobre bloques de matrices y delega esas operaciones a kernels altamente optimizados.

La comparación, por lo tanto, no significa que nuestra implementación sea matemáticamente incorrecta ni que LAPACK utilice una factorización diferente. Ambos calculan Cholesky; la diferencia observada está en la eficiencia de la implementación.

> **Idea clave:** Nuestro MPI mejora principalmente el reparto del trabajo. LAPACK/OpenBLAS muestra cuánto puede mejorar todavía el trabajo local que ejecuta cada core.

# 2. La pila LAPACKE - LAPACK/DPOTRF - BLAS - OpenBLAS

Una forma útil de entender las capas utilizadas en el benchmark es la siguiente:

| **Capa**        | **Responsabilidad**                                                                   |
|-----------------|---------------------------------------------------------------------------------------|
| Programa en C   | Invoca la rutina de factorización desde nuestra aplicación.                           |
| LAPACKE         | Interfaz C para llamar rutinas de LAPACK.                                             |
| LAPACK / DPOTRF | Implementa la factorización de Cholesky para matrices simétricas definidas positivas. |
| BLAS            | Define operaciones básicas de álgebra lineal, desde vectores hasta matrices.          |
| OpenBLAS        | Implementa las operaciones BLAS de manera optimizada para CPUs reales.                |
| CPU             | Ejecuta finalmente los kernels numéricos.                                             |

En nuestro benchmark se utilizó LAPACKE_dpotrf_work, que ejecuta la factorización de Cholesky de LAPACK sobre datos en doble precisión.

# 3. Qué es DPOTRF

DPOTRF es la rutina de LAPACK destinada a factorizar una matriz real, simétrica y definida positiva.

El nombre sigue la convención histórica de LAPACK:

- D indica números reales en doble precisión (double).
- POTRF identifica la factorización de una matriz positive definite mediante Cholesky.

Según el triángulo solicitado, la rutina produce un factor L o U que cumple una de las siguientes identidades:

$A = LL^T$

$A = U^T U$

En nuestro código se utilizó la llamada:

```c
LAPACKE_dpotrf_work(LAPACK_COL_MAJOR, 'U', n, a, n);
```

## Por qué puede ser tan rápida

La implementación bloqueada de LAPACK organiza gran parte de la factorización en subproblemas sobre bloques de la matriz. Conceptualmente, el procedimiento puede resumirse en tres pasos:

1. Factorizar el bloque diagonal.
2. Calcular el panel asociado.
3. Actualizar la submatriz restante mediante una operación equivalente a $A_{22} = A_{22} - L_{21}L_{21}^T$.

La tercera operación concentra mucho trabajo en operaciones matriz-matriz. Esto permite que LAPACK delegue una parte importante del costo a BLAS de nivel 3.

> **Aclaración:** El parámetro b usado en nuestros ensayos de propiedad de columnas (por ejemplo, b = 1 o b = 4) modificaba la distribución de columnas. No convertía automáticamente nuestro código en un Cholesky bloqueado del estilo de LAPACK.

# 4. Qué es BLAS y qué significa nivel 3

BLAS significa Basic Linear Algebra Subprograms. Es una especificación de operaciones fundamentales de álgebra lineal y suele dividirse en tres niveles.

| **Nivel** | **Tipo de operación** | **Ejemplo conceptual** | **Escala de trabajo**  |
|-----------|-----------------------|------------------------|------------------------|
| BLAS 1    | Vector con vector     | y = alpha x + y        | Aproximadamente O(n)   |
| BLAS 2    | Matriz con vector     | y = A x                | Aproximadamente O(n^2) |
| BLAS 3    | Matriz con matriz     | C = alpha A B + beta C | Puede alcanzar O(n^3)  |

En BLAS 3 el volumen de cálculo puede crecer cúbicamente mientras que los datos almacenados crecen cuadráticamente. Esto permite reutilizar muchas veces los mismos datos después de cargarlos en caché o registros y, por lo tanto, aumentar la intensidad aritmética.

> **Definición:** Intensidad aritmética = operaciones realizadas / datos transferidos.

## Operaciones BLAS 3 relevantes para Cholesky

- DTRSM: resolución triangular con múltiples columnas.
- DSYRK: actualización simétrica de rango k, conceptualmente similar a C = C - A A^T.

BLAS 3 no constituye otro algoritmo de Cholesky. Son operaciones matriciales grandes y eficientes que LAPACK utiliza como componentes para implementar la factorización.

# 5. Qué es OpenBLAS

BLAS define qué operaciones deben existir. OpenBLAS ofrece una implementación concreta y optimizada de esas operaciones para arquitecturas de CPU reales.

| **Concepto** | **Interpretación**                                                                              |
|--------------|-------------------------------------------------------------------------------------------------|
| BLAS         | Define, por ejemplo, que DGEMM realiza una multiplicación matriz-matriz.                        |
| OpenBLAS     | Implementa DGEMM y otras rutinas buscando aprovechar eficientemente la arquitectura disponible. |

Entre las técnicas de optimización que puede utilizar OpenBLAS se encuentran:

- SIMD o vectorización: una instrucción procesa varios valores.
- Uso intensivo de registros para mantener pequeños bloques en recursos rápidos del procesador.
- Blocking para caché, con bloques pensados para reutilización en L1, L2 o L3.
- Packing, es decir, reorganización temporal de bloques para facilitar el trabajo del kernel.
- Microkernels especializados para operaciones matriciales.
- Selección de kernels según la arquitectura de CPU.

En el clúster se verificó la siguiente configuración:

```text
OpenBLAS 0.3.34
DYNAMIC_ARCH
Zen
threads = 1
```

El uso de un solo hilo fue deliberado: la intención era medir la eficiencia local de LAPACK/OpenBLAS sin asignarle más cores que a una ejecución secuencial.

# 6. Qué mostraron nuestros resultados

Antes de interpretar tiempos y gráficas, conviene separar cuatro conceptos que cumplen funciones distintas en el proyecto: **residuo, mediana, Q1/Q3 y speedup**.

## Cómo leer las mediciones

### Residuo

El **residuo** es una medida de **corrección numérica**, no de rendimiento. Sirve para comprobar si el factor $L$ calculado reproduce adecuadamente la matriz original $A$. Una forma estándar de expresar esta idea es mediante un residuo relativo de reconstrucción:

$$
r = \frac{\lVert A-LL^T \rVert}{\lVert A \rVert}.
$$

Cuanto más próximo a cero es $r$, mejor coincide el producto $LL^T$ con la matriz que se quería factorizar. La expresión anterior describe el concepto; la norma y la normalización exactas dependen de la rutina de validación utilizada.

En las pruebas del proyecto, una ejecución solo se aceptaba como válida si superaba las comprobaciones numéricas establecidas. Por eso los resultados incluían indicadores como `valid=1` junto con el residuo. `valid=1` resume que la ejecución pasó las validaciones implementadas; no significa simplemente que «el tiempo fue bueno». El criterio documentado fue exigir errores suficientemente pequeños, típicamente por debajo de $10^{-12}$.

Para matrices pequeñas podía comprobarse la reconstrucción completa. En tamaños grandes se utilizó además una **comprobación proyectada**: para varios vectores $x$ se comparó $Ax$ con $L(L^T x)$. Esta técnica reduce el costo de validar, pero no equivale a reconstruir por completo $LL^T$ ni constituye un certificado matemático capaz de detectar cualquier error posible.

> **Importante:** el residuo responde a la pregunta *«¿el resultado numérico es aceptable?»*. No se utiliza para calcular el speedup, la mediana ni los cuartiles.

### Mediana

La **mediana** es el valor central de un conjunto de observaciones ordenadas. Con una cantidad impar de mediciones es la observación que queda exactamente en el centro; con una cantidad par es el promedio de las dos observaciones centrales.

En este proyecto se utilizó la mediana como **tiempo representativo** de las repeticiones de una misma configuración. Es especialmente útil en benchmarking porque una ejecución excepcionalmente lenta puede modificar mucho el promedio, mientras que la mediana es bastante más resistente a ese valor extremo.

Ejemplo: si cinco ejecuciones tardan `10, 10, 11, 11 y 40 ms`, la mediana es `11 ms`. El tiempo de `40 ms` se conserva como observación real, pero no desplaza el valor representativo tanto como ocurriría con el promedio.

### Q1 y Q3

**Q1** y **Q3** son el primer y el tercer cuartil de la distribución de tiempos. De manera intuitiva:

- **Q1** es el percentil 25: aproximadamente una cuarta parte de las observaciones queda en o por debajo de ese nivel.
- **Q3** es el percentil 75: aproximadamente tres cuartas partes de las observaciones quedan en o por debajo de ese nivel.
- El intervalo **Q1–Q3** contiene aproximadamente el 50 % central de las observaciones. Su ancho, $Q3-Q1$, es el **rango intercuartílico** y sirve para describir dispersión.

En los análisis del proyecto los cuartiles se calcularon con la convención inclusiva usada por los scripts de análisis; por eso, con pocas repeticiones, conviene leerlos como estadística descriptiva y no como una estimación inferencial.

En las gráficas del proyecto, las barras Q1–Q3 muestran la variabilidad central de los tiempos repetidos. **No son residuos numéricos, no son márgenes de error de la factorización y tampoco son intervalos de confianza.**

### Speedup

El **speedup** o aceleración cuantifica cuánto más rápido resulta un método respecto de una referencia. En las comparaciones principales del proyecto se calculó como el cociente entre **medianas contemporáneas**:

$$
S = \frac{\operatorname{mediana}(T_{\text{referencia}})}{\operatorname{mediana}(T_{\text{método}})}.
$$

Cuando la referencia es el programa secuencial propio y el método evaluado es MPI:

$$
S_{\text{MPI}} = \frac{\operatorname{mediana}(T_{\text{seq}})}{\operatorname{mediana}(T_{\text{MPI}})}.
$$

La interpretación es:

- $S>1$: el método evaluado es más rápido que la referencia.
- $S=1$: ambos tienen el mismo tiempo representativo.
- $S<1$: el método evaluado es más lento que la referencia.

La palabra **contemporáneas** es importante: se comparan mediciones obtenidas dentro de la misma campaña y bajo condiciones comparables, en lugar de dividir tiempos de sesiones diferentes. El speedup **no se calcula con Q1, Q3 ni con el residuo**.

También debe conservarse la misma frontera temporal. Un speedup de la **factorización**, un speedup de `application_s` y un speedup del **comando completo** responden preguntas distintas y no deben mezclarse.

Cuando se informa eficiencia paralela, se utiliza:

$$
E = \frac{S}{P},
$$

donde $P$ es la cantidad de procesos. Esta magnitud expresa cuánto del speedup lineal ideal se obtuvo respecto de la referencia elegida; **no equivale al porcentaje de utilización de CPU**.

La comparación dejó una conclusión central: aumentar el paralelismo no reemplaza automáticamente a un kernel local eficiente.

## Campaña grande

| **Tamaño N** | **C propio** | **MPI, P = 6** | **LAPACK/OpenBLAS, 1 hilo** |
|--------------|--------------|----------------|-----------------------------|
| 6144         | ≈ 27,27 s    | ≈ 16,30 s      | ≈ 1,90 s                    |
| 8192         | ≈ 72,09 s    | ≈ 36,95 s      | ≈ 5,92 s                    |

Para N = 6144, el cociente 27,27 / 16,30 es aproximadamente 1,67. Es decir, MPI aceleró nuestra implementación propia alrededor de 1,67 veces. En cambio, 27,27 / 1,90 es aproximadamente 14,36: LAPACK/OpenBLAS con un solo hilo fue alrededor de 14,36 veces más rápido que nuestro secuencial propio en factor_s.

Para N = 8192, 72,09 / 36,95 es aproximadamente 1,95, por lo que MPI casi duplicó el rendimiento de nuestro kernel secuencial. Aun así, LAPACK continuó claramente por delante.

## Interpretación

| **Tecnología**  | **Qué problema ataca principalmente**                                      |
|-----------------|----------------------------------------------------------------------------|
| MPI             | Reparte trabajo entre procesos y permite trabajar con memoria distribuida. |
| LAPACK/OpenBLAS | Hace mucho más eficiente el cálculo local.                                 |

Los resultados muestran que una solución HPC completa debe prestar atención simultáneamente a la distribución del trabajo y a la eficiencia del cálculo local.

# 7. Qué aportaría OpenMP

OpenMP permite crear hilos dentro de un mismo proceso y aprovechar varios cores que comparten memoria.

| **Aspecto**         | **MPI**                                       | **OpenMP**                                                |
|---------------------|-----------------------------------------------|-----------------------------------------------------------|
| Unidad de ejecución | Procesos independientes                       | Hilos dentro de un proceso                                |
| Memoria             | Cada proceso dispone de su espacio de memoria | Los hilos comparten el espacio de memoria del proceso     |
| Coordinación        | Comunicación explícita mediante MPI           | Sincronización y regiones paralelas de memoria compartida |
| Ejemplos            | MPI_Bcast, MPI_Send, MPI_Recv, MPI_Gatherv    | \#pragma omp parallel for                                 |

En C, una región de paralelismo simple puede expresarse de la siguiente manera:

```c
#pragma omp parallel for
for (int i = 0; i < n; ++i) {
    /* trabajo independiente */
}
```

En Cholesky no cualquier bucle puede paralelizarse de esta forma. Existen dependencias de datos entre etapas de la factorización, por lo que agregar directivas sin analizar esas dependencias puede producir resultados incorrectos o un rendimiento pobre.

# 8. Qué generaría OpenMP en nuestro proyecto

Una evolución natural sería estudiar un esquema híbrido MPI + OpenMP. La idea sería utilizar pocos procesos MPI y varios hilos dentro de cada proceso.

| **Nivel** | **Función posible**                                                      |
|-----------|--------------------------------------------------------------------------|
| MPI       | Distribuir datos y trabajo entre procesos, y potencialmente entre nodos. |
| OpenMP    | Aprovechar varios cores que comparten memoria dentro de cada proceso.    |

Como ejemplo conceptual, sobre una asignación de 24 cores podría explorarse una configuración de 6 procesos MPI con 4 hilos OpenMP por proceso, en lugar de utilizar 24 procesos MPI.

## Qué podría aportar

- Menos procesos MPI.
- Menor necesidad de intercambiar datos entre hilos del mismo rank.
- Aprovechamiento natural de la memoria compartida dentro de un nodo.
- Posibilidad de combinar paralelismo entre nodos con paralelismo intranodo.

> **Modelo simplificado:** MPI puede pensarse como el nivel de distribución entre procesos o nodos, mientras que OpenMP puede aprovechar cores que comparten memoria dentro de un proceso. Es un modelo mental útil, aunque no una regla obligatoria.

## Precaución: oversubscription

Al combinar MPI, OpenMP y una BLAS multihilo es necesario controlar explícitamente la cantidad total de hilos. Por ejemplo, 6 ranks MPI × 4 hilos OpenMP × 4 hilos OpenBLAS producirían 96 hilos de ejecución, una configuración inadecuada sobre una asignación de 24 cores.

Una versión híbrida debe definir con claridad qué nivel controla el paralelismo y cuántos recursos consume cada componente.

# 9. OpenMP y Cholesky bloqueado

Agregar OpenMP al kernel actual podría aportar rendimiento, pero una evolución más interesante sería combinarlo con una reorganización bloqueada de Cholesky.

En un Cholesky bloqueado la matriz se divide conceptualmente en submatrices. Después de factorizar el bloque necesario y calcular el panel asociado, pueden aparecer varias actualizaciones de bloques con un mayor grado de independencia.

| **Etapa**              | **Idea**                                                           |
|------------------------|--------------------------------------------------------------------|
| 1. Factorizar bloque  | Resolver el bloque diagonal requerido.                             |
| 2. Calcular panel     | Obtener los datos necesarios para las actualizaciones posteriores. |
| 3. Actualizar bloques | Aplicar varias actualizaciones sobre submatrices restantes.        |

Este tipo de trabajo se adapta mejor a tareas o hilos OpenMP, a operaciones BLAS 3 sobre bloques y a una mayor reutilización de caché.

> **Dirección técnica:** La mejora futura más interesante no sería simplemente “agregar OpenMP”, sino estudiar en conjunto bloqueo, BLAS 3 y paralelismo.

# 10. Distribución MPI 1D y 2D

## Distribución 1D

Nuestro diseño actual distribuye esencialmente columnas entre procesos. Con cuatro ranks y una distribución cíclica, la propiedad puede representarse de la siguiente manera:

| **Columna** | **0** | **1** | **2** | **3** | **4** | **5** | **6** | **7** |
|-------------|-------|-------|-------|-------|-------|-------|-------|-------|
| Dueño       | P0    | P1    | P2    | P3    | P0    | P1    | P2    | P3    |

La propiedad cambia en una sola dimensión: la columna.

## Distribución 2D

En una distribución 2D los procesos se organizan lógicamente en una grilla. Seis procesos, por ejemplo, pueden organizarse como una grilla de 2 × 3:

| **Columna lógica 1** | **Columna lógica 2** | **Columna lógica 3** |
|----------------------|----------------------|----------------------|
| P0                   | P1                   | P2                   |
| P3                   | P4                   | P5                   |

La matriz se divide en bloques y esos bloques se reparten tanto por filas como por columnas. Cuando el patrón de bloques se repite cíclicamente sobre la grilla se habla de una distribución 2D block-cyclic, utilizada por bibliotecas distribuidas como ScaLAPACK.

## Por qué puede ser útil

En álgebra lineal densa intervienen filas y columnas simultáneamente. Una grilla 2D puede permitir que determinadas comunicaciones se realicen dentro de filas o columnas de procesos, reduciendo la presión de comunicación global cuando el número de procesos crece.

Esto no implica que una distribución 2D sea automáticamente mejor para cualquier tamaño. Su conveniencia depende de que la escala del problema y la cantidad de procesos justifiquen la complejidad adicional.

> **No confundir:** Cholesky bloqueado describe cómo se organiza el cálculo. Distribución 2D describe cómo se reparten los datos o bloques entre procesos. Son decisiones distintas que pueden combinarse.

# 11. Hoja de ruta técnica posible

A partir de los resultados obtenidos, las mejoras futuras pueden ordenarse como una secuencia de complejidad creciente:

| **Etapa**       | **Tecnologías**                                                                       | **Objetivo**                                                               |
|-----------------|---------------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| Actual          | Cholesky right-looking propio + optimización de accesos + MPI 1D cíclico por columnas | Base experimental ya construida.                                           |
| Futuro A        | OpenMP                                                                                | Varios hilos dentro de cada proceso.                                       |
| Futuro B        | Cholesky bloqueado + BLAS 3                                                           | Mejor localidad, uso de caché y SIMD.                                      |
| Futuro C        | MPI + OpenMP + bloques/BLAS                                                           | Combinar paralelismo distribuido con eficiencia local.                     |
| Futuro avanzado | Distribución MPI 2D block-cyclic + bloques + MPI/OpenMP                               | Explorar escalas mayores con una organización distribuida más sofisticada. |

No es necesario implementar todas estas extensiones para validar el proyecto actual. Funcionan como una hoja de ruta de optimización coherente con los resultados experimentales obtenidos.

# 12. Resumen para recordar

| **Concepto**       | **Qué hace**                                            | **Papel en nuestro proyecto**                             |
|--------------------|---------------------------------------------------------|-----------------------------------------------------------|
| MPI                | Procesos con memoria separada y comunicación explícita. | Distribuye columnas y permite estudiar escalabilidad.     |
| OpenMP             | Hilos que comparten memoria dentro de un proceso.       | Posible mejora futura para paralelismo intranodo.         |
| DPOTRF             | Rutina LAPACK que calcula Cholesky.                     | Referencia optimizada utilizada en el benchmark.          |
| BLAS 3             | Operaciones grandes sobre matrices o bloques.           | Favorecen reutilización de datos e intensidad aritmética. |
| OpenBLAS           | Implementación optimizada de BLAS para CPU.             | Backend utilizado por LAPACK en las pruebas.              |
| Cholesky bloqueado | Reorganiza el cálculo en submatrices.                   | Posible mejora futura para explotar BLAS 3.               |
| Distribución 1D    | Reparte datos en una dimensión.                         | Diseño MPI actual, por columnas.                          |
| Distribución 2D    | Reparte bloques en una grilla de procesos.              | Alternativa futura para escalas mayores.                  |

> **Idea central:** MPI mejora cómo repartimos el trabajo; OpenMP puede mejorar cómo usamos varios cores que comparten memoria; el bloqueo y BLAS mejoran cómo se ejecuta el cálculo local.

Los resultados del proyecto muestran por qué estas dimensiones deben analizarse en conjunto: más paralelismo no garantiza por sí solo mejor rendimiento si el kernel local conserva un gran margen de optimización.

# 13. ScaLAPACK: qué es y cómo se diferencia de LAPACK

LAPACK está orientado al álgebra lineal densa en memoria local. Para Cholesky utiliza rutinas como DPOTRF, que operan sobre una matriz disponible localmente y aprovechan BLAS optimizado.

ScaLAPACK significa Scalable LAPACK. Extiende este tipo de operaciones a sistemas de memoria distribuida, es decir, a múltiples procesos MPI y potencialmente a varios nodos de un clúster.

## Diferencia principal

| **Aspecto**            | **LAPACK**                             | **ScaLAPACK**                                       |
|------------------------|----------------------------------------|-----------------------------------------------------|
| Ubicación de la matriz | Disponible localmente                  | Distribuida entre procesos                          |
| Comunicación MPI       | No distribuye datos entre procesos MPI | Utiliza comunicación entre procesos                 |
| Cholesky               | DPOTRF                                 | PDPOTRF                                             |
| Organización típica    | Memoria local                          | Grilla 2D de procesos con distribución block-cyclic |

ScaLAPACK suele organizar los procesos en una grilla 2D y distribuir los bloques de la matriz por filas y columnas. Esto contrasta con nuestra implementación, que utiliza una distribución 1D cíclica por columnas.

## Comparación conceptual con nuestra implementación

| **Nuestra implementación MPI**             | **ScaLAPACK**                                   |
|--------------------------------------------|-------------------------------------------------|
| Distribución 1D por columnas               | Distribución 2D block-cyclic                    |
| Kernel Cholesky propio                     | Algoritmos distribuidos maduros                 |
| Comunicación MPI implementada por nosotros | Infraestructura especializada para comunicación |
| Cálculo local propio                       | Kernels locales BLAS/LAPACK optimizados         |

ScaLAPACK también utiliza componentes específicos para álgebra lineal distribuida:

- PBLAS: versiones paralelas o distribuidas de operaciones BLAS.
- BLACS: infraestructura para organizar comunicaciones y grillas de procesos.

## ¿Habría sido necesario usar ScaLAPACK en este proyecto?

No necesariamente. El objetivo principal fue estudiar nuestra propia paralelización de Cholesky con MPI comparando el C secuencial propio contra el C propio con MPI. Esa comparación permite analizar directamente cuánto aportan el paralelismo, la distribución de datos, la comunicación, el número de procesos y el tamaño del problema.

LAPACK/OpenBLAS de un hilo se utilizó después como referencia para responder una pregunta distinta: cuánto margen de optimización local conserva nuestro kernel.

Usar ScaLAPACK habría respondido otra pregunta: cómo se compara nuestra implementación MPI educativa con una biblioteca profesional de álgebra lineal distribuida. Esa comparación sería interesante, pero introduciría simultáneamente varias diferencias adicionales:

- Distribución 2D.
- Cholesky bloqueado.
- BLAS optimizado.
- Comunicaciones especializadas.
- Distintos esquemas de balance de carga.
- Ajuste de tamaños de bloque y de la grilla de procesos.

Por lo tanto, incorporar ScaLAPACK habría ampliado considerablemente el alcance del proyecto.

## Conclusión

ScaLAPACK no fue necesario para validar el objetivo actual del trabajo. Puede considerarse una referencia distribuida futura si se desea estudiar no solo el margen del kernel local, sino también la estrategia de distribución y comunicación.

| **Herramienta** | **Forma simple de recordarla**                              |
|-----------------|-------------------------------------------------------------|
| LAPACK          | Factorizar una matriz local de forma muy eficiente.         |
| ScaLAPACK       | Factorizar una matriz distribuida entre múltiples procesos. |
| C propio        | Baseline secuencial del proyecto.                           |
| MPI propio      | Efecto de paralelizar nuestro diseño.                       |
| LAPACK/OpenBLAS | Referencia de optimización local.                           |
| ScaLAPACK       | Posible referencia distribuida futura.                      |

> **Nota editorial:** Este informe adapta el contenido del cuaderno Cronologia.ipynb a un formato de lectura continua. Se eliminaron marcas de Markdown, diagramas de caracteres y fragmentos ambiguos de formato, sin cambiar el sentido técnico de las explicaciones.
