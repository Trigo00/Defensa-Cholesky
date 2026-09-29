# Cholesky: construcción y evaluación por etapas

## Etapa 19: comparación final con matrices grandes

[Informe final MPI frente a LAPACK](../output/pdf/Cholesky_Etapa_19_Comparacion_final_grande.pdf).
N=6144 y 8192; seis observaciones útiles por método (C propio, MPI P6,
LAPACK/OpenBLAS un hilo). Se verificaron 43 hashes y las estadísticas coinciden
con el análisis adjunto. MPI acelera la factorización propia 1,67 y 1,95 veces,
pero tarda 8,58 y 6,25 veces lo que LAPACK. Hay acercamiento relativo entre esos
dos puntos, sin cruce observado ni extrapolación de un cruce futuro.

Métrica principal: `factor_s`; los relojes secundarios se mantienen separados.
Paquetes y análisis en `resultados/final_grande_cluster_20260928/`.
Reproducción: `python docs/generar_informe_final_grande_cluster.py`.
Recomendación vigente: cerrar experimentación y consolidar conclusión y defensa;
las propuestas de etapas anteriores conservan su contexto histórico.

## Etapas 17 y 18: escalabilidad y LAPACK en el clúster

- [Etapa 17: escalabilidad y dos relojes](../output/pdf/Cholesky_Etapa_17_Escalabilidad_cluster.pdf).
  168 observaciones útiles y 24 warmups, con tiempos internos/externos pareados;
  todos los estados de salida registrados son cero. Para P6: N=2048 da S interno
  5,83 y externo 1,43; N=4096 da 2,51 y 1,87. En N=512/1024 ningún MPI mejora
  la mediana externa frente a SEQ. Datos en `resultados/escalabilidad_cluster_20260928/`.
- [Etapa 18: referencia LAPACK](../output/pdf/Cholesky_Etapa_18_LAPACK_cluster.pdf).
  OpenBLAS 0.3.34 a un hilo, seis repeticiones alternadas por método en N=2048/4096.
  Cocientes propio/LAPACK del kernel: 13,05 y 16,70; del total interno: 9,87 y 10,21.
  Es LAPACK local, no ScaLAPACK. Datos en `resultados/lapack_cluster_20260928/`.

Ambos informes auditan los paquetes recibidos, documentan límites de procedencia,
incluyen gráficos y mantienen separados los bancos y sus relojes. Generador:
`python docs/generar_informes_escalabilidad_lapack_cluster.py`. Con estas campañas
se recomienda consolidar la conclusión universitaria; una confirmación selectiva
es opcional. Las secciones siguientes conservan el estado de etapas anteriores.

## Etapa 16: cruce formal en el clúster

[Informe de la campaña formal](../output/pdf/Cholesky_Etapa_16_Cruce_cluster.pdf):
210 observaciones útiles y 30 warmups; 493 entradas del manifiesto verificadas.
Con S>1,10 y Q3_MPI<Q1_SEQ, primer N ensayado con mejora clara:
P2=256, P3=192, P4=224, P6=256; P1 no cumple en la grilla.
Se conservan originales y análisis en `resultados/cruce_cluster_20260928/`.
Los nombres repetidos se normalizaron sin modificar los archivos recibidos;
su estructura coincide con las rondas y el orden previstos. No hubo incremento
de throttling entre las lecturas archivadas. El siguiente bloque es escalabilidad
mayor con dos relojes; el cruce formal ya está completado en esta sesión.
Reproducción: `python docs/generar_informe_cruce_cluster.py`.

## Etapa 15: exploración en el clúster (28/09/2026)

Informe nuevo: [Cholesky_Etapa_15_Exploracion_cluster.pdf](../output/pdf/Cholesky_Etapa_15_Exploracion_cluster.pdf).
Continúa el documento unificado de las etapas 1-14, que conserva el cierre local.
La bitácora recibida describe 53 ejecuciones; la campaña formal de cruce figura
pendiente. Los datos reconstruidos, la bitácora íntegra, las cinco fuentes con
hashes coincidentes, cuatro gráficos y la versión Markdown están en
`resultados/cluster_exploratorio_20260928/`.

