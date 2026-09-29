# Cierre local: candidato y dos relojes

Fecha: 24/09/2026. Una sesión WSL; ver entorno.txt y tests/mpi_version.txt.
El comando mpirun --version emitió un aviso sobre un archivo de ayuda ausente;
ompi_info confirmó Open MPI 5.0.10. Los lanzamientos medidos terminaron con código 0.

N=256,512,1024,2048. Métodos: secuencial autónomo y MPI P=1,2,3,4,6.
Ocho rondas, primera descartada: 192 ejecuciones; 168 observaciones medidas.
Orden de métodos rotado por ronda; tamaños en orden creciente fijo.
Cada observación ejecuta un proceso nuevo: no hay calentamiento interno amortizado.
Secuencial: taskset CPU0. MPI: --bind-to core --map-by core.
La comprobación adicional tests/affinity.log confirma núcleos 0..5 con seis procesos.
No se ejecutaron otras campañas de rendimiento simultáneamente.

Candidato: right-looking escalar con vector local, cíclico 1D b=1,
generación distribuida, L completo en memoria del rango 0. Semilla 2026.
Entrada SPD diagonalmente dominante; no se generaliza a otras familias.
Secuencial: right buffered, mismo generador y validación, sin MPI.

application_s: reserva hasta L reunido, reloj monotónico de rango 0.
max_local_s: máximo de las duraciones locales; no sumar máximos de fases.
validation_s: regenerar A y comprobar ocho proyecciones; diagonal finita y positiva.
external_s: fork hasta terminación del comando, medido en C; incluye validación,
salida CSV, liberación e inicialización/cierre MPI. Excluye iniciar WSL, cola y
escritura de la matriz (no implementada). El CSV del cronómetro se escribe después.
other_external_s se calcula por observación; NO es una medición pura de arranque.

Estadística: mediana y cuartiles inclusivos Q1-Q3, siete muestras.
Speedup útil: mediana secuencial / mediana MPI. Eficiencia: speedup / P.
Escalabilidad interna alternativa: MPI1 / MPIP, guardada en resumen.csv.
No se calculan intervalos de confianza ni se prueba estabilidad entre sesiones.

30 configuraciones pequeñas adicionales: N=1,2,7,31,128, con secuencial y cinco P;
residuo completo y proyectado. Tests numéricos anteriores pasan. Comprobaciones
suplementarias verifican códigos de error y cronómetro externo con true/false.
Fuentes congeladas en fuentes/ y hashes relativos a esa carpeta en fuentes.sha256.
El analizador y constructor PDF se conservan también en el repositorio Git.
