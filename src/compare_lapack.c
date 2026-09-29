/* Compara el kernel propio con LAPACK/OpenBLAS forzado a un hilo, con matrices y validacion comunes.
 * Lectura: ver docs/guia_codigo.md. Los comentarios explican instrucciones logicas;
 * las llaves y las continuaciones de una misma instruccion comparten explicacion.
 */
/* Habilita las declaraciones POSIX, incluido CLOCK_MONOTONIC. */
#define _POSIX_C_SOURCE 200809L
/* Declara generadores, kernels secuenciales y residuos. */
#include "cholesky.h"
/* Reutiliza conversiones y comparacion de factores para evitar codigo duplicado. */
#include "bench_utils.h"
/* Interfaz C de LAPACK y rutina de Cholesky DPOTRF. */
#include <lapacke.h>
/* API de OpenBLAS para fijar y consultar la cantidad de hilos. */
#include <cblas.h>
/* Entrada/salida de mensajes, archivos y registros CSV. */
#include <stdio.h>
/* Reserva/liberacion de memoria, conversion numerica y terminacion del proceso. */
#include <stdlib.h>
/* Copia y comparacion de buffers o argumentos. */
#include <string.h>
/* Reloj CLOCK_MONOTONIC y estructura timespec. */
#include <time.h>
/* Funciones matematicas y controles de finitud: sqrt, fabs, isfinite, NAN e INFINITY. */
#include <math.h>
/* Permite detectar errores de conversion o interrupciones de llamadas POSIX. */
#include <errno.h>
/* Lee segundos del reloj monotono: sirve para diferencias de tiempo, no para fecha y hora. */
static double now(void)
{
    /* Define t: instante local o estructura del reloj. */
    struct timespec t;
    /* Consulta el reloj monotono; sus diferencias dan tiempo transcurrido en segundos. */
    clock_gettime(CLOCK_MONOTONIC, &t);
    /* Convierte segundos y nanosegundos a una unica cantidad de segundos. */
    return t.tv_sec + 1e-9 * t.tv_nsec;
}
/* Reserva memoria; pide al menos un byte para admitir rangos sin columnas. */
static void *alloc(size_t n)
{
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    void *p = malloc(n ? n : 1);
    /* Detecta que no se pudo obtener el recurso solicitado; no se usa un puntero nulo. */
    if (!p)
    {
        /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
        fputs("allocation failed\n", stderr);
        /* Termina el proceso con el codigo de error indicado. */
        exit(3);
    }
    /* Entrega la memoria reservada al llamador, que debera liberarla. */
    return p;
}
/* Native column-major upper triangle aliases row-major lower triangle.
 * Symmetric A has identical storage after transpose; U^T is our L.
 * _work avoids LAPACKE row-major transpose and optional NaN scan. */
