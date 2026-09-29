#ifndef CHOLESKY_H
#define CHOLESKY_H

#include <stddef.h>
#include <stdint.h>

/* Matrices densas por filas: A[i,j] = a[i*n+j]. */
void generate_spd(double *a, size_t n, uint64_t seed);
/* Genera columnas ciclicas, almacenadas por filas, identicas a generate_spd.
 * Requiere n>0 y 0<=rank*/
void generate_spd_columns(double *a, size_t n, uint64_t seed, int rank, int processes);
/* Columnas arbitrarias crecientes; indices validos y sin duplicados. */
void generate_spd_selected(double *a, size_t n, uint64_t seed, const int *columns, size_t count);
int symmetric_finite(const double *a, size_t n);

/* A debe ser simetrica y finita. Sobrescribe su triangulo inferior con L.
 * El triangulo superior NO pertenece a L y queda sin modificar.
 * Devuelve 0 al completar o -1 por entrada/pivote invalido.
 * Tras un fallo, la matriz puede haber sido modificada parcialmente. */
int cholesky_right(double *a, size_t n);
/* Mismo contrato de almacenamiento y validez que cholesky_right. */
int cholesky_left(double *a, size_t n);
/* Misma factorizacion right-looking. column dispone de n doubles y no
 * comparte memoria con a. Se reserva antes de llamar; el empaquetado
 * de cada columna ocurre dentro de la factorizacion. */
int cholesky_right_buffered(double *a, size_t n, double *column);

/* Interpreta solo el triangulo inferior de factor como L. Fuera del timer. */
double relative_residual(const double *original, const double *factor, size_t n);
/* Maximo ||Ax-L(L^T x)||_2 / ||Ax||_2 sobre probes vectores de signos.
 * O(probes*n*n); prueba reproducible, NO residuo Frobenius ni certificado.
 * workspace: 2*n long double; separado de las matrices. */
double projected_residual(const double *a, const double *l, size_t n, unsigned probes, uint64_t seed,
                          long double *workspace);

#endif
