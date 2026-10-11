#ifndef CHOLESKY_MPI_H
#define CHOLESKY_MPI_H
#include <mpi.h>
#include <stdint.h>

typedef struct
{
    int n, p, rank, cyclic, cols, first, block;
    MPI_Comm comm;
} Layout;

typedef struct
{
    double compute, broadcast;
    uint64_t updates;
} Profile;

typedef struct
{
    double compute, reduce, broadcast;
    uint64_t products;
} LeftProfile;

Layout layout_create(int n, int cyclic, MPI_Comm comm);
Layout layout_block_create(int n, int b, MPI_Comm comm);
int layout_owner(const Layout *d, int column);
int layout_global(const Layout *d, int local_column);
int layout_before(const Layout *d, int column);
int cholesky_mpi(double *local, double *column, const Layout *d, Profile *profile);
int cholesky_mpi_local(double *local, double *column, double *local_column, const Layout *d, Profile *profile);
int cholesky_left_mpi(double *local, double *partial, double *reduced, const Layout *d, LeftProfile *profile);
#endif
