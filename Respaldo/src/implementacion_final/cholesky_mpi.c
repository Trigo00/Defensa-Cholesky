/* Reparto de columnas y Cholesky right-looking distribuido. Cada proceso almacena n*cols doubles por filas.
 * Lectura: ver docs/guia_codigo.md. Los comentarios explican instrucciones logicas;
 * las llaves y las continuaciones de una misma instruccion comparten explicacion.
 */
#include "cholesky_mpi.h"
#include <math.h>
#include <stddef.h> //Define size_t, adecuado para tamanos e indices de memoria.

/* no distribuye físicamente la matriz ni ejecuta operaciones de Cholesky. Solamente calcula la información necesaria para organizar el reparto. */
Layout layout_create(int n, int cyclic, MPI_Comm comm) // Layout es un tipo de estructura definido por nuestro proyecto, utilizado para almacenar los metadatos de la distribución.
{
    Layout d = {.n = n, .cyclic = cyclic, .comm = comm};
    MPI_Comm_rank(comm, &d.rank); // Consulta el identificador de este proceso dentro del comunicador y lo guarda en d
    MPI_Comm_size(comm, &d.p); // Consulta cuantos procesos participan en el comunicador y lo guarda en d
    int q = n / d.p, r = n % d.p; //Define q: cantidad base de columnas que recibe cada proceso.; r: cantidad de columnas adicionales que debemos repartir
    d.cols = q + (d.rank < r); //Cada rango recibe q columnas y los primeros r reciben una extra.
    d.first = cyclic ? d.rank : d.rank * q + (d.rank < r ? d.rank : r); //calcula cuál es la primera columna global que le corresponde al proceso actual, dependiendo de si utilizamos una distribución cíclica o contigua.
    return d; //Devuelve la estructura completa al código que la llamó.
}
/* Recibe el número de una columna global k y devuelve qué proceso MPI es dueño de esa columna. */
int layout_owner(const Layout *d, int k)
{
    /*
     * DISTRIBUCION BLOQUE-CICLICA:
     *
     * Las columnas se agrupan en bloques de d->block elementos.
     * Primero calculamos a que bloque pertenece k mediante
     * la division entera k / d->block.
     *
     * Luego, con % d->p, obtenemos el proceso propietario.
     *
     * Ejemplo: k=7, block=2, P=3
     *   7/2 = 3 (bloque numero 3)
     *   3%3 = 0 (propietario: proceso 0)
     */
    if (d->cyclic == 2)
        return (k / d->block) % d->p;
    /*
     * DISTRIBUCION CICLICA SIMPLE (LA UTILIZADA):
     *
     * Se asigna una columna por turno a cada proceso.
     * Cuando llegamos al ultimo proceso, volvemos al primero.
     *
     * El resto de dividir k entre P indica el propietario.
     *
     * Ejemplo: k=7, P=3
     *   7%3 = 1 (propietario: proceso 1)
     *
     * P0: columnas 0, 3, 6, 9...
     * P1: columnas 1, 4, 7, 10...
     * P2: columnas 2, 5, 8, 11...
     */
    if (d->cyclic)
        return k % d->p;
    /*
     * DISTRIBUCION CONTIGUA:
     *
     * Cada proceso recibe un conjunto de columnas consecutivas.
     *
     * q: cantidad minima de columnas por proceso.
     * r: columnas sobrantes, asignadas una a cada uno
     *    de los primeros r procesos.
     *
     * boundary: primera columna posterior a los segmentos
     * de los procesos que recibieron una columna extra.
     *
     * Ejemplo: N=10, P=3
     *   q=3, r=1, boundary=4
     *
     * P0: columnas 0,1,2,3 (4 columnas)
     * P1: columnas 4,5,6   (3 columnas)
     * P2: columnas 7,8,9   (3 columnas)
     */
    int q = d->n / d->p;
    int r = d->n % d->p;
    int boundary = (q + 1) * r;
    /*
     * Si k < boundary:
     *   La columna pertenece a uno de los primeros r procesos,
     *   que tienen q+1 columnas cada uno.
     *
     * Si k >= boundary:
     *   La columna pertenece a uno de los procesos restantes.
     *   Restamos boundary para obtener su posicion dentro de
     *   esa segunda region, dividimos entre q y sumamos r
     *   para obtener el rango MPI correcto.
     *
     * Ejemplo: k=7, q=3, r=1, boundary=4
     *   k >= 4
     *   propietario = 1 + (7-4)/3 = 2
     */
    return k < boundary ? k / (q + 1) : r + (k - boundary) / q;
}

