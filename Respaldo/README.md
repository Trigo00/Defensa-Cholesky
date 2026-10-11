# Cholesky en C: memoria, MPI y referencia LAPACK

Investigación universitaria sobre cuándo el paralelismo reduce el tiempo de Cholesky y cuánto depende esa ventaja del kernel local y del reloj elegido. Se conservan experimentos locales y nueve paquetes originales del clúster: cinco campañas del 28/09 y cuatro paquetes de strong scaling del 03/10, sin mezclar sus referencias.

El candidato es **right-looking en double, vector local, columnas 1D cíclicas b=1, generación distribuida y reunión en rango 0**. Se compila también una referencia secuencial desde la misma entrada. LAPACK/OpenBLAS se usa en un banco de comparación separado, con un hilo. OpenMP y ScaLAPACK son propuestas futuras, no implementaciones medidas.

## Leer el trabajo

- [Documento Word principal](output/Documentacion/Documentacion-Cholesky-HPC.docx): versión maquetada para lectura, edición y defensa.
- [Inventario técnico](docs/inventario_tecnico.md) y [manifest](MANIFEST.md).
- [Guía paso a paso de los experimentos](docs/guia_paso_a_paso_experimentos.md): qué archivo mostrar, cómo ejecutar cada etapa y qué significa su salida.
- [Demo con matriz externa](src/experimentos/implementacion_con_matriz_sin_generar/PRESENTACION.md): editar MATRIZ.txt y ejecutar el lanzador Windows.

## Organización

| Ruta | Contenido |
|---|---|
| `src/implementacion_final/` | Programa final secuencial/MPI y sus interfaces |
| `src/experimentos/` | Bancos comparativos, cronómetro y utilidades compartidas |
| `tests/`, `Makefile` | Pruebas, validaciones, fixture de regresión y reglas de compilación |
| `scripts/` | Análisis de datos y scripts de campañas; el Word se edita manualmente |
| `data/raw/local/` | CSV originales, registros y fuentes congeladas locales |
| `data/raw/cluster/` | Nueve tar.gz originales, leídos sin extraer durante el análisis |
| `data/processed/` | Observaciones normalizadas, cuartiles, cocientes y auditoría |
| `docs/media/` | Imágenes actuales; correspondencia con el Word en docs/recursos_actuales.md |
| `docs/`, `output/Documentacion/` | Guías y Word principal |