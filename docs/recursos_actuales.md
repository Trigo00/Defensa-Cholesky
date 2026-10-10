# Recursos actuales de presentación y evidencia

El [Word principal](../output/Documentacion/Documentacion-Cholesky-HPC.docx) es la referencia de presentación y se edita manualmente. Este índice se actualiza con el verificador de entrega. No modifica el Word ni sus imágenes.

## Imágenes conservadas

La correspondencia se verifica por SHA-256 del contenido, no por el nombre. El contexto se extrae del texto próximo en el XML del Word; sirve como pista de búsqueda y no certifica una ubicación visual ni una página.

| Imagen | Imagen idéntica incorporada al Word | Contexto textual próximo |
|---|---|---|
| [image138.jpeg](media/image138.jpeg) | word/media/image138.jpeg | 1.88 / Medianas de doce repeticiones por variante y tamaño. Un cociente mayor que 1 favorece a right con vector. Cada comparación usa exclusivamente observaciones de esta segunda c |
| [image139.png](media/image139.png) | word/media/image139.png | Repartos estáticos: contiguo, cíclico y por bloques / En un reparto estático, el propietario de cada columna se fija antes de factorizar. Round-robin por columnas es exactamente el |
| [image222.jpeg](media/image222.jpeg) | word/media/image222.jpeg | MPI_Wtime mide tiempo local. Fuente: documentación oficial de Open MPI. / Resultado: más procesos no siempre ayudan |
| [image223.jpeg](media/image223.jpeg) | word/media/image223.jpeg | Con n=64 no conviene paralelizar este kernel. El primer tamaño probado con mejora clara del contiguo es n=256. Para n=1024 y P=3, el contiguo tarda 40,03 ms frente a 82,65 ms del s |
| [image224.png](media/image224.png) | word/media/image224.png | Cíclico59 652 15359 652 15359 652 494 / Pero el tiempo depende también de cuánto cuesta cada actualización y cuándo queda disponible. En el contiguo, el vector difundido se lee en  |
| [image245.jpeg](media/image245.jpeg) | word/media/image245.jpeg | Un cociente mayor que 1 indica una mejora. Usamos medianas y cuartiles inclusivos Q1-Q3. Las barras de dispersión no son intervalos de confianza; ocho repeticiones en una campaña n |
| [image246.jpeg](media/image246.jpeg) | word/media/image246.jpeg | El control con un solo proceso / Antes de copiar, P=1 da 83,28 ms en contiguo y 147,55 ms en cíclico. Con el vector local, quedan en 86,33 y 84,81 ms, con cuartiles superpuestos. L |
| [image279.jpeg](media/image279.jpeg) | word/media/image279.jpeg | CorrectitudResiduo relativo <=10^-12 y comparación con el factor right secuencial. / Resultado: right fue más rápido en todos los casos |
| [image280.png](media/image280.png) | word/media/image280.png | Con tres procesos, left tardó 54,08 ms y right 31,48 ms: left fue 1,72 veces más lento. Respecto de su propio P=1, left alcanzó 2,89x y right 2,79x. Ambos mejoraron al paralelizar  |
| [image372.jpeg](media/image372.jpeg) | word/media/image372.jpeg | 3/3 / Cada intervalo muestra el mínimo y máximo de las tres aceleraciones calculadas por ronda. No es un intervalo de confianza. “Criterio” cuenta las rondas que cumplen simultánea |
| [image394.jpeg](media/image394.jpeg) | word/media/image394.jpeg | WSL, Ryzen 5 2600; 6 núcleos físicos. Tamaños 512, 1024 y 2048; P=1 a 6; semilla 2026; un calentamiento y 6 repeticiones alternadas por método. Total: 216 observaciones. Centraliza |
| [image396.jpeg](media/image396.jpeg) | word/media/image396.jpeg | Quedan fuera el lanzamiento y cierre de MPI, las referencias de prueba, la validación, la liberación de memoria y escribir resultados. Es el flujo de procesamiento, no el tiempo ex |
| [image397.jpeg](media/image397.jpeg) | word/media/image397.jpeg | La comparación incluye resultados equivalentes y matrices idénticas. Las diferencias observadas dentro de la factorización pueden incorporar efectos del estado de memoria y de la l |
| [image402.png](media/image402.png) | word/media/image402.png | Excluye lanzamiento/cierre MPI, referencias, validación y liberación. Las fases incluyen esperas. Se compara la mediana de totales medidos directamente. / Tiempo hasta obtener el r |
| [image403.jpeg](media/image403.jpeg) | word/media/image403.jpeg | El total contempla los cambios de generación y desempaquetado provocados por el reparto, además del kernel. Una menor mediana aislada es un candidato para repetir, no una demostrac |
| [image420.jpeg](media/image420.jpeg) | word/media/image420.jpeg | LAPACKE 3.12.1; OpenBLAS 0.3.32, backend Zen, un hilo comprobado. Los logs incluyen dependencias dinámicas y configuración. La optimización interna de OpenBLAS no usa necesariament |
| [image423.jpeg](media/image423.jpeg) | word/media/image423.jpeg | Rotamos el orden de los seis métodos entre rondas; los tamaños siguen un orden fijo. No es una aleatorización completa. / WSL local, Ryzen 5 2600, seis núcleos físicos y doce proce |
| [image425.jpeg](media/image425.jpeg) | word/media/image425.jpeg | En N = 1024, tres y seis procesos tardan 54,69 ms y 54,54 ms: duplicar los recursos apenas cambia la latencia y reduce la eficiencia de 54,7 % a 27,4 %. Tres procesos son una elecc |
| [image426.jpeg](media/image426.jpeg) | word/media/image426.jpeg | N=128,160,192,224,256; SEQ y MPI P=1,2,3,4,6. Una ronda descartada y siete medidas. Orden de métodos rotado; tamaños en orden creciente. Afinidad prevista: SEQ con taskset CPU0; MP |
| [image427 - copia.png](media/image427%20-%20copia.png) | word/media/image427.png | 6256 / distintas |
| [image427.png](media/image427.png) | word/media/image427.png | 6256 / distintas |
| [image428.png](media/image428.png) | word/media/image428.png | Conclusión parcial / Aumentar procesos no asegura menor tiempo. En matrices pequeñas los costos adicionales compiten con el trabajo que se reparte; una configuración intermedia pue |
| [image429.jpeg](media/image429.jpeg) | word/media/image429.jpeg | Cada aceleración utiliza la referencia secuencial y el reloj de su propia comparación. La eficiencia S/P expresa rendimiento relativo a esa referencia y no utilización de CPU. La e |
| [image430.jpeg](media/image430.jpeg) | word/media/image430.jpeg | ¿El mínimo del tiempo interno sigue siendo útil para quien espera que termine el comando? La validación secuencial y el costo de lanzar MPI pueden cambiar la respuesta, especialmen |
| [image431.png](media/image431.png) | word/media/image431.png | En N = 512 y N = 1024, incluso la menor mediana externa MPI supera a la secuencial. En N = 2048 y N = 4096, seis procesos reducen el comando completo, con aceleraciones de 1,43 y 1 |
| [image432.jpeg](media/image432.jpeg) | word/media/image432.jpeg | La rotación reduce el sesgo de posición, pero no constituye aleatorización. / Resultados formales: N = 8192 |
| [image433.jpeg](media/image433.jpeg) | word/media/image433.jpeg | P=32 tuvo el menor tiempo mediano entre las seis configuraciones. La reducción absoluta frente a P=1 fue de 50.566130 s por factorización. El ideal T(1)/32 sería 2.003429 s; se uti |
| [image434.jpeg](media/image434.jpeg) | word/media/image434.jpeg | Speedup y eficiencia / Figura 2. Speedup calculado con las medianas formales y referencia ideal S(P)=P. No se estiman intervalos de confianza para las razones. |
| [image435.jpeg](media/image435.jpeg) | word/media/image435.jpeg | El speedup alcanza 4.734× con 32 procesos, mientras la eficiencia baja a 14.79%. Menor tiempo de respuesta y mayor aprovechamiento relativo de procesos son criterios distintos. La  |
| [image436.jpeg](media/image436.jpeg) | word/media/image436.jpeg | La campaña no instrumentó colectivas, desbalance, caché o tiempos por rango de cada fase. Atribuir la anomalía a MPI_Bcast, red o memoria sería una hipótesis sin contrastar. / Tiem |
| [image437.jpeg](media/image437.jpeg) | word/media/image437.jpeg | La validación es trabajo adicional fuera de ambos tiempos. Por ello, estas métricas no deben usarse como una medida directa del tiempo total de una ejecución interactiva o de un tr |
| [image438.png](media/image438.png) | word/media/image438.png | factor_s mide únicamente la llamada al kernel. total_s incluye reserva del arreglo y workspace, generación y factorización. Excluye preparar la matriz original/referencia del banco |
| [image439.png](media/image439.png) | word/media/image439.png | Generación y reunión quedan fuera de factor_s; los relojes secundarios tienen límites distintos. El banco C/LAPACK alterna métodos dentro de un proceso; MPI se lanza por separado.  |
| [image440.png](media/image440.png) | word/media/image440.png | CV usa desviación muestral dividida por la media. La variación MPI en N=6144 es mayor que la de los otros grupos, pero la separación respecto de LAPACK es amplia: incluso el menor  |
| [image97.jpeg](media/image97.jpeg) | word/media/image97.jpeg | No es un speedup MPI. / Qué dicen los datos y qué no demuestran |

