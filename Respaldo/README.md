# Cholesky en C: memoria, MPI y referencia LAPACK

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