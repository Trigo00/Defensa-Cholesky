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

/* Construye A simetrica y estrictamente dominante en diagonal; asi es definida positiva. */
void generate_spd(double *a, size_t n, uint64_t seed)
{
    /* Define state: estado del generador. */
    uint64_t state = seed;
    /* Recorre las filas del intervalo indicado. */
    for (size_t i = 0; i < n; ++i)
    {
        /* Limpia la diagonal antes de construir su valor positivo definitivo. */
        a[i * n + i] = 0.0;
        /* Recorre las columnas del intervalo indicado. */
        for (size_t j = i + 1; j < n; ++j)
        {
            /* 53 bits, convertidos al intervalo [-1,1). */
            /* Usa los 53 bits superiores para obtener un double reproducible en [-1,1). */
            double value = 2.0 * (double)(next_random(&state) >> 11) * 0x1.0p-53 - 1.0;
            /* Escribe la entrada superior (i,j) en almacenamiento por filas. */
            a[i * n + j] = value;
            /* Escribe su reflejo (j,i), conservando simetria bit a bit. */
            a[j * n + i] = value;
        }
    }
    /* Recorre las filas del intervalo indicado. */
    for (size_t i = 0; i < n; ++i)
    {
        /* Define sum: acumulador del producto o de magnitudes. */
        double sum = 0.0;
        /* Recorre las columnas del intervalo indicado. */
        for (size_t j = 0; j < n; ++j)
            /* Excluye la diagonal: se construira con la suma de magnitudes mas uno. */
            if (i != j)
                /* Acumula la magnitud de cada entrada fuera de la diagonal. */
                sum += fabs(a[i * n + j]);
        /* Hace la diagonal mayor que la suma de valores absolutos de su fila. */
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

/* Obtiene el valor de un par i!=j sin recorrer los numeros aleatorios anteriores. */
static double indexed_value(size_t i, size_t j, size_t n, uint64_t seed)
{
    /* Ordena el par de indices para que (i,j) y (j,i) generen exactamente el mismo valor. */
    if (i > j)
    {
        /* Guarda temporalmente i para intercambiar los indices sin perderlo. */
        size_t t = i;
        /* Coloca el menor indice en i. */
        i = j;
        /* Completa el intercambio: j queda con el mayor indice. */
        j = t;
    }
    /* Cuenta entradas previas del triangulo superior y el desplazamiento dentro de la fila i. */
    uint64_t index = (uint64_t)i * (2 * (uint64_t)n - i - 1) / 2 + (j - i - 1);
    /* Salta directamente al estado anterior al valor correspondiente al par (i,j). */
    uint64_t state = seed + index * UINT64_C(0x9e3779b97f4a7c15);
    /* Convierte 53 bits aleatorios al intervalo [-1,1), igual que el generador secuencial. */
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

/* Genera solamente las columnas j=rank+c*processes del reparto ciclico. */
void generate_spd_columns(double *a, size_t n, uint64_t seed, int rank, int processes)
{
    /* Cuenta columnas ciclicas: cociente n/P mas una para los primeros n%P rangos. */
    size_t cols = n / (size_t)processes + ((size_t)rank < n % (size_t)processes);
    /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
    for (size_t c = 0; c < cols; ++c)
    {
        /* La columna local c corresponde a la global rank+c*P. */
        size_t j = (size_t)rank + c * (size_t)processes;
        /* Delega en la rutina comun la construccion de esta columna y su diagonal. */
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

/* Calcula L usando productos con columnas anteriores; sobrescribe solo el triangulo inferior. */
int cholesky_left(double *a, size_t n)
{
    /* Comprueba punteros o dimensiones requeridos antes de acceder a memoria. */
    if (!a || n == 0)
        /* Informa entrada o pivote invalido al llamador. */
        return -1;
    /* Avanza columna por columna: la columna j depende de las anteriores. */
    for (size_t j = 0; j < n; ++j)
    {
        /* Define sum: acumulador del producto o de magnitudes. */
        double sum = 0.0;
        /* Recorre las contribuciones o columnas dentro del limite triangular indicado. */
        for (size_t k = 0; k < j; ++k)
            /* Suma L(j,k)^2 de columnas ya factorizadas para corregir el pivote. */
            sum += a[j * n + k] * a[j * n + k];
        /* Resta la contribucion anterior a A(j,j); su raiz sera L(j,j). */
        double pivot = a[j * n + j] - sum;
        /* Un pivote debe ser finito y positivo; de lo contrario no se puede continuar Cholesky. */
        if (!isfinite(pivot) || pivot <= 0.0)
            /* Informa entrada o pivote invalido al llamador. */
            return -1;
        /* Guarda el pivote positivo L(j,j) sobre la diagonal de A. */
        a[j * n + j] = sqrt(pivot);
        /* Recorre las filas por debajo del pivote de la columna activa. */
        for (size_t i = j + 1; i < n; ++i)
        {
            /* Reinicia el acumulador para la siguiente fila o producto escalar. */
            sum = 0.0;
            /* Recorre las contribuciones o columnas dentro del limite triangular indicado. */
            for (size_t k = 0; k < j; ++k)
                /* Forma el producto escalar de las partes ya conocidas de las filas i y j. */
                sum += a[i * n + k] * a[j * n + k];
            /* Calcula L(i,j) restando contribuciones previas y dividiendo por L(j,j). */
            a[i * n + j] = (a[i * n + j] - sum) / a[j * n + j];
        }
    }
    /* Devuelve exito: la operacion termino sin detectar fallos. */
    return 0;
}

/* Calcula L y aplica inmediatamente su contribucion al triangulo restante. */
int cholesky_right(double *a, size_t n)
{
    /* Comprueba punteros o dimensiones requeridos antes de acceder a memoria. */
    if (!a || n == 0)
        /* Informa entrada o pivote invalido al llamador. */
        return -1;
    /* Avanza columna por columna: la columna j depende de las anteriores. */
    for (size_t j = 0; j < n; ++j)
    {
        /* 1. Pivote: las columnas anteriores ya actualizaron a[j,j]. */
        /* Define pivot: valor de diagonal que define el siguiente pivote. */
        double pivot = a[j * n + j];
        /* Un pivote debe ser finito y positivo; de lo contrario no se puede continuar Cholesky. */
        if (!isfinite(pivot) || pivot <= 0.0)
            /* Informa entrada o pivote invalido al llamador. */
            return -1;
        /* Guarda el pivote positivo L(j,j) sobre la diagonal de A. */
        a[j * n + j] = sqrt(pivot);

        /* 2. Completar la columna. Cada i escribe un elemento distinto. */
        /* Recorre las filas por debajo del pivote de la columna activa. */
        for (size_t i = j + 1; i < n; ++i)
            /* Completa L(i,j) usando el pivote de la columna activa. */
            a[i * n + j] /= a[j * n + j];

        /* 3. Right-looking: actualizar la region inferior derecha.*/
        /* Recorre las filas por debajo del pivote de la columna activa. */
        for (size_t i = j + 1; i < n; ++i)
        {
            /* Reutiliza L(i,j) en todas las actualizaciones de esta fila. */
            double lij = a[i * n + j];
            /* Recorre las contribuciones o columnas dentro del limite triangular indicado. */
            for (size_t k = j + 1; k <= i; ++k)
                /* Aplica A(i,k) -= L(i,j)*L(k,j); la segunda lectura recorre una columna con saltos. */
                a[i * n + k] -= lij * a[k * n + j];
        }
    }
    /* Devuelve exito: la operacion termino sin detectar fallos. */
    return 0;
}

/* Mismo right-looking, con copia de la columna para leer valores contiguos en el bucle interno. */
int cholesky_right_buffered(double *a, size_t n, double *column)
{
    /* Comprueba punteros o dimensiones requeridos antes de acceder a memoria. */
    if (!a || !column || n == 0)
        /* Informa entrada o pivote invalido al llamador. */
        return -1;
    /* Avanza columna por columna: la columna j depende de las anteriores. */
    for (size_t j = 0; j < n; ++j)
    {
        /* Define pivot: valor de diagonal que define el siguiente pivote. */
        double pivot = a[j * n + j];
        /* Un pivote debe ser finito y positivo; de lo contrario no se puede continuar Cholesky. */
        if (!isfinite(pivot) || pivot <= 0.0)
            /* Informa entrada o pivote invalido al llamador. */
            return -1;
        /* Guarda el pivote positivo L(j,j) sobre la diagonal de A. */
        a[j * n + j] = sqrt(pivot);
        /* Recorre las filas por debajo del pivote de la columna activa. */
        for (size_t i = j + 1; i < n; ++i)
            /* Completa L(i,j) usando el pivote de la columna activa. */
            a[i * n + j] /= a[j * n + j];

        /* Recorre las filas por debajo del pivote de la columna activa. */
        for (size_t i = j + 1; i < n; ++i)
            /* Copia L(i,j) al vector contiguo; esta copia forma parte del kernel. */
            column[i] = a[i * n + j];

        /* Recorre las filas por debajo del pivote de la columna activa. */
        for (size_t i = j + 1; i < n; ++i)
        {
            /* Reutiliza L(i,j) en todas las actualizaciones de esta fila. */
            double lij = a[i * n + j];
            /* Recorre las contribuciones o columnas dentro del limite triangular indicado. */
            for (size_t k = j + 1; k <= i; ++k)
                /* Aplica la misma actualizacion leyendo L(k,j) del vector contiguo. */
                a[i * n + k] -= lij * column[k];
        }
    }
    /* Devuelve exito: la operacion termino sin detectar fallos. */
    return 0;
}

/* Reconstruye LL^T y devuelve su error relativo de Frobenius; costo cubico, fuera del benchmark. */
double relative_residual(const double *original, const double *factor, size_t n)
{
    /* Comprueba punteros o dimensiones requeridos antes de acceder a memoria. */
    if (!original || !factor || n == 0)
        /* Representa validacion numerica fallida con un residuo infinito. */
        return INFINITY;
    /* Define squared_error: suma de cuadrados del error; squared_norm: suma de cuadrados de A. */
    long double squared_error = 0.0L, squared_norm = 0.0L;
    /* Recorre las filas del intervalo indicado. */
    for (size_t i = 0; i < n; ++i)
    {
        /* Recorre las columnas del intervalo indicado. */
        for (size_t j = 0; j < n; ++j)
        {
            /* Solo k<=min(i,j) contribuye al producto de dos filas de L triangular. */
            size_t last = i < j ? i : j;
            /* Define reconstructed: entrada reconstruida de LL^T. */
            long double reconstructed = 0.0L;
            /* Recorre los indices que contribuyen a esta suma o comprobacion. */
            for (size_t k = 0; k <= last; ++k)
                /* Acumula LL^T(i,j) en precision extendida para reducir error de la comprobacion. */
                reconstructed += (long double)factor[i * n + k] * factor[j * n + k];
            /* Lee la entrada original A(i,j) para compararla con la reconstruccion. */
            long double value = original[i * n + j];
            /* Calcula la diferencia A(i,j)-LL^T(i,j). */
            long double error = value - reconstructed;
            /* Comprueba finitud y/o tolerancias para que NaN e infinito no pasen la validacion. */
            if (!isfinite(error) || !isfinite(value))
                /* Representa validacion numerica fallida con un residuo infinito. */
                return INFINITY;
            /* Acumula el numerador cuadrado de la norma de Frobenius. */
            squared_error += error * error;
            /* Acumula el denominador cuadrado de la norma de A. */
            squared_norm += value * value;
        }
    }
    /* Evita dividir por una norma nula. */
    if (squared_norm == 0.0L)
        /* Representa validacion numerica fallida con un residuo infinito. */
        return INFINITY;
    /* Normaliza el error y extrae la raiz antes de convertir el resultado a double. */
    double result = (double)sqrtl(squared_error / squared_norm);
    /* Conserva un residuo finito; cualquier desbordamiento se informa como fallo numerico. */
    return isfinite(result) ? result : INFINITY;
}

/* Comprueba Ax frente a L(L^T x) para vectores de signos; no sustituye un certificado completo. */
double projected_residual(const double *a, const double *l, size_t n, unsigned probes, uint64_t seed,
                          long double *workspace)
{
    /* Comprueba punteros o dimensiones requeridos antes de acceder a memoria. */
    if (!a || !l || !workspace || !n || !probes)
        /* Representa validacion numerica fallida con un residuo infinito. */
        return INFINITY;
    /* Divide el espacio de trabajo: x ocupa los primeros n valores e y los siguientes n. */
    long double *x = workspace, *y = workspace + n;
    /* Recorre las filas del intervalo indicado. */
    for (size_t i = 0; i < n; ++i)
    {
        /* Comprueba finitud y/o tolerancias para que NaN e infinito no pasen la validacion. */
        if (!isfinite(l[i * n + i]) || l[i * n + i] <= 0)
            /* Representa validacion numerica fallida con un residuo infinito. */
            return INFINITY;
        /* Recorre las columnas del intervalo indicado. */
        for (size_t j = 0; j < n; ++j)
            /* Comprueba finitud y/o tolerancias para que NaN e infinito no pasen la validacion. */
            if (!isfinite(a[i * n + j]) || (j <= i && !isfinite(l[i * n + j])))
                /* Representa validacion numerica fallida con un residuo infinito. */
                return INFINITY;
    }
    /* Define worst: peor residuo proyectado. */
    long double worst = 0;
    /* Repite la validacion con otro vector de signos reproducible. */
    for (unsigned p = 0; p < probes; ++p)
    {
        /* Recorre las filas del intervalo indicado. */
        for (size_t i = 0; i < n; ++i)
            /* Elige un signo reproducible para la componente i del vector de prueba. */
            x[i] = (next_random(&seed) & 1) ? 1 : -1;
        /* Recorre las columnas del intervalo indicado. */
        for (size_t j = 0; j < n; ++j)
        {
            /* Inicia la componente j de y=L^T*x. */
            y[j] = 0;
            /* Recorre las filas del intervalo indicado. */
            for (size_t i = j; i < n; ++i)
                /* Acumula la columna j de L multiplicada por x, es decir L^T*x. */
                y[j] += (long double)l[i * n + j] * x[i];
        }
        /* Define error: norma del error proyectado; norm: norma de A*x. */
        long double error = 0, norm = 0;
        /* Recorre las filas del intervalo indicado. */
        for (size_t i = 0; i < n; ++i)
        {
            /* Define ax: componente de A*x; ly: componente de L*y. */
            long double ax = 0, ly = 0;
            /* Recorre las columnas del intervalo indicado. */
            for (size_t j = 0; j < n; ++j)
                /* Calcula la componente i del producto A*x. */
                ax += (long double)a[i * n + j] * x[j];
            /* Recorre exclusivamente el triangulo inferior, que contiene el factor L. */
            for (size_t j = 0; j <= i; ++j)
                /* Calcula la componente i de L*y usando solo el triangulo inferior. */
                ly += (long double)l[i * n + j] * y[j];
            /* Acumula la norma euclidea del error mediante hypotl para evitar cuadrados directos. */
            error = hypotl(error, ax - ly);
            /* Acumula la norma euclidea de A*x para normalizar la prueba. */
            norm = hypotl(norm, ax);
        }
        /* Comprueba finitud y/o tolerancias para que NaN e infinito no pasen la validacion. */
        if (!isfinite(error) || !isfinite(norm) || norm == 0)
            /* Representa validacion numerica fallida con un residuo infinito. */
            return INFINITY;
        /* Calcula el residuo relativo de esta direccion de prueba. */
        long double ratio = error / norm;
        /* Conserva el peor residuo entre los vectores de prueba. */
        if (ratio > worst)
            /* Actualiza el maximo observado. */
            worst = ratio;
    }
    /* Devuelve el mayor residuo proyectado, convertido a double. */
    return (double)worst;
}
