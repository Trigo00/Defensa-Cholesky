/* Cronometro externo POSIX: ejecuta un comando y registra su duracion y codigo de salida.
 * Lectura: ver docs/guia_codigo.md. Los comentarios explican instrucciones logicas;
 * las llaves y las continuaciones de una misma instruccion comparten explicacion.
 */
/* Habilita las declaraciones POSIX, incluido CLOCK_MONOTONIC. */
#define _POSIX_C_SOURCE 200809L
/* Entrada/salida de mensajes, archivos y registros CSV. */
#include <stdio.h>
/* Reserva/liberacion de memoria, conversion numerica y terminacion del proceso. */
#include <stdlib.h>
/* Reloj CLOCK_MONOTONIC y estructura timespec. */
#include <time.h>
/* Espera y decodificacion del estado del proceso hijo. */
#include <sys/wait.h>
/* API POSIX para fork, execvp y _exit. */
#include <unistd.h>
/* Permite detectar errores de conversion o interrupciones de llamadas POSIX. */
#include <errno.h>
/* Lee segundos del reloj monotono: sirve para diferencias de tiempo, no para fecha y hora. */
static double now(void)
{
    /* Define t: instante local o estructura del reloj. */
    struct timespec t;
    /* Consulta el reloj monotono; sus diferencias dan tiempo transcurrido en segundos. */
    clock_gettime(CLOCK_MONOTONIC, &t);
    /* Convierte segundos y nanosegundos a una unica cantidad de segundos. */
    return t.tv_sec + t.tv_nsec * 1e-9;
}
/* Punto de entrada: procesa argumentos, ejecuta el caso y devuelve el estado al sistema operativo. */
int main(int argc, char **argv)
{
    /* Comprueba la forma de invocacion y los limites antes de usar los argumentos. */
    if (argc < 3)
        /* Informa uso incorrecto de argumentos. */
        return 2;
    /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
    double start = now();
    /* Crea el hijo que ejecutara el comando: negativo es error, cero identifica al hijo. */
    pid_t pid = fork();
    /* Detecta que fork no pudo crear el proceso hijo. */
    if (pid < 0)
        /* Informa un fallo de recursos o del entorno de ejecucion. */
        return 3;
    /* Solo el hijo entra aqui: fork devuelve cero en el nuevo proceso. */
    if (!pid)
    {
        /* Sustituye el hijo por el comando; si funciona, esta llamada no retorna. */
        execvp(argv[2], argv + 2);
        /* Muestra el error del sistema asociado a la llamada que fallo. */
        perror("execvp");
        /* Termina el hijo sin ejecutar limpieza heredada del padre cuando execvp fallo. */
        _exit(127);
    }
    /* Define status: codigo devuelto por la factorizacion. */
    int status;
    /* Espera al hijo; repite la espera si una señal la interrumpe. */
    while (waitpid(pid, &status, 0) < 0)
        /* Rechaza errores de conversion, caracteres sobrantes o valores fuera del rango permitido. */
        if (errno != EINTR)
            /* Informa un fallo de recursos o del entorno de ejecucion. */
            return 3;
    /* Toma una marca o diferencia temporal en esta frontera; conserva el alcance del banco original. */
    double elapsed = now() - start;
    /* Conserva el codigo normal del hijo o usa 128+señal si termino por una señal. */
    int result = WIFEXITED(status) ? WEXITSTATUS(status) : 128 + WTERMSIG(status);
    /* Abre el archivo CSV indicado por argv[1] para escribir el resultado del cronometro. */
    FILE *out = fopen(argv[1], "w");
    /* Detecta que no se pudo obtener el recurso solicitado; no se usa un puntero nulo. */
    if (!out)
        /* Informa un fallo de recursos o del entorno de ejecucion. */
        return 3;
    /* Guarda duracion externa y codigo de salida en el archivo solicitado. */
    fprintf(out, "external_s,exit_code\n%.12g,%d\n", elapsed, result);
    /* Cierra el CSV para completar su escritura. */
    fclose(out);
    /* Propaga el estado acumulado: cero indica que no hubo fallos. */
    return result;
}
