# Validación de la etapa 8

- `make test-application`: n=1,2,3,7,31,128 con P=1,3,6; tres métodos; PASS.
- Cada ejecución comprueba residuo proyectado, comparación elemento a elemento con el factor secuencial y residuo completo para n<=128.
- AddressSanitizer + UndefinedBehaviorSanitizer: banco completo `--test` con P=3, PASS. OpenMPI con `--mca memory ^patcher`, `ASAN_OPTIONS=detect_leaks=0` por compatibilidad; no se comprobó fugas con este comando.
- Análisis de 162 observaciones: verifica orden, configuración, valores finitos, tolerancia 1e-12 y suma de fases versus total.
- Semillas: matriz 2026; ocho proyecciones 91827. Una sesión, seis repeticiones por método/configuración; pendientes sesiones independientes.
- Total principal: tiempo de rango 0 hasta resultado completo. Conserva máximo local como control. La referencia secuencial se ejecuta dentro de MPI mientras otros procesos esperan.
- Reserva real por repetición; primer acceso a páginas atribuido a la fase donde ocurre. Referencias de validación mantienen memoria adicional fuera del cronómetro.