Control N=4096, tres repeticiones por método: mediana secuencial 10,327 s,
MPI P=6 4,123 s, cociente 2,505 y eficiencia descriptiva 41,74 %. Es evidencia
exploratoria dentro de una sesión, con SEQ sin afinidad explícita; no es una
campaña formal ni una medición del comando externo. La edición revisada incorpora
53 CSV originales, 53 archivos de error, dos logs de compilación y cinco fuentes
del paquete del clúster; se verificaron sus 113 hashes. Las estadísticas y gráficos
se recalculan desde los originales, manteniendo separados los conjuntos.

Reproducir documentación: `python docs/generar_informe_cluster_exploratorio.py`
(matplotlib, reportlab y pypdf). Próximos pasos: completar
el cruce, repetir escalabilidad mayor con afinidad controlada, medir tiempo externo
y confirmar los casos decisivos en otra sesión. El PDF detalla preguntas y límites.

**Documento principal:** `../output/pdf/Cholesky_Investigacion_Completa.pdf`.
Sus primeras ocho páginas explican el recorrido y las decisiones actuales;
después reúne íntegros los catorce informes de esta investigación.

La etapa 14 repite la campaña el 27/09 sin cambiar las fuentes. Resultados en
`resultados/cierre_local_20260927/`, comparados por sesión con los del 24/09.
N=2048/P=6: speedup hasta L 1,95 y externo 1,16; todos los lanzamientos válidos.
Referencia Git local: `candidato-local-v1`; no representa una conclusión del clúster.

## Cierre local vigente: etapas 11-13

`make candidate` construye `build/cholesky_candidate_mpi`, la referencia autónoma
`build/cholesky_candidate_seq` y `build/measure_command`. La entrada es
`src/main_candidate.c`; el algoritmo MPI seleccionado no cambió.
`scripts/cierre_local.sh` y `scripts/analizar_cierre.py` ejecutan y analizan la campaña.
Resultados: `resultados/cierre_local_20260924/`. Se completaron programa, speedup,
eficiencia y tiempo externo. Las secciones posteriores conservan el historial;
las referencias antiguas a trabajo pendiente describen su etapa.

Este directorio inicia un trabajo nuevo. Los archivos anteriores quedan como antecedentes; sus cifras no se usan como evidencia de esta implementación.

El algoritmo, la generación de matrices, las optimizaciones y MPI se implementarán en C. Python se utilizará para estadísticas, gráficos y preparación de documentos.

## Forma de trabajo

Cada etapa documenta: pregunta → hipótesis → implementación → experimento → resultados → interpretación y límites → próxima pregunta. Se distinguen resultados medidos, deducciones teóricas y propuestas pendientes.

1. Cholesky, left-looking y right-looking, elección de variante y generación de matrices.
2. Comparación secuencial left-looking y right-looking en C (implementada, probada y medida).
3. Acceso a memoria: right-looking con columna copiada a un vector contiguo (implementado, probado y medido).
4. Primer reparto MPI: contiguo y cíclico, comunicación y validación (implementado y medido localmente).
5. Vector local para MPI: comparación de cuatro variantes (implementado y medido).
6. Precisar cuándo compensa MPI (tres rondas locales completadas).
7. Comparar directamente left-looking MPI y right-looking MPI (implementado y medido).
8. Medir entrada, factorización, reunión y total (implementado y medido).
9. Repetir dentro de un nodo y entre nodos del clúster queda pendiente.

Las etapas posteriores son un plan revisable. El alcance principal termina cuando podamos explicar con evidencia el comportamiento de MPI 1D; 2D y tareas son posibles extensiones.

## Documento vigente

