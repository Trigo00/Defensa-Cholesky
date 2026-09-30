#include "matrix_io.h"

#include <ctype.h>
#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

MatrixIoStatus matrix_read_text(const char *path, double **values, size_t *rows, size_t *columns)
{
    if (!path || !values || !rows || !columns)
        return MATRIX_IO_FORMAT;
    *values = NULL;
    *rows = *columns = 0;

    FILE *file = fopen(path, "r");
    if (!file)
        return MATRIX_IO_OPEN;

    size_t r, c;
    if (fscanf(file, "%zu %zu", &r, &c) != 2)
    {
        fclose(file);
        return MATRIX_IO_FORMAT;
    }
    if (r == 0 || c == 0 || c > SIZE_MAX / r || r * c > SIZE_MAX / sizeof(double))
    {
        fclose(file);
        return MATRIX_IO_DIMENSIONS;
    }

    size_t cells = r * c;
    double *data = malloc(cells * sizeof(*data));
    if (!data)
    {
        fclose(file);
        return MATRIX_IO_MEMORY;
    }

    MatrixIoStatus status = MATRIX_IO_OK;
    for (size_t i = 0; i < cells; ++i)
    {
        if (fscanf(file, "%lf", &data[i]) != 1)
        {
            status = MATRIX_IO_FORMAT;
            break;
        }
        if (!isfinite(data[i]))
        {
            status = MATRIX_IO_NONFINITE;
            break;
        }
    }

    if (status == MATRIX_IO_OK)
    {
        int ch;
        do
            ch = fgetc(file);
        while (ch != EOF && isspace((unsigned char)ch));
        if (ch != EOF)
            status = MATRIX_IO_FORMAT;
    }

    if (ferror(file) && status == MATRIX_IO_OK)
        status = MATRIX_IO_FORMAT;
    fclose(file);
    if (status != MATRIX_IO_OK)
    {
        free(data);
        return status;
    }

    *values = data;
    *rows = r;
    *columns = c;
    return MATRIX_IO_OK;
}

MatrixIoStatus matrix_write_text(const char *path, const double *values, size_t rows, size_t columns,
                                 int lower_only)
{
    if (!path || !values || rows == 0 || columns == 0)
        return MATRIX_IO_WRITE;
    FILE *file = fopen(path, "w");
    if (!file)
        return MATRIX_IO_OPEN;

    int failed = fprintf(file, "%zu %zu\n", rows, columns) < 0;
    for (size_t i = 0; i < rows && !failed; ++i)
    {
        for (size_t j = 0; j < columns; ++j)
        {
            double value = lower_only && j > i ? 0.0 : values[i * columns + j];
            if (fprintf(file, j + 1 == columns ? "%.17g" : "%.17g ", value) < 0)
            {
                failed = 1;
                break;
            }
        }
        if (!failed && fputc('\n', file) == EOF)
            failed = 1;
    }
    if (fclose(file) != 0)
        failed = 1;
    return failed ? MATRIX_IO_WRITE : MATRIX_IO_OK;
}

const char *matrix_io_message(MatrixIoStatus status)
{
    switch (status)
    {
    case MATRIX_IO_OK:
        return "sin error";
    case MATRIX_IO_OPEN:
        return "no se pudo abrir el archivo";
    case MATRIX_IO_FORMAT:
        return "formato invalido o cantidad incorrecta de valores";
    case MATRIX_IO_DIMENSIONS:
        return "dimensiones invalidas o demasiado grandes";
    case MATRIX_IO_NONFINITE:
        return "la matriz contiene NaN o infinito";
    case MATRIX_IO_MEMORY:
        return "no hay memoria suficiente";
    case MATRIX_IO_WRITE:
        return "fallo al escribir el archivo";
    }
    return "error desconocido";
}
