# Bitácora experimental — Cholesky MPI en clúster

## Propósito de este documento

Este archivo registra, en orden cronológico, la etapa de experimentación en clúster del proyecto de HPC sobre factorización de Cholesky en C con MPI.

La intención es conservar no solo los resultados, sino también:

- la pregunta experimental de cada etapa;
- por qué se realiza cada prueba;
- las condiciones de ejecución;
- los comandos utilizados;
- los resultados obtenidos;
- la interpretación;
- la conclusión parcial;
- las limitaciones de cada medición;
- la siguiente pregunta que surge.

Este documento no reemplaza la documentación de la investigación local previa. La etapa local explica cómo se llegó al candidato actual; la etapa de clúster busca validar ese candidato en un nuevo entorno y generar evidencia de rendimiento propia de dicho entorno.

---

# 1. Objetivo de la etapa de clúster

Determinar experimentalmente, en el entorno de clúster disponible:

1. Cuándo la implementación MPI mejora frente a la referencia secuencial.
2. Cómo escala al aumentar la cantidad de procesos.
3. Cuánto cuestan por separado:
   - reserva de memoria;
   - generación de la matriz;
   - factorización;
   - reunión/reconstrucción del factor;
   - aplicación completa.
4. Qué limitaciones presenta el diseño MPI seleccionado.
5. Qué resultados de la etapa local se mantienen y cuáles dependen del nuevo entorno.

No se pretende repetir desde cero toda la investigación realizada previamente en la PC local.

---

# 2. Candidato seleccionado

La implementación que se toma como candidato principal para la campaña de clúster es:

- Cholesky right-looking.
- Matrices densas en `double`.
- Distribución 1D cíclica de columnas.
- Tamaño de bloque de propiedad `b=1`.
- Vector local auxiliar para acceso contiguo.
- Generación distribuida de la matriz SPD.
- Semilla fija `2026`.
- Cada proceso almacena solamente sus columnas locales.
- Al finalizar, el factor `L` completo se reúne en el rango 0.
- Validación mediante residuo proyectado.
- Para `N <= 128`, validación adicional mediante residuo exacto.
- Criterio de aceptación: residuo `<= 1e-12`.

La implementación principal se construye con:

- `main_candidate.c`
- `cholesky.c`
- `cholesky.h`
- `cholesky_mpi.c`
- `cholesky_mpi.h`

Existen además bancos experimentales anteriores (`compare_mpi.c`, `compare_mpi_local.c`, `compare_blocks.c`, `compare_mpi_algorithms.c`, entre otros). No forman parte de la campaña principal inicial del clúster. Se conservarán para eventuales verificaciones puntuales posteriores.

---

# 3. Entorno del clúster

Datos registrados:

- CPU física visible: AMD EPYC 7B12.
- El host informa 128 CPUs visibles.
- Este número no debe interpretarse como CPUs asignadas a la sesión.
- Límite cgroup de CPU:
  - `cpu.max = 600000 100000`
  - equivalente a 6 CPUs.
- Límite de memoria:
  - `25769803776` bytes;
  - aproximadamente 24 GiB.
- GCC 13.3.0.
- Open MPI 4.1.6.
- Python 3.13.11.
- Entorno de trabajo: VSCode web.
- Directorio actual del proyecto en el clúster:
  - `~/cholesky`

Consecuencia metodológica:

La campaña principal no utilizará más de 6 procesos MPI mientras esta sea la asignación efectiva disponible.

---

# 4. Separación entre etapa local y etapa de clúster

## Pregunta

¿Es necesario repetir en el clúster todas las pruebas que ya se realizaron en la PC?

## Decisión

No.

La etapa local ya documentó el recorrido de investigación que llevó al candidato actual. Repetir sistemáticamente todas las variantes en el clúster sería costoso y redundante.

En el clúster sí se debe:

1. comprobar que el candidato compile;
2. comprobar corrección numérica;
3. elegir tamaños mediante pilotos;
4. medir una nueva referencia secuencial en el mismo entorno;
5. medir MPI en ese mismo entorno;
6. calcular speedup y eficiencia usando exclusivamente datos del clúster;
7. repetir variantes históricas solo si existe una pregunta concreta que lo justifique.

Los tiempos obtenidos en la PC no se usarán como denominadores de speedup del clúster.

---

# 5. Identificación de las variantes MPI existentes

Al inspeccionar los fuentes se identificaron las siguientes piezas:

## `cholesky_mpi.c`

Contiene:

- `layout_create(...)`
  - distribución contigua;
  - distribución cíclica 1D.
- `layout_block_create(...)`
  - distribución cíclica por grupos de `b` columnas.
- `cholesky_mpi(...)`
  - kernel MPI original.
- `cholesky_mpi_local(...)`
  - variante con lectura interna contigua mediante vector local.

## `cholesky_left_mpi.c`

Contiene la alternativa left-looking MPI.

## Bancos de comparación

- `compare_mpi.c`
  - reparto contiguo vs cíclico.
- `compare_mpi_local.c`
  - kernel original vs kernel con vector local.
- `compare_mpi_algorithms.c`
  - left-looking MPI vs right-looking MPI.
- `compare_mpi_total.c`
  - comparación incluyendo entrada, cálculo y salida.
- `compare_generation.c`
  - generación centralizada vs distribuida.
- `compare_application.c`
  - flujo completo con generación distribuida.
