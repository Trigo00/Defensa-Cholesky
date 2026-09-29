# Verificación de reparto bloque-cíclico

- `make test-blocks`: P=1,3,6; n=1,2,3,7,31,65; b=1,2,4,8,16,32,64. PASS.
- Mapas: propietario por columna, cantidad local, índices globales y prefijos; b=1 comparado con distribución cíclica histórica.
- Factores completos comparados con right secuencial. Residuo Frobenius en pruebas pequeñas; ocho proyecciones y comparación del factor en campañas grandes.
- `make test-application`: regresión del mapa cíclico previo, PASS.
- ASan/UBSan: banco `--test` P=3, PASS; OpenMPI `--mca memory ^patcher`, fugas desactivadas mediante `ASAN_OPTIONS=detect_leaks=0`.
- Campaña inicial: 441 observaciones, 7 repeticiones por variante, una sesión WSL. Orden rotado y fuente congelada.
- Confirmación: dos lanzamientos nuevos para n=1024 y n=2048, P=6; 98 observaciones. Candidato b=4 fijado después de campaña inicial y antes de repetir. Misma sesión, no campañas independientes en distintos días.
- El máximo trabajo dividido por la media se verifica mediante enumeración independiente en Python. No representa desequilibrio instantáneo ni costo de comunicación.
- El total contiene reserva/mapas, generación distribuida, kernel y salida centralizada; no contiene MPI_Init/Finalize ni validación.
