# Manifiesto de la entrega actual

| Ruta | Propósito |
|---|---|
| `output/Documentacion/Documentacion-Cholesky-HPC.docx` | Documento principal, editado manualmente |
| `docs/media/` | Imágenes conservadas para la presentación |
| [Índice de recursos](docs/recursos_actuales.md) | Correspondencia por hash con imágenes del Word y registros de los paquetes |
| `src/implementacion_final/` | Candidato secuencial/MPI |
| `src/experimentos/implementacion_con_matriz_sin_generar/` | Demo con matriz externa, lanzador y pruebas |
| `src/experimentos/` | Bancos comparativos |
| `tests/` | Pruebas, verificadores e instantánea histórica |
| `data/raw/` | Evidencia original local y nueve paquetes del clúster |
| `data/processed/` | Tablas y auditorías; las salidas de publicación antiguas que aún existan no son entradas del flujo vigente |
| `docs/guia_codigo.md` | Explicación del código |
| `docs/guia_paso_a_paso_experimentos.md` | Recorrido experimental |
| `docs/verificacion_entrega.json` | Resultado fechado de la última verificación y límites de su alcance |
| `output/` | Word, apuntes y PDF de referencia conservados |
| `scripts/` | Análisis y campañas; los generadores de la publicación anterior están fuera del flujo vigente |

## Reproducción

El análisis predeterminado reconstruye estadísticas, sin generar imágenes. La opción --figures produce gráficas auxiliares en output/analisis/figures, una carpeta opcional. Los recursos actuales del Word no dependen de esa opción.

Los comandos vigentes están en el [README](README.md). La verificación de entrega no acredita una nueva ejecución C/MPI ni equivalencia funcional de los fuentes actuales con los históricos. Esa comprobación se solicita por separado con tests/validation/verify_code_refactor.py y requiere Linux/WSL con sus dependencias.

Las transcripciones independientes de comandos del clúster fueron retiradas. Los paquetes conservan datos, fuentes y registros; no se afirma que contengan un launcher exacto si no está presente. El índice de recursos enumera los miembros relevantes disponibles.
