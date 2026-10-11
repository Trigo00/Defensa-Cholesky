/* Compara propiedad contigua y ciclica con el kernel MPI original; mide solo la factorizacion.
 * Lectura: ver docs/guia_codigo.md. Los comentarios explican instrucciones logicas;
 * las llaves y las continuaciones de una misma instruccion comparten explicacion.
 */
/* Habilita extensiones GNU para consultar CPU y afinidad en Linux. */
#define _GNU_SOURCE
/* Declara generadores, kernels secuenciales y residuos. */
#include "cholesky.h"
/* Reutiliza conversiones y comparacion de factores para evitar codigo duplicado. */
#include "bench_utils.h"
/* Declara Layout, perfiles y kernels distribuidos; incluye la API MPI. */
#include "cholesky_mpi.h"
/* Permite detectar errores de conversion o interrupciones de llamadas POSIX. */
#include <errno.h>
/* Limites de los tipos enteros de C. */
#include <limits.h>
/* Funciones matematicas y controles de finitud: sqrt, fabs, isfinite, NAN e INFINITY. */
#include <math.h>
/* Consulta CPU y afinidad para documentar el entorno Linux. */
#include <sched.h>
/* Entrada/salida de mensajes, archivos y registros CSV. */
#include <stdio.h>
/* Reserva/liberacion de memoria, conversion numerica y terminacion del proceso. */
#include <stdlib.h>
/* Copia y comparacion de buffers o argumentos. */
#include <string.h>

/* Reserva memoria local, incluso si no hay columnas; un fallo de reserva aborta el comunicador. */
static void *allocate(size_t bytes)
{
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    void *p = malloc(bytes ? bytes : sizeof(double));
    /* Detecta que no se pudo obtener el recurso solicitado; no se usa un puntero nulo. */
    if (!p)
    {
        /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
        fprintf(stderr, "Memoria insuficiente\n");
        /* Aborta el comunicador para que otros rangos no queden esperando tras el fallo. */
        MPI_Abort(MPI_COMM_WORLD, 3);
    }
    /* Entrega la memoria reservada al llamador, que debera liberarla. */
    return p;
}
/* root es el unico que conserva A completa. La conversion a columnas
 * locales, Scatterv, Gatherv y validacion quedan fuera del cronometro. */