- `compare_blocks.c`
  - comparación de valores de `b`.
- `compare_lapack.c`
  - referencia externa con LAPACK.

## `main_candidate.c`

Consolida el candidato principal:

- distribución cíclica 1D (`b=1`);
- generación distribuida;
- `cholesky_mpi_local`;
- `MPI_Gatherv`;
- reconstrucción completa de `L` en rango 0;
- validación numérica.

---

# 6. Congelación de los fuentes

## Pregunta

¿Los archivos subidos al clúster son exactamente los mismos que los presentes en la copia de referencia de Windows?

## Procedimiento

Se calculó SHA-256 primero en Windows y luego en el clúster.

## Resultado

Los cinco hashes coincidieron exactamente.

```text
main_candidate.c
C7CD7AEE15CD7C0B5315E2683EC0154D9C1DCE00B2A51BC9FAB0F9E7F1F82948

cholesky.c
82AEC76CF2D568445C87A347C2C5C076A13AE36173C7343A1DF33A05CDB2D169

cholesky.h
39E2A4912D186BB7EC5E235AC8BC01C74B67C32773E1DFFCEF8B21D18A8300CB

cholesky_mpi.c
7F3DDB4807CAADA4B8EFC9CC33B2446EF12BB858DA6B8EB65A6D1F086C62AB0D

cholesky_mpi.h
5F354D7D4AA977356D959D5D5B9225B57A34A986688C36EE413765C122738A92
```

## Conclusión

Quedó identificado un snapshot concreto del candidato que se utilizará como base de la campaña de clúster.

Mientras estos fuentes no se modifiquen, los resultados podrán asociarse inequívocamente a esta versión.

---

# 7. Compilación en el clúster

## Pregunta

¿El candidato compila correctamente en las dos rutas necesarias para la comparación principal?

Se necesitan:

1. una referencia secuencial;
2. el candidato MPI.

## Comandos

### Secuencial

```bash
gcc -O3 -std=c11 -Wall -Wextra -Wpedantic \
    main_candidate.c cholesky.c \
    -lm -o cholesky_candidate_seq
```

### MPI

```bash
mpicc -O3 -std=c11 -Wall -Wextra -Wpedantic -DUSE_MPI \
    main_candidate.c cholesky.c cholesky_mpi.c \
    -lm -o cholesky_candidate_mpi
```

Las salidas de compilación se conservaron en:

```text
build_candidate_seq.log
build_candidate_mpi.log
```

## Resultado

Ambos ejecutables fueron creados correctamente.

No aparecieron warnings ni errores visibles.

## Conclusión parcial

El snapshot seleccionado compila correctamente en el entorno actual con GCC 13.3.0 y Open MPI 4.1.6.

Todavía no se extrae ninguna conclusión de rendimiento.

---

# 8. Qué mide `main_candidate.c`

El reloj de aplicación comienza después de una barrera inicial MPI y termina después de la reconstrucción del factor completo.

## `allocation_s`

Incluye las reservas de memoria realizadas dentro del intervalo `t0` a `t1`.

## `generation_s`

En MPI, mide en el rango 0 el intervalo durante el cual cada proceso genera sus columnas mediante `generate_spd_columns`.

En secuencial, corresponde a `generate_spd`.

## `factor_s`

En MPI:

```c
cholesky_mpi_local(...)
```

En secuencial:

```c
cholesky_right_buffered(...)
```

## `gather_s`

En MPI incluye:

1. `MPI_Gatherv`;
2. la reconstrucción serial de la matriz completa `L` en rango 0.

Por lo tanto, no debe describirse como tiempo puro de `MPI_Gatherv`.

En secuencial no existe una reunión real; el campo queda prácticamente en cero porque se conserva el mismo formato de salida CSV.

## `application_s`

Intervalo completo:

```text
reserva + generación + factorización + reunión/reconstrucción
```

No incluye:

- `MPI_Init`;
- validación;
- `MPI_Finalize`;
- costo externo de `mpirun`.

## `max_local_s`

Cada proceso mide su propio `t4 - t0`.

Posteriormente se utiliza:

```c
MPI_Reduce(..., MPI_MAX, ...)
```

Por lo tanto, este campo representa el máximo tiempo local de aplicación entre procesos.

## `validation_s`

Se mide fuera del reloj de aplicación.

Incluye:

- regeneración de la matriz original;
- residuo proyectado;
- residuo exacto cuando `N <= 128`;
- comprobaciones de finitud;
- comprobación de diagonal positiva.

## Observación metodológica

Los tiempos individuales de fase (`generation_s`, `factor_s`, `gather_s`) corresponden al reloj del rango 0.

No existe un `MPI_MAX` independiente para cada fase.

Esto deberá tenerse en cuenta al interpretar perfiles por fase.

---

# 9. Validación secuencial en el clúster

## Pregunta experimental

¿La ruta secuencial produce una factorización numéricamente correcta en el nuevo entorno?

## Motivación

Antes de medir rendimiento es necesario demostrar que el ejecutable secuencial utilizado como referencia funciona correctamente.

## Condiciones

```text
N = 128
P = 1
semilla = 2026
```

## Comando

```bash
./cholesky_candidate_seq 128 \
    2> >(tee validacion_seq_n128.err >&2) \
    | tee validacion_seq_n128.csv
```

## Resultado

