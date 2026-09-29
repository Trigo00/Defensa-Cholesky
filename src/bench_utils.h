#ifndef BENCH_UTILS_H
#define BENCH_UTILS_H

#include <stddef.h>
#include <stdint.h>

/* Implementaciones comentadas en bench_utils.c. */
int parse_unsigned(const char *text, uint64_t *value);
int parse_bounded(const char *text, int maximum);
double factor_difference(const double *factor, const double *reference, size_t n);

#endif
