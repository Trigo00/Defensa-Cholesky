/* Reparto de columnas y Cholesky right-looking distribuido. Cada proceso almacena n*cols doubles por filas.
 * Lectura: ver docs/guia_codigo.md. Los comentarios explican instrucciones logicas;
 * las llaves y las continuaciones de una misma instruccion comparten explicacion.
 */
/* Declara Layout, perfiles y kernels distribuidos; incluye la API MPI. */
#include "cholesky_mpi.h"
/* Funciones matematicas y controles de finitud: sqrt, fabs, isfinite, NAN e INFINITY. */
#include <math.h>
/* Define size_t, adecuado para tamanos e indices de memoria. */
#include <stddef.h>

/* Calcula la propiedad contigua o ciclica para el proceso que llama; no reserva ni mueve matrices. */
Layout layout_create(int n, int cyclic, MPI_Comm comm)
{
    /* Define d: metadatos del reparto. */
    Layout d = {.n = n, .cyclic = cyclic, .comm = comm};
    /* Consulta el identificador de este proceso dentro del comunicador. */
    MPI_Comm_rank(comm, &d.rank);
    /* Consulta cuantos procesos participan en el comunicador. */
    MPI_Comm_size(comm, &d.p);
    /* Define q: columnas base por rango; r: resto de la division de columnas. */
    int q = n / d.p, r = n % d.p;
    /* Cada rango recibe q columnas y los primeros r reciben una extra. */
    d.cols = q + (d.rank < r);
    /* En ciclico se empieza en rank; en contiguo se cuentan las columnas de rangos anteriores. */
    d.first = cyclic ? d.rank : d.rank * q + (d.rank < r ? d.rank : r);
    /* Entrega los metadatos calculados; la estructura se devuelve por valor. */
    return d;
}
/* Devuelve el rango propietario de la columna global k; requiere 0<=k<n. */
int layout_owner(const Layout *d, int k)
{
    /* Selecciona el mapa ciclico por grupos de columnas. */
    if (d->cyclic == 2)
        /* El numero del bloque global, modulo P, identifica su propietario. */
        return (k / d->block) % d->p;
    /* Selecciona el reparto ciclico simple. */
    if (d->cyclic)
        /* La columna global k pertenece al rango k modulo P. */
        return k % d->p;
    /* Define q: columnas base por rango; r: resto de la division de columnas; boundary: fin del grupo de rangos con una columna extra. */
    int q = d->n / d->p, r = d->n % d->p, boundary = (q + 1) * r;
    /* Ubica k entre rangos largos o cortos; si q=0, un k valido siempre usa la primera rama. */
    return k < boundary ? k / (q + 1) : r + (k - boundary) / q;
}
/* Convierte un indice de columna local en su indice global. */
int layout_global(const Layout *d, int t)
{
    /* Selecciona el mapa ciclico por grupos de columnas. */
    if (d->cyclic == 2)
        /* Combina ciclo, propietario y posicion dentro del bloque para recuperar la columna global. */
        return (t / d->block * d->p + d->rank) * d->block + t % d->block;
    /* Avanza P columnas globales por columna local ciclica, o una en el reparto contiguo. */
    return d->first + t * (d->cyclic ? d->p : 1);
}
/* Cuenta columnas propias anteriores a k; si este rango posee k, tambien da su indice local. */
int layout_before(const Layout *d, int k)
{
    /* Selecciona el mapa ciclico por grupos de columnas. */
    if (d->cyclic == 2)
    {
        /* Recorta consultas anteriores al inicio de la matriz. */
        if (k < 0)
            /* Fija el limite inferior de la consulta. */
            k = 0;
        /* Recorta consultas posteriores al final de la matriz. */
        if (k > d->n)
            /* Fija el limite superior de la consulta. */
            k = d->n;
        /* Define cycle: columnas de una vuelta completa entre rangos; tail: columnas propias de la vuelta incompleta. */
        int cycle = d->block * d->p, tail = k % cycle - d->rank * d->block;
        /* Este rango aun no recibio columnas en el ciclo incompleto. */
        if (tail < 0)
            /* Aporta cero columnas del ciclo incompleto. */
            tail = 0;
        /* El ciclo incompleto ya contiene todo el bloque de este rango. */
        if (tail > d->block)
            /* Limita la contribucion parcial a un bloque. */
            tail = d->block;
        /* Suma columnas de ciclos completos y del bloque parcial. */
        return k / cycle * d->block + tail;
    }
    /* Define count: cantidad de columnas contabilizadas. */
    int count;
    /* No hay columnas propias con indice menor que k. */
    if (k <= d->first)
        /* No hay ninguna columna propia anterior a este limite. */
        return 0;
    /* Cuenta indices anteriores a k usando el salto ciclico o el intervalo contiguo. */
    count = d->cyclic ? (k - 1 - d->first) / d->p + 1 : k - d->first;
    /* Nunca cuenta mas columnas que las que almacena este proceso. */
    return count < d->cols ? count : d->cols;
}
/* Configura propiedad ciclica por grupos de b columnas, admitiendo procesos sin columnas. */
Layout layout_block_create(int n, int b, MPI_Comm comm)
{
    /* Construye el mapa local con el reparto de columnas indicado. */
    Layout d = layout_create(n, 1, comm);
    /* Marca la modalidad por bloques para las funciones de mapeo. */
    d.cyclic = 2;
    /* Conserva la cantidad de columnas consecutivas por turno. */
    d.block = b;
    /* Localiza el inicio del primer bloque de este rango. */
    d.first = d.rank * b;
    /* Cuenta todas sus columnas, incluyendo un posible bloque final incompleto. */
    d.cols = layout_before(&d, n);
    /* Entrega los metadatos calculados; la estructura se devuelve por valor. */
    return d;
}
/* Solo el propietario calcula el pivote y la columna; NAN comunica un fallo en el mismo mensaje. */
static void prepare_column(double *a, double *column, const Layout *d, int j, int owner)
{
    /* Define n: orden de la matriz; m: numero de columnas locales. */
    int n = d->n, m = d->cols;
    /* Solo el propietario tiene almacenada la columna que se va a completar. */
    if (d->rank == owner)
    {
        /* Obtiene el indice local de j dentro de su propietario. */
        int c = layout_before(d, j);
        /* Define pivot: valor de diagonal que define el siguiente pivote. */
        double pivot = a[(size_t)j * m + c];
        /* Deja el marcador de fallo hasta comprobar que el pivote permite continuar. */
        column[j] = NAN; /* Un mismo mensaje transporta pivote/estado. */
        /* Un pivote debe ser finito y positivo; de lo contrario no se puede continuar Cholesky. */
        if (isfinite(pivot) && pivot > 0)
        {
            /* Guarda L(j,j) tanto en la matriz local como en el mensaje a difundir. */
            column[j] = a[(size_t)j * m + c] = sqrt(pivot);
            /* Recorre las filas por debajo del pivote de la columna activa. */
            for (int i = j + 1; i < n; ++i)
                /* Divide por el pivote y copia L(i,j) al mensaje de la columna. */
                column[i] = a[(size_t)i * m + c] /= column[j];
        }
        /* Ruta alternativa cuando no se cumplio la condicion anterior. */
        else
        {
            /* Recorre las filas por debajo del pivote de la columna activa. */
            for (int i = j + 1; i < n; ++i)
                /* Inicializa el resto del mensaje de fallo para no transmitir memoria sin definir. */
                column[i] = 0;
        }
    }
}

