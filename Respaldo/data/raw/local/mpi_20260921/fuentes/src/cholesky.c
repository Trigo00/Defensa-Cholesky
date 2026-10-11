#include "cholesky.h"
#include <math.h>

/* Generador entero de estado fijo; no depende de rand() de cada biblioteca. */
static uint64_t next_random(uint64_t *state) {
    *state += UINT64_C(0x9e3779b97f4a7c15);
    uint64_t x = *state;
    x = (x ^ (x >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    x = (x ^ (x >> 27)) * UINT64_C(0x94d049bb133111eb);
    return x ^ (x >> 31);
}

void generate_spd(double *a, size_t n, uint64_t seed) {
    uint64_t state = seed;
    for (size_t i = 0; i < n; ++i) {
        a[i*n+i] = 0.0;
        for (size_t j = i+1; j < n; ++j) {
            /* 53 bits, convertidos al intervalo [-1,1). */
            double value = 2.0 * (double)(next_random(&state) >> 11) * 0x1.0p-53 - 1.0;
            a[i*n+j] = value;
            a[j*n+i] = value;
        }
    }
    for (size_t i = 0; i < n; ++i) {
        double sum = 0.0;
        for (size_t j = 0; j < n; ++j)
            if (i != j) sum += fabs(a[i*n+j]);
        a[i*n+i] = sum + 1.0;
    }
}

int symmetric_finite(const double *a, size_t n) {
    if (!a || n == 0) return 0;
    for (size_t i = 0; i < n; ++i)
        for (size_t j = 0; j < n; ++j)
            if (!isfinite(a[i*n+j]) || a[i*n+j] != a[j*n+i]) return 0;
    return 1;
}

int cholesky_left(double *a, size_t n) {
    if (!a || n == 0) return -1;
    for (size_t j = 0; j < n; ++j) {
        /* Reunir las contribuciones anteriores cuando se necesita j. */
        double sum = 0.0;
        for (size_t k = 0; k < j; ++k) sum += a[j*n+k] * a[j*n+k];
        double pivot = a[j*n+j] - sum;
        if (!isfinite(pivot) || pivot <= 0.0) return -1;
        a[j*n+j] = sqrt(pivot);
        for (size_t i = j+1; i < n; ++i) {
            sum = 0.0;
            for (size_t k = 0; k < j; ++k) sum += a[i*n+k] * a[j*n+k];
            a[i*n+j] = (a[i*n+j] - sum) / a[j*n+j];
        }
    }
    return 0;
}

int cholesky_right(double *a, size_t n) {
    if (!a || n == 0) return -1;
    for (size_t j = 0; j < n; ++j) {
        /* 1. Pivote: las columnas anteriores ya actualizaron a[j,j]. */
        double pivot = a[j*n+j];
        if (!isfinite(pivot) || pivot <= 0.0) return -1;
        a[j*n+j] = sqrt(pivot);

        /* 2. Completar la columna. Cada i escribe un elemento distinto. */
        for (size_t i = j+1; i < n; ++i)
            a[i*n+j] /= a[j*n+j];

        /* 3. Right-looking: actualizar la region inferior derecha.
         * Con la columna j lista, cada par (i,k) es una actualizacion
         * independiente dentro de ESTA iteracion. j sigue siendo ordenado. */
        for (size_t i = j+1; i < n; ++i) {
            double lij = a[i*n+j];
            for (size_t k = j+1; k <= i; ++k)
                a[i*n+k] -= lij * a[k*n+j];
        }
    }
    return 0;
}

int cholesky_right_buffered(double *a, size_t n, double *column) {
    if (!a || !column || n == 0) return -1;
    for (size_t j = 0; j < n; ++j) {
        double pivot = a[j*n+j];
        if (!isfinite(pivot) || pivot <= 0.0) return -1;
        a[j*n+j] = sqrt(pivot);
        for (size_t i = j+1; i < n; ++i)
            a[i*n+j] /= a[j*n+j];

        /* Copia O(n) por columna, incluida en el tiempo del algoritmo.
         * El vector solo necesita las entradas debajo del pivote. */
        for (size_t i = j+1; i < n; ++i)
            column[i] = a[i*n+j];

        /* Mismo orden (j,i,k), mismos destinos y mismas operaciones.
         * Solo cambia la lectura interna: column[k] es contigua. */
        for (size_t i = j+1; i < n; ++i) {
            double lij = a[i*n+j];
            for (size_t k = j+1; k <= i; ++k)
                a[i*n+k] -= lij * column[k];
        }
    }
    return 0;
}

double relative_residual(const double *original, const double *factor, size_t n) {
    if (!original || !factor || n == 0) return INFINITY;
    long double squared_error = 0.0L, squared_norm = 0.0L;
    for (size_t i = 0; i < n; ++i) {
        for (size_t j = 0; j < n; ++j) {
            size_t last = i < j ? i : j;
            long double reconstructed = 0.0L;
            for (size_t k = 0; k <= last; ++k)
                reconstructed += (long double)factor[i*n+k] * factor[j*n+k];
            long double value = original[i*n+j];
            long double error = value - reconstructed;
            if (!isfinite(error) || !isfinite(value)) return INFINITY;
            squared_error += error * error;
            squared_norm += value * value;
        }
    }
    if (squared_norm == 0.0L) return INFINITY;
    double result = (double)sqrtl(squared_error / squared_norm);
    return isfinite(result) ? result : INFINITY;
}