**Etapa vigente: 10 (24/09/2026)**:
`../output/pdf/Cholesky_Etapa_10_Preparacion_cluster.pdf`.
Campaña `resultados/precluster_20260924`, 76 observaciones nuevas válidas.
La confirmación en nueva sesión no mantuvo la ventaja de b=4: para n=1024, P=6,
b=1 42,339 ms y b=4 43,359 ms; para n=2048, 767,989 y 798,865 ms.
Se conserva b=1 como referencia principal. n=3072 también se ejecutó (dos
repeticiones por variante: exploratorio, no conclusión estadística).

Referencia C independiente de MPI: LAPACKE + OpenBLAS 0.3.32, un hilo comprobado
y afinidad CPU0. Para n=2048, C propio factor 1484,349 ms / total 1527,235 ms;
LAPACK factor 116,300 ms / total 156,854 ms. El total incluye reserva y generación;
validación y liberación fuera. Es comparación de implementaciones, no speedup MPI.
Se usa interpretación column-major U del mismo arreglo simétrico para obtener L
row-major, sin conversión; caso conocido valida el almacenamiento.

Comandos: `make lapack test-lapack`, `bash scripts/precluster_local.sh`;
`python scripts/analizar_precluster.py resultados/<campaña>`.
Scripts operativos: `scripts/campana_cluster.sh` y `scripts/analizar_pares_cluster.py`.
Instrucciones y límites: `docs/GUIA_CLUSTER.md`. Preparación local completada;
ejecución entre nodos pendiente de acceso y asignación del administrador.
No se requieren bloques algorítmicos, almacenamiento triangular ni MPI+OpenMP
antes del clúster. Las etapas siguientes del README son historia de decisiones.

La etapa 9 estudia **distribución bloque-cíclica**, distinta del algoritmo Cholesky
por bloques. `layout_block_create` permite b=1,2,4,8,16,32,64 con el mismo kernel
right-looking. Generación y reunión usan el nuevo mapa; b=1 conserva la propiedad
cíclica. Todos los tamaños usan la misma ruta general de índices en la campaña.
No deben atribuirse diferencias frente a campañas históricas exclusivamente al reparto.

Reproducción: `make blocks test-blocks`; `bash scripts/comparar_bloques.sh`;
`python scripts/analizar_bloques.py resultados/<campaña>`.
La campaña `resultados/bloques_local_20260922` comprende n=512,1024,2048,
P=1,3,6 y siete repeticiones por bloque (441 observaciones). El protocolo rota
el orden de bloques y P. `docs/generar_informe_bloques.py` usa esa campaña.
El total rank0 incluye reserva/mapas, generación, kernel y reunión; validación y
lanzamiento MPI quedan fuera. El factor se compara con la referencia secuencial.
El conteo de trabajo `sum(k*(n-k))` describe actualizaciones acumuladas por proceso,
no tiempos ni balance en cada etapa. Los mínimos elegidos a posteriori requieren
confirmación antes de adoptar un bloque distinto de 1.

Informe: `../output/pdf/Cholesky_Etapa_9_Distribucion_bloque_ciclica.pdf`.
Se completó una repetición de 98 observaciones para n=1024,2048 con P=6.
Candidato b=4: en n=1024, 48,930 ms (b=1) contra 44,016 ms (b=4), alrededor
de 10 % menos; en n=2048, 931,669 contra 929,698 ms, apenas 0,2 % menos.
La ventaja de n=1024 persiste en dos lanzamientos de la misma sesión, mientras
que n=2048 no sostiene una mejora práctica. Mantener b=1 como referencia,
b=4 como candidato localizado; no hay tamaño universal demostrado.
Corrección, regresión y ASan/UBSan pasaron; `pruebas.md` detalla los límites.

**Etapa vigente: 8**, `../output/pdf/Cholesky_Etapa_8_Flujo_con_generacion.pdf`.
Campaña `resultados/aplicacion_local_20260922`: 162 observaciones, n=512,1024,2048,
P=1,3,6. Centralizada y distribuida producen L completa en rango 0; secuencial
contemporáneo genera y factoriza en rango 0. El reloj principal incluye reserva,
generación, distribución, factorización y recolección; excluye inicio/cierre MPI,
validación, referencias y liberación. No es el tiempo externo del comando.
Las fases consecutivas del rango 0 suman el total por ejecución e incluyen esperas.
La mediana total se calcula directamente; las proporciones se calculan por ejecución.

