/* Nucleo secuencial: generacion reproducible, tres factorizaciones y validacion numerica.
 * Lectura: ver docs/guia_codigo.md. Los comentarios explican instrucciones logicas;
 * las llaves y las continuaciones de una misma instruccion comparten explicacion.
 */
/* Declara generadores, kernels secuenciales y residuos. */
#include "cholesky.h"
/* Funciones matematicas y controles de finitud: sqrt, fabs, isfinite, NAN e INFINITY. */
#include <math.h>

/* Generador entero de estado fijo; no depende de rand() de cada biblioteca. */
/* Avanza SplitMix64: aritmetica entera reproducible, con desbordamiento unsigned definido. */
static uint64_t next_random(uint64_t *state)
{
    /* Avanza el estado por una constante impar; el desbordamiento modulo 2^64 es intencional. */
    *state += UINT64_C(0x9e3779b97f4a7c15);
    /* Copia el estado para mezclar sus bits sin perder el contador del generador. */
    uint64_t x = *state;
    /* Primera mezcla de bits mediante XOR, desplazamiento y multiplicacion unsigned. */
    x = (x ^ (x >> 30)) * UINT64_C(0xbf58476d1ce4e5b9);
    /* Segunda mezcla: dispersa diferencias pequeñas del estado por la palabra de 64 bits. */
    x = (x ^ (x >> 27)) * UINT64_C(0x94d049bb133111eb);
    /* Devuelve los bits mezclados que se usaran para generar el siguiente valor. */
    return x ^ (x >> 31);
}

/*
 * Genera una matriz A de dimension n x n,
 * simetrica y definida positiva (SPD).
 *
 * Primero genera los elementos fuera de la diagonal
 * en el intervalo [-1, 1).
 *
 * Despues construye una diagonal positiva y estrictamente
 * dominante, garantizando que A sea SPD.
 *
 * La semilla permite reproducir la misma matriz.
 */
void generate_spd(double *a, size_t n, uint64_t seed)
{
    // Estado inicial del generador pseudoaleatorio.
    uint64_t state = seed;
     /*
     * PRIMERA ETAPA: construir la parte no diagonal.
     */
    for (size_t i = 0; i < n; ++i)
    {
        /* Limpia la diagonal antes de construir su valor positivo definitivo. */
        a[i * n + i] = 0.0;
        /*Recorremos solo el triangulo superior. Empezamos en i+1 para evitar la diagonal y no generar dos veces el mismo par.*/
        for (size_t j = i + 1; j < n; ++j)
        {
            /*
             * Genera un entero pseudoaleatorio de 64 bits.
             * Conserva 53 bits y los transforma en un
             * double perteneciente a [-1, 1).
             */
            double value = 2.0 * (double)(next_random(&state) >> 11) * 0x1.0p-53 - 1.0;
            /*
             * Escribimos el mismo valor en A(i,j) y A(j,i) para garantizar la simetria.
             */
            a[i * n + j] = value;
            a[j * n + i] = value;
        }
    }
    /*
     * SEGUNDA ETAPA: construir la diagonal.
     * A(i,i) = 1 + suma de |A(i,j)| para j distinto de i.
     * Esto hace que la diagonal sea positiva y estrictamente dominante.
     */
    for (size_t i = 0; i < n; ++i)
    {
        double sum = 0.0;
        // Sumamos magnitudes de elementos no diagonales.
        for (size_t j = 0; j < n; ++j)
            if (i != j)
                sum += fabs(a[i * n + j]);
        // Diagonal mayor que la suma de las magnitudes.
        a[i * n + i] = sum + 1.0;
    }
}

/* Comprueba simetria exacta y finitud: devuelve 1 si ambas se cumplen, 0 si no. */
int symmetric_finite(const double *a, size_t n)
{
    /* Comprueba punteros o dimensiones requeridos antes de acceder a memoria. */
    if (!a || n == 0)
        /* Devuelve falso: la entrada no cumple el contrato comprobado. */
        return 0;
    /* Recorre las filas del intervalo indicado. */
    for (size_t i = 0; i < n; ++i)
        /* Recorre las columnas del intervalo indicado. */
        for (size_t j = 0; j < n; ++j)
            /* Comprueba finitud y/o tolerancias para que NaN e infinito no pasen la validacion. */
            if (!isfinite(a[i * n + j]) || a[i * n + j] != a[j * n + i])
                /* Devuelve falso: la entrada no cumple el contrato comprobado. */
                return 0;
    /* Devuelve verdadero: la entrada paso todas las comprobaciones. */
    return 1;
}

