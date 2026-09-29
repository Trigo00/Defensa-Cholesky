/* Compara el flujo centralizado, distribuido y secuencial incluyendo reserva y generacion.
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

/* Reserva memoria; pide al menos un byte para admitir rangos sin columnas. */
static void *alloc(size_t bytes)
{
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    void *p = malloc(bytes ? bytes : 1);
    /* Detecta que no se pudo obtener el recurso solicitado; no se usa un puntero nulo. */
    if (!p)
        /* Aborta el comunicador para que otros rangos no queden esperando tras el fallo. */
        MPI_Abort(MPI_COMM_WORLD, 3);
    /* Entrega la memoria reservada al llamador, que debera liberarla. */
    return p;
}
/* Convierte entre matriz por filas y bloques por rango; gather elige la direccion de la copia. */
static void rearrange(double *full, double *packed, int n, int p, int gather)
{
    /* Define offset: inicio del siguiente segmento empaquetado. */
    size_t offset = 0;
    /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
    for (int r = 0; r < p; ++r)
    {
        /* Define m: numero de columnas locales. */
        int m = n / p + (r < n % p);
        /* Recorre las filas del intervalo indicado. */
        for (int i = 0; i < n; ++i)
            /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
            for (int c = 0; c < m; ++c)
            {
                /* Calcula dos indices: a en la matriz global y b en el segmento empaquetado. */
                size_t a = (size_t)i * n + r + c * p, b = offset + (size_t)i * m + c;
                /* El selector indica si reconstruir la matriz global o empaquetarla. */
                if (gather)
                    /* Devuelve una entrada del segmento recibido a su fila y columna global. */
                    full[a] = packed[b];
                /* Ruta alternativa cuando no se cumplio la condicion anterior. */
                else
                    /* Copia una entrada global al segmento por filas del propietario correspondiente. */
                    packed[b] = full[a];
            }
        /* Avanza al segmento del siguiente propietario en el buffer empaquetado. */
        offset += (size_t)n * m;
    }
}
/* Ejecuta un caso del banco, conserva las preparaciones y devuelve si hubo algun fallo. */
static int run(int n, int reps)
{
    /* Construye el mapa local con el reparto de columnas indicado. */
    Layout d = layout_create(n, 1, MPI_COMM_WORLD);
    /* Define bytes: bytes de una matriz densa. */
    size_t bytes = (size_t)n * n * sizeof(double);
    /* Define original: matriz A sin factorizar; reference: factor secuencial de referencia. */
    double *original = NULL, *reference = NULL;
    /* Define checkwork: espacio para la validacion proyectada. */
    long double *checkwork = NULL;
    /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
    if (!d.rank)
    {
        /* Reserva matriz A sin factorizar; el llamador liberara el buffer al terminar. */
        original = alloc(bytes);
        /* Reserva factor secuencial de referencia; el llamador liberara el buffer al terminar. */
        reference = alloc(bytes);
        /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
        double *w = alloc(n * sizeof(double));
        /* Reserva espacio para la validacion proyectada; el llamador liberara el buffer al terminar. */
        checkwork = alloc(2 * (size_t)n * sizeof(long double));
        /* Construye la matriz SPD reproducible con la semilla indicada. */
        generate_spd(original, n, 2026);
        /* Copia los datos sin operaciones numericas; prepara una entrada o referencia independiente. */
        memcpy(reference, original, bytes);
        /* Construye el factor de referencia y detecta un fallo antes de medir las variantes. */
        if (cholesky_right_buffered(reference, n, w))
            /* Aborta el comunicador para que otros rangos no queden esperando tras el fallo. */
            MPI_Abort(d.comm, 4);
        /* Libera w; free(NULL) es valido para buffers que este rango no reservo. */
        free(w);
    }
    /* Define ordenes balanceados para no favorecer siempre a la misma variante. */
    const int orders[6][3] = {{0, 1, 2}, {0, 2, 1}, {1, 0, 2}, {1, 2, 0}, {2, 0, 1}, {2, 1, 0}};
    /* Define names: etiquetas que se escriben en CSV. */
    const char *names[] = {"centralized", "distributed", "sequential"};
    /* Define failed: acumulador de fallos. */
    int failed = 0;
    /* Incluye rep=0 como preparacion; rep=1..reps son las repeticiones utiles. */
    for (int rep = 0; rep <= reps; ++rep)
        /* Recorre las posiciones del orden de ejecucion de esta repeticion. */
        for (int pos = 0; pos < 3; ++pos)
        {
            /* Define method: metodo elegido. */
            int method = rep ? orders[(rep - 1) % 6][pos] : pos;
            /* Define full: matriz global del rango 0; packed: buffer agrupado por propietario; local: columnas propias almacenadas por filas; column: columna global que se difunde; work: vector auxiliar del kernel. */
            double *full = NULL, *packed = NULL, *local = NULL, *column = NULL, *work = NULL;
            /* Define counts: cantidades de elementos por rango; displs: desplazamientos de los segmentos; status: codigo devuelto por la factorizacion. */
            int *counts = NULL, *displs = NULL, status = 0;
            /* Espera a todos los rangos antes de iniciar la medicion; no sincroniza sus relojes. */
            MPI_Barrier(d.comm);
            /* Define t: instante local o estructura del reloj. */
            double t[6];
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t[0] = MPI_Wtime();
            /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
            if (!d.rank)
                /* Reserva matriz global del rango 0; el llamador liberara el buffer al terminar. */
                full = alloc(bytes);
            /* Elige la ruta centralizada, distribuida o secuencial del banco. */
            if (method != 2)
            {
                /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
                if (!d.rank)
                    /* Reserva buffer agrupado por propietario; el llamador liberara el buffer al terminar. */
                    packed = alloc(bytes);
                /* Reserva columnas propias almacenadas por filas; el llamador liberara el buffer al terminar. */
                local = alloc((size_t)n * d.cols * sizeof(double));
                /* Reserva columna global que se difunde; el llamador liberara el buffer al terminar. */
                column = alloc(n * sizeof(double));
                /* Reserva vector auxiliar del kernel; el llamador liberara el buffer al terminar. */
                work = alloc((size_t)(d.cols ? d.cols : 1) * sizeof(double));
                /* Reserva cantidades de elementos por rango; el llamador liberara el buffer al terminar. */
                counts = alloc(d.p * sizeof(int));
                /* Reserva desplazamientos de los segmentos; el llamador liberara el buffer al terminar. */
                displs = alloc(d.p * sizeof(int));
                /* Define offset: inicio del siguiente segmento empaquetado. */
                int offset = 0;
                /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
                for (int r = 0; r < d.p; ++r)
                {
                    /* Calcula cuantos elementos de matriz corresponden a este rango. */
                    counts[r] = n * (n / d.p + (r < n % d.p));
                    /* Guarda el inicio del segmento de este rango. */
                    displs[r] = offset;
                    /* Avanza al segmento del siguiente propietario en el buffer empaquetado. */
                    offset += counts[r];
                }
            }
            /* Evalua esta alternativa solo si no se cumplio la condicion anterior. */
            else if (!d.rank)
                /* Reserva vector auxiliar del kernel; el llamador liberara el buffer al terminar. */
                work = alloc(n * sizeof(double));
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t[1] = MPI_Wtime();
            /* Elige la ruta centralizada, distribuida o secuencial del banco. */
            if (method == 1)
                /* Genera exactamente las columnas ciclicas propias con la semilla comun. */
                generate_spd_columns(local, n, 2026, d.rank, d.p);
            /* Evalua esta alternativa solo si no se cumplio la condicion anterior. */
            else if (!d.rank)
                /* Construye la matriz SPD reproducible con la semilla indicada. */
                generate_spd(full, n, 2026);
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t[2] = MPI_Wtime();
            /* Elige la ruta centralizada, distribuida o secuencial del banco. */
            if (method == 0)
            {
                /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
                if (!d.rank)
                    /* Agrupa las columnas de A por propietario antes del reparto. */
                    rearrange(full, packed, n, d.p, 0);
                /* Rango 0 reparte counts[r] doubles desde displs[r]; cada rango recibe sus columnas. */
                MPI_Scatterv(packed, counts, displs, MPI_DOUBLE, local, n * d.cols, MPI_DOUBLE, 0, d.comm);
            }
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t[3] = MPI_Wtime();
            /* Elige la ruta centralizada, distribuida o secuencial del banco. */
            if (method == 2)
            {
                /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
                if (!d.rank)
                    /* Ejecuta el kernel elegido y conserva su codigo de retorno. */
                    status = cholesky_right_buffered(full, n, work);
            }
            /* Ruta alternativa cuando no se cumplio la condicion anterior. */
            else
                /* Ejecuta el kernel elegido y conserva su codigo de retorno. */
                status = cholesky_mpi_local(local, column, work, &d, NULL);
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t[4] = MPI_Wtime();
            /* Elige la ruta centralizada, distribuida o secuencial del banco. */
            if (method != 2)
            {
                /* Reune cantidades distintas de columnas en rango 0, en los segmentos indicados. */
                MPI_Gatherv(local, n * d.cols, MPI_DOUBLE, packed, counts, displs, MPI_DOUBLE, 0, d.comm);
                /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
                if (!d.rank)
                    /* Reconstruye el factor global desde los segmentos. */
                    rearrange(full, packed, n, d.p, 1);
            }
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t[5] = MPI_Wtime();
            /* Rank 0 owns the requested output. Its consecutive phases add exactly
             * to its total. Also record max local duration, without summing maxima. */
            /* Define elapsed: duracion local medida; max_elapsed: mayor duracion local. */
            double elapsed = t[5] - t[0], max_elapsed = 0;
            /* Obtiene en rango 0 el maximo de cada duracion local; no se suman esos maximos. */
            MPI_Reduce(&elapsed, &max_elapsed, 1, MPI_DOUBLE, MPI_MAX, 0, d.comm);
            /* Define bad: fallo de la ejecucion actual; any: fallo combinado de todos los rangos. */
            int bad = (status != 0), any;
            /* Entrega a todos el mayor estado/fallo; permite detectar si algun rango fallo. */
            MPI_Allreduce(&bad, &any, 1, MPI_INT, MPI_MAX, d.comm);
            /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
            failed |= any;
            /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
            if (!d.rank)
            {
                /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
                double v0 = MPI_Wtime();
                /* Mide el residuo proyectado con ocho vectores y semilla 91827, fuera del kernel. */
                double residual = projected_residual(original, full, n, 8, 91827, checkwork), diff = 0;
                /* Compara el triangulo inferior con la referencia mediante la utilidad compartida. */
                diff = factor_difference(full, reference, n);
                /* Reconstruye LL^T para medir el residuo completo; -1 indica que se omitio por tamano. */
                double exact = n <= 128 ? relative_residual(original, full, n) : -1;
                /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                failed |= !isfinite(residual) || residual > 1e-12 || diff > 1e-12 ||
                          /* Incluye la tolerancia del residuo completo solo cuando se calculo. */
                          (n <= 128 && (!isfinite(exact) || exact > 1e-12));
                /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
                double validation = MPI_Wtime() - v0;
                /* Publica solo repeticiones utiles y respeta los selectores de prueba/perfil indicados. */
                if (rep)
                    /* Publica resultados del caso en el formato CSV original; las preparaciones se filtran antes. */
                    printf(
                        "%d,%d,%d,%d,%s,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g\n",
                        n, d.p, rep, pos + 1, names[method], t[1] - t[0], t[2] - t[1], t[3] - t[2],
                        t[4] - t[3], t[5] - t[4], elapsed, max_elapsed, validation, residual, diff, exact);
            }
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
            /* Libera displs; free(NULL) es valido para buffers que este rango no reservo. */
            free(displs);
        }
    /* Define any: fallo combinado de todos los rangos. */
    int any;
    /* Entrega a todos el mayor estado/fallo; permite detectar si algun rango fallo. */
    MPI_Allreduce(&failed, &any, 1, MPI_INT, MPI_MAX, d.comm);
    /* Libera original; free(NULL) es valido para buffers que este rango no reservo. */
    free(original);
    /* Libera reference; free(NULL) es valido para buffers que este rango no reservo. */
    free(reference);
    /* Libera checkwork; free(NULL) es valido para buffers que este rango no reservo. */
    free(checkwork);
    /* Propaga el estado acumulado: cero indica que no hubo fallos. */
    return any;
}
/* Punto de entrada: procesa argumentos, ejecuta el caso y devuelve el estado al sistema operativo. */
int main(int argc, char **argv)
{
    /* Inicializa MPI antes de usar comunicadores o colectivas. */
    MPI_Init(&argc, &argv);
    /* Define rank: rango actual. */
    int rank;
    /* Consulta el identificador de este proceso dentro del comunicador. */
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
    if (!rank)
        /* Publica los nombres de columnas CSV en el orden usado por las filas siguientes. */
        puts(
            "N,P,repetition,order,method,allocation_s,generation_s,distribution_s,factor_s,gather_s,total_s,max_local_s,validation_s,projected_residual,factor_difference,exact_residual");
    /* Define result: estado que devolvera el programa. */
    int result = 0;
    /* Comprueba la forma de invocacion y los limites antes de usar los argumentos. */
    if (argc == 2 && !strcmp(argv[1], "--test"))
    {
        /* Define sizes: tamanos de las pruebas. */
        int sizes[] = {1, 2, 3, 7, 31, 128};
        /* Recorre los casos pequenos definidos para verificar el programa. */
        for (int i = 0; i < 6; ++i)
            /* Acumula el resultado del caso de prueba en el estado final. */
            result |= run(sizes[i], 1);
    }
    /* Ruta alternativa cuando no se cumplio la condicion anterior. */
    else
    {
        /* Convierte el argumento de texto y conserva los limites/valores por defecto del programa. */
        int n = argc > 1 ? parse_bounded(argv[1], 20000) : -1,
            /* Lee repeticiones opcionales y conserva el valor por defecto de este banco. */
            reps = argc > 2 ? parse_bounded(argv[2], 120) : 6;
        /* Rechaza dimensiones o cantidades de repeticiones incompatibles con el banco. */
        if (n < 1 || reps < 1 || reps % 6 || argc > 3)
        {
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
        /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
        fprintf(stderr, "rank=%d host=%s cpu=%d\n", rank, host, sched_getcpu());
        /* Ejecuta el caso solicitado y conserva su resultado. */
        result = run(n, reps);
    }
    /* Cierra MPI; todos los rangos deben llegar a esta finalizacion. */
    MPI_Finalize();
    /* Propaga el estado acumulado: cero indica que no hubo fallos. */
    return result;
}