En n=2048, P=6: centralizada 874,604 ms, distribuida 837,392 ms (reducción 4,25 %),
secuencial 1617,307 ms. La factorización ocupa una mediana del 91,14 % del flujo
distribuido. Una campaña no prueba que la pequeña mejora total sea estable.
Próximo foco: factorización/reparto; confirmar resultados en otras sesiones.
Pruebas pequeñas P=1,3,6 y sanitizadores P=3 pasaron. Se valida contra factor
secuencial y mediante ocho proyecciones; residuo completo en n<=128.

Reproducir: `make application test-application`, `bash scripts/comparar_aplicacion.sh`,
`python scripts/analizar_aplicacion.py resultados/<campaña>`.
El constructor `docs/generar_informe_aplicacion.py` usa la campaña fijada arriba.

La continuación posterior a la consulta docente es `../output/pdf/Cholesky_Etapa_7_Generacion_distribuida.pdf`.
La campaña `resultados/generacion_local_20260922` compara generar y repartir desde rango 0
contra generar directamente columnas cíclicas idénticas bit a bit (216 observaciones).
Con n=2048, P=6: 51,862 ms centralizado y 8,385 ms distribuido. Con P=1,
la generación directa fue más lenta para los tres tamaños. Estos son tiempos de preparación,
NO de aplicación completa. Reserva, factorización, validación e inicio MPI están excluidos.

Se agregó `projected_residual`: comprobación reproducible con vectores de signos,
O(k*n*n), complementaria al residuo completo. Puede dejar errores sin detectar y no
es un certificado ni un residuo Frobenius. Las pruebas de corrección y ASan/UBSan pasaron.
Los bancos históricos conservan su validación original. Próximo paso: integrar generación,
reserva, distribución, factorización y salida en un nuevo banco con métricas explícitas.

Reproducción: `make generation test`; `bash scripts/comparar_generacion.sh`;
`python scripts/analizar_generacion.py resultados/<campaña>`.
El informe usa la campaña fijada arriba; cambiarla requiere revisar el texto.

Pendientes locales: flujo completo; tamaños mayores y 1-6 procesos; bloque-cíclica;
almacenamiento triangular; vectorización; referencia LAPACK. Bloques y MPI+OpenMP
se decidirán según evidencia y alcance defendible. Las siguientes secciones conservan
la historia; sus referencias al siguiente paso corresponden a cada etapa.

El capítulo más reciente es `../output/pdf/Cholesky_Etapa_6_Tiempo_total_MPI.pdf`: mide el flujo completo con entrada y salida centralizadas. Los capítulos previos conservan el desarrollo de la decisión algorítmica.

El capítulo más reciente es `../output/pdf/Cholesky_Etapa_5_Left_vs_Right_MPI.pdf`: explica dónde se paraliza cada variante y presenta una comparación directa con la misma matriz y distribución. Los capítulos anteriores conservan la evolución de las decisiones.

El capítulo más reciente es `../output/pdf/Cholesky_Etapa_4_Cuando_conviene_MPI.pdf`: tamaños intermedios, tres rondas y criterio de conveniencia fijado antes de medir. Los capítulos previos conservan la historia de los experimentos.

La etapa más reciente está en `../output/pdf/Cholesky_Etapa_3_MPI_vector_local.pdf`: copia local, comparación controlada de cuatro variantes y revisión de la elección del reparto. Los PDF anteriores se conservan como etapas históricas del razonamiento.

La continuación está en `../output/pdf/Cholesky_Etapa_2_MPI_y_distribuciones.pdf`: implementación MPI, mediciones con P=1,2,3,4, aceleración útil, perfiles por rango y límites de la comparación. El PDF de etapa 1 conserva el razonamiento previo al experimento MPI; sus referencias a pruebas pendientes corresponden a ese momento del trabajo.

