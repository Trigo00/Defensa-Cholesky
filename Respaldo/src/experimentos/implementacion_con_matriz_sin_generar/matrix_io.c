// Declaraciones de las funciones y códigos de estado de entrada/salida.
#include "matrix_io.h"

// Reconoce espacios y saltos de línea al terminar de leer.
#include <ctype.h>
// Errores de la biblioteca C (incluido para posibles extensiones).
#include <errno.h>
// Comprueba que los valores leídos sean finitos.
#include <math.h>
// SIZE_MAX permite detectar tamaños demasiado grandes.
#include <stdint.h>
// Apertura, lectura y escritura de archivos.
#include <stdio.h>
// Reserva y liberación de memoria.
#include <stdlib.h>

// Lee un archivo de texto con dimensiones y valores de la matriz.
MatrixIoStatus matrix_read_text(const char *path, double **values, size_t *rows, size_t *columns)
{
    // Comprueba punteros antes de escribir a través de ellos.
    if (!path || !values || !rows || !columns)
        // Rechaza una llamada con argumentos inválidos.
        return MATRIX_IO_FORMAT;
    // La salida empieza en NULL por si la lectura falla.
    *values = NULL;
    // Inicializa las dimensiones de salida en cero.
    *rows = *columns = 0;

    // Abre el archivo de entrada en modo lectura.
    FILE *file = fopen(path, "r");
    // Si no se puede abrir, informa el error.
    if (!file)
        // Devuelve fallo de apertura.
        return MATRIX_IO_OPEN;

    // Dimensiones que deben aparecer al comienzo del archivo.
    size_t r, c;
    // Lee primero filas y columnas.
    if (fscanf(file, "%zu %zu", &r, &c) != 2)
    {
        // Cierra el archivo antes de salir por error.
        fclose(file);
        // Faltan dimensiones o no tienen el formato esperado.
        return MATRIX_IO_FORMAT;
    }
    // Rechaza matrices vacías y tamaños que desbordan size_t.
    if (r == 0 || c == 0 || c > SIZE_MAX / r || r * c > SIZE_MAX / sizeof(double))
    {
        // Cierra el archivo cuando el tamaño no es válido.
        fclose(file);
        // No intenta reservar un tamaño imposible.
        return MATRIX_IO_DIMENSIONS;
    }

    // Cantidad total de valores a leer.
    size_t cells = r * c;
    // Reserva espacio para la matriz en memoria contigua.
    double *data = malloc(cells * sizeof(*data));
    // Si no hay memoria disponible, aborta la lectura.
    if (!data)
    {
        // Cierra el archivo abierto.
        fclose(file);
        // Devuelve el error de memoria.
        return MATRIX_IO_MEMORY;
    }

    // Mientras no se detecte un problema, la lectura sigue.
    MatrixIoStatus status = MATRIX_IO_OK;
    // Lee todos los valores, uno por uno.
    for (size_t i = 0; i < cells; ++i)
    {
        // Espera un double por cada posición de la matriz.
        if (fscanf(file, "%lf", &data[i]) != 1)
        {
            // Si falta un número o es inválido, falla el formato.
            status = MATRIX_IO_FORMAT;
            // Detiene la lectura al primer error.
            break;
        }
        // No se aceptan NaN ni infinito como valores de entrada.
        if (!isfinite(data[i]))
        {
            // Identifica el error numérico.
            status = MATRIX_IO_NONFINITE;
            // No necesita seguir leyendo.
            break;
        }
    }

    // Revisa que no queden datos adicionales al final.
    if (status == MATRIX_IO_OK)
    {
        // Carácter usado para recorrer lo que queda del archivo.
        int ch;
        // Avanza hasta encontrar algo que no sea espacio.
        do
            // Lee el siguiente carácter.
            ch = fgetc(file);
        // Ignora espacios, tabulaciones y saltos de línea.
        while (ch != EOF && isspace((unsigned char)ch));
        // Si quedó texto, el archivo tenía más datos de los esperados.
        if (ch != EOF)
            // Marca el formato como inválido.
            status = MATRIX_IO_FORMAT;
    }

    // También controla errores de lectura del stream.
    if (ferror(file) && status == MATRIX_IO_OK)
        // Marca el error si todavía no había otro.
        status = MATRIX_IO_FORMAT;
    // Siempre cierra el archivo después de leer.
    fclose(file);
    // Si hubo un fallo, no entrega datos parciales.
    if (status != MATRIX_IO_OK)
    {
        // Libera el arreglo reservado.
        free(data);
        // Devuelve el código específico del problema.
        return status;
    }

    // Entrega al llamador el arreglo ya leído.
    *values = data;
    // Devuelve la cantidad de filas.
    *rows = r;
    // Devuelve la cantidad de columnas.
    *columns = c;
    // La lectura terminó correctamente.
    return MATRIX_IO_OK;
}