```text
N,P,allocation_s,generation_s,factor_s,gather_s,application_s,max_local_s,validation_s,projected_residual,exact_residual,valid
128,1,1.54599547386e-05,5.71911223233e-05,0.000195124186575,2.98023223877e-08,0.00026780506596,0.00026780506596,0.00145201710984,3.89642258138e-16,3.79030613921e-16,1
```

## Interpretación

- `valid = 1`.
- Residuo proyectado:
  - `3.89642258138e-16`.
- Residuo exacto:
  - `3.79030613921e-16`.
- Ambos están muy por debajo del criterio `1e-12`.

## Conclusión parcial

La ruta secuencial produce un resultado numéricamente correcto en el entorno de clúster.

Esta ejecución se clasifica como prueba de validación y no como medición formal de rendimiento.

---

# 10. Validación MPI en el clúster

## Pregunta experimental

¿El candidato MPI conserva la corrección numérica cuando se ejercita con la cantidad máxima de procesos actualmente disponible?

## Motivación

Esta prueba fuerza el uso de:

- distribución cíclica;
- generación distribuida;
- comunicación MPI;
- kernel `cholesky_mpi_local`;
- reunión;
- reconstrucción final.

Se elige `P=6` porque el cgroup disponible equivale actualmente a 6 CPUs.

## Condiciones

```text
N = 128
P = 6
semilla = 2026
```

## Comando

```bash
mpirun --bind-to core --map-by core -np 6 \
    ./cholesky_candidate_mpi 128 \
    2> >(tee validacion_mpi_n128_p6.err >&2) \
    | tee validacion_mpi_n128_p6.csv
```

## Resultado

```text
N,P,allocation_s,generation_s,factor_s,gather_s,application_s,max_local_s,validation_s,projected_residual,exact_residual,valid
128,6,1.06710940599e-05,1.09802931547e-05,0.000424367841333,0.000132551882416,0.000578571110964,0.000578571110964,0.00151919899508,3.89642258138e-16,3.79030613921e-16,1
```

## Interpretación

- `valid = 1`.
- Residuo proyectado:
  - `3.89642258138e-16`.
- Residuo exacto:
  - `3.79030613921e-16`.

Los residuos coinciden con los obtenidos por la ejecución secuencial para la misma entrada.

## Conclusión parcial

El candidato MPI funciona correctamente en el clúster con 6 procesos para `N=128`.

La prueba valida la portabilidad y la corrección del flujo distribuido completo.

No se utilizará esta ejecución aislada para concluir rendimiento o speedup.

---

# 11. Estado actual de la investigación en clúster

Hasta este punto se ha comprobado:

- snapshot de código identificado mediante SHA-256;
- compilación secuencial correcta;
- compilación MPI correcta;
- validación numérica secuencial correcta;
- validación numérica MPI con `P=6` correcta.

Por lo tanto, la pregunta de investigación puede pasar de:

> ¿El candidato funciona en este entorno?

a:

> ¿Qué tamaños de matriz son adecuados para construir una campaña de rendimiento significativa en este entorno?

---

# 12. Pilotos de tamaño

## Pregunta experimental

¿Qué tamaños `N` producen tiempos suficientemente largos como para que el ruido y el costo de medición no dominen, pero sigan siendo razonables para una campaña repetida?

## Motivación

La validación con `N=128` produjo tiempos del orden de cientos de microsegundos. Ese tamaño es útil para comprobar corrección, pero es demasiado pequeño para caracterizar con confianza el rendimiento del candidato.

Antes de fijar una campaña formal se decidió ejecutar un piloto exploratorio con tamaños mayores.

## Naturaleza de la prueba

Esta etapa es **exploratoria**.

Los resultados de una sola ejecución por configuración no se utilizarán para afirmar speedup, escalabilidad ni cantidad óptima de procesos.

## Condiciones

Se probaron:

```text
N = 512, 1024, 2048, 4096
```

Para cada tamaño:

- una ejecución secuencial;
- una ejecución MPI con `P=6`.

La salida y los errores se conservaron con `tee`.

## Comando utilizado

```bash
set -euo pipefail

for n in 512 1024 2048 4096; do
    echo "=== PILOTO SEQ N=$n ==="
    ./cholesky_candidate_seq "$n" \
        2> >(tee "piloto_seq_n${n}.err" >&2) \
        | tee "piloto_seq_n${n}.csv"

    echo "=== PILOTO MPI N=$n P=6 ==="
    mpirun --bind-to core --map-by core -np 6 \
        ./cholesky_candidate_mpi "$n" \
        2> >(tee "piloto_mpi_n${n}_p6.err" >&2) \
        | tee "piloto_mpi_n${n}_p6.csv"
done
```

## Resultados

| N | Secuencial `application_s` | MPI P=6 `application_s` | Cociente exploratorio SEQ/MPI | `valid` |
|---:|---:|---:|---:|---:|
| 512 | 0.0167575921 s | 0.00525140995 s | 3.19 | 1 |
| 1024 | 0.102381021 s | 0.0282395100 s | 3.63 | 1 |
| 2048 | 1.16226986 s | 0.188845360 s | 6.15 | 1 |
| 4096 | 10.3885298 s | 4.13568442 s | 2.51 | 1 |

Los residuos proyectados fueron:

```text
N=512   8.62942181151e-16
N=1024  1.21583547435e-15
N=2048  1.61090616269e-15
N=4096  2.27491802514e-15
```

Todos quedaron muy por debajo del criterio de aceptación `1e-12`.