El capítulo inicial se entrega en `../output/pdf/Cholesky_Etapa_1_Fundamentos_y_diseno.pdf`. Sustituye al PDF anterior de fundamentos y validación. Explica el algoritmo y las decisiones antes de avanzar a implementación y mediciones.

El PDF reemplaza la primera medición aislada por una comparación controlada de ambas variantes. Explica la candidatura de right-looking para MPI, el criterio de costo/beneficio para elegir P y las distribuciones contigua, cíclica, bloque-cíclica y dinámica. Round-robin por columnas equivale a cíclica estática. Los conteos de trabajo del ejemplo de distribución no son tiempos medidos.

En la primera campaña, left-looking obtuvo menor mediana desde N=128; para N=1024 right original tardó 8,06 veces más. Este resultado se conserva como antecedente del siguiente experimento.

En la segunda campaña, right con vector contiguo obtuvo menor mediana en los seis tamaños probados. Para N=1024: left 144,79 ms, right original 1159,09 ms y right con vector 76,92 ms. La última variante es 15,07 veces más rápida que right original y 1,88 veces más rápida que left en esa campaña local. Copiar la columna forma parte del tiempo medido; reservar el vector no. No se ha aislado cuánto de la mejora corresponde a caché o a decisiones del compilador.

Right con vector es la referencia secuencial para MPI. Ya ejecutamos una primera campaña local con n=64,256,512,1024 y P=1,2,3,4. Para n=1024: referencia secuencial 82,65 ms; MPI contiguo P=3, 40,03 ms (2,06x útil); MPI cíclico P=3, 51,67 ms (1,60x útil). Son medianas de esta campaña, no comparaciones con tiempos de campañas anteriores.

En esa primera implementación, el cíclico equilibró mejor las operaciones, pero fue más lento. También hubo diferencias con P=1, donde la propiedad coincide: el costo local de indexación y acceso impidió atribuir todo al reparto de carga. Esa observación motivó el experimento del vector local, completado abajo. No hay mediciones entre nodos ni un umbral universal de conveniencia.

## Experimento 4: vector local en MPI

La función `cholesky_mpi_local` conserva los propietarios, las difusiones y la aritmética. Copia una vez por etapa los valores de las columnas futuras propias a un vector ordenado localmente. El bucle interno usa `local_column[c]` en vez de `column[layout_global(d,c)]`. La reserva está fuera del cronómetro y la copia dentro. El kernel original sigue disponible.

Campaña `resultados/mpi_local_20260921`: n=64,256,512,1024; P=1,2,3,4; contiguo/cíclico por original/local. Ocho repeticiones por configuración (512 tiempos MPI); orden equilibrado de cuatro variantes; 144 referencias secuenciales contemporáneas y 48 registros de perfil aparte. Las cifras son de esta nueva campaña.

Para n=1024 y P=3: cíclico original 72,04 ms; cíclico con vector 32,77 ms; contiguo con vector 39,66 ms. El mejor secuencial fue 88,62 ms: aceleración útil de 2,70x para el cíclico con vector. Con P=1 la gran diferencia entre repartos se redujo. El cíclico con vector queda como candidato principal para continuar; el contiguo original permanece como referencia. Varias distribuciones de tiempos se superponen y no se declara una superioridad universal. En n=64, todos los casos MPI con P>1 pierden frente al secuencial.

Desde `desde_cero`:

```bash
make mpi-local test-mpi-local
mpirun --bind-to core --map-by core -np 3 ./build/compare_mpi_local 1024 8
bash scripts/comparar_mpi_local.sh
python3 scripts/analizar_mpi_local.py resultados/<carpeta_generada>
python3 docs/generar_informe_mpi_local.py
```

El banco exige repeticiones múltiplo de cuatro. `--test` ejecuta casos de corrección; `profile` como tercer argumento numérico activa cronómetros internos en una ejecución aparte. El PDF carga explícitamente la campaña registrada: para otra campaña hay que actualizar su ruta DATA y revisar las conclusiones. `pruebas.md` detalla los sanitizadores; `fuentes/` conserva una copia del código medido.