/* Right-looking MPI original: todos los rangos difunden la misma columna y actualizan su parte. */
int cholesky_mpi(double *a, double *column, const Layout *d, Profile *prof)
{
    /* Define n: orden de la matriz; m: numero de columnas locales. */
    int n = d->n, m = d->cols;
    /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
    if (prof)
        /* Inicializa en cero todos los tiempos y contadores del perfil. */
        *prof = (Profile){0};
    /* Avanza columna por columna: la columna j depende de las anteriores. */
    for (int j = 0; j < n; ++j)
    {
        /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
        double t = prof ? MPI_Wtime() : 0;
        /* Determina que rango es responsable de la columna global activa. */
        int owner = layout_owner(d, j);
        /* Completa la columna solo en su propietario; el resto espera la difusion siguiente. */
        prepare_column(a, column, d, j, owner);
        /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
        if (prof)
        {
            /* Acumula tiempo de trabajo local solo cuando se solicito instrumentacion. */
            prof->compute += MPI_Wtime() - t;
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t = MPI_Wtime();
        }
        /* El propietario envia n-j doubles de la columna activa a todos, incluido el pivote/estado. */
        MPI_Bcast(column + j, n - j, MPI_DOUBLE, owner, d->comm);
        /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
        if (prof)
        {
            /* Acumula el tiempo local de la difusion, incluidas sus esperas. */
            prof->broadcast += MPI_Wtime() - t;
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t = MPI_Wtime();
        }
        /* Un pivote debe ser finito y positivo; de lo contrario no se puede continuar Cholesky. */
        if (!isfinite(column[j]) || column[j] <= 0)
            /* Informa entrada o pivote invalido al llamador. */
            return -1;
        /* Primera columna local futura: excluye la columna activa y las anteriores. */
        int begin = layout_before(d, j + 1);
        /* Recorre las filas por debajo del pivote de la columna activa. */
        for (int i = j + 1; i < n; ++i)
        {
            /* Lee L(i,j) de la columna que todos los procesos acaban de recibir. */
            double lij = column[i];
            /* Limite local exclusivo para actualizar solo columnas globales <=i. */
            int end = layout_before(d, i + 1);
            /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
            for (int c = begin; c < end; ++c)
                /* Actualiza A local con L(i,j)*L(k,j), traduciendo c a la columna global k. */
                a[(size_t)i * m + c] -= lij * column[layout_global(d, c)];
        }
        /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
        if (prof)
            /* Acumula tiempo de trabajo local solo cuando se solicito instrumentacion. */
            prof->compute += MPI_Wtime() - t;
    }
    /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
    if (prof)
        /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
        for (int c = 0; c < m; ++c)
        {
            /* Traduce el indice local a la columna global correspondiente. */
            uint64_t k = (uint64_t)layout_global(d, c);
            /* Cuenta actualizaciones de la columna global k a lo largo de toda la factorizacion. */
            prof->updates += k * (n - k);
        }
    /* Devuelve exito: la operacion termino sin detectar fallos. */
    return 0;
}

