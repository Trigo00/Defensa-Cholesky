/* Compara left, right y right con vector; recorre las seis permutaciones para equilibrar el orden.
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

/* Lee segundos del reloj monotono: sirve para diferencias de tiempo, no para fecha y hora. */
static double now(void)
{
    /* Define t: instante local o estructura del reloj. */
    struct timespec t;
    /* Consulta el reloj monotono; sus diferencias dan tiempo transcurrido en segundos. */
    if (clock_gettime(CLOCK_MONOTONIC, &t))
    {
        /* Consulta el reloj monotono; sus diferencias dan tiempo transcurrido en segundos. */
        perror("clock_gettime");
        /* Termina el proceso con el codigo de error indicado. */
        exit(1);
    }
    /* Convierte segundos y nanosegundos a una unica cantidad de segundos. */
    return (double)t.tv_sec + (double)t.tv_nsec * 1e-9;
}

/* Punto de entrada: procesa argumentos, ejecuta el caso y devuelve el estado al sistema operativo. */
int main(int argc, char **argv)
{
    /* Define input: N leido como entero sin signo; reps: cantidad de repeticiones utiles; seed: semilla reproducible. */
    uint64_t input = 0, reps = 12, seed = 2026;
    /* Comprueba la forma de invocacion y los limites antes de usar los argumentos. */
    if (argc < 2 || argc > 4 || !parse_unsigned(argv[1], &input) ||
        (argc > 2 && !parse_unsigned(argv[2], &reps)) || (argc > 3 && !parse_unsigned(argv[3], &seed)) ||
        !input || input > SIZE_MAX || !reps || reps > 10000 || reps % 6 != 0)
    {
        /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
        fprintf(stderr, "Uso: %s N [repeticiones=12, multiplo de 6] [semilla=2026]\n", argv[0]);
        /* Termina este caso con un codigo de fallo. */
        return 1;
    }
    /* Define n: orden de la matriz. */
    size_t n = (size_t)input;
    /* Evita que el calculo de elementos o bytes desborde size_t. */
    if (n > SIZE_MAX / n || n * n > SIZE_MAX / sizeof(double))
        /* Termina este caso con un codigo de fallo. */
        return 1;
    /* Define bytes: bytes de una matriz densa. */
    size_t bytes = n * n * sizeof(double);
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    double *a = malloc(bytes), *factor = malloc(bytes), *column = malloc(n * sizeof(double));
    /* Comprueba punteros o dimensiones requeridos antes de acceder a memoria. */
    if (!a || !factor || !column)
    {
        /* Libera a; free(NULL) es valido para buffers que este rango no reservo. */
        free(a);
        /* Libera factor; free(NULL) es valido para buffers que este rango no reservo. */
        free(factor);
        /* Libera column; free(NULL) es valido para buffers que este rango no reservo. */
        free(column);
        /* Termina este caso con un codigo de fallo. */
        return 1;
    }
    /* Construye la matriz SPD reproducible con la semilla indicada. */
    generate_spd(a, n, seed);
    /* Rechaza una matriz generada que no sea simetrica y finita. */
    if (!symmetric_finite(a, n))
    {
        /* Libera a; free(NULL) es valido para buffers que este rango no reservo. */
        free(a);
        /* Libera factor; free(NULL) es valido para buffers que este rango no reservo. */
        free(factor);
        /* Libera column; free(NULL) es valido para buffers que este rango no reservo. */
        free(column);
        /* Termina este caso con un codigo de fallo. */
        return 1;
    }
    /* Define names: etiquetas que se escriben en CSV. */
    const char *names[] = {"left", "right", "right_buffered"};
    /* Define ordenes balanceados para no favorecer siempre a la misma variante. */
    const int orders[6][3] = {{0, 1, 2}, {0, 2, 1}, {1, 0, 2}, {1, 2, 0}, {2, 0, 1}, {2, 1, 0}};
    /* Publica los nombres de columnas CSV en el orden usado por las filas siguientes. */
    puts("N,repetition,order,variant,seed,seconds,relative_residual");
    /* Incluye rep=0 como preparacion; rep=1..reps son las repeticiones utiles. */
    for (uint64_t rep = 0; rep <= reps; ++rep)
    {
        /* Define permutation: permutacion de esta repeticion. */
        size_t permutation = rep == 0 ? 0 : (size_t)((rep - 1) % 6);
        /* Recorre las posiciones del orden de ejecucion de esta repeticion. */
        for (int order = 0; order < 3; ++order)
        {
            /* Define variant: variante elegida. */
            int variant = orders[permutation][order];
            /* Copia los datos sin operaciones numericas; prepara una entrada o referencia independiente. */
            memcpy(factor, a, bytes);
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            double start = now();
            /* Define status: codigo devuelto por la factorizacion. */
            int status;
            /* Selecciona la implementacion asociada a esta variante. */
            if (variant == 0)
                /* Ejecuta el kernel elegido y conserva su codigo de retorno. */
                status = cholesky_left(factor, n);
            /* Evalua esta alternativa solo si no se cumplio la condicion anterior. */
            else if (variant == 1)
                /* Ejecuta el kernel elegido y conserva su codigo de retorno. */
                status = cholesky_right(factor, n);
            /* Ruta alternativa cuando no se cumplio la condicion anterior. */
            else
                /* Ejecuta el kernel elegido y conserva su codigo de retorno. */
                status = cholesky_right_buffered(factor, n, column);
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            double elapsed = now() - start;
            /* Reconstruye LL^T para medir el residuo completo; -1 indica que se omitio por tamano. */
            double residual = status == 0 ? relative_residual(a, factor, n) : INFINITY;
            /* Comprueba finitud y/o tolerancias para que NaN e infinito no pasen la validacion. */
            if (status || !isfinite(residual) || residual > 1e-12)
            {
                /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
                fprintf(stderr, "Fallo: %s N=%zu rep=%" PRIu64 " r=%g\n", names[variant], n, rep, residual);
                /* Libera a; free(NULL) es valido para buffers que este rango no reservo. */
                free(a);
                /* Libera factor; free(NULL) es valido para buffers que este rango no reservo. */
                free(factor);
                /* Libera column; free(NULL) es valido para buffers que este rango no reservo. */
                free(column);
                /* Termina este caso con un codigo de fallo. */
                return 1;
            }
            /* Publica solo repeticiones utiles y respeta los selectores de prueba/perfil indicados. */
            if (rep)
                /* Publica resultados del caso en el formato CSV original; las preparaciones se filtran antes. */
                printf("%zu,%" PRIu64 ",%d,%s,%" PRIu64 ",%.12g,%.12g\n", n, rep, order + 1, names[variant],
                       seed, elapsed, residual);
        }
    }
    /* Libera a; free(NULL) es valido para buffers que este rango no reservo. */
    free(a);
    /* Libera factor; free(NULL) es valido para buffers que este rango no reservo. */
    free(factor);
    /* Libera column; free(NULL) es valido para buffers que este rango no reservo. */
    free(column);
    /* Devuelve exito: la operacion termino sin detectar fallos. */
    return 0;
}