/*
 * Convierte un indice de columna LOCAL (t) en su indice GLOBAL.
 *
 * Cada proceso almacena sus columnas en posiciones locales
 * consecutivas: 0, 1, 2...
 *
 * Sin embargo, esas posiciones pueden representar columnas
 * diferentes de la matriz original.
 *
 * Ejemplo ciclico: N=8, P=3, rank=1
 *   Local 0 -> Global 1
 *   Local 1 -> Global 4
 *   Local 2 -> Global 7
 */int layout_global(const Layout *d, int t)
{
     /*
     * DISTRIBUCION BLOQUE-CICLICA:
     *
     * Las columnas se asignan en bloques de tamano b.
     *
     * t / block:
     *   Indica el numero de bloque LOCAL.
     *
     * t / block * P + rank:
     *   Obtiene el numero del bloque GLOBAL.
     *
     * Multiplicar por block:
     *   Obtiene la primera columna global de ese bloque.
     *
     * t % block:
     *   Indica la posicion dentro del bloque.
     *
     * Ejemplo: t=3, block=2, P=3, rank=1
     *   Bloque local: 3/2 = 1
     *   Bloque global: 1*3+1 = 4
     *   Inicio global: 4*2 = 8
     *   Posicion interna: 3%2 = 1
     *   Resultado: columna global 9
     */
    if (d->cyclic == 2)
        return (t / d->block * d->p + d->rank) * d->block + t % d->block;
    /*
     * DISTRIBUCION CICLICA SIMPLE (NUESTRO CANDIDATO):
     *
     * Cada proceso recibe una columna cada P posiciones.
     * La primera columna global es d->first (igual al rank).
     *
     * global = first + t*P
     *
     * Ejemplo: rank=1, P=3, t=2
     *   global = 1 + 2*3 = 7
     *
     * DISTRIBUCION CONTIGUA:
     *
     * Las columnas son consecutivas.
     * Solo sumamos t a la primera columna.
     *
     * global = first + t
     *
     * El operador ternario selecciona P si cyclic=1,
     * o selecciona 1 si cyclic=0.
     */
    return d->first + t * (d->cyclic ? d->p : 1);
}

/*
 * Cuenta cuantas columnas PROPIAS tiene este proceso
 * con indice global menor que k.
 *
 * Si el proceso es propietario de la columna k,
 * el resultado tambien es su indice LOCAL.
 *
 * Ejemplo ciclico: N=8, P=3, rank=1
 *   Columnas propias: 1, 4, 7
 *
 *   layout_before(d, 7) = 2
 *
 * Hay dos columnas propias anteriores a 7 (1 y 4).
 * Por lo tanto, la columna global 7 esta en
 * la posicion local 2.
 */