/*
 * Obtiene directamente el valor no diagonal A(i,j) que produciria el generador secuencial.
 * No necesita generar los numeros aleatorios anteriores. Esto permite que cada proceso MPI genere sus propias columnas y reproduzca la misma matriz global.
 * La matriz es simetrica: A(i,j) = A(j,i).
 */
static double indexed_value(size_t i, size_t j, size_t n, uint64_t seed)
{
    /*
     * Ordenamos los indices para trabajar siempre con una posicion del triangulo superior.
     * Ejemplo: (3,1) pasa a ser (1,3).
     * Asi ambos elementos simetricos producen exactamente el mismo valor.
     */
    if (i > j)
    {
        size_t t = i;
        i = j;
        j = t;
    }
    /*
     * Calculamos la posicion del valor aleatorio dentro del recorrido secuencial del triangulo superior.
     * Primera parte:
     *   i*(2*n-i-1)/2 Cuenta los valores de las filas anteriores.
     * Segunda parte:
     *   j-i-1 Indica el desplazamiento dentro de la fila i.
     * Ejemplo: n=4, (i,j)=(1,3)
     *   index = 1*(8-1-1)/2 + (3-1-1)
     *   index = 3+1 = 4
     */
    uint64_t index = (uint64_t)i * (2 * (uint64_t)n - i - 1) / 2 + (j - i - 1);
    /*
     * SplitMix64 avanza su estado sumando una constante fija por cada numero generado.
     * Calculamos directamente el estado anterior al valor que queremos obtener, sin recorrer toda la secuencia.
     */
    uint64_t state = seed + index * UINT64_C(0x9e3779b97f4a7c15);
    /*
     * Generamos el valor correspondiente y lo convertimos al intervalo [-1,1), utilizando la misma expresion del generador secuencial.
     */
    return 2.0 * (double)(next_random(&state) >> 11) * 0x1.0p-53 - 1.0;
}

/* Genera una columna global j dentro del buffer local; conserva el orden de suma original. */
static void generate_column(double *a, size_t n, uint64_t seed, size_t cols, size_t c, size_t j)
{
    /* Define sum: acumulador del producto o de magnitudes. */
    double sum = 0;
    /* Recorre las filas del intervalo indicado. */
    for (size_t i = 0; i < n; ++i)
        /* Excluye la diagonal: se construira con la suma de magnitudes mas uno. */
        if (i != j)
        {
            /* Define value: valor temporal de la operacion. */
            double value = indexed_value(i, j, n, seed);
            /* Guarda A(i,j) en la columna local c; cada fila local contiene cols elementos. */
            a[i * cols + c] = value;
            /* Acumula la magnitud en orden creciente de fila para reproducir la diagonal original. */
            sum += fabs(value);
        }
    /* Construye la diagonal global j dentro de su columna local c. */
    a[j * cols + c] = sum + 1.0;
}

/*
 * Genera directamente las columnas pertenecientes al proceso actual mediante distribucion ciclica.
 * No genera toda la matriz ni utiliza MPI_Scatterv. Cada proceso trabaja con su propio buffer local.
 * Ejemplo: N=8, P=3, rank=1
 *   Columnas globales propias: 1, 4, 7
 *   Indices locales: 0, 1, 2
 * Todos utilizan la misma semilla para reproducir
 * la matriz que generaria la version secuencial.
 */
void generate_spd_columns(double *a, size_t n, uint64_t seed, int rank, int processes)
{
    /*
     * Calculamos cuantas columnas pertenecen al proceso actual.
     * n/P: cantidad base de columnas.
     * n%P: procesos que reciben una columna adicional.
     */
    size_t cols = n / (size_t)processes + ((size_t)rank < n % (size_t)processes);

    // Recorremos las posiciones de columnas locales.
    for (size_t c = 0; c < cols; ++c)
    {
        /*
         * Convertimos el indice local c al indice global j utilizando la distribucion ciclica.
         * global = rank + c*P
         */
        size_t j = (size_t)rank + c * (size_t)processes;
        /*
         * Generamos los n elementos de la columna global j dentro de la columna local c.
         */
        generate_column(a, n, seed, cols, c, j);
    }
}