Se conservan 35 archivos externos con 34 contenidos distintos. El Word también contiene recursos embebidos que no tienen copia externa.

## Evidencia del clúster

Los siguientes nombres son miembros internos de paquetes tar.gz, no rutas extraídas. Pueden consultarse con `tar -tf paquete.tar.gz` y leerse con `tar -xOf paquete.tar.gz miembro`. Los registros de entorno, compilación y afinidad no equivalen a una transcripción completa de los comandos.

### campana_cruce_20260928.tar.gz

[Paquete original](../data/raw/cluster/campana_cruce_20260928.tar.gz) · 494 archivos internos.

- `campana_cruce_20260928/provenance/build_candidate_mpi.log`
- `campana_cruce_20260928/provenance/build_candidate_seq.log`
- `campana_cruce_20260928/entorno.txt`

Lanzadores .sh conservados: ninguno en este paquete.

### campana_escalabilidad_20260928.tar.gz

[Paquete original](../data/raw/cluster/campana_escalabilidad_20260928.tar.gz) · 592 archivos internos.

- `campana_escalabilidad_20260928/entorno.txt`
- `campana_escalabilidad_20260928/provenance/build_candidate_seq.log`
- `campana_escalabilidad_20260928/provenance/build_candidate_mpi.log`
- `campana_escalabilidad_20260928/provenance/build_measure_command.log`

