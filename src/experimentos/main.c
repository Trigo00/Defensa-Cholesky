/* Primer banco secuencial: mide right-looking y valida el factor completo fuera del intervalo medido.
 * Lectura: ver docs/guia_codigo.md. Los comentarios explican instrucciones logicas;
 * las llaves y las continuaciones de una misma instruccion comparten explicacion.
 */
/* Habilita las declaraciones POSIX, incluido CLOCK_MONOTONIC. */
#define _POSIX_C_SOURCE 200809L
/* Declara generadores, kernels secuenciales y residuos. */
#include "cholesky.h"
/* Reutiliza conversiones y comparacion de factores para evitar codigo duplicado. */
#include "bench_utils.h"
/* Permite detectar errores de conversion o interrupciones de llamadas POSIX. */
#include <errno.h>
/* Macros PRIu64 para imprimir uint64_t de forma portable. */
#include <inttypes.h>
/* Funciones matematicas y controles de finitud: sqrt, fabs, isfinite, NAN e INFINITY. */
#include <math.h>
/* Entrada/salida de mensajes, archivos y registros CSV. */
#include <stdio.h>
/* Reserva/liberacion de memoria, conversion numerica y terminacion del proceso. */
#include <stdlib.h>
/* Copia y comparacion de buffers o argumentos. */
#include <string.h>
/* Reloj CLOCK_MONOTONIC y estructura timespec. */
#include <time.h>

/* Lee el reloj monotono y termina con error si el sistema no puede consultarlo. */
static double wall_time(void)
{
    /* Define now: estructura que recibe el reloj. */
    struct timespec now;
    /* Consulta el reloj monotono; sus diferencias dan tiempo transcurrido en segundos. */
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0)
    {
        /* Consulta el reloj monotono; sus diferencias dan tiempo transcurrido en segundos. */
        perror("clock_gettime");
        /* Termina el proceso con el codigo de error indicado. */
        exit(EXIT_FAILURE);
    }
    /* Convierte segundos y nanosegundos a una unica cantidad de segundos. */
    return (double)now.tv_sec + (double)now.tv_nsec * 1e-9;
}

/* Punto de entrada: procesa argumentos, ejecuta el caso y devuelve el estado al sistema operativo. */
int main(int argc, char **argv)
{
    /* Define requested_n: N solicitado; repetitions: cantidad de repeticiones utiles; seed: semilla reproducible. */
    uint64_t requested_n = 0, repetitions = 7, seed = 2026;
    /* Comprueba la forma de invocacion y los limites antes de usar los argumentos. */
    if (argc < 2 || argc > 4 || !parse_unsigned(argv[1], &requested_n) ||
        (argc >= 3 && !parse_unsigned(argv[2], &repetitions)) ||
        (argc == 4 && !parse_unsigned(argv[3], &seed)) || requested_n == 0 || repetitions == 0 ||
        repetitions > 10000 || requested_n > SIZE_MAX)
    {
        /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
        fprintf(stderr, "Uso: %s N [repeticiones=7] [semilla=2026]\n", argv[0]);
        /* Devuelve al sistema operativo el codigo de exito o fallo indicado. */
        return EXIT_FAILURE;
    }
    /* Define n: orden de la matriz. */
    size_t n = (size_t)requested_n;
    /* Evita que el calculo de elementos o bytes desborde size_t. */
    if (n > SIZE_MAX / n || n * n > SIZE_MAX / sizeof(double))
    {
        /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
        fprintf(stderr, "N excede el espacio de direcciones.\n");
        /* Devuelve al sistema operativo el codigo de exito o fallo indicado. */
        return EXIT_FAILURE;
    }
    /* Define bytes: bytes de una matriz densa. */
    size_t bytes = n * n * sizeof(double);
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    double *original = malloc(bytes), *factor = malloc(bytes);
    /* Comprueba punteros o dimensiones requeridos antes de acceder a memoria. */
    if (!original || !factor)
    {
        /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
        fprintf(stderr, "Memoria insuficiente para las dos matrices.\n");
        /* Libera original; free(NULL) es valido para buffers que este rango no reservo. */
        free(original);
        /* Libera factor; free(NULL) es valido para buffers que este rango no reservo. */
        free(factor);
        /* Devuelve al sistema operativo el codigo de exito o fallo indicado. */
        return EXIT_FAILURE;
    }
    /* Construye la matriz SPD reproducible con la semilla indicada. */
    generate_spd(original, n, seed);
    /* Rechaza una matriz generada que no sea simetrica y finita. */
    if (!symmetric_finite(original, n))
    {
        /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
        fprintf(stderr, "Generacion invalida.\n");
        /* Libera original; free(NULL) es valido para buffers que este rango no reservo. */
        free(original);
        /* Libera factor; free(NULL) es valido para buffers que este rango no reservo. */
        free(factor);
        /* Devuelve al sistema operativo el codigo de exito o fallo indicado. */
        return EXIT_FAILURE;
    }
    /* Publica los nombres de columnas CSV en el orden usado por las filas siguientes. */
    puts("N,repetition,seed,seconds,relative_residual");
    /* Incluye rep=0 como preparacion; rep=1..reps son las repeticiones utiles. */
    for (uint64_t rep = 0; rep <= repetitions; ++rep)
    {
        /* Copia los datos sin operaciones numericas; prepara una entrada o referencia independiente. */
        memcpy(factor, original, bytes);
        /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
        double start = wall_time();
        /* Ejecuta el kernel seleccionado y guarda el estado de la factorizacion. */
        int status = cholesky_right(factor, n);
        /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
        double elapsed = wall_time() - start;
        /* Reconstruye LL^T para medir el residuo completo; -1 indica que se omitio por tamano. */
        double residual = status == 0 ? relative_residual(original, factor, n) : INFINITY;
        /* Comprueba finitud y/o tolerancias para que NaN e infinito no pasen la validacion. */
        if (status != 0 || !isfinite(residual) || residual > 1e-12)
        {
            /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
            fprintf(stderr, "Validacion fallida: N=%zu rep=%" PRIu64 " r=%g\n", n, rep, residual);
            /* Libera original; free(NULL) es valido para buffers que este rango no reservo. */
            free(original);
            /* Libera factor; free(NULL) es valido para buffers que este rango no reservo. */
            free(factor);
            /* Devuelve al sistema operativo el codigo de exito o fallo indicado. */
            return EXIT_FAILURE;
        }
        /* Publica solo repeticiones utiles y respeta los selectores de prueba/perfil indicados. */
        if (rep != 0)
            /* Publica resultados del caso en el formato CSV original; las preparaciones se filtran antes. */
            printf("%zu,%" PRIu64 ",%" PRIu64 ",%.12g,%.12g\n", n, rep, seed, elapsed, residual);
    }
    /* Libera original; free(NULL) es valido para buffers que este rango no reservo. */
    free(original);
    /* Libera factor; free(NULL) es valido para buffers que este rango no reservo. */
    free(factor);
    /* Devuelve al sistema operativo el codigo de exito o fallo indicado. */
    return EXIT_SUCCESS;
}
