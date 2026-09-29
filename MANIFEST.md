# Manifest de la entrega

## Mapa de contenido

| Ruta | Propósito | Origen | Tipo | Campaña |
|---|---|---|---|---|
| `src/implementacion_final` | Implementación final comentada: entrada, Cholesky secuencial y MPI | Revisión didáctica del árbol `desde_cero` | source | Estado candidato |
| `src/experimentos` | Bancos, cronómetro y utilidades comunes comentados | Revisión didáctica del árbol `desde_cero` | source | Bancos experimentales |
| `tests`, `Makefile` | Pruebas conservadas y compilación de ambas carpetas | Revisión didáctica del árbol `desde_cero` | source/build | Estado candidato y bancos |
| `archive/formato_previo_20260929` | Cuatro copias con formato previo; mismos tokens que los medidos | Estado recibido antes de comentar | source_snapshot | Revisión didáctica |
| `archive/src_medidos_20260928` | Fuentes y Makefile exactos anteriores a la refactorización, con hashes | Copia del estado medido conservado en la entrega | measured_source | Referencia histórica |
| `scripts/verify_code_refactor.py` | Regresión funcional entre fuentes anteriores y actuales | Creado para esta revisión | validation | Revisión didáctica |
| `docs/guia_codigo.md` | Guía de lectura, memoria, MPI y defensa | Código inspeccionado | documentation | Revisión didáctica |
| `scripts/*.sh`, `scripts/analizar_*.py` | Lanzamiento y análisis; cuatro scripts incorporan las nuevas dependencias al copiar fuentes | `desde_cero/scripts`, revisión de dependencias | scripts | Local y preparación |
| `archive/scripts_previos_20260929` | Copias exactas de esos cuatro scripts anteriores | Estado previo | historical_script | Trazabilidad |
| `scripts/analyze_results.py` | Reanálisis independiente del árbol antiguo | Creado para esta entrega, reutiliza criterios históricos | analysis | Todas las campañas verificables |
| `scripts/publication_visuals.py`, `scripts/publication_pdf.py` | Estilo, esquemas y maquetación | Creado para esta entrega | publication | Síntesis |
| `scripts/build_documentation.py` | Tablas y publicación de relato | Creado para esta entrega | publication | Síntesis |
| `scripts/verify_delivery.py` | Integridad y consistencia final | Creado para esta entrega | validation | Entrega |
| `data/raw/local` | Observaciones originales, entornos y snapshots | `desde_cero/resultados`, copias byte a byte | raw | Quince directorios locales |
| `data/raw/cluster/*.tar.gz` | Evidencia canónica comprimida | Paquetes recibidos del clúster | raw_archive | Preformal, cruce, escalabilidad, LAPACK, final grande |
| `data/processed` | Observaciones normalizadas, resúmenes, auditoría y tablas | Regenerados desde raw | processed | Campaña y cohorte en cada fila |
| `figures` | Dieciséis figuras PNG y SVG | Trece gráficas de datos y tres esquemas conceptuales | figure | Procedencia en captions |
| `docs/investigacion_completa.md.in` | Narrativa editable con marcadores de tablas | Reconstrucción técnica | documentation_source | Historia completa |
| `docs/investigacion_completa.md`, `output/pdf` | Informe publicado | Plantilla + tablas procesadas | documentation | Síntesis |
| `docs/metodologia_experimental.md`, `docs/reproducibilidad.md` | Contratos, condiciones y ejecución | Inspección de código y evidencia | documentation | Transversal |
| `archive/docs_etapas` | PDF históricos existentes | `output/pdf` del árbol original | historical_documentation | Informes1-19 y recorrido local |
| `archive/docs_fuentes` | Generadores/guías/README anteriores | `desde_cero/docs` y README | historical_documentation | Local y clúster |
| `archive/analisis_previos` | Derivados anteriores, ZIP de análisis y bitácora | Carpetas de resultados originales | historical_derivative/context | Según subdirectorio |
| `archive/antecedentes` | Prototipo anterior y utilidades no vigentes | Raíz original | legacy | Excluidos de cocientes actuales |

Los logs, entornos y fuentes congeladas acompañan a la campaña que los produjo, en lugar de duplicarse en directorios globales. Dentro de un tar, `archive_members.csv` permite localizar el miembro exacto. Los resúmenes finales no dependen de extraer los paquetes ni de volver a acceder a las rutas del escritorio.

## Inventarios exhaustivos

- `docs/inventario_original.csv`: 1.962 archivos relevantes existentes al comienzo, 12.627.509 bytes. Excluye `.git`, temporales, caches y build. Cada fila conserva ruta, tamaño y SHA-256.
- `docs/procedencia_copias.csv`: relación archivo copiado, origen, tipo, campaña, tamaño y SHA-256. Los nuevos documentos y derivados no se hacen pasar por copias.
- `docs/duplicados_originales.json`: 72 grupos de contenido idéntico, incluidos archivos vacíos. La igualdad de bytes no significa que sus papeles experimentales sean intercambiables.
- `docs/inventario_herramientas.csv`: código y herramientas con tamaños y hashes.
- `data/processed/archive_members.csv`: contenido de los cinco paquetes, sin extracción permanente.
- `data/processed/verified_hashes.csv`: comprobaciones de manifiestos y hashes originales disponibles.
- `data/processed/document_table_trace.csv`: estadísticas fuente de las tablas del informe.
- `docs/verificacion_entrega.json`: controles ejecutados sobre esta entrega, con alcance explícito.

La entrega previa `output/entrega_precluster_20260924` permanece intacta en el árbol original. No se duplica completa: su correspondencia con archivos incluidos se registra en `docs/entrega_previa_correspondencia.csv`; los contenidos únicos se preservan en `archive/entrega_previa`. Los archivos recompilables sueltos no se presentan como evidencia de nuevas campañas.

## Tamaño y publicación

El mayor archivo del inventario inicial ocupa 1.044.565 bytes, alrededor de 1 MiB. El volumen es manejable y no requiere una migración a Git LFS. Las bibliotecas temporales y los binarios recompilados quedan fuera de la entrega versionable. Los tar.gz pequeños preservan la evidencia con menos duplicación; los PDF históricos se mantienen porque documentan la evolución. No se eliminó ningún original.

No se inicializó otro repositorio, no se configuró remoto y no se publicó. La carpeta puede revisarse antes de subirla. Las rutas o nombres de host registrados en logs forman parte de la evidencia original y no se reescribieron.

