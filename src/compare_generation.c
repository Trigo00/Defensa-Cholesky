/* Compara generar y repartir desde rango 0 con generar directamente las columnas locales.
 * Lectura: ver docs/guia_codigo.md. Los comentarios explican instrucciones logicas;
 * las llaves y las continuaciones de una misma instruccion comparten explicacion.
 */
/* Declara generadores, kernels secuenciales y residuos. */
#include "cholesky.h"
/* Declara Layout, perfiles y kernels distribuidos; incluye la API MPI. */
#include "cholesky_mpi.h"
/* Entrada/salida de mensajes, archivos y registros CSV. */
#include <stdio.h>
/* Reserva/liberacion de memoria, conversion numerica y terminacion del proceso. */
#include <stdlib.h>
/* Copia y comparacion de buffers o argumentos. */
#include <string.h>
/* Funciones matematicas y controles de finitud: sqrt, fabs, isfinite, NAN e INFINITY. */
#include <math.h>
/* Reserva memoria; pide al menos un byte para admitir rangos sin columnas. */
static void *alloc(size_t bytes)
{
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    void *p = malloc(bytes ? bytes : 1);
    /* Detecta que no se pudo obtener el recurso solicitado; no se usa un puntero nulo. */
    if (!p)
        /* Aborta el comunicador para que otros rangos no queden esperando tras el fallo. */
        MPI_Abort(MPI_COMM_WORLD, 2);
    /* Entrega la memoria reservada al llamador, que debera liberarla. */
    return p;
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
    /* Define n: orden de la matriz; reps: cantidad de repeticiones utiles. */
    int n = argc > 1 ? atoi(argv[1]) : 512, reps = argc > 2 ? atoi(argv[2]) : 6;
    /* Rechaza dimensiones o cantidades de repeticiones incompatibles con el banco. */
    if (n < 1 || n > 20000 || reps < 2 || reps % 2)
    {
        /* Cierra MPI; todos los rangos deben llegar a esta finalizacion. */
        MPI_Finalize();
        /* Informa uso incorrecto de argumentos. */
        return 2;
    }
    /* Construye el mapa local con el reparto de columnas indicado. */
    Layout d = layout_create(n, 1, MPI_COMM_WORLD);
    /* Define bytes: bytes de una matriz densa. */
    size_t bytes = (size_t)n * n * sizeof(double);
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    double *full = rank ? NULL : alloc(bytes), *packed = rank ? NULL : alloc(bytes);
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    double *local = alloc((size_t)n * d.cols * sizeof(double));
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    double *expected = alloc((size_t)n * d.cols * sizeof(double));
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    int *counts = alloc(p * sizeof(int)), *displs = alloc(p * sizeof(int));
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
    /* Independent legacy reference, created outside measurements. */
    /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
    if (!rank)
    {
        /* Construye la matriz SPD reproducible con la semilla indicada. */
        generate_spd(full, n, 2026);
        /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
        for (int r = 0; r < p; ++r)
        {
            /* Define m: numero de columnas locales. */
            int m = counts[r] / n;
            /* Recorre los casos pequenos definidos para verificar el programa. */
            for (int i = 0; i < n; ++i)
                /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
                for (int c = 0; c < m; ++c)
                    /* Copia una entrada global al segmento por filas del propietario correspondiente. */
                    packed[displs[r] + i * m + c] = full[(size_t)i * n + r + c * p];
        }
    }
    /* Rango 0 reparte counts[r] doubles desde displs[r]; cada rango recibe sus columnas. */
    MPI_Scatterv(packed, counts, displs, MPI_DOUBLE, expected, n * d.cols, MPI_DOUBLE, 0, d.comm);
    /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
    if (!rank)
        /* Publica los nombres de columnas CSV en el orden usado por las filas siguientes. */
        puts("N,P,repetition,method,generation_s,distribution_s,total_s,identical");
    /* Define failed: acumulador de fallos. */
    int failed = 0;
    /* Incluye rep=0 como preparacion; rep=1..reps son las repeticiones utiles. */
    for (int rep = 0; rep <= reps; ++rep)
        /* Recorre las posiciones del orden de ejecucion de esta repeticion. */
        for (int pos = 0; pos < 2; ++pos)
        {
            /* Define distributed: selector de generacion distribuida. */
            int distributed = (rep + pos) % 2;
            /* Espera a todos los rangos antes de iniciar la medicion; no sincroniza sus relojes. */
            MPI_Barrier(d.comm);
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            double start = MPI_Wtime(), middle, end;
            /* Separa generacion local de generacion centralizada con reparto. */
            if (distributed)
            {
                /* Genera exactamente las columnas ciclicas propias con la semilla comun. */
                generate_spd_columns(local, n, 2026, rank, p);
                /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
                middle = MPI_Wtime();
                /* La generacion distribuida no tiene fase de reparto: su duracion es cero. */
                end = middle;
            }
            /* Ruta alternativa cuando no se cumplio la condicion anterior. */
            else
            {
                /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
                if (!rank)
                    /* Construye la matriz SPD reproducible con la semilla indicada. */
                    generate_spd(full, n, 2026);
                /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
                middle = MPI_Wtime();
                /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
                if (!rank)
                    /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
                    for (int r = 0; r < p; ++r)
                    {
                        /* Define m: numero de columnas locales. */
                        int m = counts[r] / n;
                        /* Recorre los casos pequenos definidos para verificar el programa. */
                        for (int i = 0; i < n; ++i)
                            /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
                            for (int c = 0; c < m; ++c)
                                /* Copia una entrada global al segmento por filas del propietario correspondiente. */
                                packed[displs[r] + i * m + c] = full[(size_t)i * n + r + c * p];
                    }
                /* Rango 0 reparte counts[r] doubles desde displs[r]; cada rango recibe sus columnas. */
                MPI_Scatterv(packed, counts, displs, MPI_DOUBLE, local, n * d.cols, MPI_DOUBLE, 0, d.comm);
                /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
                end = MPI_Wtime();
            }
            /* Define times: duraciones de fases; maximum: maximo entre rangos. */
            double times[3] = {middle - start, end - middle, end - start}, maximum[3];
            /* Obtiene en rango 0 el maximo de cada duracion local; no se suman esos maximos. */
            MPI_Reduce(times, maximum, 3, MPI_DOUBLE, MPI_MAX, 0, d.comm);
            /* Compara los bytes locales con la referencia; exige igualdad exacta, no aproximada. */
            int same = memcmp(local, expected, (size_t)n * d.cols * sizeof(double)) == 0, all;
            /* Con MPI_MIN, la igualdad global solo vale 1 si todos los rangos coinciden bit a bit. */
            MPI_Allreduce(&same, &all, 1, MPI_INT, MPI_MIN, d.comm);
            /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
            failed |= !all;
            /* Publica solo repeticiones utiles y respeta los selectores de prueba/perfil indicados. */
            if (rep && !rank)
                /* Publica resultados del caso en el formato CSV original; las preparaciones se filtran antes. */
                printf("%d,%d,%d,%s,%.12g,%.12g,%.12g,%d\n", n, p, rep,
                       distributed ? "distributed" : "centralized", maximum[0], maximum[1], maximum[2], all);
        }
    /* Libera full; free(NULL) es valido para buffers que este rango no reservo. */
    free(full);
    /* Libera packed; free(NULL) es valido para buffers que este rango no reservo. */
    free(packed);
    /* Libera local; free(NULL) es valido para buffers que este rango no reservo. */
    free(local);
    /* Libera expected; free(NULL) es valido para buffers que este rango no reservo. */
    free(expected);
    /* Libera counts; free(NULL) es valido para buffers que este rango no reservo. */
    free(counts);
    /* Libera displs; free(NULL) es valido para buffers que este rango no reservo. */
    free(displs);
    /* Cierra MPI; todos los rangos deben llegar a esta finalizacion. */
    MPI_Finalize();
    /* Propaga el estado acumulado: cero indica que no hubo fallos. */
    return failed;
}
