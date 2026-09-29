/* Programa principal de la entrega. USE_MPI selecciona MPI; sin esa macro se compila la referencia secuencial.
 * Lectura: ver docs/guia_codigo.md. Los comentarios explican instrucciones logicas;
 * las llaves y las continuaciones de una misma instruccion comparten explicacion.
 */
/* Habilita las declaraciones POSIX, incluido CLOCK_MONOTONIC. */
#define _POSIX_C_SOURCE 200809L
/* Declara generadores, kernels secuenciales y residuos. */
#include "cholesky.h"
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
/* Declara Layout, perfiles y kernels distribuidos; incluye la API MPI. */
#include "cholesky_mpi.h"
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
/* Permite detectar errores de conversion o interrupciones de llamadas POSIX. */
#include <errno.h>
/* Funciones matematicas y controles de finitud: sqrt, fabs, isfinite, NAN e INFINITY. */
#include <math.h>
/* Entrada/salida de mensajes, archivos y registros CSV. */
#include <stdio.h>
/* Reserva/liberacion de memoria, conversion numerica y terminacion del proceso. */
#include <stdlib.h>
/* Reloj CLOCK_MONOTONIC y estructura timespec. */
#include <time.h>

/* Lee segundos del reloj monotono: sirve para diferencias de tiempo, no para fecha y hora. */
static double now(void)
{
    /* Define t: instante local o estructura del reloj. */
    struct timespec t;
    /* Consulta el reloj monotono; sus diferencias dan tiempo transcurrido en segundos. */
    clock_gettime(CLOCK_MONOTONIC, &t);
    /* Convierte segundos y nanosegundos a una unica cantidad de segundos. */
    return t.tv_sec + t.tv_nsec * 1e-9;
}
/* Reserva count elementos de size bytes; un fallo termina el programa y, en MPI, todos los rangos. */
static void *reserve(size_t count, size_t size)
{
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    void *p = malloc((count ? count : 1) * size);
    /* Detecta que no se pudo obtener el recurso solicitado; no se usa un puntero nulo. */
    if (!p)
    {
        /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
        fputs("No se pudo reservar memoria\n", stderr);
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
        /* Aborta el comunicador para que otros rangos no queden esperando tras el fallo. */
        MPI_Abort(MPI_COMM_WORLD, 3);
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
        /* Termina el proceso con el codigo de error indicado. */
        exit(3);
    }
    /* Entrega la memoria reservada al llamador, que debera liberarla. */
    return p;
}
/* Punto de entrada: procesa argumentos, ejecuta el caso y devuelve el estado al sistema operativo. */
int main(int argc, char **argv)
{
    /* Define rank: rango actual; processes: cantidad de procesos. */
    int rank = 0, processes = 1;
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
    /* Inicializa MPI antes de usar comunicadores o colectivas. */
    MPI_Init(&argc, &argv);
    /* Consulta el identificador de este proceso dentro del comunicador. */
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    /* Consulta cuantos procesos participan en el comunicador. */
    MPI_Comm_size(MPI_COMM_WORLD, &processes);
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
    /* Define end: puntero al primer caracter no convertido. */
    char *end = NULL;
    /* Limpia el error previo antes de la conversion numerica. */
    errno = 0;
    /* Convierte el argumento de texto y conserva los limites/valores por defecto del programa. */
    long value = argc == 2 ? strtol(argv[1], &end, 10) : 0;
    /* Comprueba la forma de invocacion y los limites antes de usar los argumentos. */
    if (argc != 2 || errno || !end || *end || value < 1 || value > 20000)
    {
        /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
        if (!rank)
            /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
            fputs("Uso: cholesky_candidate N (1..20000)\n", stderr);
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
        /* Cierra MPI; todos los rangos deben llegar a esta finalizacion. */
        MPI_Finalize();
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
        /* Informa uso incorrecto de argumentos. */
        return 2;
    }
    /* Define n: orden de la matriz; failed: acumulador de fallos. */
    int n = (int)value, failed = 0;
    /* Define cells: numero total de entradas de A. */
    size_t cells = (size_t)n * n;
    /* Define full: matriz global del rango 0; packed: buffer agrupado por propietario; local: columnas propias almacenadas por filas; column: columna global que se difunde; work: vector auxiliar del kernel. */
    double *full = NULL, *packed = NULL, *local = NULL, *column = NULL, *work = NULL;
    /* Define counts: cantidades de elementos por rango; offsets: desplazamientos de los segmentos. */
    int *counts = NULL, *offsets = NULL;
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
    /* Espera a todos los rangos antes de iniciar la medicion; no sincroniza sus relojes. */
    MPI_Barrier(MPI_COMM_WORLD);
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
    /* Inicia application_s antes de reservar los buffers del candidato. */
    double t0 = now();
    /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
    if (!rank)
        /* Reserva matriz global del rango 0; el llamador liberara el buffer al terminar. */
        full = reserve(cells, sizeof(double));
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
    /* Construye el mapa local con el reparto de columnas indicado. */
    Layout d = layout_create(n, 1, MPI_COMM_WORLD);
    /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
    if (!rank)
        /* Reserva buffer agrupado por propietario; el llamador liberara el buffer al terminar. */
        packed = reserve(cells, sizeof(double));
    /* Reserva columnas propias almacenadas por filas; el llamador liberara el buffer al terminar. */
    local = reserve((size_t)n * d.cols, sizeof(double));
    /* Reserva columna global que se difunde; el llamador liberara el buffer al terminar. */
    column = reserve(n, sizeof(double));
    /* Reserva vector auxiliar del kernel; el llamador liberara el buffer al terminar. */
    work = reserve(d.cols, sizeof(double));
    /* Reserva cantidades de elementos por rango; el llamador liberara el buffer al terminar. */
    counts = reserve(processes, sizeof(int));
    /* Reserva desplazamientos de los segmentos; el llamador liberara el buffer al terminar. */
    offsets = reserve(processes, sizeof(int));
    /* Define offset: inicio del siguiente segmento empaquetado. */
    int offset = 0;
    /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
    for (int r = 0; r < processes; ++r)
    {
        /* Calcula cuantos elementos de matriz corresponden a este rango. */
        counts[r] = n * (n / processes + (r < n % processes));
        /* Guarda el inicio del segmento de este rango. */
        offsets[r] = offset;
        /* Avanza al segmento del siguiente propietario en el buffer empaquetado. */
        offset += counts[r];
    }
/* Ruta alternativa de compilacion para la version secuencial. */
#else
    /* Reserva vector auxiliar del kernel; el llamador liberara el buffer al terminar. */
    work = reserve(n, sizeof(double));
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
    /* Termina allocation_s e inicia generation_s. */
    double t1 = now();
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
    /* Genera exactamente las columnas ciclicas propias con la semilla comun. */
    generate_spd_columns(local, n, 2026, rank, processes);
/* Ruta alternativa de compilacion para la version secuencial. */
#else
    /* Construye la matriz SPD reproducible con la semilla indicada. */
    generate_spd(full, n, 2026);
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
    /* Termina generation_s e inicia factor_s. */
    double t2 = now();
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
    /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
    failed = cholesky_mpi_local(local, column, work, &d, NULL) != 0;
/* Ruta alternativa de compilacion para la version secuencial. */
#else
    /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
    failed = cholesky_right_buffered(full, n, work) != 0;
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
    /* Termina factor_s e inicia gather_s; en MPI incluye espera dentro del kernel. */
    double t3 = now();
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
    /* Reune cantidades distintas de columnas en rango 0, en los segmentos indicados. */
    MPI_Gatherv(local, n * d.cols, MPI_DOUBLE, packed, counts, offsets, MPI_DOUBLE, 0, MPI_COMM_WORLD);
    /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
    if (!rank)
        /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
        for (int r = 0; r < processes; ++r)
        {
            /* Define m: numero de columnas locales. */
            int m = n / processes + (r < n % processes);
            /* Recorre los casos pequenos definidos para verificar el programa. */
            for (int i = 0; i < n; ++i)
                /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
                for (int c = 0; c < m; ++c)
                    /* Devuelve una entrada del segmento recibido a su fila y columna global. */
                    full[(size_t)i * n + r + c * processes] = packed[offsets[r] + (size_t)i * m + c];
        }
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
    /* Cierra gather_s y application_s; luego se calcula por separado el maximo entre rangos. */
    double t4 = now(), elapsed = t4 - t0, max_elapsed = elapsed;
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
    /* Obtiene en rango 0 el maximo de cada duracion local; no se suman esos maximos. */
    MPI_Reduce(&elapsed, &max_elapsed, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
    /* Define any: fallo combinado de todos los rangos. */
    int any;
    /* Entrega a todos el mayor estado/fallo; permite detectar si algun rango fallo. */
    MPI_Allreduce(&failed, &any, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
    failed = any;
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
    /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
    if (!rank)
    {
        /* Inicia validation_s despues de cerrar el tiempo de aplicacion. */
        double v0 = now();
        /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
        double *original = reserve(cells, sizeof(double));
        /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
        long double *check = reserve(2 * (size_t)n, sizeof(long double));
        /* Construye la matriz SPD reproducible con la semilla indicada. */
        generate_spd(original, n, 2026);
        /* Mide el residuo proyectado con ocho vectores y semilla 91827, fuera del kernel. */
        double residual = projected_residual(original, full, n, 8, 91827, check);
        /* Reconstruye LL^T para medir el residuo completo; -1 indica que se omitio por tamano. */
        double exact = n <= 128 ? relative_residual(original, full, n) : -1;
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        failed |= !isfinite(residual) || residual > 1e-12;
        /* Limita la reconstruccion cubica completa a matrices pequenas. */
        if (n <= 128)
            /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
            failed |= !isfinite(exact) || exact > 1e-12;
        /* Recorre los casos pequenos definidos para verificar el programa. */
        for (int i = 0; i < n; ++i)
            /* Recorre exclusivamente el triangulo inferior, que contiene el factor L. */
            for (int j = 0; j <= i; ++j)
                /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                failed |= !isfinite(full[(size_t)i * n + j]) || (i == j && full[(size_t)i * n + j] <= 0);
        /* Cierra la validacion antes de imprimir CSV y liberar sus buffers. */
        double validation = now() - v0;
        /* Publica los nombres de columnas CSV en el orden usado por las filas siguientes. */
        puts(
            "N,P,allocation_s,generation_s,factor_s,gather_s,application_s,max_local_s,validation_s,projected_residual,exact_residual,valid");
        /* Publica resultados del caso en el formato CSV original; las preparaciones se filtran antes. */
        printf("%d,%d,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%d\n", n, processes, t1 - t0,
               t2 - t1, t3 - t2, t4 - t3, t4 - t0, max_elapsed, validation, residual, exact, !failed);
        /* Libera original; free(NULL) es valido para buffers que este rango no reservo. */
        free(original);
        /* Libera check; free(NULL) es valido para buffers que este rango no reservo. */
        free(check);
    }
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
    /* Difunde el estado del rango 0 para que todos terminen con la misma decision. */
    MPI_Bcast(&failed, 1, MPI_INT, 0, MPI_COMM_WORLD);
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
    /* Libera full; free(NULL) es valido para buffers que este rango no reservo. */
    free(full);
    /* Libera packed; free(NULL) es valido para buffers que este rango no reservo. */
    free(packed);
    /* Libera local; free(NULL) es valido para buffers que este rango no reservo. */
    free(local);
    /* Libera column; free(NULL) es valido para buffers que este rango no reservo. */
    free(column);
    /* Libera work; free(NULL) es valido para buffers que este rango no reservo. */
    free(work);
    /* Libera counts; free(NULL) es valido para buffers que este rango no reservo. */
    free(counts);
    /* Libera offsets; free(NULL) es valido para buffers que este rango no reservo. */
    free(offsets);
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
    /* Cierra MPI; todos los rangos deben llegar a esta finalizacion. */
    MPI_Finalize();
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
    /* Propaga el estado acumulado: cero indica que no hubo fallos. */
    return failed ? 1 : 0;
}