/* Genera las columnas globales indicadas, en el orden de la lista columns. */
void generate_spd_selected(double *a, size_t n, uint64_t seed, const int *columns, size_t count)
{
    /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
    for (size_t c = 0; c < count; ++c)
    {
        /* Lee el indice global de la columna seleccionada. */
        size_t j = (size_t)columns[c];
        /* Delega en la rutina comun la construccion de esta columna y su diagonal. */
        generate_column(a, n, seed, count, c, j);
    }
}

/*
 * CHOLESKY LEFT-LOOKING SECUENCIAL.
 * Factoriza A = L*L^T y almacena L en el triangulo inferior de la matriz original.
 * LEFT-LOOKING:
 * Para calcular la columna j, consulta las columnas anteriores k < j y resta sus contribuciones.
 * No actualiza anticipadamente toda la submatriz restante como lo hace right-looking.
 */
int cholesky_left(double *a, size_t n)
{
    /*
     * Comprobamos que exista la matriz y que la dimension sea valida. */
    if (!a || n == 0)
        return -1;

    // Recorremos cada columna del factor L.
    for (size_t j = 0; j < n; ++j)
    {
        /* Define sum: acumulador del producto o de magnitudes. */
        double sum = 0.0;

        /*
         * Calculamos: sum = L(j,0)^2 + ... + L(j,j-1)^2
         * Utilizamos las columnas ya factorizadas.
         */
        for (size_t k = 0; k < j; ++k)
            sum += a[j * n + k] * a[j * n + k];
            
        /* Corregimos el elemento diagonal original restando las contribuciones anteriores.*/
        double pivot = a[j * n + j] - sum;

        /* Cholesky necesita un pivote finito y estrictamente positivo. */
        if (!isfinite(pivot) || pivot <= 0.0)
            return -1;

        /* Calculamos el elemento diagonal: L(j,j) = sqrt(pivot). */
        a[j * n + j] = sqrt(pivot);
        
        /* Calculamos los elementos de la columna j que estan por debajo de la diagonal. */
        for (size_t i = j + 1; i < n; ++i)
        {
            /* Reinicia el acumulador para la siguiente fila o producto escalar. */
            sum = 0.0;

            /* Sumamos las contribuciones anteriores: sum = SUMA L(i,k)*L(j,k), con k<j. */
            for (size_t k = 0; k < j; ++k)
                sum += a[i * n + k] * a[j * n + k];
                
            /* Calculamos el nuevo elemento: L(i,j) = (A(i,j) - sum) / L(j,j). */
            a[i * n + j] = (a[i * n + j] - sum) / a[j * n + j];
        }
    }

    // La factorizacion termino sin detectar errores.
    return 0;
}

/*
 * CHOLESKY RIGHT-LOOKING SECUENCIAL.
 * Factoriza A = L*L^T y almacena L en el triangulo inferior de la matriz original.
 * A diferencia de left-looking, despues de calcular cada columna actualiza inmediatamente la submatriz que falta factorizar.
 * Por eso, cuando llegamos a una nueva columna, su pivote ya tiene descontadas las contribuciones de las columnas anteriores.
 */