// Escribe una matriz en el formato de texto usado por el lector.
MatrixIoStatus matrix_write_text(const char *path, const double *values, size_t rows, size_t columns,
                                 int lower_only)
{
    // Comprueba los punteros y las dimensiones.
    if (!path || !values || rows == 0 || columns == 0)
        // No escribe una matriz vacía o sin datos.
        return MATRIX_IO_WRITE;
    // Abre el destino; si ya existía, se reemplaza.
    FILE *file = fopen(path, "w");
    // Si no puede abrirlo, informa el error.
    if (!file)
        // No hay un archivo de salida disponible.
        return MATRIX_IO_OPEN;

    // Escribe las dos dimensiones en la primera línea.
    int failed = fprintf(file, "%zu %zu\n", rows, columns) < 0;
    // Escribe una fila completa en cada línea.
    for (size_t i = 0; i < rows && !failed; ++i)
    {
        // Avanza por las columnas de la fila actual.
        for (size_t j = 0; j < columns; ++j)
        {
            // Si se pide solo L, fuerza a cero la parte superior.
            double value = lower_only && j > i ? 0.0 : values[i * columns + j];
            // Escribe con 17 cifras significativas para conservar precisión double.
            if (fprintf(file, j + 1 == columns ? "%.17g" : "%.17g ", value) < 0)
            {
                // Registra el primer error de escritura.
                failed = 1;
                // Interrumpe la fila si no se pudo escribir.
                break;
            }
        }
        // Agrega el salto de línea después de cada fila.
        if (!failed && fputc('\n', file) == EOF)
            // Marca fallo si tampoco se pudo escribir el salto.
            failed = 1;
    }
    // Comprueba incluso los errores que aparecen al cerrar.
    if (fclose(file) != 0)
        // Conserva el error de cierre.
        failed = 1;
    // Devuelve el resultado de toda la escritura.
    return failed ? MATRIX_IO_WRITE : MATRIX_IO_OK;
}

// Traduce los códigos de estado a mensajes legibles.
const char *matrix_io_message(MatrixIoStatus status)
{
    // Elige un texto según el resultado de lectura o escritura.
    switch (status)
    {
    // La operación terminó bien.
    case MATRIX_IO_OK:
        return "sin error";
    // El archivo no se pudo abrir.
    case MATRIX_IO_OPEN:
        return "no se pudo abrir el archivo";
    // Hubo un problema de formato.
    case MATRIX_IO_FORMAT:
        return "formato invalido o cantidad incorrecta de valores";
    // Las dimensiones son inválidas o exceden memoria.
    case MATRIX_IO_DIMENSIONS:
        return "dimensiones invalidas o demasiado grandes";
    // Apareció NaN o infinito.
    case MATRIX_IO_NONFINITE:
        return "la matriz contiene NaN o infinito";
    // No se pudo reservar memoria.
    case MATRIX_IO_MEMORY:
        return "no hay memoria suficiente";
    // Falló la escritura del archivo.
    case MATRIX_IO_WRITE:
        return "fallo al escribir el archivo";
    }
    // Mensaje de respaldo para códigos desconocidos.
    return "error desconocido";
}
