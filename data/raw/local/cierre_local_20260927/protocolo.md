# Repetición independiente del cierre local

27/09/2026. Repetición del protocolo del 24/09, sin cambios en código C,
Makefile ni script de ejecución. Los hashes de las fuentes se contrastan
automáticamente en generar_informe_repeticion.py antes de crear el informe.

Mismos tamaños (256,512,1024,2048), métodos (secuencial y MPI 1,2,3,4,6),
semillas, orden rotado y siete repeticiones medidas más una descartada.
Mismos relojes interno y externo. No se agrupan las muestras de ambas sesiones.
Cada speedup usa la mediana secuencial de su propia sesión y tamaño.

Mismo aviso de mpirun --version por archivo de ayuda ausente que el 24/09;
la versión de MPI se registra adicionalmente con ompi_info. El analizador
exige que todos los comandos de la campaña terminen correctamente.
No se ejecutan otras campañas de rendimiento simultáneamente.

El protocolo numérico y de tiempos está detallado en
../cierre_local_20260924/protocolo.md. Los cuartiles se guardan por sesión.
Una repetición en otra fecha no aísla temperatura, frecuencia ni carga del sistema.
La comparación sirve para evaluar sensibilidad entre sesiones, no para declarar
causalidad ni un umbral universal. Código y documentación con asistencia de IA.