int cholesky_right(double *a, size_t n)
{
    if (!a || n == 0)
        return -1;
        
    // Recorremos las columnas del factor.
    for (size_t j = 0; j < n; ++j)
    {
        /* El pivote ya fue actualizado por las iteraciones anteriores. */
        double pivot = a[j * n + j];

         // Debe ser finito y estrictamente positivo.
        if (!isfinite(pivot) || pivot <= 0.0)
            return -1;

        /* Guarda el pivote positivo L(j,j) sobre la diagonal de A. */
        a[j * n + j] = sqrt(pivot);

        /* Normalizamos los elementos inferiores de la columna j: L(i,j) = A_actualizada(i,j) / L(j,j). */
        for (size_t i = j + 1; i < n; ++i)
            a[i * n + j] /= a[j * n + j];

        /*
         * Actualizamos la submatriz inferior que todavia no fue factorizada.
         * A(i,k) = A(i,k) - L(i,j)*L(k,j)
         * Solo recorremos k<=i para trabajar sobre el triangulo inferior.
         * Esta etapa es la base del trabajo distribuido en nuestro Cholesky MPI.
         */
        for (size_t i = j + 1; i < n; ++i)
        {
            double lij = a[i * n + j];
            for (size_t k = j + 1; k <= i; ++k)
                a[i * n + k] -= lij * a[k * n + j];
        }
    }
    return 0;
}

/* Mismo right-looking, con copia de la columna para leer valores contiguos en el bucle interno. */
int cholesky_right_buffered(double *a, size_t n, double *column)
{
    // CAMBIO 1: recibimos un vector auxiliar column de n elementos para almacenar la columna activa.
    if (!a || !column || n == 0)
        return -1;

    for (size_t j = 0; j < n; ++j)
    {
        double pivot = a[j * n + j];
        if (!isfinite(pivot) || pivot <= 0.0)
            return -1;

        a[j * n + j] = sqrt(pivot);

        for (size_t i = j + 1; i < n; ++i)
            a[i * n + j] /= a[j * n + j];

        // CAMBIO 2: copiamos los valores de la columna recién calculada a un vector contiguo.
        for (size_t i = j + 1; i < n; ++i)
            column[i] = a[i * n + j];

        for (size_t i = j + 1; i < n; ++i)
        {
            double lij = a[i * n + j];
            for (size_t k = j + 1; k <= i; ++k)
                // CAMBIO 3: utilizamos column[k] en lugar de a[k*n+j], evitando lecturas con saltos dentro del bucle más interno.
                a[i * n + k] -= lij * column[k];
        }
    }
    return 0;
}

/*
 * VALIDACION COMPLETA MEDIANTE RESIDUO DE FROBENIUS.
 * Comprueba que el factor L reconstruya la matriz original A, calculando: ||A - L*L^T||_F / ||A||_F
 * Recorre todos los elementos de la matriz y reconstruye cada entrada de L*L^T.
 * Tiene costo O(n^3), por eso nuestro candidato solamente la utiliza para n <= 128.
 */
double relative_residual(const double *original, const double *factor, size_t n)
{
    /*
     * Comprobamos que existan ambas matrices y que la dimension sea mayor que cero.
     * INFINITY representa un fallo de validacion.
     */
    if (!original || !factor || n == 0)
        return INFINITY;

    /*
     * squared_error: Acumula los cuadrados de A(i,j)-(LL^T)(i,j).
     * squared_norm: Acumula los cuadrados de los elementos de A.
     * Usamos long double para mejorar la precision de la comprobacion cuando la plataforma lo permite.
     */
    long double squared_error = 0.0L, squared_norm = 0.0L;

    /*
     * Recorremos todas las posiciones de la matriz. i es la fila y j es la columna.
     */
    for (size_t i = 0; i < n; ++i)
    {
        for (size_t j = 0; j < n; ++j)
        {
            /*
             * Como L es triangular inferior, solo k <= min(i,j) contribuye al elemento (i,j) de L*L^T.
             * Ejemplo: i=2, j=1 -> last=1.
             */
            size_t last = i < j ? i : j;

            /*
             * Reconstruimos el elemento (i,j): (L*L^T)(i,j) = suma de L(i,k)*L(j,k) para k desde 0 hasta min(i,j).
             */
            long double reconstructed = 0.0L;
            for (size_t k = 0; k <= last; ++k)
                reconstructed += (long double)factor[i * n + k] * factor[j * n + k];

            /*
             * Obtenemos A(i,j) de la matriz original.
             * Calculamos la diferencia con el valor reconstruido a partir de L.
             */
            long double value = original[i * n + j];
            long double error = value - reconstructed;

            /*
             * Si el valor o la diferencia no son finitos, informamos fallo numerico.
             */
            if (!isfinite(error) || !isfinite(value))
                return INFINITY;

            /*
             * Acumulamos los cuadrados necesarios para calcular las normas de Frobenius.
             */
            squared_error += error * error;
            squared_norm += value * value;
        }
    }
    /*
     * Evitamos dividir por una norma nula.
     */
    if (squared_norm == 0.0L)
        return INFINITY;

     /*
     * Calculamos el residuo relativo: sqrt(squared_error / squared_norm)
     *Equivale a ||A-L*L^T||_F / ||A||_F. sqrtl trabaja con long double.
     */
    double result = (double)sqrtl(squared_error / squared_norm);
    
    /*
     * Devolvemos el residuo si es finito.
     * En caso contrario, devolvemos infinito.
     */
    return isfinite(result) ? result : INFINITY;
}

