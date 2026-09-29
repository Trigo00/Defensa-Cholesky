# Validación de la primera implementación MPI

Campaña local del 21/09/2026. Cálculo en C, GCC 15.2.0 y Open MPI 5.0.10.

- `make all mpi test test-mpi`: PASS; pruebas MPI con P=1,2,3,4.
- Casos MPI por P, en ambos repartos: SPD n=1,2,7,16,31, matriz 3x3 con factor conocido, pivote negativo y NaN. Incluye n no divisible por P y procesos sin columnas.
- Cada repetición medida reconstruye el factor y calcula el residuo fuera del cronómetro. Ver `validacion.json` y los CSV individuales.
- Huellas en `fuentes.sha256`: todas comprobadas después de ejecutar la campaña.
- Compilación con `-fsanitize=undefined -fno-sanitize-recover=all`: PASS con P=4.
- Compilación con `-fsanitize=address,undefined -fno-omit-frame-pointer`: PASS con P=4 usando `ASAN_OPTIONS=detect_leaks=0 mpirun --mca memory ^patcher --bind-to core --map-by core -np 4 ./build/compare_mpi_sanitize --test`.

Con memory/patcher activo, ASan falló dentro de MPI_Init. Se reprodujo con un programa que solo imprime, llama MPI_Init y MPI_Finalize, sin Cholesky. No se presenta ese intento como una prueba aprobada; no se evaluaron fugas. Desactivar patcher fue exclusivo de las pruebas, no de la campaña de tiempos.

`mpirun --version` no imprimió su versión por un archivo de ayuda ausente del paquete. La versión se registró mediante `ompi_info --version` en `version_mpi.txt`. Las ejecuciones de la campaña terminaron correctamente.

El perfil separado incluye llamadas a MPI_Wtime por etapa. El experimento principal mide solo entrada y salida del kernel. No deben sustituirse sus tiempos por los del perfil.

Las afinidades observadas permiten los dos hilos lógicos de un núcleo por rango, sin compartir núcleo entre rangos según WSL. No implica aislamiento del sistema anfitrión. `placement.log` conserva el mapeo real.