Para `N>128`, `exact_residual=-1` por diseño: el candidato solo calcula el residuo exacto cuando `N<=128`.

## Interpretación

Los cuatro tamaños son factibles en el entorno actual.

Los tiempos cubren varios regímenes:

- `N=512`: decenas de milisegundos;
- `N=1024`: alrededor de una décima de segundo en secuencial;
- `N=2048`: alrededor de un segundo en secuencial;
- `N=4096`: alrededor de diez segundos en secuencial.

Esto permite seleccionar tamaños con distinta relación entre trabajo computacional y overhead MPI.

Los cocientes SEQ/MPI de esta tabla son únicamente exploratorios porque existe una sola observación por configuración.

## Observación operativa

Durante el final de este piloto se percibió una breve pérdida de fluidez en la PC/interfaz desde la que se controlaba el clúster.

No se atribuyó este hecho directamente a falta de memoria:

- una matriz `4096 x 4096` de `double` ocupa aproximadamente 128 MiB;
- considerando las matrices y buffers principales del flujo MPI, el orden de memoria agregado de estas estructuras sigue siendo muy inferior al límite de aproximadamente 24 GiB.

Se decidió no asignar una causa sin evidencia y realizar un control específico de `N=4096`.

## Conclusión parcial

Los tamaños `512`, `1024`, `2048` y `4096` son ejecutables y numéricamente correctos.

`N=4096` es suficientemente largo para estudiar estabilidad temporal, por lo que se eligió para una comprobación adicional.

---

# 13. Control de estabilidad para N=4096

## Pregunta experimental

¿El tiempo relativamente alto observado para `N=4096, P=6` es reproducible o fue una perturbación transitoria?

## Motivación

Al duplicar `N` de 2048 a 4096:

- la factorización secuencial pasó aproximadamente de 1.13 s a 9.96 s;
- la factorización MPI P=6 pasó aproximadamente de 0.16 s a 4.04 s.

El crecimiento de la versión MPI era suficientemente llamativo como para justificar repeticiones antes de interpretar la causa.

Además, durante el primer piloto se había percibido una breve pérdida de fluidez de la interfaz.

## Procedimiento

Se ejecutaron tres pares consecutivos:

1. secuencial `N=4096`;
2. MPI `N=4096, P=6`.

## Comando

```bash
set -euo pipefail

for rep in 1 2 3; do
    echo "=== CONTROL N=4096 SEQ REP=$rep ==="
    ./cholesky_candidate_seq 4096 \
        2> >(tee "control_seq_n4096_rep${rep}.err" >&2) \
        | tee "control_seq_n4096_rep${rep}.csv"

    echo "=== CONTROL N=4096 MPI P=6 REP=$rep ==="
    mpirun --bind-to core --map-by core -np 6 \
        ./cholesky_candidate_mpi 4096 \
        2> >(tee "control_mpi_n4096_p6_rep${rep}.err" >&2) \
        | tee "control_mpi_n4096_p6_rep${rep}.csv"
done
```

## Resultados

### Secuencial

| Repetición | `factor_s` | `application_s` | `valid` |
|---:|---:|---:|---:|
| 1 | 9.88814865 | 10.3182444 | 1 |
| 2 | 10.0443255 | 10.4790873 | 1 |
| 3 | 9.89752998 | 10.3273545 | 1 |

Mediana de `application_s`:

```text
10.3273545 s
```

Rango observado:

```text
10.3182444 s a 10.4790873 s
```

### MPI P=6

| Repetición | `factor_s` | `gather_s` | `application_s` | `valid` |
|---:|---:|---:|---:|---:|
| 1 | 4.04906316 | 0.0823587650 | 4.14647907 | 1 |
| 2 | 4.00634616 | 0.0820999602 | 4.10372839 | 1 |
| 3 | 4.02602471 | 0.0820378992 | 4.12332573 | 1 |

Mediana de `application_s`:

```text
4.12332573 s
```

Rango observado:

```text
4.10372839 s a 4.14647907 s
```

Cociente de medianas secuencial/MPI, todavía con carácter de control exploratorio:

```text
10.3273545 / 4.12332573 = 2.50
```

## Interpretación

Las tres repeticiones quedaron muy agrupadas y reproducen el orden de magnitud del piloto inicial.

El comportamiento de `N=4096, P=6` no parece haber sido una anomalía de una única ejecución.

La pérdida de fluidez percibida durante el primer piloto no se repitió durante este control, por lo que no se utilizará como explicación de los tiempos.

## Conclusión parcial

`N=4096` es un tamaño utilizable para mediciones de rendimiento en este entorno.

La ejecución MPI P=6 en ese tamaño mostró buena repetibilidad en esta sesión.

Esto no explica todavía por qué el crecimiento respecto de `N=2048` es mayor que el esperado a partir de la observación anterior; solo demuestra que el valor de `N=4096` es reproducible.

---

# 14. Escaneo exploratorio de procesos para N=512..4096

## Pregunta experimental

¿Cómo se comporta el candidato al variar `P` en los tamaños mayores ya seleccionados?

## Motivación

Antes de diseñar la campaña formal era necesario comprobar que:

- todas las cantidades de procesos funcionaran;
- no aparecieran errores de distribución o reunión;
- existieran zonas de interés para estudiar escalabilidad;
- no se eligiera una campaña formal a ciegas.

## Configuraciones

Para cada:

```text
N = 512, 1024, 2048, 4096
```