int layout_before(const Layout *d, int k)
{
     /*
     * DISTRIBUCION BLOQUE-CICLICA:
     *
     * Las columnas se reparten en bloques de tamano b.
     * Contamos primero las columnas de ciclos completos
     * y luego las del bloque parcial.
     */
    if (d->cyclic == 2)
    {
        // Limita k al intervalo valido [0, n].
        if (k < 0)
            k = 0;

        if (k > d->n)
            k = d->n;
        /*
         * cycle: numero de columnas globales que ocupa
         * una vuelta completa de bloques entre procesos.
         *
         * tail: columnas propias anteriores a k dentro
         * del ultimo ciclo incompleto.
         */
        int cycle = d->block * d->p, tail = k % cycle - d->rank * d->block;
        
        // No podemos contar una cantidad negativa.
        if (tail < 0)
            /* Aporta cero columnas del ciclo incompleto. */
            tail = 0;
        // Un bloque propio tiene como maximo block columnas.
        if (tail > d->block)
            /* Limita la contribucion parcial a un bloque. */
            tail = d->block;
        /* Suma columnas de ciclos completos y del bloque parcial. */
        return k / cycle * d->block + tail;
    }

    int count; //cantidad de columnas contabilizadas
    /*
     * Si k es menor o igual a nuestra primera columna,
     * no existe ninguna columna propia anterior a k.
     */
    if (k <= d->first)
        return 0;

    /*
     * DISTRIBUCION CICLICA SIMPLE (NUESTRO CANDIDATO):
     *
     * Las columnas propias aparecen cada P posiciones.
     *
     * k-1: excluye la columna k del conteo.
     * -first: mide desde nuestra primera columna.
     * /P: cuenta los saltos entre columnas propias.
     * +1: incluye la primera columna propia.
     *
     * Ejemplo: rank=1, P=3, k=7
     *   first=1
     *   count=(7-1-1)/3+1=2
     *
     * DISTRIBUCION CONTIGUA:
     *
     * Las columnas propias son consecutivas.
     * Basta calcular k-first.
     */
    count = d->cyclic ? (k - 1 - d->first) / d->p + 1 : k - d->first;
     /*
     * No podemos contar mas columnas que las que
     * realmente posee el proceso.
     *
     * Por eso devolvemos el menor valor entre
     * count y d->cols.
     */
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
/*
 * PREPARA LA COLUMNA ACTIVA DEL FACTOR L.
 * Solo el proceso propietario de la columna global j realiza el calculo.
 * 1. Localiza la columna j en su memoria local.
 * 2. Obtiene el pivote diagonal ya actualizado.
 * 3. Calcula L(j,j) = sqrt(pivot).
 * 4. Divide los elementos inferiores por L(j,j).
 * 5. Copia los resultados al vector column.
 * El vector sera enviado al resto mediante MPI_Bcast desde cholesky_mpi_local().
 * Si el pivote es invalido, se deja NAN como marcador de error para que todos los procesos lo detecten.
 */
static void prepare_column(double *a, double *column, const Layout *d, int j, int owner)
{
    /*
     * n: dimension global de la matriz.
     * m: cantidad de columnas locales del proceso.
     */
    int n = d->n, m = d->cols;
    /*
     * Solamente el propietario posee la columna j. Los demas procesos no calculan esta columna.
     */
    if (d->rank == owner)
    {
        /* Convierte la columna global j en su posicion local c. */
        int c = layout_before(d, j);
        /*
         * Lee el elemento diagonal de la columna j. Como la matriz local se almacena por filas, el indice es fila*m + columna_local.
         * El pivote ya contiene las actualizaciones realizadas por las columnas anteriores.
         */
        double pivot = a[(size_t)j * m + c];
        /*
         * NAN funciona como marcador de fallo. Se reemplazara si el pivote es valido.
         */
        column[j] = NAN;
        /*
         * Cholesky requiere un pivote finito y estrictamente positivo.
         */
        if (isfinite(pivot) && pivot > 0)
        {
             /*
             * Calcula L(j,j) = sqrt(pivot).
             * Guarda el valor en la matriz local y tambien en el vector que sera difundido.
             * Las asignaciones se realizan de derecha a izquierda.
             */
            column[j] = a[(size_t)j * m + c] = sqrt(pivot);
            /*
             * Calcula los elementos inferiores:
             * L(i,j) = A_actualizada(i,j) / L(j,j) 
             * /= divide y guarda el resultado.
             * Tambien copia cada resultado a column[i] para transmitir la columna completa.
             */
            for (int i = j + 1; i < n; ++i)
                column[i] = a[(size_t)i * m + c] /= column[j];
        }
        else
        {
            /*
             * Si el pivote es invalido: column[j] conserva NAN.
             * Inicializamos los demas elementos en cero para no difundir memoria sin inicializar.
             * El kernel detectara el fallo despues de MPI_Bcast y terminara.
             */
            for (int i = j + 1; i < n; ++i)
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

/*
 * Variante optimizada del Cholesky MPI right-looking.
 *
 * Realiza las mismas operaciones matematicas y comunicaciones que cholesky_mpi().
 *
 * DIFERENCIA PRINCIPAL:
 * cholesky_mpi() obtiene L(k,j) directamente desde column[layout_global(d,c)] en cada actualizacion.
 * cholesky_mpi_local() copia previamente esos valores al vector auxiliar local_column, organizado segunlos indices locales del proceso.
 * Esto permite acceder a local_column[c] de forma contigua dentro del bucle interno y evita repetir la conversion de indices locales a globales.
 * La copia tiene un costo adicional, pero puede mejorar la localidad de memoria y el rendimiento.
 * Esta es la variante utilizada en nuestro candidato.
 */

/*
 * FACTORIZACION CHOLESKY MPI RIGHT-LOOKING.
 * Cada proceso almacena solamente sus columnas.
 * Para cada columna global j:
 * 1. Identificamos su proceso propietario.
 * 2. El propietario calcula el pivote y la columna.
 * 3. Difundimos la columna mediante MPI_Bcast.
 * 4. Cada proceso actualiza sus columnas futuras.
 * La factorizacion avanza secuencialmente entre columnas por las dependencias matematicas, pero distribuye las actualizaciones entre procesos.
 */
int cholesky_mpi_local(double *a, double *column, double *local_column, const Layout *d, Profile *prof)
{
     // Dimension global y cantidad de columnas propias.
    int n = d->n, m = d->cols;
    /*
     * Si se solicita perfilado, inicializamos a cero los tiempos y contadores.
     * Nuestro candidato pasa NULL, por lo que esta instrumentacion no se ejecuta.
     */
    if (prof)
        *prof = (Profile){0};

     /*
     * Recorremos las columnas globales en orden. Cada columna depende de las actualizaciones realizadas por las anteriores.
     */
    for (int j = 0; j < n; ++j)
    {
        /*
         * Marca temporal opcional. MPI_Wtime devuelve tiempo en segundos.
         */
        double t = prof ? MPI_Wtime() : 0;
        /*
         * Identificamos el propietario de j. En distribucion ciclica: owner = j % P.
         */
        int owner = layout_owner(d, j);
        /*
         * Solo el propietario calcula el pivote y los elementos inferiores de la columna.
         * Los resultados quedan en el vector column.
         */
        prepare_column(a, column, d, j, owner);

        /*
         * Si hay perfilado, acumulamos el tiempo empleado en preparar la columna.
         */
        if (prof)
        {
            prof->compute += MPI_Wtime() - t;
            t = MPI_Wtime();
        }

        /*
         * MPI_Bcast difunde la columna activa.
         * column+j: empezamos desde la diagonal j.
         * n-j: cantidad de elementos que transmitimos.
         * MPI_DOUBLE: tipo de cada elemento.
         * owner: proceso que proporciona los datos.
         * d->comm: comunicador de los procesos.
         * Todos los procesos participan en la colectiva.
         *
         * Ejemplo: n=8, j=4
         * Se comunican column[4] ... column[7].
         */
        MPI_Bcast(column + j, n - j, MPI_DOUBLE, owner, d->comm);

        /*
         * Acumulamos el tiempo local de la difusion. Puede incluir esperas, no solo transferencia.
         */
        if (prof)
        {
            prof->broadcast += MPI_Wtime() - t;
            t = MPI_Wtime();
        }

        /*
         * El propietario coloca NAN si el pivote falla.
         * Como el marcador se difundio, todos los procesos pueden detectar el mismo error.
         * Cholesky requiere pivotes finitos y positivos.
         */
        if (!isfinite(column[j]) || column[j] <= 0)
            return -1;
            
        /*
        * Calculamos la primera columna LOCAL que debemos actualizar despues de factorizar la columna global j.
        * layout_before(d, j+1) cuenta las columnas propias con indice global <= j, por lo que las excluye.
        *
        * Ejemplo: N=8, P=3, j=3
        *   P0: columnas 0,3,6 -> begin=2
        *   P1: columnas 1,4,7 -> begin=1
        *   P2: columnas 2,5   -> begin=1
        */
        int begin = layout_before(d, j + 1);
        /*
        * Preparamos los valores de la columna activa que corresponden a nuestras columnas locales futuras.
        * layout_global(d,c) convierte el indice local c al indice global que debemos consultar en column.
        *
        * Ejemplo para P1, j=3:
        *   local_column[1] = column[4]
        *   local_column[2] = column[7]
        *
        * Esta copia permite reutilizar los valores con accesos contiguos en el bucle de actualizacion.
        */
        for (int c = begin; c < m; ++c)
            local_column[c] = column[layout_global(d, c)];

        /*
        * Recorremos las filas que quedan por debajo de la columna activa j. Solo actualizamos la region inferior derecha que todavia falta factorizar.
        *
        * Ejemplo: si n=8 y j=3, recorremos i=4,5,6,7.
        */
        for (int i = j + 1; i < n; ++i)
        {
             /*
            * Recuperamos L(i,j) de la columna que recibimos mediante MPI_Bcast.
            * Este valor se reutiliza para actualizar varios elementos de la fila i.
            */
            double lij = column[i];

            /*
            * end indica hasta donde llegan las columnas locales que podemos actualizar en la fila i.
            * layout_before(d,i+1) cuenta las columnas propias con indice global <= i.
            * Usamos i+1 porque solo actualizamos el triangulo inferior, donde la columna global k debe cumplir k <= i.
            *
            * Ejemplo: N=8, P=3, j=3, i=6
            *   P0: begin=2, end=3 -> columna global 6
            *   P1: begin=1, end=2 -> columna global 4
            *   P2: begin=1, end=2 -> columna global 5
            */
            int end = layout_before(d, i + 1);

            /*
            * Recorremos solamente nuestras columnas locales pendientes, desde begin hasta end (excluido).
            * Si begin == end, este proceso no tiene elementos para actualizar en esta fila.
            */
            for (int c = begin; c < end; ++c)
                /*
                * ACTUALIZACION RIGHT-LOOKING:
                * A(i,k) = A(i,k) - L(i,j)*L(k,j)
                * a[i*m+c]: elemento local correspondiente a la fila global i y columna k.
                * lij: L(i,j), valor de la columna activa.
                * local_column[c]: L(k,j), donde k es el indice global de la columna local c.
                * El operador -= resta el producto y guarda el resultado en la propia matriz local.
                * Cada proceso actualiza exclusivamente las columnas que le pertenecen.
                */
                a[(size_t)i * m + c] -= lij * local_column[c];
        }
        /*
        * Si solicitamos perfilado, acumulamos el tiempo local de la fase de actualizacion posterior al MPI_Bcast.
        * Este intervalo tambien incluye el trabajo auxiliar ejecutado despues de la difusion.
        */
        if (prof)
            prof->compute += MPI_Wtime() - t;
    }
    /*
    * Una vez terminada la factorizacion, calculamos cuantas actualizaciones escalares corresponden a las columnas propias del proceso.
    * Este calculo solo se realiza si prof != NULL.
    */
    if (prof)
        for (int c = 0; c < m; ++c)
        {
            /* Traduce el indice local a la columna global correspondiente. */
            uint64_t k = (uint64_t)layout_global(d, c);

            /*
            * Una columna global k recibe actualizaciones desde las k columnas anteriores.
            * Para cada una, se actualizan n-k filas del triangulo inferior.
            * Total de actualizaciones = k*(n-k).
            *
            * Ejemplo: n=8, k=3
            *   3 columnas anteriores.
            *   5 filas pendientes.
            *   Total = 3*5 = 15 actualizaciones.
            *
            * Se cuentan actualizaciones escalares, no FLOPs individuales.
            */
            prof->updates += k * (n - k);
        }
    return 0;
}
