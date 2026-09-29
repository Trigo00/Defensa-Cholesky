# Metodología experimental

## Unidad de comparación

Cada grupo se identifica por máquina, campaña, subgrupo, N, método, P y reloj. Las repeticiones de una misma matriz caracterizan variación temporal. La semilla de la matriz es 2026; no se muestrean matrices independientes en cada repetición de rendimiento. Los pilotos, tests, preparaciones y perfiles instrumentados se separan de los grupos principales.

La referencia de un speedup pertenece al mismo tamaño, campaña y reloj. No se combinan denominadores WSL con resultados del clúster, ni datos del cruce con escalabilidad, ni LAPACK con una campaña MPI anterior para crear un cociente pretendidamente simultáneo.

## Estadísticos y fórmulas

- Mediana de los tiempos individuales; Q1 y Q3 mediante `statistics.quantiles(..., method='inclusive')`.
- IQR=Q3-Q1. Son estadísticos descriptivos, no intervalos de confianza.
- Speedup útil S=mediana(T_SEQ)/mediana(T_MPI,P).
- Eficiencia MPI E=S/P, o 100E en porcentaje. No es utilización de CPU.
- Escalado interno MPI: mediana(T_MPI,1)/mediana(T_MPI,P), diferente del anterior.
- Referencia de biblioteca: mediana(T_own)/mediana(T_LAPACK); no se informa como eficiencia MPI.
- Distancia final: mediana(T_MPI,P6)/mediana(T_LAPACK,1hilo).

No se calculan p-values ni se ajustan modelos para extrapolar un cruce. El criterio de mejora clara es descriptivo: S>1,10 y Q3_MPI<Q1_SEQ. El primer N ensayado que lo cumple no es un umbral exacto. En el estudio local del kernel se exigió en tres rondas de la misma sesión; en el cruce formal del clúster se aplica a siete observaciones por grupo.

Las figuras temporales muestran medianas y Q1-Q3 cuando procede. Las figuras de speedup muestran cocientes puntuales de medianas sin barras de incertidumbre inferencial. La composición de fases usa la media de las fracciones individuales; el total se resume directamente y nunca se sustituye por una suma de medianas.

## Fronteras temporales verificadas en el código

| Campo o banco | Inicio y fin | Exclusiones y cautelas |
|---|---|---|
| `allocation_s` del candidato | Desde t0 hasta completar reservas y mapas | Después de MPI_Init y barrera. malloc no obliga a tocar todas las páginas |
| `generation_s` | Generación de A o columnas locales | Primer acceso a páginas puede cobrarse aquí |
| `factor_s` candidato | Llamada a right_buffered o cholesky_mpi_local | MPI informa duración de rank 0 con comunicación/esperas; no máximo entre ranks |
| `gather_s` | Después del factor hasta completar Gatherv y reconstrucción | Incluye bucles seriales de rank 0; en SEQ solo el intervalo de reloj sin reunión |
| `application_s` | t4-t0 observado en rank 0 | Reserva + generación + factor + reunión; excluye validación, reducciones auxiliares y finalización |
| `max_local_s` | Máximo de t4-t0 entre procesos | No es suma de máximos de fases |
| `validation_s` | Regenerar referencia y comprobar resultado en rank 0 | Fuera de aplicación; dentro del comando externo |
| `external_s` | Antes de fork hasta terminar waitpid | Incluye comando, mpirun cuando corresponde, validación y cierre; no cola ni arranque del servicio; escritura del CSV externo excluida |
| `compare_lapack.factor_s` | Llamada al kernel propio o DPOTRF | Preparación del banco y validación fuera |
| `compare_lapack.total_s` | Reserva + generación + kernel | No es tiempo externo ni aplicación MPI con gather |
| Primeros bancos MPI | Máximo de duración del kernel por proceso tras barrera | Scatterv, Gatherv, reserva y validación fuera |
| `compare_mpi_total` | Entrada + factor + salida | Máximos de fases separados, no aditivos; reserva/generación fuera |
| `compare_generation` | Generar y disponer columnas locales | Sin factor; máximos de fases por separado |
| `compare_application`, `compare_blocks` | Reserva hasta L completo en rank 0 | Referencias, validación y cierre fuera; no equivalentes a primeros bancos |