El cruce se estudió después con tamaños intermedios y tres rondas de lanzamientos separados, en la misma sesión. No se consideran campañas independientes en distintos días; se describe a continuación.

## Experimento 5: cuándo empieza a compensar MPI

Campaña `resultados/umbral_20260922`: n=64,96,128,160,192,224,256 y P=1,2,3; tres rondas con orden de tamaños y procesos rotado. Se reutilizó el banco de cuatro variantes sin cambiar los kernels C. El análisis principal se fijó de antemano en cíclico con vector, P=2 y P=3; los demás resultados quedan como controles.

Regla previa: aceleración frente al mejor secuencial mayor que 1,10 **y** Q3 de MPI menor que Q1 del secuencial en las tres rondas. Es una regla descriptiva conservadora, no una prueba de significación estadística. Se validaron 2016 tiempos MPI y 756 secuenciales, sin fallos numéricos.

Hasta n=192 MPI fue más lento en las tres rondas; en n=224 hubo una mejora pequeña con P=3 solo en una ronda. n=256, P=3 fue el primer punto probado que cumplió el criterio 3/3: aceleraciones 1,49; 1,12; 1,27. P=2 en n=256 ganó por mediana las tres veces, pero cumplió la regla completa solo 2/3 por superposición de cuartiles. No se infiere una regla universal para todo n>=256 ni se incorpora selección automática.

```bash
bash scripts/medir_umbral.sh
python3 scripts/analizar_umbral.py resultados/<carpeta_generada>
python3 docs/generar_informe_umbral.py
```

El PDF usa explícitamente `resultados/umbral_20260922`; otra campaña requiere actualizar la ruta y revisar el texto. `protocolo.txt` registra las condiciones previas y `fuentes/` conserva el código medido. Las tres rondas ocurrieron en la misma sesión WSL. El nombre de la carpeta se corrigió al día local del experimento, 22/09/2026.

Siguiente experimento propuesto: medir distribución inicial, factorización y reunión por separado y en conjunto. El umbral del kernel no equivale al de una aplicación completa. La evaluación entre nodos y las repeticiones en otros días siguen pendientes.

## Experimento 6: left-looking MPI frente a right-looking MPI

Se implementó `cholesky_left_mpi` para responder experimentalmente cuál variante conviene paralelizar. Cada proceso forma sumas parciales con sus columnas anteriores; MPI_Reduce las entrega al propietario de la columna actual y MPI_Bcast difunde el pivote. Right-looking usa el kernel cíclico con vector local del experimento 4. Ambos comparten matriz, distribución, almacenamiento local, compilador, afinidad y validación.

Campaña `resultados/left_right_mpi_20260922`: n=64,128,256,512,1024; P=1,2,3,4; ocho repeticiones alternadas por algoritmo. Se aceptaron 320 tiempos. Right tuvo menor mediana en las 20 configuraciones. Para n=1024 y P=3: left 54,08 ms; right 31,48 ms. Respecto de P=1, ambos escalaron aproximadamente 2,8x, pero right conservó el menor tiempo absoluto. Ambos empeoraron al pasar de tres a cuatro procesos.

La interpretación es concreta: left reúne contribuciones anteriores mediante más colectivas; right difunde la columna terminada y actualiza datos locales. En esta versión, left ejecuta hasta 3n-1 colectivas frente a n difusiones en right. El perfil muestra entre 10,80 y 14,29 ms dentro de MPI_Reduce para left en n=1024, P=3. El tiempo colectivo incluye espera.

Por tanto, continuamos con right-looking MPI cíclico y vector local. No se afirma una superioridad universal: left por bloques, con BLAS, menos reducciones o comunicación no bloqueante puede comportarse de otra forma.

```bash
make mpi-algorithms test-mpi-algorithms
bash scripts/comparar_left_right_mpi.sh
python3 scripts/analizar_left_right_mpi.py resultados/<carpeta_generada>
python3 docs/generar_informe_left_right_mpi.py
```

