/* Explora propiedad por grupos de columnas. No implementa paneles ni kernels BLAS-3.
 * Lectura: ver docs/guia_codigo.md. Los comentarios explican instrucciones logicas;
 * las llaves y las continuaciones de una misma instruccion comparten explicacion.
 */
/* Declara generadores, kernels secuenciales y residuos. */
#include "cholesky.h"
/* Reutiliza conversiones y comparacion de factores para evitar codigo duplicado. */
#include "bench_utils.h"
/* Declara Layout, perfiles y kernels distribuidos; incluye la API MPI. */
#include "cholesky_mpi.h"
/* Entrada/salida de mensajes, archivos y registros CSV. */
#include <stdio.h>
/* Reserva/liberacion de memoria, conversion numerica y terminacion del proceso. */
#include <stdlib.h>
/* Copia y comparacion de buffers o argumentos. */
#include <string.h>
/* Funciones matematicas y controles de finitud: sqrt, fabs, isfinite, NAN e INFINITY. */
#include <math.h>
/* Permite detectar errores de conversion o interrupciones de llamadas POSIX. */
#include <errno.h>
/* Reserva memoria; pide al menos un byte para admitir rangos sin columnas. */
static void *alloc(size_t bytes)
{
    /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
    void *a = malloc(bytes ? bytes : 1);
    /* Detecta que no se pudo obtener el recurso solicitado; no se usa un puntero nulo. */
    if (!a)
        /* Aborta el comunicador para que otros rangos no queden esperando tras el fallo. */
        MPI_Abort(MPI_COMM_WORLD, 3);
    /* Entrega la memoria reservada al llamador, que debera liberarla. */
    return a;
}
/* Verifica propietarios, indices y conteos; b=1 debe coincidir con el reparto ciclico simple. */
static int mapping_test(int n)
{
    /* Define bad: fallo de la ejecucion actual. */
    int bad = 0;
    /* Define blocks: granularidades de propiedad ensayadas. */
    const int blocks[] = {1, 2, 4, 8, 16, 32, 64};
    /* Recorre las granularidades de bloques ensayadas. */
    for (int v = 0; v < 7; ++v)
    {
        /* Construye el mapa local con el reparto de columnas indicado. */
        Layout d = layout_block_create(n, blocks[v], MPI_COMM_WORLD),
               /* Construye el reparto ciclico simple para contrastar el caso b=1. */
               old = layout_create(n, 1, MPI_COMM_WORLD);
        /* Define count: cantidad de columnas contabilizadas. */
        int count = 0;
        /* Recorre los indices que contribuyen a esta suma o comprobacion. */
        for (int k = 0; k < n; ++k)
        {
            /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
            bad |= layout_before(&d, k) != count;
            /* Define owner: propietario de la columna activa. */
            int owner = (k / blocks[v]) % d.p;
            /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
            bad |= layout_owner(&d, k) != owner;
            /* Comprueba si la columna pertenece al rango actual. */
            if (owner == d.rank)
            {
                /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                bad |= layout_global(&d, count) != k;
                /* Cuenta una columna global que pertenece a este proceso. */
                ++count;
            }
            /* Con b=1 el nuevo mapa debe coincidir con la distribucion ciclica simple. */
            if (blocks[v] == 1)
                /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                bad |= layout_owner(&d, k) != layout_owner(&old, k) ||
                       /* Comprueba tambien que ambos mapas cuentan las mismas columnas anteriores. */
                       layout_before(&d, k) != layout_before(&old, k);
        }
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        bad |= count != d.cols || layout_before(&d, n) != count;
        /* Con b=1 el nuevo mapa debe coincidir con la distribucion ciclica simple. */
        if (blocks[v] == 1)
            /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
            bad |= d.cols != old.cols;
    }
    /* Define any: fallo combinado de todos los rangos. */
    int any;
    /* Entrega a todos el mayor estado/fallo; permite detectar si algun rango fallo. */
    MPI_Allreduce(&bad, &any, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    /* Propaga el estado acumulado: cero indica que no hubo fallos. */
    return any;
}
/* Ejecuta un caso del banco, conserva las preparaciones y devuelve si hubo algun fallo. */
static int run(int n, int reps, int testing, int pair)
{
    /* Define rank: rango actual; p: cantidad de procesos. */
    int rank, p;
    /* Consulta el identificador de este proceso dentro del comunicador. */
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    /* Consulta cuantos procesos participan en el comunicador. */
    MPI_Comm_size(MPI_COMM_WORLD, &p);
    /* Define bytes: bytes de una matriz densa. */
    size_t bytes = (size_t)n * n * sizeof(double);
    /* Define failed: acumulador de fallos. */
    int failed = mapping_test(n);
    /* Define original: matriz A sin factorizar; ref: factor secuencial de referencia. */
    double *original = NULL, *ref = NULL;
    /* Define check: espacio para la validacion proyectada. */
    long double *check = NULL;
    /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
    if (!rank)
    {
        /* Reserva matriz A sin factorizar; el llamador liberara el buffer al terminar. */
        original = alloc(bytes);
        /* Reserva factor secuencial de referencia; el llamador liberara el buffer al terminar. */
        ref = alloc(bytes);
        /* Reserva espacio para la validacion proyectada; el llamador liberara el buffer al terminar. */
        check = alloc(2 * (size_t)n * sizeof(long double));
        /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
        double *w = alloc(n * sizeof(double));
        /* Construye la matriz SPD reproducible con la semilla indicada. */
        generate_spd(original, n, 2026);
        /* Copia los datos sin operaciones numericas; prepara una entrada o referencia independiente. */
        memcpy(ref, original, bytes);
        /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
        failed |= cholesky_right_buffered(ref, n, w) != 0;
        /* Libera w; free(NULL) es valido para buffers que este rango no reservo. */
        free(w);
    }
    /* Define blocks: granularidades de propiedad ensayadas. */
    const int blocks[] = {1, 2, 4, 8, 16, 32, 64};
    /* Define variants: numero de variantes o funciones disponibles. */
    int variants = pair ? 2 : 7;
    /* Incluye rep=0 como preparacion; rep=1..reps son las repeticiones utiles. */
    for (int rep = 0; rep <= reps; ++rep)
        /* Recorre las posiciones del orden de ejecucion de esta repeticion. */
        for (int pos = 0; pos < variants; ++pos)
        {
            /* Define index: indice rotado de variante. */
            int index = (pos + (rep ? rep - 1 : 0)) % variants;
            /* Define b: columnas consecutivas por turno. */
            int b = pair ? (index ? 4 : 1) : blocks[index];
            /* Espera a todos los rangos antes de iniciar la medicion; no sincroniza sus relojes. */
            MPI_Barrier(MPI_COMM_WORLD);
            /* Define t: instante local o estructura del reloj. */
            double t[5];
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t[0] = MPI_Wtime();
            /* Construye el mapa local con el reparto de columnas indicado. */
            Layout d = layout_block_create(n, b, MPI_COMM_WORLD);
            /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
            int *columns = alloc(d.cols * sizeof(int)), *counts = alloc(p * sizeof(int)),
                /* Reserva el vector de desplazamientos de los segmentos por rango. */
                *displs = alloc(p * sizeof(int));
            /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
            for (int c = 0; c < d.cols; ++c)
                /* Guarda el indice global asociado a la columna local c. */
                columns[c] = layout_global(&d, c);
            /* Define offset: inicio del siguiente segmento empaquetado. */
            int offset = 0;
            /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
            for (int r = 0; r < p; ++r)
            {
                /* Define other: metadatos de otro propietario. */
                Layout other = d;
                /* Configura una copia del mapa para inspeccionar otro rango sin comunicacion. */
                other.rank = r;
                /* Calcula cuantos elementos de matriz corresponden a este rango. */
                counts[r] = n * layout_before(&other, n);
                /* Guarda el inicio del segmento de este rango. */
                displs[r] = offset;
                /* Avanza al segmento del siguiente propietario en el buffer empaquetado. */
                offset += counts[r];
            }
            /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
            double *local = alloc((size_t)n * d.cols * sizeof(double)), *col = alloc(n * sizeof(double)),
                   /* Reserva el vector auxiliar con una entrada por columna propia. */
                   *work = alloc(d.cols * sizeof(double));
            /* Reserva los buffers indicados; el tamano usa elementos por sizeof(tipo) para obtener bytes. */
            double *packed = rank ? NULL : alloc(bytes), *full = rank ? NULL : alloc(bytes);
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t[1] = MPI_Wtime();
            /* Genera las columnas del mapa por bloques, sin construir A en rango 0. */
            generate_spd_selected(local, n, 2026, columns, d.cols);
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t[2] = MPI_Wtime();
            /* Ejecuta el kernel seleccionado y guarda el estado de la factorizacion. */
            int bad = cholesky_mpi_local(local, col, work, &d, NULL) != 0;
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t[3] = MPI_Wtime();
            /* Reune cantidades distintas de columnas en rango 0, en los segmentos indicados. */
            MPI_Gatherv(local, n * d.cols, MPI_DOUBLE, packed, counts, displs, MPI_DOUBLE, 0, d.comm);
            /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
            if (!rank)
                /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
                for (int r = 0; r < p; ++r)
                {
                    /* Define other: metadatos de otro propietario. */
                    Layout other = d;
                    /* Configura una copia del mapa para inspeccionar otro rango sin comunicacion. */
                    other.rank = r;
                    /* Define m: numero de columnas locales. */
                    int m = counts[r] / n;
                    /* Recorre las filas del intervalo indicado. */
                    for (int i = 0; i < n; ++i)
                        /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
                        for (int c = 0; c < m; ++c)
                            /* Prepara el destino global de la entrada recibida; la expresion continua en la siguiente linea. */
                            full[(size_t)i * n + layout_global(&other, c)] =
                                /* Copia una entrada global al segmento por filas del propietario correspondiente. */
                                packed[displs[r] + (size_t)i * m + c];
                }
            /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
            t[4] = MPI_Wtime();
            /* Define updates: actualizaciones teoricas propias. */
            unsigned long long updates = 0;
            /* Recorre las columnas locales del intervalo indicado; c no es un indice global. */
            for (int c = 0; c < d.cols; ++c)
            {
                /* Define k: indice lineal o global usado en el calculo. */
                unsigned long long k = columns[c];
                /* Suma k*(n-k), el trabajo teorico acumulado de la columna global k. */
                updates += k * (n - k);
            }
            /* Define maxwork: mayor trabajo entre rangos; sumwork: trabajo agregado. */
            unsigned long long maxwork = 0, sumwork = 0;
            /* Obtiene en rango 0 el mayor conteo de trabajo de un proceso. */
            MPI_Reduce(&updates, &maxwork, 1, MPI_UNSIGNED_LONG_LONG, MPI_MAX, 0, d.comm);
            /* Suma el trabajo teorico de todos los procesos en rango 0. */
            MPI_Reduce(&updates, &sumwork, 1, MPI_UNSIGNED_LONG_LONG, MPI_SUM, 0, d.comm);
            /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
            if (!rank)
            {
                /* Mide el residuo proyectado con ocho vectores y semilla 91827, fuera del kernel. */
                double res = projected_residual(original, full, n, 8, 91827, check), diff = 0;
                /* Compara el triangulo inferior con la referencia mediante la utilidad compartida. */
                diff = factor_difference(full, ref, n);
                /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                bad |= !isfinite(res) || res > 1e-12 || diff > 1e-12;
                /* Selecciona el control de prueba: matriz conocida, entrada invalida o validacion completa. */
                if (testing)
                {
                    /* Reconstruye LL^T para medir el residuo completo; -1 indica que se omitio por tamano. */
                    double exact = relative_residual(original, full, n);
                    /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
                    bad |= !isfinite(exact) || exact > 1e-12;
                }
                /* Publica solo repeticiones utiles y respeta los selectores de prueba/perfil indicados. */
                if (rep && !testing)
                    /* Publica resultados del caso en el formato CSV original; las preparaciones se filtran antes. */
                    printf("%d,%d,%d,%d,%d,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g\n", n, p, rep,
                           pos + 1, b, t[1] - t[0], t[2] - t[1], t[3] - t[2], t[4] - t[3], t[4] - t[0], res,
                           diff, sumwork ? (double)maxwork * p / sumwork : 1.);
            }
            /* Define any: fallo combinado de todos los rangos. */
            int any;
            /* Entrega a todos el mayor estado/fallo; permite detectar si algun rango fallo. */
            MPI_Allreduce(&bad, &any, 1, MPI_INT, MPI_MAX, d.comm);
            /* Acumula el fallo sin borrar errores de casos anteriores; se propagara al codigo de salida. */
            failed |= any;
            /* Libera columns; free(NULL) es valido para buffers que este rango no reservo. */
            free(columns);
            /* Libera counts; free(NULL) es valido para buffers que este rango no reservo. */
            free(counts);
            /* Libera displs; free(NULL) es valido para buffers que este rango no reservo. */
            free(displs);
            /* Libera local; free(NULL) es valido para buffers que este rango no reservo. */
            free(local);
            /* Libera col; free(NULL) es valido para buffers que este rango no reservo. */
            free(col);
            /* Libera work; free(NULL) es valido para buffers que este rango no reservo. */
            free(work);
            /* Libera packed; free(NULL) es valido para buffers que este rango no reservo. */
            free(packed);
            /* Libera full; free(NULL) es valido para buffers que este rango no reservo. */
            free(full);
        }
    /* Libera original; free(NULL) es valido para buffers que este rango no reservo. */
    free(original);
    /* Libera ref; free(NULL) es valido para buffers que este rango no reservo. */
    free(ref);
    /* Libera check; free(NULL) es valido para buffers que este rango no reservo. */
    free(check);
    /* Define any: fallo combinado de todos los rangos. */
    int any;
    /* Entrega a todos el mayor estado/fallo; permite detectar si algun rango fallo. */
    MPI_Allreduce(&failed, &any, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    /* Propaga el estado acumulado: cero indica que no hubo fallos. */
    return any;
}
/* Punto de entrada: procesa argumentos, ejecuta el caso y devuelve el estado al sistema operativo. */
int main(int argc, char **argv)
{
    /* Inicializa MPI antes de usar comunicadores o colectivas. */
    MPI_Init(&argc, &argv);
    /* Define rank: rango actual. */
    int rank;
    /* Consulta el identificador de este proceso dentro del comunicador. */
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    /* Define result: estado que devolvera el programa. */
    int result = 0;
    /* Comprueba la forma de invocacion y los limites antes de usar los argumentos. */
    if (argc == 2 && !strcmp(argv[1], "--test"))
    {
        /* Define sizes: tamanos de las pruebas. */
        int sizes[] = {1, 2, 3, 7, 31, 65};
        /* Recorre los casos pequenos definidos para verificar el programa. */
        for (int i = 0; i < 6; ++i)
            /* Acumula el resultado del caso de prueba en el estado final. */
            result |= run(sizes[i], 0, 1, 0);
        /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
        if (!rank)
            /* Publica el resultado de las pruebas de este banco. */
            printf("block tests: %s\n", result ? "FAIL" : "PASS");
    }
    /* Ruta alternativa cuando no se cumplio la condicion anterior. */
    else
    {
        /* Convierte el argumento de texto y conserva los limites/valores por defecto del programa. */
        int n = argc > 1 ? parse_bounded(argv[1], 20000) : -1,
            /* Lee repeticiones opcionales y conserva el valor por defecto de este banco. */
            reps = argc > 2 ? parse_bounded(argv[2], 20000) : 7;
        /* Define pair: selector de comparacion b=1 contra b=4. */
        int pair = argc == 4 && !strcmp(argv[3], "pair");
        /* Rechaza dimensiones o cantidades de repeticiones incompatibles con el banco. */
        if (n < 1 || reps < 1 || reps > 28 || reps % (pair ? 2 : 7) || argc > 4 || (argc == 4 && !pair))
        {
            /* Cierra MPI; todos los rangos deben llegar a esta finalizacion. */
            MPI_Finalize();
            /* Informa uso incorrecto de argumentos. */
            return 2;
        }
        /* Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales. */
        if (!rank)
            /* Publica los nombres de columnas CSV en el orden usado por las filas siguientes. */
            puts(
                "N,P,repetition,order,block,allocation_s,generation_s,factor_s,gather_s,total_s,projected_residual,factor_difference,work_imbalance");
        /* Ejecuta el caso solicitado y conserva su resultado. */
        result = run(n, reps, 0, pair);
    }
    /* Cierra MPI; todos los rangos deben llegar a esta finalizacion. */
    MPI_Finalize();
    /* Propaga el estado acumulado: cero indica que no hubo fallos. */
    return result;
}
