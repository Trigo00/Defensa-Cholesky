#ifndef CHOLESKY_H
#define CHOLESKY_H

#include <stddef.h>
#include <stdint.h>

void generate_spd(double *a, size_t n, uint64_t seed);
void generate_spd_columns(double *a, size_t n, uint64_t seed, int rank, int processes);
void generate_spd_selected(double *a, size_t n, uint64_t seed, const int *columns, size_t count);
int symmetric_finite(const double *a, size_t n);
int cholesky_right(double *a, size_t n);
int cholesky_left(double *a, size_t n);
int cholesky_right_buffered(double *a, size_t n, double *column);
double relative_residual(const double *original, const double *factor, size_t n);
double projected_residual(const double *a, const double *l, size_t n, unsigned probes, uint64_t seed, long double *workspace);
#endif