se ejecutó:

```text
SEQ
MPI P=1
MPI P=2
MPI P=3
MPI P=4
MPI P=6
```

Una sola vez por configuración.

## Comando

```bash
set -euo pipefail

for n in 512 1024 2048 4096; do
    echo "=== ESCANEO N=$n SEQ ==="
    ./cholesky_candidate_seq "$n" \
        2> >(tee "scan_seq_n${n}.err" >&2) \
        | tee "scan_seq_n${n}.csv"

    for p in 1 2 3 4 6; do
        echo "=== ESCANEO N=$n MPI P=$p ==="
        mpirun --bind-to core --map-by core -np "$p" \
            ./cholesky_candidate_mpi "$n" \
            2> >(tee "scan_mpi_n${n}_p${p}.err" >&2) \
            | tee "scan_mpi_n${n}_p${p}.csv"
    done
done
```

## Resultados: `application_s`

| N | SEQ | MPI P=1 | MPI P=2 | MPI P=3 | MPI P=4 | MPI P=6 |
|---:|---:|---:|---:|---:|---:|---:|
| 512 | 0.0167210 | 0.0183186 | 0.0104873 | 0.00574808 | 0.00503541 | 0.00525209 |
| 1024 | 0.103386 | 0.108026 | 0.0692106 | 0.0366968 | 0.0404128 | 0.0277996 |
| 2048 | 1.151211 | 1.114651 | 0.634390 | 0.413603 | 0.592001 | 0.192791 |
| 4096 | 10.390189 | 10.494172 | 5.607934 | 4.663816 | 5.232251 | 4.148838 |

## Cocientes exploratorios SEQ/MPI

| N | P=1 | P=2 | P=3 | P=4 | P=6 |
|---:|---:|---:|---:|---:|---:|
| 512 | 0.91 | 1.59 | 2.91 | 3.32 | 3.18 |
| 1024 | 0.96 | 1.49 | 2.82 | 2.56 | 3.72 |
| 2048 | 1.03 | 1.81 | 2.78 | 1.94 | 5.97 |
| 4096 | 0.99 | 1.85 | 2.23 | 1.99 | 2.50 |

Estos valores no constituyen speedups formales porque existe una única observación por configuración.

## Corrección numérica

Todas las configuraciones devolvieron:

```text
valid = 1
```

Los residuos proyectados fueron consistentes con los pilotos anteriores para cada `N`.

## Observaciones

### MPI P=1 no es idéntico al ejecutable secuencial

El camino secuencial utiliza:

```c
generate_spd(...)
cholesky_right_buffered(...)
```

Mientras que la compilación MPI, incluso con `P=1`, utiliza:

```c
generate_spd_columns(...)
cholesky_mpi_local(...)
MPI_Gatherv(...)
```

Por lo tanto, `MPI P=1` debe interpretarse como el costo del flujo MPI con un solo proceso, no como una réplica exacta del ejecutable secuencial.

### Comportamiento no monótono

En varias observaciones `P=4` fue más lento que `P=3`, mientras que `P=6` volvió a mejorar.

Ejemplo para `N=2048`:

```text
P=3 factor_s = 0.395026 s
P=4 factor_s = 0.559002 s
P=6 factor_s = 0.167786 s
```

Este patrón no se atribuyó a una causa específica.

Entre las posibles variables a estudiar se consideraron:

- afinidad;
- topología NUMA;
- caché y localidad;
- balance efectivo del trabajo;
- comportamiento de colectivas;
- frecuencia de CPU;
- interferencia de otros procesos;
- cuota del cgroup.

No existe evidencia suficiente en esta etapa para seleccionar una de ellas como explicación.

### Resultado llamativo en N=2048, P=6

El cociente exploratorio SEQ/MPI fue cercano a 6.

No se interpretó como evidencia definitiva de speedup superlineal.

Puede haber efectos de localidad/memoria o variabilidad; se requieren repeticiones formales antes de analizarlo.

## Conclusión parcial

El candidato funciona en todo el conjunto `P=1,2,3,4,6`.

El comportamiento no es estrictamente monótono con `P`, por lo que la campaña formal deberá conservar varias cantidades de procesos y múltiples repeticiones.

Antes de fijar el protocolo definitivo se decidió comprobar la afinidad y topología efectivamente utilizadas.

---

# 15. Diagnóstico de CPU, NUMA y afinidad

## Pregunta experimental

¿Qué CPUs puede utilizar realmente la sesión y dónde coloca Open MPI los procesos cuando usamos `--bind-to core --map-by core`?

## Motivación

El host muestra 128 CPUs, pero el cgroup tiene una cuota equivalente a 6 CPUs.

Además, el comportamiento no monótono de `P=3`, `P=4` y `P=6` hacía necesario descartar una explicación trivial basada en que los procesos cruzaran sockets o nodos NUMA.

## Comando

```bash
echo "=== CPU VISIBLE ==="
nproc
nproc --all

echo
echo "=== CGROUP CPU ==="
cat /sys/fs/cgroup/cpu.max
cat /sys/fs/cgroup/cpuset.cpus.effective

echo
echo "=== AFINIDAD DEL SHELL ==="
grep Cpus_allowed_list /proc/self/status

echo
echo "=== TOPOLOGIA ==="
lscpu | grep -E 'Model name|CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)|NUMA node\(s\)'

echo
echo "=== BINDING MPI P=6 ==="
mpirun --report-bindings --bind-to core --map-by core -np 6 /bin/true
```

