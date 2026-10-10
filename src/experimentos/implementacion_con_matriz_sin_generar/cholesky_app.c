#include "cholesky.h"
#include "cholesky_mpi.h"
#include "matrix_io.h"

#include <limits.h>
#include <math.h>
#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum
{
    APP_OK = 0,
    APP_USAGE = 2,
    APP_INPUT = 3,
    APP_DIMENSIONS = 4,
    APP_NONFINITE = 5,
    APP_NONSYMMETRIC = 6,
    APP_NOT_POSITIVE_DEFINITE = 7,
    APP_OUTPUT = 8,
    APP_MEMORY = 9
};

static void *checked_calloc(size_t count, size_t size)
{
    if (size && count > (size_t)-1 / size)
        return NULL;
    return calloc(count ? count : 1, size);
}

static void build_counts(int n, int processes, int *counts, int *offsets)
{
    int offset = 0;
    for (int r = 0; r < processes; ++r)
    {
        int columns = n / processes + (r < n % processes);
        counts[r] = n * columns;
        offsets[r] = offset;
        offset += counts[r];
    }
}

static void pack_cyclic(const double *full, double *packed, int n, int processes, const int *offsets)
{
    for (int r = 0; r < processes; ++r)
    {
        int columns = n / processes + (r < n % processes);
        for (int i = 0; i < n; ++i)
            for (int c = 0; c < columns; ++c)
                packed[offsets[r] + (size_t)i * columns + c] = full[(size_t)i * n + r + c * processes];
    }
}

static void unpack_cyclic(const double *packed, double *full, int n, int processes, const int *offsets)
{
    for (int r = 0; r < processes; ++r)
    {
        int columns = n / processes + (r < n % processes);
        for (int i = 0; i < n; ++i)
            for (int c = 0; c < columns; ++c)
                full[(size_t)i * n + r + c * processes] = packed[offsets[r] + (size_t)i * columns + c];
    }
}

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);
    int rank, processes;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &processes);

    int validate = argc == 4 && strcmp(argv[3], "--validate") == 0;
    int status = APP_OK;
    if (argc != 3 && !validate)
    {
        if (!rank)
            fprintf(stderr, "Uso: %s MATRIZ_A.txt FACTOR_L.txt [--validate]\n", argv[0]);
        status = APP_USAGE;
    }

    double *full = NULL, *original = NULL, *packed = NULL;
    size_t rows = 0, columns = 0;
    int n = 0;
    if (!rank && status == APP_OK)
    {
        MatrixIoStatus io = matrix_read_text(argv[1], &full, &rows, &columns);
        if (io != MATRIX_IO_OK)
        {
            fprintf(stderr, "Error de entrada: %s (%s).\n", matrix_io_message(io), argv[1]);
            status = io == MATRIX_IO_NONFINITE ? APP_NONFINITE : APP_INPUT;
        }
        else if (rows != columns || rows > INT_MAX || rows * columns > INT_MAX)
        {
            fprintf(
                stderr,
                "Error de dimensiones: la matriz debe ser cuadrada, no vacia y compatible con conteos MPI.\n");
            status = APP_DIMENSIONS;
        }
        else if (!symmetric_finite(full, rows))
        {
            fprintf(stderr,
                    "Error de entrada: la matriz debe ser simetrica (igualdad exacta A[i,j]=A[j,i]).\n");
            status = APP_NONSYMMETRIC;
        }
        else
        {
            n = (int)rows;
            if (validate)
            {
                original = checked_calloc(rows * columns, sizeof(*original));
                if (original)
                    memcpy(original, full, rows * columns * sizeof(*original));
                else
                    status = APP_MEMORY;
            }
        }
    }

    MPI_Bcast(&status, 1, MPI_INT, 0, MPI_COMM_WORLD);
    MPI_Bcast(&n, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (status != APP_OK)
    {
        free(full);
        free(original);
        MPI_Finalize();
        return status;
    }

    Layout layout = layout_create(n, 1, MPI_COMM_WORLD);
    double *local = checked_calloc((size_t)n * layout.cols, sizeof(*local));
    double *column = checked_calloc((size_t)n, sizeof(*column));
    double *local_column = checked_calloc((size_t)layout.cols, sizeof(*local_column));
    int *counts = checked_calloc((size_t)processes, sizeof(*counts));
    int *offsets = checked_calloc((size_t)processes, sizeof(*offsets));
    int allocation_failed = !local || !column || !local_column || !counts || !offsets;
    MPI_Allreduce(&allocation_failed, &status, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    status = status ? APP_MEMORY : APP_OK;

    if (!rank && status == APP_OK)
    {
        packed = checked_calloc((size_t)n * n, sizeof(*packed));
        if (!packed)
            status = APP_MEMORY;
    }
    MPI_Bcast(&status, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (status == APP_OK)
    {
        build_counts(n, processes, counts, offsets);
        if (!rank)
            pack_cyclic(full, packed, n, processes, offsets);
        MPI_Scatterv(packed, counts, offsets, MPI_DOUBLE, local, n * layout.cols, MPI_DOUBLE, 0,
                     MPI_COMM_WORLD);

        /* Kernel validado: right-looking, reparto ciclico 1D y vector local. */
        int local_failure = cholesky_mpi_local(local, column, local_column, &layout, NULL) != 0;
        int any_failure = 0;
        MPI_Allreduce(&local_failure, &any_failure, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
        if (any_failure)
            status = APP_NOT_POSITIVE_DEFINITE;
        else
        {
            MPI_Gatherv(local, n * layout.cols, MPI_DOUBLE, packed, counts, offsets, MPI_DOUBLE, 0,
                        MPI_COMM_WORLD);
            if (!rank)
            {
                unpack_cyclic(packed, full, n, processes, offsets);
                if (validate)
                {
                    double residual = relative_residual(original, full, (size_t)n);
                    fprintf(stderr, "Validacion: residuo relativo Frobenius = %.12g\n", residual);
                    if (!isfinite(residual) || residual > 1e-12)
                        status = APP_NOT_POSITIVE_DEFINITE;
                }
                if (status == APP_OK)
                {
                    MatrixIoStatus io = matrix_write_text(argv[2], full, (size_t)n, (size_t)n, 1);
                    if (io != MATRIX_IO_OK)
                    {
                        fprintf(stderr, "Error de salida: %s (%s).\n", matrix_io_message(io), argv[2]);
                        status = APP_OUTPUT;
                    }
                }
            }
        }
    }

    MPI_Bcast(&status, 1, MPI_INT, 0, MPI_COMM_WORLD);
    if (!rank && status == APP_NOT_POSITIVE_DEFINITE)
        fprintf(stderr,
                "Fallo de Cholesky: la matriz no es definida positiva o produjo un pivote invalido.\n");
    if (!rank && status == APP_MEMORY)
        fprintf(stderr, "Error: memoria insuficiente para preparar la matriz distribuida.\n");

    free(full);
    free(original);
    free(packed);
    free(local);
    free(column);
    free(local_column);
    free(counts);
    free(offsets);
    MPI_Finalize();
    return status;
}