El PDF y el análisis cargan explícitamente `resultados/left_right_mpi_20260922`. `pruebas.md`, `protocolo.txt`, los CSV, el perfil, las huellas y la copia de las fuentes documentan la campaña. El siguiente paso continúa siendo medir el tiempo completo de distribución, factorización y reunión.

## Experimento 7: tiempo completo

La campaña `resultados/tiempo_total_20260922` parte de A completa en el rango 0 y termina con L completa allí. En MPI se miden empaquetado más Scatterv, factorización y Gatherv más desempaquetado; también se mide directamente el total. La referencia secuencial incluye copiar A y factorizarla con right más vector. Reservas, generación, validación y arranque de MPI quedan fuera.

Se compararon right MPI, left MPI y right secuencial para n=64,128,256,512,1024 y P=1,2,3,4, con 12 repeticiones por algoritmo y configuración. Las seis permutaciones del orden se repiten dos veces. Se aceptaron 720 observaciones.

Al incluir movimientos, el cruce práctico se desplaza. Para right P=3: n=256 mejora 1,08x, n=512 mejora 1,60x y n=1024 mejora 1,90x frente al secuencial contemporáneo. Dentro de esta grilla, 512 es el primer tamaño con mejora total clara; no se presenta como umbral universal. Con n=1024, P=3: entrada 5,323 ms, kernel 38,848 ms, salida 5,630 ms y total 49,699 ms. El total secuencial fue 94,523 ms.

Right conserva la ventaja sobre left en el flujo completo. Para n=1024, P=3, left tarda 70,678 ms y right 49,699 ms. La entrada y salida no bajan al aumentar P porque el rango 0 empaqueta y desempaqueta secuencialmente; es un límite del diseño actual.

```bash
make mpi-total test-mpi-total
bash scripts/comparar_tiempo_total.sh
python3 scripts/analizar_tiempo_total.py resultados/<carpeta_generada>
python3 docs/generar_informe_tiempo_total.py
```

El informe usa explícitamente `resultados/tiempo_total_20260922`. Los CSV, `protocolo.txt`, `pruebas.md`, las huellas y `fuentes/` conservan la trazabilidad. El siguiente paso requiere acceso al clúster: repetir dentro de un nodo y entre nodos. Si la comunicación domina, entonces tendrá sentido estudiar una versión por bloques y BLAS.

## Primera implementación MPI

El propietario de j calcula y difunde su columna. Cada proceso actualiza sus columnas propias, guardadas por filas sin huecos para columnas ajenas. Todos participan en las colectivas aunque no tengan columnas. El proceso 0 conserva la entrada completa y reúne el resultado para validarlo fuera del cronómetro.

Desde `desde_cero`, con Open MPI instalado en Linux/WSL:

```bash
make mpi test-mpi
mpirun --bind-to core --map-by core -np 3 ./build/compare_mpi 1024 8
bash scripts/comparar_mpi.sh
python3 scripts/analizar_mpi.py resultados/<carpeta_mpi_generada>
python3 docs/generar_informe_mpi.py
```

- `src/cholesky_mpi.c` y `.h`: reparto y kernel distribuido en C.
- `src/compare_mpi.c`: pruebas, validación, cronómetro y perfil opcional (`profile` como tercer argumento).
- `resultados/mpi_20260921`: 256 tiempos MPI, 144 referencias secuenciales y 60 registros de perfil por rango; protocolo y huellas de fuentes.
- `resultados/mpi_20260921/pruebas.md`: pruebas ejecutadas y configuración de sanitizadores.

Tiempo principal: máximo de las duraciones locales del kernel, después de una barrera, sin instrumentación interna. Excluye inicio de MPI, generación, distribución inicial, reunión y validación. El perfil se ejecuta por separado, con 3 repeticiones; el tiempo dentro de Bcast incluye esperas. Las barras de los gráficos son Q1-Q3, no intervalos de confianza.

