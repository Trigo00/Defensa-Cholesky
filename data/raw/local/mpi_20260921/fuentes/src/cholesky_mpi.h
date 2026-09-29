#ifndef CHOLESKY_MPI_H
#define CHOLESKY_MPI_H
#include <mpi.h>
#include <stdint.h>

/* Columnas globales crecientes, empaquetadas por filas en cada proceso.
 * local[i*cols+t] representa A[i, global_column(t)]. */
typedef struct {
    int n, p, rank, cyclic, cols, first;
    MPI_Comm comm;
} Layout;
typedef struct { double compute, broadcast; uint64_t updates; } Profile;
Layout layout_create(int n, int cyclic, MPI_Comm comm);
int layout_owner(const Layout *d, int column);
int layout_global(const Layout *d, int local_column);
/* Cantidad de columnas locales cuyos indices globales son < column. */
int layout_before(const Layout *d, int column);
/* Todas las tareas llaman en el mismo orden. column tiene n doubles.
 * Devuelve -1 colectivamente si aparece un pivote no positivo/no finito.
 * profile=NULL elimina los cronometros internos del experimento principal. */
int cholesky_mpi(double *local, double *column, const Layout *d, Profile *profile);
#endif