/* Prepara, mide y verifica un caso; las variantes y repeticiones siguen el orden del banco original. */
static int run_case(int n, int reps, int mode, int test)
{
    /* Define rank: rango actual; p: cantidad de procesos. */
    int rank, p;
    /* Consulta el identificador de este proceso dentro del comunicador. */
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    /* Consulta cuantos procesos participan en el comunicador. */
    MPI_Comm_size(MPI_COMM_WORLD, &p);
    /* Define bytes: bytes de una matriz densa. */
    size_t bytes = (size_t)n * n * sizeof(double);
    /* Define original: matriz A sin factorizar; packed: buffer agrupado por propietario; factor: matriz que recibira L; ref: factor secuencial de referencia; work: vector auxiliar del kernel. */
    double *original = NULL, *packed = NULL, *factor = NULL, *ref = NULL, *work = NULL;
    /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
    if (!rank)
    {
        /* Reserva matriz A sin factorizar; el llamador liberara el buffer al terminar. */
        original = allocate(bytes);
        /* Reserva buffer agrupado por propietario; el llamador liberara el buffer al terminar. */
        packed = allocate(bytes);
        /* Reserva matriz que recibira L; el llamador liberara el buffer al terminar. */
        factor = allocate(bytes);
        /* Reserva factor secuencial de referencia; el llamador liberara el buffer al terminar. */
        ref = allocate(bytes);
        /* Reserva vector auxiliar del kernel; el llamador liberara el buffer al terminar. */
        work = allocate((size_t)n * sizeof(double));
        /* Construye la matriz SPD reproducible con la semilla indicada. */
        generate_spd(original, n, 2026);
        /* Selecciona el control de prueba: matriz conocida, entrada invalida o validacion completa. */
        if (test == 1)
        { /* Matriz con factor conocido. */
            /* Define known: matriz con factor conocido. */
            double known[9] = {4, 12, -16, 12, 37, -43, -16, -43, 98};
            /* Copia los datos sin operaciones numericas; prepara una entrada o referencia independiente. */
            memcpy(original, known, sizeof known);
        }
        /* Evalua esta alternativa solo si no se cumplio la condicion anterior. */
        else if (test == 2)
            /* Introduce deliberadamente un pivote invalido para verificar el fallo colectivo. */
            original[0] = -1;
        /* Evalua esta alternativa solo si no se cumplio la condicion anterior. */
        else if (test == 3)
            /* Introduce deliberadamente un pivote invalido para verificar el fallo colectivo. */
            original[0] = NAN;
        /* Copia los datos sin operaciones numericas; prepara una entrada o referencia independiente. */
        memcpy(ref, original, bytes);
        /* Selecciona el control de prueba: matriz conocida, entrada invalida o validacion completa. */
        if (test < 2 && cholesky_right_buffered(ref, n, work))
            /* Aborta el comunicador para que otros rangos no queden esperando tras el fallo. */
            MPI_Abort(MPI_COMM_WORLD, 4);
    }
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    int *counts = allocate((size_t)p * sizeof(int)), *displs = allocate((size_t)p * sizeof(int));
    /* Define failed: acumulador de fallos. */
    int failed = 0;
    /* Calentamiento y repeticiones, alternando cual reparto se ejecuta primero. */
    /* Incluye rep=0 como preparacion; rep=1..reps son las repeticiones utiles. */
    for (int rep = 0; rep <= reps; ++rep)
        /* Recorre las posiciones del orden de ejecucion de esta repeticion. */
        for (int order = 0; order < 2; ++order)
        {
            /* Define cyclic: selector de reparto. */
            int cyclic = (rep + order) % 2;
            /* Construye el mapa local con el reparto de columnas indicado. */
            Layout d = layout_create(n, cyclic, MPI_COMM_WORLD);
            /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
            double *local = allocate((size_t)n * d.cols * sizeof(double));
            /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
            double *column = allocate((size_t)n * sizeof(double));
            /* Define offset: inicio del siguiente segmento empaquetado. */
            int offset = 0;
            /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
            for (int r = 0; r < p; ++r)
            {
                /* Define other: metadatos de otro propietario. */
                Layout other = d;
                /* Configura una copia del mapa para inspeccionar otro rango sin comunicacion. */
                other.rank = r;
                /* Define q: columnas base por rango; rem: columnas sobrantes. */
                int q = n / p, rem = n % p;
                /* Recalcula la cantidad de columnas del rango indicado, incluido el resto. */
                other.cols = q + (r < rem);
                /* Calcula la primera columna global del rango que se esta inspeccionando. */
                other.first = cyclic ? r : r * q + (r < rem ? r : rem);
                /* Calcula cuantos elementos de matriz corresponden a este rango. */
                counts[r] = n * other.cols;
                /* Guarda el inicio del segmento de este rango. */
                displs[r] = offset;
                /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
                if (!rank)
                    /* Recorre las filas del intervalo indicado. */
                    for (int i = 0; i < n; ++i)
                        /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
                        for (int c = 0; c < other.cols; ++c)
                            /* Copia una entrada global al segmento por filas del propietario correspondiente. */
                            packed[offset + i * other.cols + c] =
                                /* Lee la entrada de A cuya columna global pertenece a este segmento. */
                                original[(size_t)i * n + layout_global(&other, c)];
                /* Avanza al segmento del siguiente propietario en el buffer empaquetado. */
                offset += counts[r];
            }
            /* Rango 0 reparte counts[r] doubles desde displs[r]; cada rango recibe sus columnas. */
            MPI_Scatterv(packed, counts, displs, MPI_DOUBLE, local, n * d.cols, MPI_DOUBLE, 0,
                         MPI_COMM_WORLD);
            /* Espera a todos los rangos antes de iniciar la medicion; no sincroniza sus relojes. */
            MPI_Barrier(MPI_COMM_WORLD);
            /* Define prof: perfil right-looking. */
            Profile prof = {0};
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            double start = MPI_Wtime();
            /* Ejecuta el kernel seleccionado y guarda el estado de la factorizacion. */
            int status = cholesky_mpi(local, column, &d, mode ? &prof : NULL);
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            double elapsed = MPI_Wtime() - start, maximum = 0;
            /* Obtiene en rango 0 el maximo de cada duracion local; no se suman esos maximos. */
            MPI_Reduce(&elapsed, &maximum, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);
            /* Define status_min: menor estado entre rangos; status_max: mayor estado entre rangos. */
            int status_min, status_max;
            /* Entrega a todos el menor estado para comprobar acuerdo colectivo. */
            MPI_Allreduce(&status, &status_min, 1, MPI_INT, MPI_MIN, MPI_COMM_WORLD);
            /* Entrega a todos el mayor estado/fallo; permite detectar si algun rango fallo. */
            MPI_Allreduce(&status, &status_max, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
            /* Selecciona el control de prueba: matriz conocida, entrada invalida o validacion completa. */
            if (status_min != status_max || status != (test >= 2 ? -1 : 0))
                /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                failed = 1;
            /* Reune cantidades distintas de columnas en rango 0, en los segmentos indicados. */
            MPI_Gatherv(local, n * d.cols, MPI_DOUBLE, packed, counts, displs, MPI_DOUBLE, 0, MPI_COMM_WORLD);
            /* Define residual: residuo numerico; difference: diferencia maxima frente al factor de referencia. */
            double residual = 0, difference = 0;
            /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
            if (!rank && test < 2)
            {
                /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
                for (int r = 0; r < p; ++r)
                {
                    /* Define other: metadatos de otro propietario. */
                    Layout other = d;
                    /* Configura una copia del mapa para inspeccionar otro rango sin comunicacion. */
                    other.rank = r;
                    /* Recalcula la cantidad de columnas del rango indicado, incluido el resto. */
                    other.cols = counts[r] / n;
                    /* Define q: columnas base por rango; rem: columnas sobrantes. */
                    int q = n / p, rem = n % p;
                    /* Calcula la primera columna global del rango que se esta inspeccionando. */
                    other.first = cyclic ? r : r * q + (r < rem ? r : rem);
                    /* Recorre las filas del intervalo indicado. */
                    for (int i = 0; i < n; ++i)
                        /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
                        for (int c = 0; c < other.cols; ++c)
                            /* Prepara el destino global de la entrada recibida; la expresion continua en la siguiente linea. */
                            factor[(size_t)i * n + layout_global(&other, c)] =
                                /* Copia una entrada global al segmento por filas del propietario correspondiente. */
                                packed[displs[r] + i * other.cols + c];
                }
                /* Calcula el error del factor fuera del intervalo de factorizacion medido. */
                residual = relative_residual(original, factor, n);
                /* Compara el triangulo inferior con la referencia mediante la utilidad compartida. */
                difference = factor_difference(factor, ref, n);
                /* Selecciona el control de prueba: matriz conocida, entrada invalida o validacion completa. */
                if (test == 1)
                {
                    /* Define knownL: factor triangular conocido. */
                    double knownL[9] = {2, 0, 0, 6, 1, 0, -8, 5, 3};
                    /* Recorre las filas del intervalo indicado. */
                    for (int i = 0; i < n; ++i)
                        /* Recorre exclusivamente el triangulo inferior, que contiene el factor L. */
                        for (int j = 0; j <= i; ++j)
                            /* Compara esta entrada de L con el factor conocido usando tolerancia 1e-13. */
                            if (fabs(factor[i * n + j] - knownL[i * n + j]) > 1e-13)
                                /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                                failed = 1;
                }
                /* Comprueba finitud y/o tolerancias para que NaN e infinito no pasen la validacion. */
                if (!isfinite(residual) || residual > 1e-12 || difference > 1e-13)
                    /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                    failed = 1;
            }
            /* Publica solo repeticiones utiles y respeta los selectores de prueba/perfil indicados. */
            if (rep > 0 && !test)
            {
                /* Selecciona entre resultados ordinarios y perfiles por proceso. */
                if (!mode && !rank)
                    /* Publica resultados del caso en el formato CSV original; las preparaciones se filtran antes. */
                    printf("%d,%d,%d,%d,%s,%.12g,%.12g,%.12g\n", n, p, rep, order + 1,
                           cyclic ? "cyclic" : "contiguous", maximum, residual, difference);
                /* Selecciona entre resultados ordinarios y perfiles por proceso. */
                if (mode)
                {
                    /* Define values: campos del perfil local. */
                    double values[4] = {elapsed, prof.compute, prof.broadcast, (double)prof.updates};
                    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
                    double *all = !rank ? allocate((size_t)p * 4 * sizeof(double)) : NULL;
                    /* Reune la misma cantidad de campos por rango para publicar el perfil individual. */
                    MPI_Gather(values, 4, MPI_DOUBLE, all, 4, MPI_DOUBLE, 0, MPI_COMM_WORLD);
                    /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
                    if (!rank)
                        /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
                        for (int r = 0; r < p; ++r)
                            /* Publica resultados del caso en el formato CSV original; las preparaciones se filtran antes. */
                            printf("%d,%d,%d,%s,%d,%.12g,%.12g,%.12g,%.0f\n", n, p, rep,
                                   cyclic ? "cyclic" : "contiguous", r, all[4 * r], all[4 * r + 1],
                                   all[4 * r + 2], all[4 * r + 3]);
                    /* Libera all; free(NULL) es valido para buffers que este rango no reservo. */
                    free(all);
                }
            }
            /* Libera local; free(NULL) es valido para buffers que este rango no reservo. */
            free(local);
            /* Libera column; free(NULL) es valido para buffers que este rango no reservo. */
            free(column);
        }
    /* Define any: fallo combinado de todos los rangos. */
    int any;
    /* Entrega a todos el mayor estado/fallo; permite detectar si algun rango fallo. */
    MPI_Allreduce(&failed, &any, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    /* Libera original; free(NULL) es valido para buffers que este rango no reservo. */
    free(original);
    /* Libera packed; free(NULL) es valido para buffers que este rango no reservo. */
    free(packed);
    /* Libera factor; free(NULL) es valido para buffers que este rango no reservo. */
    free(factor);
    /* Libera ref; free(NULL) es valido para buffers que este rango no reservo. */
    free(ref);
    /* Libera work; free(NULL) es valido para buffers que este rango no reservo. */
    free(work);
    /* Libera counts; free(NULL) es valido para buffers que este rango no reservo. */
    free(counts);
    /* Libera displs; free(NULL) es valido para buffers que este rango no reservo. */
    free(displs);
    /* Propaga el estado acumulado: cero indica que no hubo fallos. */
    return any;
}
/* Punto de entrada: procesa argumentos, ejecuta el caso y devuelve el estado al sistema operativo. */
int main(int argc, char **argv)
{
    /* Inicializa MPI antes de usar comunicadores o colectivas. */
    MPI_Init(&argc, &argv);
    /* Define rank: rango actual; p: cantidad de procesos. */
    int rank, p;
    /* Consulta el identificador de este proceso dentro del comunicador. */
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    /* Consulta cuantos procesos participan en el comunicador. */
    MPI_Comm_size(MPI_COMM_WORLD, &p);
    /* Define failed: acumulador de fallos. */
    int failed = 0;
    /* Comprueba la forma de invocacion y los limites antes de usar los argumentos. */
    if (argc == 2 && !strcmp(argv[1], "--test"))
    {
        /* Define sizes: tamanos de las pruebas. */
        int sizes[] = {1, 2, 7, 16, 31};
        /* Recorre los casos pequenos definidos para verificar el programa. */
        for (int k = 0; k < 5; ++k)
            /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
            failed |= run_case(sizes[k], 1, 0, -1);
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        failed |= run_case(3, 1, 0, 1);
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        failed |= run_case(3, 1, 0, 2);
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        failed |= run_case(3, 1, 0, 3);
        /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
        if (!rank)
            /* Publica resultados del caso en el formato CSV original; las preparaciones se filtran antes. */
            printf("MPI P=%d: %s (ambos repartos, SPD, factor conocido y fallos colectivos)\n", p,
                   failed ? "FAIL" : "PASS");
    }
    /* Ruta alternativa cuando no se cumplio la condicion anterior. */
    else
    {
        /* Convierte el argumento de texto y conserva los limites/valores por defecto del programa. */
        int n = argc > 1 ? parse_bounded(argv[1], 46340) : -1;
        /* Convierte el argumento de texto y conserva los limites/valores por defecto del programa. */
        int reps = argc > 2 ? parse_bounded(argv[2], 1000) : 8;
        /* Define mode: selector de instrumentacion. */
        int mode = argc == 4 && !strcmp(argv[3], "profile");
        /* Rechaza dimensiones o cantidades de repeticiones incompatibles con el banco. */
        if (n < 1 || reps < 1 || argc > 4 || (argc == 4 && !mode))
        {
            /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
            if (!rank)
                /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
                fprintf(stderr, "Uso: compare_mpi N [repeticiones=8] [profile]\n");
            /* Cierra MPI; todos los rangos deben llegar a esta finalizacion. */
            MPI_Finalize();
            /* Informa uso incorrecto de argumentos. */
            return 2;
        }
        /* Define host: nombre del equipo. */
        char host[MPI_MAX_PROCESSOR_NAME];
        /* Define len: longitud del nombre del equipo. */
        int len;
        /* Consulta el nombre del equipo para registrar donde corre cada rango. */
        MPI_Get_processor_name(host, &len);
        /* Define mask: mascara de afinidad Linux. */
        cpu_set_t mask;
        /* Vacia la mascara antes de pedir al sistema la afinidad del proceso. */
        CPU_ZERO(&mask);
        /* Obtiene los CPUs permitidos para registrar el entorno; no modifica la afinidad. */
        sched_getaffinity(0, sizeof mask, &mask);
        /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
        fprintf(stderr, "rank=%d P=%d host=%s cpu=%d affinity_count=%d\n", rank, p, host, sched_getcpu(),
                CPU_COUNT(&mask));
        /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
        if (!rank)
            /* Publica los nombres de columnas CSV en el orden usado por las filas siguientes. */
            puts(mode ? "N,P,repetition,distribution,rank,total,compute,broadcast,updates"
                      : "N,P,repetition,order,distribution,seconds,relative_residual,factor_difference");
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        failed = run_case(n, reps, mode, 0);
    }
    /* Cierra MPI; todos los rangos deben llegar a esta finalizacion. */
    MPI_Finalize();
    /* Propaga el estado acumulado: cero indica que no hubo fallos. */
    return failed ? 1 : 0;
}