/*
 * VALIDACION MEDIANTE RESIDUO PROYECTADO.
 * Comprueba si A*x coincide aproximadamente con L*(L^T*x) para varios vectores de prueba.
 * En lugar de reconstruir toda la matriz L*L^T, utiliza productos matriz-vector.
 * Devuelve el mayor residuo relativo observado: ||A*x - L*(L^T*x)|| / ||A*x||
 * Una prueba con pocos vectores no garantiza detectar todos los errores posibles.
 */
double projected_residual(const double *a, const double *l, size_t n, unsigned probes, uint64_t seed,
                          long double *workspace)
{
    /*
     * Si faltan datos o las dimensiones son invalidas, devolvemos infinito como marcador de fallo.
     */
    if (!a || !l || !workspace || !n || !probes)
        return INFINITY;

    /*
     * Dividimos workspace en dos vectores:
     * x: vector de prueba.
     * y: resultado de L^T*x.
     */
    long double *x = workspace, *y = workspace + n;
    
    /*
     * Comprobamos que la diagonal de L sea positiva y finita, que toda A sea finita y que el triangulo inferior de L sea finito.
     */
    for (size_t i = 0; i < n; ++i)
    {
        if (!isfinite(l[i * n + i]) || l[i * n + i] <= 0)
            return INFINITY;
        for (size_t j = 0; j < n; ++j)
            if (!isfinite(a[i * n + j]) || (j <= i && !isfinite(l[i * n + j])))
                return INFINITY;
    }

    // Conservaremos el mayor residuo observado.
    long double worst = 0;

    // Repetimos la validacion con varios vectores.
    for (unsigned p = 0; p < probes; ++p)
    {
        /*
         * Generamos un vector reproducible formado por componentes +1 y -1.
         * &1 observa el bit menos significativo del numero pseudoaleatorio generado.
         */
        for (size_t i = 0; i < n; ++i)
            x[i] = (next_random(&seed) & 1) ? 1 : -1;

        /*
        * Calculamos y = L^T*x.
        * Solo recorremos desde i=j porque L es triangular inferior.
        */
        for (size_t j = 0; j < n; ++j)
        {
            y[j] = 0;
            for (size_t i = j; i < n; ++i)
                y[j] += (long double)l[i * n + j] * x[i];
        }
        /*
         * error: norma de A*x - L*y.
         * norm: norma de A*x para normalizar el error.
         */
        long double error = 0, norm = 0;
        for (size_t i = 0; i < n; ++i)
        {
            long double ax = 0, ly = 0;
            // Componente i de A*x.
            for (size_t j = 0; j < n; ++j)
                ax += (long double)a[i * n + j] * x[j];

             // Componente i de L*y, donde y=L^T*x.
            for (size_t j = 0; j <= i; ++j)
                ly += (long double)l[i * n + j] * y[j];

            /*
             * Acumulamos las normas euclideas usando hypotl, que evita cuadrados directos potencialmente problematicos.
             */
            error = hypotl(error, ax - ly);
            norm = hypotl(norm, ax);
        }
        /*
         * Evitamos residuos invalidos y division por cero.
         */
        if (!isfinite(error) || !isfinite(norm) || norm == 0)
            return INFINITY;

        long double ratio = error / norm;

        // Conservamos el peor resultado entre las pruebas.
        if (ratio > worst)
            worst = ratio;
    }
    // Devolvemos el mayor residuo observado.
    return (double)worst;
}