/* Usa DPOTRF column-major superior: el mismo almacenamiento corresponde al L inferior row-major. */
static int lapack(double *a, int n)
{
    /* Factoriza por la API de trabajo, evitando la conversion row-major de LAPACKE. */
    return LAPACKE_dpotrf_work(LAPACK_COL_MAJOR, 'U', n, a, n);
}
/* Ejecuta un caso del banco, conserva las preparaciones y devuelve si hubo algun fallo. */
static int run(int n, int reps, int test)
{
    /* Define bytes: bytes de una matriz densa. */
    size_t bytes = (size_t)n * n * sizeof(double);
    /* Define failed: acumulador de fallos. */
    int failed = 0;
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    double *original = alloc(bytes), *reference = alloc(bytes), *w = alloc(n * sizeof(double));
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    long double *check = alloc(2 * (size_t)n * sizeof(long double));
    /* Construye la matriz SPD reproducible con la semilla indicada. */
    generate_spd(original, n, 2026);
    /* Copia los datos sin operaciones numericas; prepara una entrada o referencia independiente. */
    memcpy(reference, original, bytes);
    /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
    failed |= cholesky_right_buffered(reference, n, w) != 0;
    /* Incluye rep=0 como preparacion; rep=1..reps son las repeticiones utiles. */
    for (int rep = 0; rep <= reps; ++rep)
        /* Recorre las posiciones del orden de ejecucion de esta repeticion. */
        for (int pos = 0; pos < 2; ++pos)
        {
            /* Define method: metodo elegido. */
            int method = (pos + (rep ? rep - 1 : 0)) % 2;
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            double start = now();
            /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
            double *a = alloc(bytes), *workspace = alloc(n * sizeof(double));
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            double t1 = now();
            /* Construye la matriz SPD reproducible con la semilla indicada. */
            generate_spd(a, n, 2026);
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            double t2 = now();
            /* Ejecuta el kernel seleccionado y guarda el estado de la factorizacion. */
            int status = method ? lapack(a, n) : cholesky_right_buffered(a, n, workspace);
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            double end = now();
            /* Mide el residuo proyectado con ocho vectores y semilla 91827, fuera del kernel. */
            double residual = projected_residual(original, a, n, 8, 91827, check), diff = 0;
            /* Compara el triangulo inferior con la referencia mediante la utilidad compartida. */
            diff = factor_difference(a, reference, n);
            /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
            failed |= status != 0 || !isfinite(residual) || residual > 1e-12 || diff > 1e-12;
            /* Selecciona el control de prueba: matriz conocida, entrada invalida o validacion completa. */
            if (test)
            {
                /* Reconstruye LL^T para medir el residuo completo; -1 indica que se omitio por tamano. */
                double r = relative_residual(original, a, n);
                /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                failed |= !isfinite(r) || r > 1e-12;
            }
            /* Publica solo repeticiones utiles y respeta los selectores de prueba/perfil indicados. */
            if (rep && !test)
                /* Publica resultados del caso en el formato CSV original; las preparaciones se filtran antes. */
                printf("%d,%d,%d,%s,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g\n", n, rep, pos + 1,
                       method ? "lapack" : "own", t1 - start, t2 - t1, end - t2, end - start, residual, diff);
            /* Libera a; free(NULL) es valido para buffers que este rango no reservo. */
            free(a);
            /* Libera workspace; free(NULL) es valido para buffers que este rango no reservo. */
            free(workspace);
        }
    /* Libera original; free(NULL) es valido para buffers que este rango no reservo. */
    free(original);
    /* Libera reference; free(NULL) es valido para buffers que este rango no reservo. */
    free(reference);
    /* Libera w; free(NULL) es valido para buffers que este rango no reservo. */
    free(w);
    /* Libera check; free(NULL) es valido para buffers que este rango no reservo. */
    free(check);
    /* Propaga el estado acumulado: cero indica que no hubo fallos. */
    return failed;
}
/* Punto de entrada: procesa argumentos, ejecuta el caso y devuelve el estado al sistema operativo. */
int main(int argc, char **argv)
{
    /* Fija un unico hilo en OpenBLAS antes de ejecutar cualquier comparacion. */
    openblas_set_num_threads(1);
    /* Escribe diagnostico en stderr para no mezclarlo con las filas CSV de stdout. */
    fprintf(stderr, "OpenBLAS threads=%d config=%s\n", openblas_get_num_threads(), openblas_get_config());
    /* Verifica por API que OpenBLAS realmente usara un hilo; no se supone por una variable de entorno. */
    if (openblas_get_num_threads() != 1)
        /* Informa un fallo de recursos o del entorno de ejecucion. */
        return 3;
    /* Comprueba la forma de invocacion y los limites antes de usar los argumentos. */
    if (argc == 2 && !strcmp(argv[1], "--test"))
    {
        /* Define failed: acumulador de fallos. */
        int failed = 0;
        /* Define ns: tamanos de las pruebas. */
        int ns[] = {1, 2, 3, 7, 31, 65, 128};
        /* Recorre los casos pequenos definidos para verificar el programa. */
        for (int i = 0; i < 7; ++i)
            /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
            failed |= run(ns[i], 0, 1);
        /* Define known: matriz con factor conocido. */
        double known[] = {4, 12, -16, 12, 37, -43, -16, -43, 98};
        /* Define expected: datos o factor esperado por la prueba. */
        double expected[] = {2, 0, 0, 6, 1, 0, -8, 5, 3};
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        failed |= lapack(known, 3) != 0;
        /* Recorre los casos pequenos definidos para verificar el programa. */
        for (int i = 0; i < 3; ++i)
            /* Recorre exclusivamente el triangulo inferior, que contiene el factor L. */
            for (int j = 0; j <= i; ++j)
                /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                failed |= fabs(known[i * 3 + j] - expected[i * 3 + j]) > 1e-12;
        /* Define bad: fallo de la ejecucion actual. */
        double bad[] = {1, 2, 2, 1};
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        failed |= lapack(bad, 2) <= 0;
        /* Publica el resultado de las pruebas de este banco. */
        printf("LAPACK tests: %s\n", failed ? "FAIL" : "PASS");
        /* Propaga el estado acumulado: cero indica que no hubo fallos. */
        return failed;
    }
    /* Convierte el argumento de texto y conserva los limites/valores por defecto del programa. */
    int n = argc > 1 ? parse_bounded(argv[1], 20000) : -1,
        /* Lee repeticiones opcionales y conserva el valor por defecto de este banco. */
        reps = argc > 2 ? parse_bounded(argv[2], 20000) : 6;
    /* Rechaza dimensiones o cantidades de repeticiones incompatibles con el banco. */
    if (n < 1 || reps < 2 || reps > 28 || reps % 2 || argc > 3)
        /* Informa uso incorrecto de argumentos. */
        return 2;
    /* Publica los nombres de columnas CSV en el orden usado por las filas siguientes. */
    puts(
        "N,repetition,order,method,allocation_s,generation_s,factor_s,total_s,projected_residual,factor_difference");
    /* Ejecuta el banco ordinario y devuelve si sus comprobaciones fallaron. */
    return run(n, reps, 0);
}
