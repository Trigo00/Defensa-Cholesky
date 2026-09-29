#define _POSIX_C_SOURCE 200809L
#include "cholesky.h"
#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static int parse_unsigned(const char *text, uint64_t *value) {
    if (!*text) return 0;
    for (const char *p = text; *p; ++p) if (*p < '0' || *p > '9') return 0;
    char *end = NULL;
    errno = 0;
    unsigned long long parsed = strtoull(text, &end, 10);
    if (errno || *end || parsed > UINT64_MAX) return 0;
    *value = (uint64_t)parsed;
    return 1;
}

static double wall_time(void) {
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
        perror("clock_gettime");
        exit(EXIT_FAILURE);
    }
    return (double)now.tv_sec + (double)now.tv_nsec * 1e-9;
}

int main(int argc, char **argv) {
    uint64_t requested_n = 0, repetitions = 7, seed = 2026;
    if (argc < 2 || argc > 4 || !parse_unsigned(argv[1], &requested_n)
        || (argc >= 3 && !parse_unsigned(argv[2], &repetitions))
        || (argc == 4 && !parse_unsigned(argv[3], &seed))
        || requested_n == 0 || repetitions == 0 || repetitions > 10000
        || requested_n > SIZE_MAX) {
        fprintf(stderr, "Uso: %s N [repeticiones=7] [semilla=2026]\n", argv[0]);
        return EXIT_FAILURE;
    }
    size_t n = (size_t)requested_n;
    if (n > SIZE_MAX / n || n*n > SIZE_MAX / sizeof(double)) {
        fprintf(stderr, "N excede el espacio de direcciones.\n");
        return EXIT_FAILURE;
    }
    size_t bytes = n*n*sizeof(double);
    double *original = malloc(bytes), *factor = malloc(bytes);
    if (!original || !factor) {
        fprintf(stderr, "Memoria insuficiente para las dos matrices.\n");
        free(original); free(factor);
        return EXIT_FAILURE;
    }
    generate_spd(original, n, seed);
    if (!symmetric_finite(original, n)) {
        fprintf(stderr, "Generacion invalida.\n");
        free(original); free(factor);
        return EXIT_FAILURE;
    }
    puts("N,repetition,seed,seconds,relative_residual");
    for (uint64_t rep = 0; rep <= repetitions; ++rep) {
        /* Copiar la entrada SIEMPRE; la factorizacion trabaja in-place. */
        memcpy(factor, original, bytes);
        double start = wall_time();
        int status = cholesky_right(factor, n);
        double elapsed = wall_time() - start;
        /* La validacion cubica queda completamente fuera del cronometro. */
        double residual = status == 0 ? relative_residual(original, factor, n) : INFINITY;
        if (status != 0 || !isfinite(residual) || residual > 1e-12) {
            fprintf(stderr, "Validacion fallida: N=%zu rep=%" PRIu64 " r=%g\n", n, rep, residual);
            free(original); free(factor);
            return EXIT_FAILURE;
        }
        /* rep=0 es el calentamiento, no una observacion medida. */
        if (rep != 0)
            printf("%zu,%" PRIu64 ",%" PRIu64 ",%.12g,%.12g\n", n, rep, seed, elapsed, residual);
    }
    free(original); free(factor);
    return EXIT_SUCCESS;
}
