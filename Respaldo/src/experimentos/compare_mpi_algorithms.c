/* Compara right y left MPI sobre la misma distribucion ciclica; profile separa medidas instrumentadas.
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
    void *p = malloc(bytes ? bytes : 1);
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
/* Copia las columnas del rango indicado al segmento que Scatterv le enviara. */
static void pack_for_rank(const double *full, double *packed, int offset, Layout d, int rank)
{
    /* Define q: columnas base por rango; rem: columnas sobrantes. */
    const int q = d.n / d.p, rem = d.n % d.p;
    /* Describe al propietario indicado usando una copia local de Layout. */
    d.rank = rank;
    /* Calcula cuantas columnas corresponden a ese propietario. */
    d.cols = q + (rank < rem);
    /* En reparto ciclico, el rango empieza en su propia columna global. */
    d.first = rank; /* cíclico */
    /* Recorre las filas del intervalo indicado. */
    for (int i = 0; i < d.n; ++i)
        /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
        for (int c = 0; c < d.cols; ++c)
            /* Copia una entrada global al segmento por filas del propietario correspondiente. */
            packed[offset + i * d.cols + c] = full[(size_t)i * d.n + layout_global(&d, c)];
}
/* Coloca las columnas recibidas de un rango en sus posiciones globales. */
static void unpack_rank(double *full, const double *packed, int offset, Layout d, int rank)
{
    /* Define q: columnas base por rango; rem: columnas sobrantes. */
    const int q = d.n / d.p, rem = d.n % d.p;
    /* Describe al propietario indicado usando una copia local de Layout. */
    d.rank = rank;
    /* Calcula cuantas columnas corresponden a ese propietario. */
    d.cols = q + (rank < rem);
    /* En reparto ciclico, el rango empieza en su propia columna global. */
    d.first = rank;
    /* Recorre las filas del intervalo indicado. */
    for (int i = 0; i < d.n; ++i)
        /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
        for (int c = 0; c < d.cols; ++c)
            /* Devuelve una entrada del segmento recibido a su fila y columna global. */
            full[(size_t)i * d.n + layout_global(&d, c)] = packed[offset + i * d.cols + c];
}

