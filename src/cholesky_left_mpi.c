/* Cholesky left-looking MPI: cada rango aporta productos y el propietario completa la columna.
 * Lectura: ver docs/guia_codigo.md. Los comentarios explican instrucciones logicas;
 * las llaves y las continuaciones de una misma instruccion comparten explicacion.
 */
/* Declara Layout, perfiles y kernels distribuidos; incluye la API MPI. */
#include "cholesky_mpi.h"
/* Funciones matematicas y controles de finitud: sqrt, fabs, isfinite, NAN e INFINITY. */
#include <math.h>
/* Define size_t, adecuado para tamanos e indices de memoria. */
#include <stddef.h>

/* Suma contribuciones distribuidas al propietario y difunde el pivote para sincronizar el estado. */
int cholesky_left_mpi(double *a, double *partial, double *reduced, const Layout *d, LeftProfile *prof)
{
    /* Comprueba punteros o dimensiones requeridos antes de acceder a memoria. */
    if (!d || !a || !partial || !reduced || d->n < 1)
        /* Informa entrada o pivote invalido al llamador. */
        return -1;
    /* Define n: orden de la matriz; m: numero de columnas locales. */
    const int n = d->n, m = d->cols;
    /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
    if (prof)
        /* Inicializa en cero todos los tiempos y contadores del perfil. */
        *prof = (LeftProfile){0};

    /* Avanza columna por columna: la columna j depende de las anteriores. */
    for (int j = 0; j < n; ++j)
    {
        /* Determina que rango es responsable de la columna global activa. */
        const int owner = layout_owner(d, j);
        /* Cuenta columnas propias anteriores al limite global indicado. */
        const int previous = layout_before(d, j);
        /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
        double t = prof ? MPI_Wtime() : 0.0;
        /* Define local_diagonal: suma local de cuadrados para el pivote. */
        double local_diagonal = 0.0;
        /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
        for (int c = 0; c < previous; ++c)
        {
            /* Define value: valor temporal de la operacion. */
            const double value = a[(size_t)j * m + c];
            /* Suma la contribucion de una columna anterior propia a la diagonal j. */
            local_diagonal += value * value;
        }
        /* Recorre las filas por debajo del pivote de la columna activa. */
        for (int i = j + 1; i < n; ++i)
        {
            /* Define sum: acumulador del producto o de magnitudes. */
            double sum = 0.0;
            /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
            for (int c = 0; c < previous; ++c)
                /* Forma la contribucion local al producto entre las filas i y j. */
                sum += a[(size_t)i * m + c] * a[(size_t)j * m + c];
            /* Empaqueta el producto parcial de la fila i en un vector de longitud n-j-1. */
            partial[i - j - 1] = sum;
        }
        /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
        if (prof)
        {
            /* Acumula tiempo de trabajo local solo cuando se solicito instrumentacion. */
            prof->compute += MPI_Wtime() - t;
            /* Cuenta productos locales: columnas previas por diagonal y filas inferiores. */
            prof->products += (uint64_t)previous * (uint64_t)(n - j);
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t = MPI_Wtime();
        }

        /* Define diagonal_sum: suma global recibida por el propietario. */
        double diagonal_sum = 0.0;
        /* Suma las contribuciones escalares de todos los rangos; solo el propietario recibe la suma. */
        MPI_Reduce(&local_diagonal, &diagonal_sum, 1, MPI_DOUBLE, MPI_SUM, owner, d->comm);
        /* Omite la reduccion vectorial al llegar a la ultima columna, que no tiene filas inferiores. */
        if (n - j - 1 > 0)
            /* Suma los productos parciales de las filas inferiores y los entrega al propietario. */
            MPI_Reduce(partial, reduced, n - j - 1, MPI_DOUBLE, MPI_SUM, owner, d->comm);
        /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
        if (prof)
        {
            /* Acumula el tiempo local de las reducciones, incluidas sus esperas. */
            prof->reduce += MPI_Wtime() - t;
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t = MPI_Wtime();
        }

        /* Define pivot: valor de diagonal que define el siguiente pivote. */
        double pivot = NAN;
        /* Solo el propietario tiene almacenada la columna que se va a completar. */
        if (d->rank == owner)
        {
            /* En el propietario, la columna j sigue inmediatamente a las columnas previas. */
            const int current = previous;
            /* Resta la suma global de cuadrados para formar el pivote left-looking. */
            const double value = a[(size_t)j * m + current] - diagonal_sum;
            /* Comprueba finitud y/o tolerancias para que NaN e infinito no pasen la validacion. */
            if (isfinite(value) && value > 0.0)
            {
                /* Obtiene el pivote positivo de Cholesky. */
                pivot = sqrt(value);
                /* Guarda L(j,j) en la columna local del propietario. */
                a[(size_t)j * m + current] = pivot;
                /* Recorre las filas por debajo del pivote de la columna activa. */
                for (int i = j + 1; i < n; ++i)
                    /* Obtiene L(i,j) restando la suma global recibida y dividiendo por el pivote. */
                    a[(size_t)i * m + current] = (a[(size_t)i * m + current] - reduced[i - j - 1]) / pivot;
            }
        }
        /* Difunde el pivote: NAN hace que todos los rangos detecten el mismo fallo. */
        MPI_Bcast(&pivot, 1, MPI_DOUBLE, owner, d->comm);
        /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
        if (prof)
        {
            /* Acumula preparacion del pivote y difusion, segun el perfil left original. */
            prof->broadcast += MPI_Wtime() - t;
        }
        /* Un pivote debe ser finito y positivo; de lo contrario no se puede continuar Cholesky. */
        if (!isfinite(pivot) || pivot <= 0.0)
            /* Informa entrada o pivote invalido al llamador. */
            return -1;
    }
    /* Devuelve exito: la operacion termino sin detectar fallos. */
    return 0;
}
