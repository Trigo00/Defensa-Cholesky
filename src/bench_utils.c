/* Utilidades comunes de los bancos, explicadas en este archivo C.
 * Se enlaza una sola implementacion para evitar repetir conversiones y validaciones.
 */
/* Declaraciones publicas de estas tres funciones. */
#include "bench_utils.h"
/* Detecta errores de conversion. */
#include <errno.h>
/* Proporciona fabs, fmax, isfinite e INFINITY. */
#include <math.h>
/* Proporciona strtol y strtoull. */
#include <stdlib.h>

/* Utilidades de los bancos: no cambian el algoritmo ni las fronteras temporales. */
/* Acepta solo digitos decimales y entrega uint64_t; 1 indica conversion valida. */
int parse_unsigned(const char *text, uint64_t *value)
{
    /* Rechaza el argumento vacio. */
    if (!*text)
        /* Devuelve falso: la entrada no cumple el contrato comprobado. */
        return 0;
    /* Revisa todos los caracteres del argumento, uno por uno. */
    for (const char *p = text; *p; ++p)
        /* Rechaza signos, espacios y cualquier caracter distinto de un digito decimal. */
        if (*p < '0' || *p > '9')
            /* Devuelve falso: la entrada no cumple el contrato comprobado. */
            return 0;
    /* Define end: puntero al primer caracter no convertido. */
    char *end = NULL;
    /* Limpia el error previo antes de la conversion numerica. */
    errno = 0;
    /* Convierte el argumento de texto y conserva los limites/valores por defecto del programa. */
    unsigned long long parsed = strtoull(text, &end, 10);
    /* Rechaza errores de conversion, caracteres sobrantes o valores fuera del rango permitido. */
    if (errno || *end || parsed > UINT64_MAX)
        /* Devuelve falso: la entrada no cumple el contrato comprobado. */
        return 0;
    /* Escribe el entero validado en la direccion recibida del llamador. */
    *value = (uint64_t)parsed;
    /* Devuelve verdadero: la entrada paso todas las comprobaciones. */
    return 1;
}

/* Convierte un entero decimal entre 1 y maximum; -1 indica argumento invalido. */
int parse_bounded(const char *text, int maximum)
{
    /* Define end: puntero al primer caracter no convertido. */
    char *end;
    /* Limpia el error previo antes de la conversion numerica. */
    errno = 0;
    /* Convierte el argumento de texto y conserva los limites/valores por defecto del programa. */
    long value = strtol(text, &end, 10);
    /* Entrega el entero validado o -1 si la conversion/rango no es aceptable. */
    return errno || !*text || *end || value < 1 || value > maximum ? -1 : (int)value;
}

/* Misma comparación por elemento que empleaban los bancos originales. */
/* Maximo de |L-Lref|/max(1,|Lref|) en el triangulo inferior; no interpreta el triangulo superior. */
double factor_difference(const double *factor, const double *reference, size_t n)
{
    /* Define difference: diferencia maxima frente al factor de referencia. */
    double difference = 0;
    /* Recorre las filas del intervalo indicado. */
    for (size_t i = 0; i < n; ++i)
        /* Recorre exclusivamente el triangulo inferior, que contiene el factor L. */
        for (size_t j = 0; j <= i; ++j)
        {
            /* Define k: indice lineal o global usado en el calculo. */
            size_t k = i * n + j;
            /* Calcula el error relativo de esta entrada, con denominador al menos uno. */
            double delta = fabs(factor[k] - reference[k]) / fmax(1.0, fabs(reference[k]));
            /* Comprueba finitud y/o tolerancias para que NaN e infinito no pasen la validacion. */
            if (!isfinite(delta))
                /* Actualiza la diferencia maxima observada frente al factor de referencia. */
                difference = INFINITY;
            /* Evalua esta alternativa solo si no se cumplio la condicion anterior. */
            else if (delta > difference)
                /* Actualiza la diferencia maxima observada frente al factor de referencia. */
                difference = delta;
        }
    /* Devuelve el mayor error por elemento del triangulo inferior. */
    return difference;
}