La campaña alterna los dos repartos en 8 repeticiones, rota P entre tamaños y mide las tres referencias secuenciales antes y después de MPI. Cada proceso está ligado a un núcleo distinto según WSL. El guion está pensado para una sola máquina; el lanzamiento y afinidad entre nodos deberán adaptarse al planificador del clúster. El generador del PDF usa explícitamente `resultados/mpi_20260921`; para otra campaña hay que actualizar la ruta y revisar las conclusiones.

## Archivos y ejecución en Linux / WSL

- `src/cholesky.c`: generador SPD, ambas factorizaciones y residuo.
- `src/cholesky.h`: contrato de las funciones y almacenamiento.
- `src/compare_seq.c`: comparación alternada de left y right, con CSV por repetición.
- `src/compare_memory.c`: comparación de left, right original y right con vector; orden equilibrado entre las tres variantes.
- `tests/test_variants.c`: valida ambas variantes y compara sus factores.
- `tests/test_buffered.c`: valida la nueva variante, su espacio de trabajo y su equivalencia numérica con right original.
- `scripts/comparar_variantes.sh`: campaña fijada a una CPU, con entorno y huellas del código.
- `scripts/analizar_variantes.py`: estadísticas, gráfico medido y diagrama de distribuciones.
- `scripts/comparar_memoria.sh`: campaña de las tres variantes con 12 repeticiones por tamaño.
- `scripts/analizar_memoria.py`: comprueba el protocolo y genera estadísticas y gráfico de esa campaña.
- `docs/generar_informe_decisiones.py`: genera el PDF vigente a partir de la campaña registrada.

Se necesitan GCC, make, taskset y Python 3. El análisis gráfico usa matplotlib; generar el PDF requiere además reportlab y svglib. Desde `desde_cero`:

```bash
make all test
make sanitize
./build/compare_seq 256 7 2026
bash scripts/comparar_variantes.sh
python3 scripts/analizar_variantes.py resultados/<carpeta_generada>
bash scripts/comparar_memoria.sh
python3 scripts/analizar_memoria.py resultados/<carpeta_memoria_generada>
python3 docs/generar_informe_decisiones.py
```

En `compare_seq` hay un calentamiento no guardado por variante y tamaño. Cada repetición restaura la misma matriz fuera del cronómetro. Se mide solo la factorización; no se incluyen generación, copia inicial ni reconstrucción. Se alterna el orden left/right entre repeticiones. La salida se acepta si el residuo relativo es finito y menor o igual a 1e-12. Los argumentos son N, repeticiones y semilla; este ejecutable es secuencial. MPI tiene su propio ejecutable, descrito arriba.

La primera campaña es `resultados/left_right_20260921`: siete mediciones por variante y tamaño (64, 128, 256, 512 y 1024). La nueva campaña es `resultados/memoria_20260921`: 12 mediciones por cada una de las tres variantes y tamaños 64, 128, 256, 512, 1000 y 1024 (216 observaciones). En esta última se ejecutan las seis permutaciones del orden dos veces, tras un calentamiento por variante. Se conservan CSV, resumen, gráfico, entorno y huellas SHA-256. Los cocientes de rendimiento se calculan entre medianas de la misma campaña.

El generador de PDF usa explícitamente ambas campañas mediante DATA y MEMORY. Una nueva campaña requiere revisar sus conclusiones y actualizar las rutas antes de publicar otra edición. La comparación de memoria incluye la copia de la columna dentro de la factorización; excluye la copia inicial de la matriz, la reserva de memoria y la validación.

El generador recorre las parejas de índices en un orden fijo; la misma semilla y N producen la misma entrada. La implementación MPI preserva esa matriz: la genera el proceso 0 y la distribuye, sin reiniciar generadores diferentes en cada proceso.

## Antecedentes

Los archivos de factorización en Python y `docs/01_secuencial.md` son antecedentes ajenos al camino acordado. También se conserva la campaña antigua `c_secuencial_20260921`, pero su tabla se retiró del informe. El nuevo informe no contiene la sección “La diferencia en un elemento” ni la antigua “Primera comprobación y mediciones”.
