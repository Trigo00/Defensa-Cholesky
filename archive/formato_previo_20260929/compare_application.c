#define _GNU_SOURCE
#include "cholesky.h"
#include "cholesky_mpi.h"
#include <errno.h>
#include <math.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void *alloc(size_t bytes)
{
    void *p = malloc(bytes ? bytes : 1);
    if (!p)
        MPI_Abort(MPI_COMM_WORLD, 3);
    return p;
}
static int number(const char *s, int max)
{
    char *end;
    errno = 0;
    long x = strtol(s, &end, 10);
    return errno || !*s || *end || x < 1 || x > max ? -1 : (int)x;
}
static void rearrange(double *full, double *packed, int n, int p, int gather)
{
    size_t offset = 0;
    for (int r = 0; r < p; ++r)
    {
        int m = n / p + (r < n % p);
        for (int i = 0; i < n; ++i)
            for (int c = 0; c < m; ++c)
            {
                size_t a = (size_t)i * n + r + c * p, b = offset + (size_t)i * m + c;
                if (gather)
                    full[a] = packed[b];
                else
                    packed[b] = full[a];
            }
        offset += (size_t)n * m;
    }
}
static int run(int n, int reps)
{
    Layout d = layout_create(n, 1, MPI_COMM_WORLD);
    size_t bytes = (size_t)n * n * sizeof(double);
    double *original = NULL, *reference = NULL;
    long double *checkwork = NULL;
    if (!d.rank)
    {
        original = alloc(bytes);
        reference = alloc(bytes);
        double *w = alloc(n * sizeof(double));
        checkwork = alloc(2 * (size_t)n * sizeof(long double));
        generate_spd(original, n, 2026);
        memcpy(reference, original, bytes);
        if (cholesky_right_buffered(reference, n, w))
            MPI_Abort(d.comm, 4);
        free(w);
    }
    const int orders[6][3] = {{0, 1, 2}, {0, 2, 1}, {1, 0, 2}, {1, 2, 0}, {2, 0, 1}, {2, 1, 0}};
    const char *names[] = {"centralized", "distributed", "sequential"};
    int failed = 0;
    for (int rep = 0; rep <= reps; ++rep)
        for (int pos = 0; pos < 3; ++pos)
        {
            int method = rep ? orders[(rep - 1) % 6][pos] : pos;
            double *full = NULL, *packed = NULL, *local = NULL, *column = NULL, *work = NULL;
            int *counts = NULL, *displs = NULL, status = 0;
            MPI_Barrier(d.comm);
            double t[6];
            t[0] = MPI_Wtime();
            if (!d.rank)
                full = alloc(bytes);
            if (method != 2)
            {
                if (!d.rank)
                    packed = alloc(bytes);
                local = alloc((size_t)n * d.cols * sizeof(double));
                column = alloc(n * sizeof(double));
                work = alloc((size_t)(d.cols ? d.cols : 1) * sizeof(double));
                counts = alloc(d.p * sizeof(int));
                displs = alloc(d.p * sizeof(int));
                int offset = 0;
                for (int r = 0; r < d.p; ++r)
                {
                    counts[r] = n * (n / d.p + (r < n % d.p));
                    displs[r] = offset;
                    offset += counts[r];
                }
            }
            else if (!d.rank)
                work = alloc(n * sizeof(double));
            t[1] = MPI_Wtime();
            if (method == 1)
                generate_spd_columns(local, n, 2026, d.rank, d.p);
            else if (!d.rank)
                generate_spd(full, n, 2026);
            t[2] = MPI_Wtime();
            if (method == 0)
            {
                if (!d.rank)
                    rearrange(full, packed, n, d.p, 0);
                MPI_Scatterv(packed, counts, displs, MPI_DOUBLE, local, n * d.cols, MPI_DOUBLE, 0, d.comm);
            }
            t[3] = MPI_Wtime();
            if (method == 2)
            {
                if (!d.rank)
                    status = cholesky_right_buffered(full, n, work);
            }
            else
                status = cholesky_mpi_local(local, column, work, &d, NULL);
            t[4] = MPI_Wtime();
            if (method != 2)
            {
                MPI_Gatherv(local, n * d.cols, MPI_DOUBLE, packed, counts, displs, MPI_DOUBLE, 0, d.comm);
                if (!d.rank)
                    rearrange(full, packed, n, d.p, 1);
            }
            t[5] = MPI_Wtime();
            /* Rank 0 owns the requested output. Its consecutive phases add exactly
             * to its total. Also record max local duration, without summing maxima. */
            double elapsed = t[5] - t[0], max_elapsed = 0;
            MPI_Reduce(&elapsed, &max_elapsed, 1, MPI_DOUBLE, MPI_MAX, 0, d.comm);
            int bad = (status != 0), any;
            MPI_Allreduce(&bad, &any, 1, MPI_INT, MPI_MAX, d.comm);
            failed |= any;
            if (!d.rank)
            {
                double v0 = MPI_Wtime();
                double residual = projected_residual(original, full, n, 8, 91827, checkwork), diff = 0;
                for (int i = 0; i < n; ++i)
                    for (int j = 0; j <= i; ++j)
                    {
                        size_t k = (size_t)i * n + j;
                        double delta = fabs(full[k] - reference[k]) / fmax(1.0, fabs(reference[k]));
                        if (!isfinite(delta))
                            diff = INFINITY;
                        else if (delta > diff)
                            diff = delta;
                    }
                double exact = n <= 128 ? relative_residual(original, full, n) : -1;
                failed |= !isfinite(residual) || residual > 1e-12 || diff > 1e-12 || (n <= 128 && (!isfinite(exact) || exact > 1e-12));
                double validation = MPI_Wtime() - v0;
                if (rep)
                    printf("%d,%d,%d,%d,%s,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g\n",
                           n, d.p, rep, pos + 1, names[method], t[1] - t[0], t[2] - t[1], t[3] - t[2], t[4] - t[3], t[5] - t[4],
                           elapsed, max_elapsed, validation, residual, diff, exact);
            }
            free(full);
            free(packed);
            free(local);
            free(column);
            free(work);
            free(counts);
            free(displs);
        }
    int any;
    MPI_Allreduce(&failed, &any, 1, MPI_INT, MPI_MAX, d.comm);
    free(original);
    free(reference);
    free(checkwork);
    return any;
}
int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);
    int rank;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    if (!rank)
        puts("N,P,repetition,order,method,allocation_s,generation_s,distribution_s,factor_s,gather_s,total_s,max_local_s,validation_s,projected_residual,factor_difference,exact_residual");
    int result = 0;
    if (argc == 2 && !strcmp(argv[1], "--test"))
    {
        int sizes[] = {1, 2, 3, 7, 31, 128};
        for (int i = 0; i < 6; ++i)
            result |= run(sizes[i], 1);
    }
    else
    {
        int n = argc > 1 ? number(argv[1], 20000) : -1, reps = argc > 2 ? number(argv[2], 120) : 6;
        if (n < 1 || reps < 1 || reps % 6 || argc > 3)
        {
            MPI_Finalize();
            return 2;
        }
        char host[MPI_MAX_PROCESSOR_NAME];
        int len;
        MPI_Get_processor_name(host, &len);
        fprintf(stderr, "rank=%d host=%s cpu=%d\n", rank, host, sched_getcpu());
        result = run(n, reps);
    }
    MPI_Finalize();
    return result;
}
