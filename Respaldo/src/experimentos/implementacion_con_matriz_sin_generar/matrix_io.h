#ifndef MATRIX_IO_H
#define MATRIX_IO_H

#include <stddef.h>

typedef enum
{
    MATRIX_IO_OK = 0,
    MATRIX_IO_OPEN,
    MATRIX_IO_FORMAT,
    MATRIX_IO_DIMENSIONS,
    MATRIX_IO_NONFINITE,
    MATRIX_IO_MEMORY,
    MATRIX_IO_WRITE
} MatrixIoStatus;

/* Formato: dos enteros (filas columnas), seguidos por filas*columnas doubles. */
MatrixIoStatus matrix_read_text(const char *path, double **values, size_t *rows, size_t *columns);

/* Escribe una matriz densa por filas. Si lower_only!=0, reemplaza por cero
 * el triangulo superior; esto permite guardar L sin datos residuales de A. */
MatrixIoStatus matrix_write_text(const char *path, const double *values, size_t rows, size_t columns,
                                 int lower_only);

const char *matrix_io_message(MatrixIoStatus status);

#endif
