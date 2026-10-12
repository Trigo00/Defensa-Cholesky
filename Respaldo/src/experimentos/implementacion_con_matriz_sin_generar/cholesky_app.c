// Funciones de Cholesky secuencial y comprobación del resultado.
#include "cholesky.h"
// Implementación MPI y estructura del reparto de columnas.
#include "cholesky_mpi.h"
// Lectura y escritura de matrices de texto.
#include "matrix_io.h"

// Límites de los enteros usados en los conteos de MPI.
#include <limits.h>
// Operaciones y comprobaciones con números de punto flotante.
#include <math.h>
// Funciones de comunicación entre procesos.
#include <mpi.h>
// Entrada y salida por consola.
#include <stdio.h>
// Reserva y liberación de memoria.
#include <stdlib.h>
// Comparación de argumentos de texto.
#include <string.h>

// Códigos de salida: cada error tiene un número distinto.
enum
{
    APP_OK = 0,
    APP_USAGE = 2,
    APP_INPUT = 3,
    APP_DIMENSIONS = 4,
    APP_NONFINITE = 5,
    APP_NONSYMMETRIC = 6,
    APP_NOT_POSITIVE_DEFINITE = 7,
    APP_OUTPUT = 8,
    APP_MEMORY = 9
};

// Reserva memoria inicializada a cero y evita desbordar el tamaño solicitado.
static void *checked_calloc(size_t count, size_t size)
{
    // Comprueba la multiplicación antes de reservar memoria.
    if (size && count > (size_t)-1 / size)
        // Si el tamaño no es representable, no reserva nada.
        return NULL;
    // Incluso para cero elementos, pide un bloque mínimo a calloc.
    return calloc(count ? count : 1, size);
}

// Prepara los tamaños y desplazamientos que necesita Scatterv y Gatherv.
static void build_counts(int n, int processes, int *counts, int *offsets)
{
    // Desplazamiento acumulado en el arreglo empaquetado.
    int offset = 0;
    // Calcula cuántos datos enviará o recibirá cada rango.
    for (int r = 0; r < processes; ++r)
    {
        // El reparto cíclico da una columna extra a los primeros n % P rangos.
        int columns = n / processes + (r < n % processes);
        // Cada columna contiene n valores double.
        counts[r] = n * columns;
        // El bloque del rango empieza donde terminó el anterior.
        offsets[r] = offset;
        // Avanza hasta el próximo bloque.
        offset += counts[r];
    }
}

// Reordena la matriz completa en bloques, uno por proceso.
static void pack_cyclic(const double *full, double *packed, int n, int processes, const int *offsets)
{
    // Procesa los rangos en el mismo orden usado por MPI.
    for (int r = 0; r < processes; ++r)
    {
        // Cantidad de columnas propias de este rango.
        int columns = n / processes + (r < n % processes);
        // Recorre todas las filas de las columnas asignadas.
        for (int i = 0; i < n; ++i)
            // Recorre las columnas locales.
            for (int c = 0; c < columns; ++c)
                // La global de la columna local c es r + c * processes.
                packed[offsets[r] + (size_t)i * columns + c] = full[(size_t)i * n + r + c * processes];
    }
}

// Invierte el empaquetado para reconstruir la matriz en rango 0.
static void unpack_cyclic(const double *packed, double *full, int n, int processes, const int *offsets)
{
    // Recorre cada bloque recibido.
    for (int r = 0; r < processes; ++r)
    {
        // Recupera cuántas columnas tenía ese proceso.
        int columns = n / processes + (r < n % processes);
        // Recorre las filas del bloque local.
        for (int i = 0; i < n; ++i)
            // Recorre sus columnas.
            for (int c = 0; c < columns; ++c)
                // Copia cada valor a su posición global en la matriz.
                full[(size_t)i * n + r + c * processes] = packed[offsets[r] + (size_t)i * columns + c];
    }
}