/* Variante experimental: mismo algoritmo, lectura interna contigua. */
/* Right-looking MPI seleccionado: reutiliza una copia contigua de valores de columnas propias. */
int cholesky_mpi_local(double *a, double *column, double *local_column, const Layout *d, Profile *prof)
{
    /* Define n: orden de la matriz; m: numero de columnas locales. */
    int n = d->n, m = d->cols;
    /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
    if (prof)
        /* Inicializa en cero todos los tiempos y contadores del perfil. */
        *prof = (Profile){0};
    /* Avanza columna por columna: la columna j depende de las anteriores. */
    for (int j = 0; j < n; ++j)
    {
        /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
        double t = prof ? MPI_Wtime() : 0;
        /* Determina que rango es responsable de la columna global activa. */
        int owner = layout_owner(d, j);
        /* Completa la columna solo en su propietario; el resto espera la difusion siguiente. */
        prepare_column(a, column, d, j, owner);
        /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
        if (prof)
        {
            /* Acumula tiempo de trabajo local solo cuando se solicito instrumentacion. */
            prof->compute += MPI_Wtime() - t;
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t = MPI_Wtime();
        }
        /* El propietario envia n-j doubles de la columna activa a todos, incluido el pivote/estado. */
        MPI_Bcast(column + j, n - j, MPI_DOUBLE, owner, d->comm);
        /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
        if (prof)
        {
            /* Acumula el tiempo local de la difusion, incluidas sus esperas. */
            prof->broadcast += MPI_Wtime() - t;
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t = MPI_Wtime();
        }
        /* Un pivote debe ser finito y positivo; de lo contrario no se puede continuar Cholesky. */
        if (!isfinite(column[j]) || column[j] <= 0)
            /* Informa entrada o pivote invalido al llamador. */
            return -1;
        /* Primera columna local futura: excluye la columna activa y las anteriores. */
        int begin = layout_before(d, j + 1);
        /* Copia incluida en el kernel: solo valores de columnas futuras
         * propias. Cada uno se reutiliza en varias filas inferiores. */
        /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
        for (int c = begin; c < m; ++c)
            /* Empaqueta L(k,j) de las columnas propias futuras; se reutilizara en varias filas. */
            local_column[c] = column[layout_global(d, c)];
        /* Recorre las filas por debajo del pivote de la columna activa. */
        for (int i = j + 1; i < n; ++i)
        {
            /* Lee L(i,j) de la columna que todos los procesos acaban de recibir. */
            double lij = column[i];
            /* Limite local exclusivo para actualizar solo columnas globales <=i. */
            int end = layout_before(d, i + 1);
            /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
            for (int c = begin; c < end; ++c)
                /* Actualiza el triangulo local leyendo el segundo factor de forma contigua. */
                a[(size_t)i * m + c] -= lij * local_column[c];
        }
        /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
        if (prof)
            /* Acumula tiempo de trabajo local solo cuando se solicito instrumentacion. */
            prof->compute += MPI_Wtime() - t;
    }
    /* Activa este costo adicional solamente cuando el llamador solicita un perfil. */
    if (prof)
        /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
        for (int c = 0; c < m; ++c)
        {
            /* Traduce el indice local a la columna global correspondiente. */
            uint64_t k = (uint64_t)layout_global(d, c);
            /* Cuenta actualizaciones de la columna global k a lo largo de toda la factorizacion. */
            prof->updates += k * (n - k);
        }
    /* Devuelve exito: la operacion termino sin detectar fallos. */
    return 0;
}