## Resultado

### Visibilidad y límites

```text
nproc:       128
nproc --all: 128

cpu.max:
600000 100000

cpuset.cpus.effective:
0-127

Cpus_allowed_list:
0-127
```

Interpretación:

- la sesión puede ser afinada sobre cualquiera de las CPUs `0-127`;
- el cgroup no restringe el conjunto de CPUs a seis cores concretos;
- la cuota temporal agregada equivale a aproximadamente 6 CPUs sostenidas.

### Topología

```text
CPU: AMD EPYC 7B12 64-Core Processor
CPU(s): 128
Thread(s) per core: 1
Core(s) per socket: 64
Socket(s): 2
NUMA node(s): 2
NUMA node0 CPU(s): 0-63
NUMA node1 CPU(s): 64-127
```

No hay SMT visible: cada CPU lógica corresponde a un core.

### Binding de MPI con P=6

Open MPI informó:

```text
rank 0 -> socket 0, core 0
rank 1 -> socket 0, core 1
rank 2 -> socket 0, core 2
rank 3 -> socket 0, core 3
rank 4 -> socket 0, core 4
rank 5 -> socket 0, core 5
```

## Interpretación

Con `P=6`:

- cada proceso queda fijado a un core físico diferente;
- todos quedan en el mismo socket;
- todos quedan en el mismo nodo NUMA.

Por lo tanto, el comportamiento observado entre `P=3`, `P=4` y `P=6` no puede explicarse simplemente porque `P=4` o `P=6` crucen sockets o NUMA bajo este mapeo.

## Decisión metodológica adicional

Las ejecuciones secuenciales exploratorias anteriores no estaban fijadas a un core.

Aunque el programa secuencial es monohilo, el scheduler podría migrarlo entre cores.

Para la campaña formal se decidió fijar la referencia secuencial en:

```bash
taskset -c 0
```

De esta forma:

```text
SEQ      -> core 0
MPI P=1  -> core 0
MPI P=2  -> cores 0-1
MPI P=3  -> cores 0-2
MPI P=4  -> cores 0-3
MPI P=6  -> cores 0-5
```

Esto mejora el control experimental de la comparación.

---

# 16. Diagnóstico de throttling del cgroup

## Pregunta experimental

¿La cuota de CPU del cgroup produce throttling observable durante una ejecución intensiva con `P=6`?

## Motivación

`P=6` utiliza tantos procesos de cálculo como CPUs-equivalentes permite la cuota.

Otros procesos de la sesión, por ejemplo Jupyter o VSCode web, pueden compartir el mismo cgroup.

Era necesario registrar esta condición como una posible limitación del entorno.

## Procedimiento

Se registró `/sys/fs/cgroup/cpu.stat` antes y después de una ejecución:

```text
N=4096
P=6
```

## Comando

```bash
echo "=== CPU STAT ANTES ==="
cat /sys/fs/cgroup/cpu.stat

echo
echo "=== EJECUCION P=6 ==="
mpirun --bind-to core --map-by core -np 6 \
    ./cholesky_candidate_mpi 4096 \
    2> >(tee diagnostico_throttle_n4096_p6.err >&2) \
    | tee diagnostico_throttle_n4096_p6.csv

echo
echo "=== CPU STAT DESPUES ==="
cat /sys/fs/cgroup/cpu.stat
```

## Resultado de la ejecución

```text
N=4096
P=6
factor_s      = 4.02994578099
gather_s      = 0.0828188420273
application_s = 4.12777583022
valid         = 1
```

Este tiempo volvió a quedar dentro del rango observado en los controles anteriores.

## Contadores del cgroup

| Métrica | Antes | Después | Incremento |
|---|---:|---:|---:|
| `usage_usec` | 451418977 | 488679573 | +37260596 |
| `user_usec` | 381790732 | 418021187 | +36230455 |
| `system_usec` | 69628245 | 70658386 | +1030141 |
| `nr_periods` | 25929 | 25995 | +66 |
| `nr_throttled` | 126 | 154 | +28 |
| `throttled_usec` | 670979 | 790260 | +119281 |

## Interpretación

Durante la prueba hubo throttling:

```text
28 de los 66 nuevos períodos registraron throttling
```

El contador `throttled_usec` aumentó aproximadamente:

```text
119 ms
```

Esto confirma que la sesión puede tocar el límite de la cuota cuando se utilizan seis procesos intensivos.

Sin embargo, esta observación por sí sola no explica:

- la no monotonía entre `P=3`, `P=4` y `P=6`;
- el comportamiento particular de `N=2048`;
- ninguna diferencia concreta de rendimiento entre configuraciones.

## Conclusión parcial

El throttling del cgroup es una **limitación real del entorno** que debe quedar documentada.

`P=6` utiliza prácticamente toda la capacidad concedida y puede competir con procesos auxiliares de la sesión.

La campaña formal deberá mantener este contexto constante y no interpretar pequeñas diferencias sin considerar esta fuente potencial de variabilidad.

---

# 17. Escaneo de tamaños pequeños: N=128 y N=256

## Pregunta experimental

¿La región donde MPI empieza a reducir el tiempo de aplicación se encuentra entre `N=128` y `N=256`?

## Motivación

El escaneo anterior comenzaba en `N=512`, donde varias configuraciones MPI ya eran claramente más rápidas en la observación exploratoria.

