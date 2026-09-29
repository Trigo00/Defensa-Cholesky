# Preparación previa al clúster, 24/09/2026

- make test, test-blocks P1/P3/P6 y test-lapack: PASS (pruebas.log).
- LAPACK: factor conocido 3x3, matrices pequeñas, residuo completo, matriz indefinida detectada; OpenBLAS 1 hilo verificado mediante API.
- Interfaz C + generador con ASan/UBSan, test-lapack: PASS. Bibliotecas precompiladas sin instrumentación propia.
- Comparación por pares MPI adicional n=7, P=3, 2 repeticiones: PASS.
- bash -n de scripts de campaña y preparación: PASS; presupuesto de 1 MiB rechazado antes de ejecutar n=3072.
- 32 observaciones confirmación MPI; 4 exploratorias n3072; 40 C/LAPACK. Análisis comprueba orden, finitud, tolerancias y suma de fases.
- Analizador portable de pares probado sobre confirmación y piloto.
- Comparaciones MPI y LAPACK se ejecutan secuencialmente, sin campañas concurrentes.
- Se instaló LAPACKE 3.12.1 y OpenBLAS 0.3.32 en WSL. Dependencias dinámicas y configuración en entorno.txt y logs por tamaño.
- free -h al terminar informó swap 0 B; no se hizo monitoreo continuo del swap. time -v conservado por lanzamiento; RSS no suma todos los rangos.
- No se probaron nodos remotos ni srun. La configuración del clúster debe ser confirmada por su administrador.
