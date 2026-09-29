#ifndef CHOLESKY_MPI_H
#define CHOLESKY_MPI_H
#include <mpi.h>
#include <stdint.h>

/* Columnas globales crecientes, empaquetadas por filas en cada proceso.*/
typedef struct {
    int n, p, rank, cyclic, cols, first, block;
    MPI_Comm comm;
} Layout;
typedef struct { double compute, broadcast; uint64_t updates; } Profile;
typedef struct { double compute, reduce, broadcast; uint64_t products; } LeftProfile;
Layout layout_create(int n, int cyclic, MPI_Comm comm);
/* cyclic=2: bloques de b columnas; b>=1. */
Layout layout_block_create(int n, int b, MPI_Comm comm);
int layout_owner(const Layout *d, int column);
int layout_global(const Layout *d, int local_column);
/* Cantidad de columnas locales cuyos indices globales son < column. */
int layout_before(const Layout *d, int column);
/* Todas las tareas llaman en el mismo orden. column tiene n doubles.
 * Devuelve -1 colectivamente si aparece un pivote no positivo/no finito.*/
int cholesky_mpi(double *local, double *column, const Layout *d, Profile *profile);
/* local_column contiene cols doubles, disjuntos de local y column.
 * Se reserva fuera del timer; su llenado queda dentro. cols=0 es valido. */
int cholesky_mpi_local(double *local, double *column, double *local_column,
                       const Layout *d, Profile *profile);
/* Left-looking distribuido por columnas. partial y reduced tienen n doubles.
 * Cada proceso forma contribuciones con sus columnas anteriores; MPI_Reduce
 * las entrega al propietario de la columna actual. */
int cholesky_left_mpi(double *local, double *partial, double *reduced,
                      const Layout *d, LeftProfile *profile);
#endif