Para estudiar el cruce era necesario incluir tamaños menores.

Además, a partir de esta etapa la referencia secuencial se fijó explícitamente al core 0.

## Configuraciones

```text
N = 128, 256
```

Para cada tamaño:

```text
SEQ
MPI P=1
MPI P=2
MPI P=3
MPI P=4
MPI P=6
```

## Comando

```bash
set -euo pipefail

for n in 128 256; do
    echo "=== ESCANEO PEQUEÑO N=$n SEQ ==="
    taskset -c 0 ./cholesky_candidate_seq "$n" \
        2> >(tee "scan_small_seq_n${n}.err" >&2) \
        | tee "scan_small_seq_n${n}.csv"

    for p in 1 2 3 4 6; do
        echo "=== ESCANEO PEQUEÑO N=$n MPI P=$p ==="
        mpirun --bind-to core --map-by core -np "$p" \
            ./cholesky_candidate_mpi "$n" \
            2> >(tee "scan_small_mpi_n${n}_p${p}.err" >&2) \
            | tee "scan_small_mpi_n${n}_p${p}.csv"
    done
done
```

## Resultados: `application_s`

| N | SEQ | MPI P=1 | MPI P=2 | MPI P=3 | MPI P=4 | MPI P=6 |
|---:|---:|---:|---:|---:|---:|---:|
| 128 | 0.000308808 | 0.000360290 | 0.000331318 | 0.000317769 | 0.000369310 | 0.000566394 |
| 256 | 0.002220256 | 0.002423532 | 0.001369835 | 0.001105699 | 0.001141559 | 0.001479857 |

## Cocientes exploratorios SEQ/MPI

| N | P=1 | P=2 | P=3 | P=4 | P=6 |
|---:|---:|---:|---:|---:|---:|
| 128 | 0.86 | 0.93 | 0.97 | 0.84 | 0.55 |
| 256 | 0.92 | 1.62 | 2.01 | 1.94 | 1.50 |

## Corrección

Para `N=128`:

```text
projected_residual = 3.89642258138e-16
exact_residual     = 3.79030613921e-16
```

Para `N=256`:

```text
projected_residual = 5.76448740546e-16
exact_residual     = -1
```

Todas las configuraciones dieron:

```text
valid = 1
```

## Interpretación

En la única observación de `N=128`, ninguna configuración MPI redujo `application_s` frente a la referencia secuencial.

En la única observación de `N=256`, `P=2`, `P=3`, `P=4` y `P=6` quedaron por debajo del secuencial.

Esto no permite fijar un umbral definitivo, pero localiza una región de interés:

```text
entre los tamaños ensayados N=128 y N=256
```

## Conclusión parcial

La campaña formal de cruce debe incluir tamaños intermedios entre 128 y 256.

Se seleccionaron:

```text
N = 128, 160, 192, 224, 256
```

El objetivo será determinar con repeticiones en qué configuraciones aparece una mejora reproducible y no solo una diferencia aislada.

---

# 18. Protocolo fijado para la campaña formal de cruce

## Estado

**Planificado, todavía no ejecutado al momento de esta actualización.**

## Pregunta principal

¿Para qué tamaños ensayados y cantidades de procesos el candidato MPI reduce de manera reproducible el tiempo de aplicación frente al ejecutable secuencial en este entorno?

## Tamaños

```text
N = 128, 160, 192, 224, 256
```

## Métodos

```text
SEQ
MPI P=1
MPI P=2
MPI P=3
MPI P=4
MPI P=6
```

## Afinidad

Referencia secuencial:

```bash
taskset -c 0
```

MPI:

```bash
mpirun --bind-to core --map-by core
```

Según el diagnóstico realizado, para `P<=6` los procesos quedan en cores consecutivos del socket 0 y dentro del mismo nodo NUMA.

## Repeticiones

Se decidió utilizar:

- una ronda de calentamiento;
- siete rondas útiles.

La ronda de calentamiento no se utilizará en los resultados finales.

## Orden

El orden de los métodos se rotará entre rondas para reducir el riesgo de asociar sistemáticamente un método con una posición temporal fija dentro de la campaña.

## Métrica principal

La comparación principal utilizará:

```text
application_s
```

Esta métrica incluye:

```text
reserva + generación + factorización + gather/reconstrucción
```

y excluye validación y arranque externo del runtime.

## Speedup

Para cada `N,P`:

```text
Speedup(N,P) =
mediana(application_s secuencial para N)
/
mediana(application_s MPI para N,P)
```

## Eficiencia

```text
Eficiencia(N,P) = Speedup(N,P) / P
```

## Criterio descriptivo de mejora clara

Antes de observar los datos formales se fijó como criterio conservador:

```text
Speedup > 1.10
```

y además:

```text
Q3(application_s MPI) < Q1(application_s secuencial)
```

Este criterio es descriptivo y no constituye una prueba formal de significación estadística.

## Uso de las fases

Se conservarán:

- `allocation_s`;
- `generation_s`;
- `factor_s`;
- `gather_s`;
- `application_s`;
- `max_local_s`;
- `validation_s`.

Las fases se utilizarán para interpretar el comportamiento del total.

No se sumarán medianas de fases para reconstruir la mediana de `application_s`; el total se analizará directamente a partir de la métrica medida por ejecución.

## Directorio previsto

```text
campana_cruce_20260928
```

## Script previsto