Lanzadores .sh conservados: ninguno en este paquete.

### campana_final_grande_20260928.tar.gz

[Paquete original](../data/raw/cluster/campana_final_grande_20260928.tar.gz) · 44 archivos internos.

- `campana_final_grande_20260928/entorno.txt`

Lanzadores .sh conservados: ninguno en este paquete.

### campana_lapack_cluster_20260928.tar.gz

[Paquete original](../data/raw/cluster/campana_lapack_cluster_20260928.tar.gz) · 12 archivos internos.

- `campana_lapack_cluster_20260928/entorno.txt`
- `campana_lapack_cluster_20260928/build_compare_lapack_cluster.log`

Lanzadores .sh conservados: ninguno en este paquete.

### evidencia_preformal_20260928.tar.gz

[Paquete original](../data/raw/cluster/evidencia_preformal_20260928.tar.gz) · 114 archivos internos.

- `evidencia_preformal_20260928/build_candidate_mpi.log`
- `evidencia_preformal_20260928/build_candidate_seq.log`

Lanzadores .sh conservados: ninguno en este paquete.

### strong_scaling_formal_8192_20261003.tar.gz

[Paquete original](../data/raw/cluster/strong_scaling_formal_8192_20261003.tar.gz) · 107 archivos internos.

- `strong_scaling_formal_8192_20261003/entorno.txt`

Lanzadores .sh conservados: ninguno en este paquete.

### strong_scaling_pilot_16384_20261003.tar.gz

[Paquete original](../data/raw/cluster/strong_scaling_pilot_16384_20261003.tar.gz) · 14 archivos internos.

- No hay registros de entorno/compilación/afinidad identificados por nombre en este paquete; consultar sus CSV y demás miembros.

Lanzadores .sh conservados: ninguno en este paquete.

### strong_scaling_pilot_8192_20261003.tar.gz

[Paquete original](../data/raw/cluster/strong_scaling_pilot_8192_20261003.tar.gz) · 20 archivos internos.

- `strong_scaling_pilot_8192_20261003/entorno.txt`

Lanzadores .sh conservados: ninguno en este paquete.

### strong_scaling_trazabilidad_20261003.tar.gz

[Paquete original](../data/raw/cluster/strong_scaling_trazabilidad_20261003.tar.gz) · 3 archivos internos.

- `binding_p32.txt`
- `build_candidate_mpi_scaling.log`

Lanzadores .sh conservados: ninguno en este paquete.