No se denomina startup a `external_s-application_s`. `other_external_s` resta además `validation_s` por observación y todavía combina múltiples operaciones.

## Diseño de campañas principales

| Campaña | Tamaños | Métodos | Observaciones útiles | Preparación |
|---|---|---|---:|---|
| Local memoria 21/09 | 64,128,256,512,1000,1024 | left/right/vector | 216, doce por grupo | Una por variante, interna |
| Local MPI inicial 21/09 | 64,256,512,1024 | P1-4, dos repartos | 256 MPI +144 referencias | Interna; perfiles aparte |
| Local vector MPI 21/09 | 64,256,512,1024 | P1-4, cuatro variantes | 512 MPI +144 referencias | Interna; perfiles aparte |
| Local umbral 22/09 | 64,96,128,160,192,224,256 | P1-3, cuatro variantes, tres rondas | 2016 MPI +756 referencias | Interna |
| Local left/right MPI 22/09 | 64,128,256,512,1024 | P1-4, dos algoritmos | 320 | Interna |
| Local entrada/salida 22/09 | 64,128,256,512,1024 | P1-4, tres métodos | 720 | Interna |
| Local generación 22/09 | 512,1024,2048 | P1-6, central/distribuida | 216 | Interna; veinte filas de tests aparte |
| Local aplicación 22/09 | 512,1024,2048 | P1,3,6, tres métodos | 162 | Interna |
| Local propiedad 22/09 | 512,1024,2048 | P1,3,6; siete b | 441 +98 de repetición | Interna |
| Local preclúster 24/09 | Confirmación 1024,2048; piloto3072; LAPACK512-3072 | MPI b1/b4 y banco LAPACK | 76 entre confirmación, piloto y biblioteca | Separación por subcarpeta |
| Cierre local 24/09 y 27/09 | 256,512,1024,2048 | SEQ/P1,2,3,4,6 | 168 por sesión | 24 por sesión, rep=0 |
| Cruce formal clúster | 128,160,192,224,256 | SEQ/P1,2,3,4,6 | 210 | 30 exportadas |
| Escalabilidad clúster | 512,1024,2048,4096 | SEQ/P1,2,3,4,6 | 168 | 24 exportadas |
| LAPACK clúster | 2048,4096 | own/lapack | 24 | Cuatro internas no exportadas; control512 aparte |
| Final grande | 6144,8192 | own/lapack/P6 | 36 | Dos MPI exportadas y cuatro internas propias/LAPACK |

Los bancos locales balancean o alternan variantes según su script; no todos tienen el mismo diseño. La rotación del candidato local está en `cierre_local.sh`. Las campañas finales del clúster no archivaron todos los scripts de lanzamiento; se conserva esa limitación en lugar de reconstruir una cronología de ejecución no registrada.

## Corrección

El candidato exige `valid=1`, finitud, diagonal positiva y residuo proyectado <=1e-12. Para N<=128 exige también residuo completo <=1e-12. En tamaños mayores `exact_residual=-1` significa no calculado. `compare_lapack` comprueba además diferencia normalizada del factor <=1e-12, pruebas pequeñas, factor conocido y rechazo de matriz no SPD. No exporta `valid`; sus columnas numéricas y el test archivado se auditan sin inventar códigos de salida.

La matriz original se preserva o regenera fuera del reloj principal según el banco. El residuo proyectado usa ocho vectores de signos de semilla91827 y no equivale a un certificado. La validación cuesta tiempo y memoria incluso cuando está excluida del reloj de aplicación.

## Procedencia de las tablas

`observations.csv` conserva origen y fila. `summary_all.csv` contiene campaña, subgrupo, N, P, método, métrica, count, cuartiles y lista de archivos fuente. `document_table_trace.csv` relaciona tablas del documento con esos resúmenes. El número total de filas normalizadas incluye tests, controles y preparaciones: no debe anunciarse como número de benchmarks formales.