```bash
set -euo pipefail

OUT="campana_cruce_20260928"
mkdir -p "$OUT"

sizes=(128 160 192 224 256)
methods=(seq p1 p2 p3 p4 p6)

run_case() {
    n="$1"
    method="$2"
    rep="$3"

    if [[ "$method" == "seq" ]]; then
        echo "=== $rep N=$n SEQ ==="
        taskset -c 0 ./cholesky_candidate_seq "$n" \
            2> >(tee "$OUT/${rep}_n${n}_seq.err" >&2) \
            | tee "$OUT/${rep}_n${n}_seq.csv"
    else
        p="${method#p}"
        echo "=== $rep N=$n MPI P=$p ==="
        mpirun --bind-to core --map-by core -np "$p" \
            ./cholesky_candidate_mpi "$n" \
            2> >(tee "$OUT/${rep}_n${n}_p${p}.err" >&2) \
            | tee "$OUT/${rep}_n${n}_p${p}.csv"
    fi
}

echo "=== RONDA DE CALENTAMIENTO ==="
for n in "${sizes[@]}"; do
    for method in "${methods[@]}"; do
        run_case "$n" "$method" "warmup"
    done
done

echo "=== 7 RONDAS MEDIDAS ==="
for rep in 1 2 3 4 5 6 7; do
    start=$(( (rep - 1) % ${#methods[@]} ))

    for n in "${sizes[@]}"; do
        for j in 0 1 2 3 4 5; do
            idx=$(( (start + j) % ${#methods[@]} ))
            run_case "$n" "${methods[$idx]}" "rep${rep}"
        done
    done
done
```

## Qué no se hará todavía

Esta campaña no compara:

- left-looking vs right-looking;
- kernel original vs vector local;
- reparto contiguo vs cíclico;
- valores de `b`;
- generación centralizada vs distribuida;
- LAPACK.

Esas variantes pertenecen a una etapa posterior y solo se reabrirán si una pregunta concreta lo justifica.

---

# 19. Estado acumulado de la etapa de clúster

Hasta este punto se ha completado:

1. identificación del candidato;
2. congelación de fuentes mediante SHA-256;
3. compilación secuencial y MPI;
4. validación numérica secuencial;
5. validación numérica MPI;
6. pilotos de tamaño;
7. control de estabilidad para `N=4096`;
8. escaneo exploratorio con `P=1,2,3,4,6`;
9. diagnóstico de CPU, sockets, NUMA y afinidad;
10. diagnóstico de throttling del cgroup;
11. escaneo de la región `N=128..256`;
12. definición del protocolo formal para estudiar el cruce.

La siguiente acción experimental es ejecutar la campaña formal de cruce.

---

# 20. Limitaciones conocidas del entorno

## Cuota de CPU

El host expone 128 cores, pero el cgroup limita el consumo agregado a aproximadamente 6 CPUs.

Por lo tanto:

- `P=6` utiliza prácticamente toda la cuota;
- procesos auxiliares de la sesión pueden competir por esa capacidad;
- el throttling fue observado experimentalmente.

## CPU compartida / host visible

La visibilidad de 128 CPUs no implica que estén dedicadas a este trabajo.

La campaña debe describirse como ejecutada bajo la cuota efectiva registrada, no como una reserva exclusiva de seis cores físicos.

## Un solo socket para P<=6 bajo el mapeo actual

Open MPI ubicó los procesos `0..5` en cores `0..5` del socket 0.

Esto reduce la complejidad NUMA de la campaña actual, pero tampoco representa todavía una ejecución multi-nodo.

## Fases medidas desde rango 0

`generation_s`, `factor_s` y `gather_s` no son máximos reducidos por fase entre todos los procesos.

La interpretación por fases debe respetar esta limitación.

## `gather_s`

Incluye `MPI_Gatherv` y la reconstrucción serial de `L` completa en rango 0.

No debe interpretarse como tiempo puro de comunicación.

## Datos exploratorios vs formales

Los pilotos y escaneos de una sola observación se conservan para justificar decisiones experimentales.

No se mezclarán con la campaña formal para calcular medianas, speedup o eficiencia.

---

# 21. Plantilla para las siguientes pruebas

Cada experimento nuevo se documentará con esta estructura:

## Pregunta experimental

Qué queremos averiguar.

## Motivación

Por qué esta prueba es necesaria.

## Hipótesis o expectativa

Solo cuando exista una expectativa razonable previa. No se modificará después de observar los datos.

## Condiciones

- fecha/sesión;
- ejecutable;
- versión/snapshot;
- `N`;
- `P`;
- afinidad;
- límites de CPU/memoria relevantes;
- número de repeticiones.

## Comando

Comando exacto ejecutado.

## Resultados

Salida cruda relevante.

## Análisis

Descripción cuantitativa de los datos.

## Interpretación

Qué evidencia aportan.

## Qué no demuestra

Límites de la prueba.

## Conclusión parcial

Conclusión estrictamente respaldada por la evidencia disponible.

## Siguiente pregunta

Qué duda queda abierta.

## Siguiente acción

Próximo experimento o procedimiento.

---

# 22. Regla de trabajo

Las mediciones de:

- validación;
- diagnóstico;
- piloto;
- campaña formal;

se mantendrán etiquetadas por separado.

Cuando se incorporen resultados de una campaña formal, se conservarán también los datos crudos y las condiciones de ejecución que permitan reconstruir el análisis posteriormente.
