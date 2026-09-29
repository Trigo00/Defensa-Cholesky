# Adenda a la Etapa 15: recepción de archivos del clúster

Posteriormente al informe inicial, el usuario entregó directamente desde el
clúster `evidencia_preformal_20260928.tar.gz`. Se conserva el paquete íntegro
en esta carpeta. Esta adenda actualiza la limitación documental del PDF:
ya se recibieron los CSV originales, sus archivos de error y los logs de
compilación. El PDF, su generador y la versión Markdown ya incorporan esta
auditoría y recalculan gráficos y estadísticas desde los CSV originales.

## Verificaciones realizadas

- 114 archivos regulares en el paquete.
- 113 entradas en SHA256SUMS.txt: todas coinciden con los contenidos archivados.
  El único archivo no listado es el propio SHA256SUMS.txt.
- 53 CSV, cada uno con una fila de resultados.
- 53 archivos .err y dos logs de compilación: todos vacíos.
- Cinco fuentes C/headers: coinciden byte por byte con las fuentes locales
  contrastadas anteriormente contra los hashes de la bitácora.
- Todos los resultados indican valid=1, tiempos finitos y no negativos,
  residuo proyectado dentro de 1e-12 y residuo completo aceptable para N<=128.
- Las cuatro fases suman application_s dentro de la precisión impresa en las
  53 filas (tolerancia máxima entre 1e-11 s y 1e-10 del total).
- Los 50 tiempos de aplicación tabulados en el informe se localizaron en los
  CSV originales. La diferencia relativa máxima fue 3,653e-6, compatible con
  el redondeo de las tablas. No cambia ninguna conclusión publicada.

## Alcance

La integridad del paquete es coherente con su manifiesto. Los logs vacíos
acreditan ausencia de texto capturado en esos archivos, no sustituyen un
registro explícito de códigos de salida. Los CSV aportan validación numérica
del programa. El paquete no contiene una campaña formal nueva ni registros
completos de binding por ejecución o diagnósticos independientes de cpu.stat.
La topología y el throttling continúan respaldados por la bitácora recibida.

La campaña formal de cruce no está incluida. Sigue siendo necesario analizarla
cuando se complete, sin mezclar estas observaciones preliminares con sus rondas.