/* Prepara, mide y verifica un caso; las variantes y repeticiones siguen el orden del banco original. */
static int run_case(int n, int reps, int profile_mode, int test)
{
    /* Define rank: rango actual; p: cantidad de procesos. */
    int rank, p;
    /* Consulta el identificador de este proceso dentro del comunicador. */
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    /* Consulta cuantos procesos participan en el comunicador. */
    MPI_Comm_size(MPI_COMM_WORLD, &p);
    /* Define bytes: bytes de una matriz densa. */
    const size_t bytes = (size_t)n * n * sizeof(double);
    /* Define original: matriz A sin factorizar; packed: buffer agrupado por propietario; factor: matriz que recibira L; reference: factor secuencial de referencia; seqwork: vector del kernel secuencial. */
    double *original = NULL, *packed = NULL, *factor = NULL, *reference = NULL, *seqwork = NULL;
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
        reference = allocate(bytes);
        /* Reserva vector del kernel secuencial; el llamador liberara el buffer al terminar. */
        seqwork = allocate((size_t)n * sizeof(double));
        /* Construye la matriz SPD reproducible con la semilla indicada. */
        generate_spd(original, (size_t)n, 2026);
        /* Selecciona el control de prueba: matriz conocida, entrada invalida o validacion completa. */
        if (test == 1)
        {
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
        memcpy(reference, original, bytes);
        /* Selecciona el control de prueba: matriz conocida, entrada invalida o validacion completa. */
        if (test < 2 && cholesky_right_buffered(reference, (size_t)n, seqwork))
            /* Aborta el comunicador para que otros rangos no queden esperando tras el fallo. */
            MPI_Abort(MPI_COMM_WORLD, 4);
    }
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    int *counts = allocate((size_t)p * sizeof(int));
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    int *displs = allocate((size_t)p * sizeof(int));
    /* Construye el mapa local con el reparto de columnas indicado. */
    Layout d = layout_create(n, 1, MPI_COMM_WORLD);
    /* Define offset: inicio del siguiente segmento empaquetado. */
    int offset = 0;
    /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
    for (int r = 0; r < p; ++r)
    {
        /* Calcula cuantos elementos de matriz corresponden a este rango. */
        counts[r] = n * (n / p + (r < n % p));
        /* Guarda el inicio del segmento de este rango. */
        displs[r] = offset;
        /* Avanza al segmento del siguiente propietario en el buffer empaquetado. */
        offset += counts[r];
    }
    /* Define failed: acumulador de fallos. */
    int failed = 0;
    /* Incluye rep=0 como preparacion; rep=1..reps son las repeticiones utiles. */
    for (int rep = 0; rep <= reps; ++rep)
        /* Recorre las posiciones del orden de ejecucion de esta repeticion. */
        for (int position = 0; position < 2; ++position)
        {
            /* Define algorithm: algoritmo elegido. */
            const int algorithm = (rep + position) % 2; /* 0 right, 1 left; orden alternado */
            /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
            if (!rank)
                /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
                for (int r = 0; r < p; ++r)
                    /* Prepara el segmento de columnas que se enviara a este propietario. */
                    pack_for_rank(original, packed, displs[r], d, r);
            /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
            double *local = allocate((size_t)n * d.cols * sizeof(double));
            /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
            double *column = allocate((size_t)n * sizeof(double));
            /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
            double *workspace = allocate((size_t)(d.cols ? d.cols : 1) * sizeof(double));
            /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
            double *partial = allocate((size_t)n * sizeof(double));
            /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
            double *reduced = allocate((size_t)n * sizeof(double));
            /* Rango 0 reparte counts[r] doubles desde displs[r]; cada rango recibe sus columnas. */
            MPI_Scatterv(packed, counts, displs, MPI_DOUBLE, local, n * d.cols, MPI_DOUBLE, 0, d.comm);
            /* Espera a todos los rangos antes de iniciar la medicion; no sincroniza sus relojes. */
            MPI_Barrier(d.comm);
            /* Define rp: perfil right-looking. */
            Profile rp = {0};
            /* Define lp: perfil left-looking. */
            LeftProfile lp = {0};
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            double start = MPI_Wtime();
            /* Define status: codigo devuelto por la factorizacion. */
            int status =
                algorithm
                    /* Rama left-looking: reduce productos parciales y completa la columna en su propietario. */
                    ? cholesky_left_mpi(local, partial, reduced, &d, profile_mode ? &lp : NULL)
                    /* Rama right-looking con vector local; el perfil se activa solo si se solicito. */
                    : cholesky_mpi_local(local, column, workspace, &d, profile_mode ? &rp : NULL);
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            double elapsed = MPI_Wtime() - start, maximum = 0.0;
            /* Obtiene en rango 0 el maximo de cada duracion local; no se suman esos maximos. */
            MPI_Reduce(&elapsed, &maximum, 1, MPI_DOUBLE, MPI_MAX, 0, d.comm);
            /* Define minimum_status: menor estado entre rangos; maximum_status: mayor estado entre rangos. */
            int minimum_status, maximum_status;
            /* Entrega a todos el menor estado para comprobar acuerdo colectivo. */
            MPI_Allreduce(&status, &minimum_status, 1, MPI_INT, MPI_MIN, d.comm);
            /* Entrega a todos el mayor estado/fallo; permite detectar si algun rango fallo. */
            MPI_Allreduce(&status, &maximum_status, 1, MPI_INT, MPI_MAX, d.comm);
            /* Selecciona el control de prueba: matriz conocida, entrada invalida o validacion completa. */
            if (minimum_status != maximum_status || status != (test >= 2 ? -1 : 0))
                /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                failed = 1;
            /* Reune cantidades distintas de columnas en rango 0, en los segmentos indicados. */
            MPI_Gatherv(local, n * d.cols, MPI_DOUBLE, packed, counts, displs, MPI_DOUBLE, 0, d.comm);
            /* Define residual: residuo numerico; difference: diferencia maxima frente al factor de referencia. */
            double residual = 0.0, difference = 0.0;
            /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
            if (!rank && test < 2)
            {
                /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
                for (int r = 0; r < p; ++r)
                    /* Reconstruye las posiciones globales de las columnas recibidas. */
                    unpack_rank(factor, packed, displs[r], d, r);
                /* Calcula el error del factor fuera del intervalo de factorizacion medido. */
                residual = relative_residual(original, factor, (size_t)n);
                /* Compara el triangulo inferior con la referencia mediante la utilidad compartida. */
                difference = factor_difference(factor, reference, n);
                /* Comprueba finitud y/o tolerancias para que NaN e infinito no pasen la validacion. */
                if (!isfinite(residual) || residual > 1e-12 || difference > 1e-12)
                    /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                    failed = 1;
            }
            /* Publica solo repeticiones utiles y respeta los selectores de prueba/perfil indicados. */
            if (rep > 0 && !test && !profile_mode && !rank)
                /* Publica resultados del caso en el formato CSV original; las preparaciones se filtran antes. */
                printf("%d,%d,%d,%d,%s,%.12g,%.12g,%.12g\n", n, p, rep, position + 1,
                       algorithm ? "left" : "right", maximum, residual, difference);
            /* Publica solo repeticiones utiles y respeta los selectores de prueba/perfil indicados. */
            if (rep > 0 && profile_mode)
            {
                /* Define values: campos del perfil local. */
                double values[5] = {
                    elapsed, algorithm ? lp.compute : rp.compute, algorithm ? lp.reduce : 0.0,
                    /* Selecciona el tiempo de difusion del algoritmo que se acaba de ejecutar. */
                    algorithm ? lp.broadcast : rp.broadcast,
                    /* Exporta el contador de trabajo del algoritmo como un campo numerico del perfil. */
                    (double)(algorithm ? lp.products : rp.updates)};
                /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
                double *all = !rank ? allocate((size_t)p * 5 * sizeof(double)) : NULL;
                /* Reune la misma cantidad de campos por rango para publicar el perfil individual. */
                MPI_Gather(values, 5, MPI_DOUBLE, all, 5, MPI_DOUBLE, 0, d.comm);
                /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
                if (!rank)
                {
                    /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
                    for (int r = 0; r < p; ++r)
                        /* Publica resultados del caso en el formato CSV original; las preparaciones se filtran antes. */
                        printf("%d,%d,%d,%s,%d,%.12g,%.12g,%.12g,%.12g,%.0f\n", n, p, rep,
                               algorithm ? "left" : "right", r, all[5 * r], all[5 * r + 1], all[5 * r + 2],
                               all[5 * r + 3], all[5 * r + 4]);
                    /* Libera all; free(NULL) es valido para buffers que este rango no reservo. */
                    free(all);
                }
            }
            /* Libera local; free(NULL) es valido para buffers que este rango no reservo. */
            free(local);
            /* Libera column; free(NULL) es valido para buffers que este rango no reservo. */
            free(column);
            /* Libera workspace; free(NULL) es valido para buffers que este rango no reservo. */
            free(workspace);
            /* Libera partial; free(NULL) es valido para buffers que este rango no reservo. */
            free(partial);
            /* Libera reduced; free(NULL) es valido para buffers que este rango no reservo. */
            free(reduced);
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
    /* Libera reference; free(NULL) es valido para buffers que este rango no reservo. */
    free(reference);
    /* Libera seqwork; free(NULL) es valido para buffers que este rango no reservo. */
    free(seqwork);
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
        int sizes[] = {1, 2, 3, 7, 16, 31};
        /* Recorre los casos pequenos definidos para verificar el programa. */
        for (int i = 0; i < 6; ++i)
            /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
            failed |= run_case(sizes[i], 1, 0, -1);
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        failed |= run_case(3, 1, 0, 1);
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        failed |= run_case(3, 1, 0, 2);
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        failed |= run_case(3, 1, 0, 3);
        /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
        if (!rank)
            /* Publica el resultado de las pruebas de este banco. */
            printf("MPI left/right P=%d: %s\n", p, failed ? "FAIL" : "PASS");
    }
    /* Ruta alternativa cuando no se cumplio la condicion anterior. */
    else
    {
        /* Convierte el argumento de texto y conserva los limites/valores por defecto del programa. */
        int n = argc > 1 ? parse_bounded(argv[1], 46340) : -1;
        /* Convierte el argumento de texto y conserva los limites/valores por defecto del programa. */
        int reps = argc > 2 ? parse_bounded(argv[2], 1000) : 8;
        /* Define profile_mode: selector de instrumentacion. */
        int profile_mode = argc == 4 && !strcmp(argv[3], "profile");
        /* Rechaza dimensiones o cantidades de repeticiones incompatibles con el banco. */
        if (n < 1 || reps < 1 || reps % 2 || argc > 4 || (argc == 4 && !profile_mode))
        {
            /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
            if (!rank)
                /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
                fprintf(stderr, "Uso: compare_mpi_algorithms N [repeticiones pares=8] [profile]\n");
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
            puts(profile_mode ? "N,P,repetition,algorithm,rank,total,compute,reduce,broadcast,work"
                              : "N,P,repetition,order,algorithm,seconds,relative_residual,factor_difference");
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        failed = run_case(n, reps, profile_mode, 0);
    }
    /* Cierra MPI; todos los rangos deben llegar a esta finalizacion. */
    MPI_Finalize();
    /* Propaga el estado acumulado: cero indica que no hubo fallos. */
    return failed ? 1 : 0;
}