// Punto de entrada: lee A, reparte columnas, factoriza y escribe L.
int main(int argc, char **argv)
{
    // Inicializa MPI antes de consultar rango y cantidad de procesos.
    MPI_Init(&argc, &argv);
    // Identificadores de este proceso y del comunicador.
    int rank, processes;
    // Obtiene el rango actual, desde 0 hasta P-1.
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    // Obtiene la cantidad de procesos que participan.
    MPI_Comm_size(MPI_COMM_WORLD, &processes);

    // La cuarta opción activa el cálculo del residuo.
    int validate = argc == 4 && strcmp(argv[3], "--validate") == 0;
    // Partimos sin errores.
    int status = APP_OK;
    // Acepta entrada y salida, con --validate opcional.
    if (argc != 3 && !validate)
    {
        // Solo el rango 0 muestra los mensajes al usuario.
        if (!rank)
            // Informa cómo debe invocarse el programa.
            fprintf(stderr, "Uso: %s MATRIZ_A.txt FACTOR_L.txt [--validate]\n", argv[0]);
        // Marca argumentos incorrectos.
        status = APP_USAGE;
    }

    // Buffers completos y empaquetados; se reservan según se necesiten.
    double *full = NULL, *original = NULL, *packed = NULL;
    // Dimensiones obtenidas del archivo.
    size_t rows = 0, columns = 0;
    // Orden de la matriz que usarán todos los procesos.
    int n = 0;
    // La entrada completa se lee solamente en el rango 0.
    if (!rank && status == APP_OK)
    {
        // Lee la matriz de texto y sus dimensiones.
        MatrixIoStatus io = matrix_read_text(argv[1], &full, &rows, &columns);
        // Si no se pudo leer correctamente, no sigue con Cholesky.
        if (io != MATRIX_IO_OK)
        {
            // Muestra el motivo que devolvió el lector.
            fprintf(stderr, "Error de entrada: %s (%s).\n", matrix_io_message(io), argv[1]);
            // Distingue valores no finitos de otros errores de lectura.
            status = io == MATRIX_IO_NONFINITE ? APP_NONFINITE : APP_INPUT;
        }
        // Los conteos de esta versión MPI deben caber en int.
        else if (rows != columns || rows > INT_MAX || rows * columns > INT_MAX)
        {
            // Explica la restricción antes de abandonar.
            fprintf(
                stderr,
                "Error de dimensiones: la matriz debe ser cuadrada, no vacia y compatible con conteos MPI.\n");
            // Guarda el error de dimensiones.
            status = APP_DIMENSIONS;
        }
        // Exige simetría exacta y valores finitos.
        else if (!symmetric_finite(full, rows))
        {
            // El mensaje aclara que se compara A[i,j] con A[j,i].
            fprintf(stderr,
                    "Error de entrada: la matriz debe ser simetrica (igualdad exacta A[i,j]=A[j,i]).\n");
            // La matriz no cumple la condición de entrada.
            status = APP_NONSYMMETRIC;
        }
        else
        {
            // Convierte el orden a int después de comprobar su rango.
            n = (int)rows;
            // Guarda una copia solo cuando se pidió validación.
            if (validate)
            {
                // Reserva el espacio para la matriz original.
                original = checked_calloc(rows * columns, sizeof(*original));
                // Comprueba que la reserva haya funcionado.
                if (original)
                    // Conserva A antes de que la factorización la sobrescriba.
                    memcpy(original, full, rows * columns * sizeof(*original));
                else
                    // Si falta memoria, se informa al resto de procesos.
                    status = APP_MEMORY;
            }
        }
    }

    // Comunica a todos si la entrada es válida.
    MPI_Bcast(&status, 1, MPI_INT, 0, MPI_COMM_WORLD);
    // Comparte el tamaño para que todos creen su reparto.
    MPI_Bcast(&n, 1, MPI_INT, 0, MPI_COMM_WORLD);
    // Si hubo un error previo, todos terminan juntos.
    if (status != APP_OK)
    {
        // Libera lo que haya llegado a reservar rango 0.
        free(full);
        // Libera la copia de referencia si existe.
        free(original);
        // Cierra MPI sin entrar al kernel.
        MPI_Finalize();
        // Devuelve el código de error.
        return status;
    }

    // Distribución cíclica de una columna por turno (b = 1).
    Layout layout = layout_create(n, 1, MPI_COMM_WORLD);
    // Matriz local: n filas por la cantidad de columnas propias.
    double *local = checked_calloc((size_t)n * layout.cols, sizeof(*local));
    // Buffer para difundir la columna activa.
    double *column = checked_calloc((size_t)n, sizeof(*column));
    // Valores de la columna adaptados al orden de columnas locales.
    double *local_column = checked_calloc((size_t)layout.cols, sizeof(*local_column));
    // Número de datos por proceso, para las colectivas variables.
    int *counts = checked_calloc((size_t)processes, sizeof(*counts));
    // Desplazamiento inicial de cada bloque empaquetado.
    int *offsets = checked_calloc((size_t)processes, sizeof(*offsets));
    // Detecta si falló alguna reserva de este proceso.
    int allocation_failed = !local || !column || !local_column || !counts || !offsets;
    // Consulta colectivamente si falló al menos un proceso.
    MPI_Allreduce(&allocation_failed, &status, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
    // Convierte ese resultado al código de error de memoria.
    status = status ? APP_MEMORY : APP_OK;

    // Rango 0 necesita además un arreglo para empaquetar la matriz.
    if (!rank && status == APP_OK)
    {
        // Reserva un espacio temporal de n por n.
        packed = checked_calloc((size_t)n * n, sizeof(*packed));
        // Verifica la última reserva del rango 0.
        if (!packed)
            // Indica que no se puede continuar por falta de memoria.
            status = APP_MEMORY;
    }
    // Propaga el estado del empaquetado a todos los rangos.
    MPI_Bcast(&status, 1, MPI_INT, 0, MPI_COMM_WORLD);
    // Solo se distribuye y factoriza si todas las reservas funcionaron.
    if (status == APP_OK)
    {
        // Prepara los conteos y desplazamientos de cada bloque.
        build_counts(n, processes, counts, offsets);
        // La matriz inicial solo existe completa en rango 0.
        if (!rank)
            // La reordena según los propietarios cíclicos.
            pack_cyclic(full, packed, n, processes, offsets);
        // Distribuye a cada proceso sus columnas locales.
        MPI_Scatterv(packed, counts, offsets, MPI_DOUBLE, local, n * layout.cols, MPI_DOUBLE, 0,
                     MPI_COMM_WORLD);

        // Cholesky right-looking MPI: cada dueño calcula su columna y la difunde.
        /* Kernel validado: right-looking, reparto ciclico 1D y vector local. */
        // Ejecuta el kernel y registra si este rango detectó un fallo.
        int local_failure = cholesky_mpi_local(local, column, local_column, &layout, NULL) != 0;
        // Espacio para reunir los fallos de todos.
        int any_failure = 0;
        // Si cualquier rango falló, todos reciben el aviso.
        MPI_Allreduce(&local_failure, &any_failure, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
        // No se intenta reunir un factor inválido.
        if (any_failure)
            // Registra que Cholesky no pudo completar la factorización.
            status = APP_NOT_POSITIVE_DEFINITE;
        else
        {
            // Devuelve al rango 0 las columnas ya factorizadas.
            MPI_Gatherv(local, n * layout.cols, MPI_DOUBLE, packed, counts, offsets, MPI_DOUBLE, 0,
                        MPI_COMM_WORLD);
            // Solo el rango 0 reconstruye y escribe el factor.
            if (!rank)
            {
                // Coloca las columnas recibidas en sus índices globales.
                unpack_cyclic(packed, full, n, processes, offsets);
                // La comprobación es opcional.
                if (validate)
                {
                    // Compara A original con L por L transpuesta mediante residuo relativo.
                    double residual = relative_residual(original, full, (size_t)n);
                    // Muestra el residuo de Frobenius calculado.
                    fprintf(stderr, "Validacion: residuo relativo Frobenius = %.12g\n", residual);
                    // Rechaza resultados no finitos o con residuo mayor a 1e-12.
                    if (!isfinite(residual) || residual > 1e-12)
                        // Marca la validación fallida.
                        status = APP_NOT_POSITIVE_DEFINITE;
                }
                // Solo escribe el archivo cuando no hubo errores.
                if (status == APP_OK)
                {
                    // Escribe el triángulo inferior de L, con ceros arriba.
                    MatrixIoStatus io = matrix_write_text(argv[2], full, (size_t)n, (size_t)n, 1);
                    // Comprueba el resultado de la escritura.
                    if (io != MATRIX_IO_OK)
                    {
                        // Informa la causa y el nombre del archivo de salida.
                        fprintf(stderr, "Error de salida: %s (%s).\n", matrix_io_message(io), argv[2]);
                        // Marca el error de escritura.
                        status = APP_OUTPUT;
                    }
                }
            }
        }
    }

    // Todos deben terminar con el mismo estado final.
    MPI_Bcast(&status, 1, MPI_INT, 0, MPI_COMM_WORLD);
    // Rango 0 da el motivo del fallo numérico.
    if (!rank && status == APP_NOT_POSITIVE_DEFINITE)
        // No se obtuvo un factor válido para la matriz de entrada.
        fprintf(stderr,
                "Fallo de Cholesky: la matriz no es definida positiva o produjo un pivote invalido.\n");
    // Rango 0 informa un fallo de reserva.
    if (!rank && status == APP_MEMORY)
        // No hubo memoria suficiente para el flujo distribuido.
        fprintf(stderr, "Error: memoria insuficiente para preparar la matriz distribuida.\n");

    // Libera la matriz completa del rango 0.
    free(full);
    // Libera la copia que se usó para validar.
    free(original);
    // Libera el buffer de distribución/reunión.
    free(packed);
    // Libera las columnas del proceso.
    free(local);
    // Libera el buffer de columna global.
    free(column);
    // Libera el vector para acceso local.
    free(local_column);
    // Libera los conteos de MPI.
    free(counts);
    // Libera los desplazamientos de MPI.
    free(offsets);
    // Termina la sesión MPI.
    MPI_Finalize();
    // Devuelve cero si todo salió bien, u otro código si hubo error.
    return status;
}
