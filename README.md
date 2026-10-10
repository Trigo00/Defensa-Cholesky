# Cholesky en C: memoria, MPI y referencia LAPACK

Investigación universitaria sobre cuándo el paralelismo reduce el tiempo de Cholesky y cuánto depende esa ventaja del kernel local y del reloj elegido. Se conservan experimentos locales y nueve paquetes originales del clúster: cinco campañas del 28/09 y cuatro paquetes de strong scaling del 03/10, sin mezclar sus referencias.

El candidato es **right-looking en double, vector local, columnas 1D cíclicas b=1, generación distribuida y reunión en rango 0**. Se compila también una referencia secuencial desde la misma entrada. LAPACK/OpenBLAS se usa en un banco de comparación separado, con un hilo. OpenMP y ScaLAPACK son propuestas futuras, no implementaciones medidas.

## Leer el trabajo

- [Documento Word principal](output/Documentacion/Documentacion-Cholesky-HPC.docx): versión maquetada para lectura, edición y defensa.
- [Inventario técnico](docs/inventario_tecnico.md) y [manifest](MANIFEST.md).
- [Guía del código para la defensa](docs/guia_codigo.md): recorrido por todos los fuentes, índices MPI, relojes y sintaxis de C.
- [Guía paso a paso de los experimentos](docs/guia_paso_a_paso_experimentos.md): qué archivo mostrar, cómo ejecutar cada etapa y qué significa su salida.

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

## Presentación y recursos actuales

- [Demo con matriz externa](src/experimentos/implementacion_con_matriz_sin_generar/PRESENTACION.md): editar MATRIZ.txt y ejecutar el lanzador Windows.
- [Índice de imágenes y evidencia](docs/recursos_actuales.md): imágenes conservadas y contenido verificable de los paquetes.
- [Funciones MPI](output/Funciones%20MPI.md): colectivas y relojes del candidato.

## Recalcular y verificar

Para compilar y verificar los fuentes actuales, ejecutar desde la raíz del proyecto en Linux/WSL con GCC, Make, MPI, LAPACKE y OpenBLAS instalados:

```bash
python3 tests/validation/verify_code_refactor.py
make -C src/experimentos/implementacion_con_matriz_sin_generar test
```

La regresión compila el candidato y los bancos, ejecuta las pruebas secuenciales y compara sus resultados con los fuentes históricos para MPI P=1,2,3,4,6. Guarda el registro y el informe en `docs/checks/`. La segunda orden compila y prueba la demo con archivos temporales.

Para verificar las estadísticas y los recursos de la entrega:

```bash
python3 scripts/analyze_results.py
python3 tests/validation/verify_delivery.py
```

Ambos comandos requieren Python 3.10 o posterior y solo su biblioteca estándar. El primero reconstruye tablas y auditorías en data/processed; el segundo comprueba estadísticas, hashes, enlaces y recursos del Word y actualiza el registro de verificación y el índice de recursos. La verificación no ejecuta ni certifica las pruebas C/MPI ni revisa visualmente la maquetación.

Las imágenes de docs/media y las incorporadas al Word son los recursos de presentación. El Word se edita manualmente: estos comandos no lo reconstruyen ni lo modifican.

Opcionalmente, con matplotlib instalado:

```bash
python3 scripts/analyze_results.py --figures
```

Las gráficas auxiliares se guardan en output/analisis/figures. No reemplazan las imágenes del Word. La antigua publicación integral está retirada; build_documentation.py solo informa de este cambio. publication_pdf.py se conserva como auxiliar de la publicación retirada, sin uso en el flujo vigente.
