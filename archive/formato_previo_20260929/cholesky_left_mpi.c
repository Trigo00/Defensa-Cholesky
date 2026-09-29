#include "cholesky_mpi.h"
#include <math.h>
#include <stddef.h>

int cholesky_left_mpi(double *a, double *partial, double *reduced,
                      const Layout *d, LeftProfile *prof)
{
    const int n = d->n, m = d->cols;
    if (!a || !partial || !reduced || !d || n < 1)
        return -1;
    if (prof)
        *prof = (LeftProfile){0};

    for (int j = 0; j < n; ++j)
    {
        const int owner = layout_owner(d, j);
        const int previous = layout_before(d, j);
        double t = prof ? MPI_Wtime() : 0.0;
        double local_diagonal = 0.0;
        for (int c = 0; c < previous; ++c)
        {
            const double value = a[(size_t)j * m + c];
            local_diagonal += value * value;
        }
        for (int i = j + 1; i < n; ++i)
        {
            double sum = 0.0;
            for (int c = 0; c < previous; ++c)
                sum += a[(size_t)i * m + c] * a[(size_t)j * m + c];
            partial[i - j - 1] = sum;
        }
        if (prof)
        {
            prof->compute += MPI_Wtime() - t;
            prof->products += (uint64_t)previous * (uint64_t)(n - j);
            t = MPI_Wtime();
        }

        double diagonal_sum = 0.0;
        MPI_Reduce(&local_diagonal, &diagonal_sum, 1, MPI_DOUBLE, MPI_SUM,
                   owner, d->comm);
        if (n - j - 1 > 0)
            MPI_Reduce(partial, reduced, n - j - 1, MPI_DOUBLE, MPI_SUM,
                       owner, d->comm);
        if (prof)
        {
            prof->reduce += MPI_Wtime() - t;
            t = MPI_Wtime();
        }

        double pivot = NAN;
        if (d->rank == owner)
        {
            const int current = previous;
            const double value = a[(size_t)j * m + current] - diagonal_sum;
            if (isfinite(value) && value > 0.0)
            {
                pivot = sqrt(value);
                a[(size_t)j * m + current] = pivot;
                for (int i = j + 1; i < n; ++i)
                    a[(size_t)i * m + current] =
                        (a[(size_t)i * m + current] - reduced[i - j - 1]) / pivot;
            }
        }
        MPI_Bcast(&pivot, 1, MPI_DOUBLE, owner, d->comm);
        if (prof)
        {
            prof->broadcast += MPI_Wtime() - t;
        }
        if (!isfinite(pivot) || pivot <= 0.0)
            return -1;
    }
    return 0;
}
