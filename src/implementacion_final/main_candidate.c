/* Programa principal de la entrega. USE_MPI selecciona MPI; sin esa macro se compila la referencia secuencial.
 * Lectura: ver docs/guia_codigo.md. Los comentarios explican instrucciones logicas;
 * las llaves y las continuaciones de una misma instruccion comparten explicacion.
 */
/* Habilita las declaraciones POSIX, incluido CLOCK_MONOTONIC. */
#define _POSIX_C_SOURCE 200809L
/* Declara generadores, kernels secuenciales y residuos. */
#include "cholesky.h"
/* Este bloque se compila solamente en la version MPI del candidato. */
#ifdef USE_MPI
/* Declara Layout, perfiles y kernels distribuidos; incluye la API MPI. */
#include "cholesky_mpi.h"
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
/* Permite detectar errores de conversion numerica. */
#include <errno.h>
/* Funciones matematicas y controles de finitud: sqrt, fabs, isfinite, NAN e INFINITY. */
#include <math.h>
/* Entrada/salida de mensajes, archivos y registros CSV. */
#include <stdio.h>
/* Reserva/liberacion de memoria, conversion numerica y terminacion del proceso. */
#include <stdlib.h>
/* Medir tiempo utilizando un reloj monotónico. */
#include <time.h>

/* Esta función permite medir cuánto tarda en ejecutarse una parte del programa. */
static double now(void)
{
    struct timespec
        t; // Declara una estructura que almacena el tiempo en dos campos: (tv_sec: segundos enteros) y (tv_nsec: nanosegundos adicionales).
    clock_gettime(CLOCK_MONOTONIC,
                  &t); // Consulta el reloj monotonico; sus diferencias dan tiempo transcurrido en segundos
    return t.tv_sec + t.tv_nsec * 1e-9; // Convierte segundos y nanosegundos a una unica cantidad de segundos.
}

/* Esta función centraliza las reservas de memoria dinámica y el tratamiento de errores. Hace count reservas de size tamaños */
static void *reserve(size_t count, size_t size)
{
    void *p = malloc(
        (count ? count : 1) *
        size); // Solicita un bloque de memoria. Si count es 0, solicita espacio para un elemento en lugar de cero. Esto resulta útil porque, en MPI, algunos procesos pueden no poseer columnas cuando hay más procesos que columnas.
    if (!p)    // Comprueba si malloc devolvio un puntero nulo
    {
        fputs("No se pudo reservar memoria\n", stderr);
#ifdef USE_MPI
        MPI_Abort(
            MPI_COMM_WORLD,
            3); //Aborta el comunicador para que otros rangos no queden esperando tras el fallo. Supongamos que estamos ejecutando Cholesky con cuatro procesos y uno no puede reservar memoria. Los otros tres podrían continuar hasta una operación colectiva como MPI_Bcast y quedarse esperando a un proceso que ya no participa.
#endif
        exit(3); //Termina el proceso con el codigo de error indicado.
    }
    return p; //Entrega la memoria reservada al llamador, que debera liberarla.
}

int main(int argc, char **argv)
{
    int rank = 0, processes = 1; // Define rank: rango actual; processes: cantidad de procesos.
#ifdef USE_MPI
    MPI_Init(&argc, &argv);
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &processes);
#endif
    char *end = NULL;
    errno = 0;
    long value =
        argc == 2
            ? strtol(argv[1], &end, 10)
            : 0; //Convierte el argumento de texto y conserva los limites/valores por defecto del programa.
    if (argc != 2 || errno || !end || *end || value < 1 ||
        value > 20000) //Comprueba la forma de invocacion y los limites antes de usar los argumentos.
    {
        if (!rank) // Solo rango 0 ejecuta esta tarea global; los demas conservan sus datos locales.
            fputs("Uso: cholesky_candidate N (1..20000)\n", stderr);
#ifdef USE_MPI
        MPI_Finalize();
#endif
        return 2;
        /*Este bloque valida el tamaño de la matriz que recibe el programa por línea de comandos. Como los argumentos llegan como cadenas de caracteres, utilizamos strtol para convertir el argumento a un número entero. A través de end comprobamos que no sobren caracteres, y con errno verificamos errores de conversión. Finalmente exigimos que el tamaño esté entre 1 y 20000. Si no se cumple, mostramos un mensaje desde el rango cero y finalizamos la ejecución.*/
    }
    int n = (int)value, failed = 0; //Define n: orden de la matriz; failed: acumulador de fallos.
    size_t cells = (size_t)n * n;   // Define cells: numero total de entradas de A.
    double *
        full = NULL,
       *packed = NULL, *local = NULL, *column = NULL,
       *work =
           NULL; // Define full: matriz global del rango 0; packed: buffer agrupado por propietario; local: columnas pertenecientes al proceso actual; column: vector para recibir o difundir una columna global; work: vector auxiliar de la factorización.
    int *
        counts = NULL,
       *offsets =
           NULL; // Define counts: cantidades de elementos por rango; offsets: desplazamientos de los segmentos.
/*Todos los punteros comienzan en NULL porque todavía no se ha reservado memoria para ellos.*/
#ifdef USE_MPI
    /* Espera a todos los rangos antes de iniciar la medicion; la barrera no sincroniza los relojes ni garantiza que todos salgan exactamente al mismo tiempo. */
    MPI_Barrier(MPI_COMM_WORLD);
#endif
    double t0 =
        now(); //Guardamos la marca de tiempo inicial que se utilizará para medir el procesamiento posterior.
    if (!rank) // solo el rango 0 reserva espacio para la matriz global completa.
        full = reserve(cells, sizeof(double));
#ifdef USE_MPI
    Layout d =
        layout_create(n, 1, MPI_COMM_WORLD); //Construye el mapa local con el reparto de columnas indicado.
    if (!rank)
        packed = reserve(
            cells,
            sizeof(
                double)); //Su finalidad es reunir los datos de los procesos agrupados por propietario antes de reconstruir la matriz global.
    local = reserve((size_t)n * d.cols,
                    sizeof(double));     //Cada proceso reserva espacio únicamente para sus columnas.
    column = reserve(n, sizeof(double)); //Reserva un vector de longitud n.
    work = reserve(
        d.cols,
        sizeof(
            double)); // Reserva un vector de longitud igual a la cantidad de columnas propias. Su objetivo es preparar datos en el mismo orden que las columnas locales y permitir que el kernel de actualización los reutilice de manera contigua. Esta decisión viene de la etapa 3 del proyecto, cuando incorporamos el vector local para mejorar los accesos a memoria.
    counts = reserve(processes, sizeof(int));  //Reserva cantidades de elementos por rango;
    offsets = reserve(processes, sizeof(int)); //Reserva desplazamientos de los segmentos;
    int offset = 0;                            //Define offset: inicio del siguiente segmento empaquetado.
    /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
    for (int r = 0; r < processes; ++r)
    {
        counts[r] =
            n * (n / processes +
                 (r < n % processes)); //Calcula cuantos elementos de matriz corresponden a este rango.
        offsets[r] = offset;           //Guarda el inicio del segmento de este rango.
        offset += counts[r]; //Avanza al segmento del siguiente propietario en el buffer empaquetado.
    }
    // Son necesarios porque no siempre todos los procesos poseen la misma cantidad de columnas.
/* Ruta alternativa de compilacion para la version secuencial. */
#else
    work = reserve(n, sizeof(double));
/* Cierra la seleccion de compilacion o la proteccion del encabezado. */
#endif
    /*En esta sección preparamos la memoria necesaria para ejecutar Cholesky. En la versión MPI construimos una distribución cíclica de columnas, donde cada proceso almacena únicamente las columnas que le pertenecen. Reservamos además un vector para recibir columnas difundidas y otro vector auxiliar para mejorar el acceso local a memoria. Finalmente, calculamos las cantidades y desplazamientos de cada proceso para poder reunir posteriormente el resultado mediante MPI.*/
    double t1 =
        now(); // Marca el final de la fase de reserva de memoria. En consecuencia, la diferencia t1 - t0 representa la duración medida de esta preparación, incluyendo la creación de la distribución en la ruta MPI.
#ifdef USE_MPI
    /* Genera exactamente las columnas ciclicas propias con la semilla comun. */
    generate_spd_columns(local, n, 2026, rank, processes);
/* Ruta alternativa de compilacion para la version secuencial. */
#else
    /* Construye la matriz SPD reproducible con la semilla indicada. */
    generate_spd(full, n, 2026);
#endif
    /* Termina generation_s e inicia factor_s. */
    double t2 = now();
#ifdef USE_MPI
    /* Acumula el fallo sin borrar errores de casos anteriores */
    failed = cholesky_mpi_local(local, column, work, &d, NULL) != 0;
#else
    /* Acumula el fallo sin borrar errores de casos anteriores */
    failed = cholesky_right_buffered(full, n, work) != 0;
#endif
    /*
    * La factorizacion MPI termino.
    * t3 marca el inicio de la etapa de recoleccion. El tiempo de factorizacion se obtiene como t3-t2.
    */
    double t3 = now();
#ifdef USE_MPI
    /*
    * MPI_Gatherv reune en el rango 0 las columnas almacenadas localmente por todos los procesos.
    * Usamos Gatherv porque los procesos pueden poseer cantidades diferentes de columnas.
    * ARGUMENTOS:
    * local: Buffer con las columnas propias del proceso.
    * n*d.cols: Cantidad de doubles enviados por este proceso.
    * MPI_DOUBLE: Tipo de los elementos enviados.
    * packed: Buffer del rango 0 que recibe los segmentos.
    * counts: Cantidad de doubles que recibimos de cada rango.
    * offsets: Posicion inicial de cada segmento en packed, expresada en elementos MPI_DOUBLE, no en bytes.
    * MPI_DOUBLE: Tipo de los elementos recibidos.
    * 0: Rango raiz que reune todos los datos.
    * MPI_COMM_WORLD: Comunicador en el que participan los procesos.
    *
    * Ejemplo: N=8, P=3
    *   counts  = {24,24,16}
    *   offsets = {0,24,48}
    * 
    *   packed[0..23]  recibe datos de P0.
    *   packed[24..47] recibe datos de P1.
    *   packed[48..63] recibe datos de P2.
    *
    * IMPORTANTE:
    * MPI_Gatherv agrupa los datos por propietario, pero no reconstruye el orden global de las columnas. Eso se realiza en el siguiente bucle.
    */
    MPI_Gatherv(local, n * d.cols, MPI_DOUBLE, packed, counts, offsets, MPI_DOUBLE, 0, MPI_COMM_WORLD);

    /*
    * MPI_Gatherv ya reunio las columnas locales en packed, pero los datos quedaron agrupados por proceso.
    * Ahora el rango 0 reconstruye la matriz global full, colocando cada elemento en su fila y columna original.
    * Solo el rango 0 realiza esta reconstruccion porque es quien posee los buffers packed y full.
    */
    if (!rank)
        /* Recorre los propietarios para construir o interpretar sus segmentos de datos. */
        for (int r = 0; r < processes; ++r)
        {
            /*
            * Calculamos cuantas columnas tenia el proceso r.
            * n/P: cantidad base de columnas.
            * n%P: procesos que reciben una columna adicional.
            *
            * Ejemplo: N=8, P=3
            *   P0: m=3
            *   P1: m=3
            *   P2: m=2
            */
            int m = n / processes + (r < n % processes);
            /* Recorremos todas las filas globales y las columnas locales del segmento recibido de r. */
            for (int i = 0; i < n; ++i)
                for (int c = 0; c < m; ++c)
                    /*
                    * DESTINO EN FULL:
                    * i*n: Inicio de la fila global i.
                    * r+c*processes: Columna global correspondiente a la columna local c del proceso r.
                    * ORIGEN EN PACKED:
                    * offsets[r]: Inicio del segmento recibido del rango r.
                    * i*m: Inicio de la fila i dentro de ese segmento.
                    * c: Columna local dentro de la fila.
                    *
                    * Ejemplo: N=8, P=3, r=1, i=2, c=1
                    * Origen: packed[24 + 2*3 + 1] = packed[31]
                    * Destino: full[2*8 + 1 + 1*3] = full[20]
                    * Se recupera A(2,4) en la matriz global.
                    */
                    full[(size_t)i * n + r + c * processes] = packed[offsets[r] + (size_t)i * m + c];
        }
#endif

    /*
    * Terminamos la etapa de recoleccion y reconstruccion.
    * t4: marca temporal final del intervalo de aplicacion.
    * elapsed: Tiempo local transcurrido desde t0 hasta t4.
    * max_elapsed: Inicialmente contiene el tiempo local. En MPI, el rango 0 recibira el mayor tiempo observado entre todos los procesos.
    * La medicion incluye reserva, generacion, factorizacion y recoleccion/reconstruccion.
    * No incluye MPI_Init, validacion numerica ni MPI_Finalize.
    */
    double t4 = now(), elapsed = t4 - t0, max_elapsed = elapsed;

#ifdef USE_MPI

    /*
    * MPI_Reduce combina los tiempos locales usando MPI_MAX.
    * No sumamos los tiempos porque los procesos ejecutan trabajo concurrentemente. Nos interesa el mayor intervalo de ejecucion observado.
    * ARGUMENTOS:
    * &elapsed: Direccion del tiempo local enviado por este proceso.
    * &max_elapsed: Direccion donde el rango 0 recibe el resultado.
    * 1: Enviamos un solo valor por proceso.
    * MPI_DOUBLE: El dato enviado es de tipo double.
    * MPI_MAX: Seleccionamos el mayor tiempo entre procesos.
    * 0: El resultado se entrega al rango 0.
    * MPI_COMM_WORLD: Participan todos los procesos del comunicador.
    *
    * Ejemplo:
    *   P0: 2.5 segundos
    *   P1: 2.8 segundos
    *   P2: 2.6 segundos
    *
    *   max_elapsed en P0 = 2.8 segundos.
    *
    * IMPORTANTE:
    * max_elapsed no incluye todas las etapas externas al intervalo t0-t4, como inicializacion de MPI, validacion o finalizacion del programa.
    */
    MPI_Reduce(&elapsed, &max_elapsed, 1, MPI_DOUBLE, MPI_MAX, 0, MPI_COMM_WORLD);

    /*
    * Combinamos los estados de error de todos los procesos.
    * Cada proceso tiene una variable failed:
    *   failed = 0 -> no detecto un fallo.
    *   failed = 1 -> detecto un fallo.
    * Queremos comprobar si AL MENOS UN proceso fallo.
    */
    int any;

    /*
    * MPI_Allreduce combina los valores y entrega el resultado a TODOS los procesos.
    * ARGUMENTOS:
    * &failed: Direccion del estado de error local.
    * &any: Direccion donde cada proceso recibirael estado de error global.
    * 1: Cada proceso aporta un unico entero.
    * MPI_INT:  Tipo de dato utilizado.
    * MPI_MAX: Selecciona el mayor valor de failed. Si algun proceso aporta 1, el resultado es 1.
    * MPI_COMM_WORLD: Participan todos los procesos MPI.
    *
    * Ejemplo:
    *   P0: failed=0
    *   P1: failed=1
    *   P2: failed=0
    *
    *   MPI_MAX(0,1,0) = 1
    *
    *   Todos reciben any=1.
    *
    * DIFERENCIA CON MPI_Reduce:
    * Reduce entrega el resultado solo al rango raiz. Allreduce lo entrega a todos los procesos.
    */
    MPI_Allreduce(&failed, &any, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);

    /*
    * Reemplazamos el estado local por el global.
    * Desde este punto, todos conocen si hubo algun fallo durante la factorizacion.
    * La validacion posterior puede detectar errores adicionales en el rango 0.
    */
    failed = any;
#endif

   /*
    * La validacion numerica se realiza solo en rango 0, porque alli reconstruimos el factor global L.
    * Esta etapa ocurre despues de medir application_s, para no incluir el costo de validacion en ese tiempo.
    */
    if (!rank)
    {
        /* Inicia validation_s despues de cerrar el tiempo de aplicacion. */
        double v0 = now();
        
        /*
        * Reservamos memoria para reconstruir la matriz A original, ya que Cholesky sobrescribio sus datos con el factor y las actualizaciones.
        */
        double *original = reserve(cells, sizeof(double));
        /* Reservamos dos vectores de longitud n, usando long double para reducir errores de redondeo durante las comprobaciones numericas. */
        long double *check = reserve(2 * (size_t)n, sizeof(long double));

        /* Regeneramos la misma matriz SPD utilizada al comenzar, con igual dimension y semilla 2026.
        * Asi podemos comparar la entrada original A con el factor L obtenido.
        */
        generate_spd(original, n, 2026);

        /*
        * VALIDACION PROYECTADA:
        * Compara A*x con L*(L^T*x) utilizando ocho vectores de prueba reproducibles.
        * original: matriz A.
        * full: factor L reconstruido.
        * n: dimension.
        * 8: cantidad de vectores de prueba.
        * 91827: semilla de esos vectores.
        * check: memoria auxiliar.
        *
        * Devuelve el mayor residuo relativo observado.
        * Es una comprobacion practica, pero no garantiza detectar todos los errores posibles.
        */
        double residual = projected_residual(original, full, n, 8, 91827, check);
        
         /*
        * VALIDACION COMPLETA:
        * Compara A con L*L^T utilizando la norma relativa de Frobenius.
        * Como requiere O(n^3) operaciones, solamente la ejecutamos cuando n <= 128.
        * Para n > 128 guardamos -1 como marcador de que la comprobacion fue omitida.
        */
        double exact = n <= 128 ? relative_residual(original, full, n) : -1;

        /*
        * VALIDACION DE LOS RESIDUOS NUMERICOS.
        * Aceptamos residuos finitos que no superen 1e-12.
        * La tolerancia permite pequenos errores de redondeo propios de la aritmetica de punto flotante.
        * El operador |= acumula nuevos fallos sin borrar los detectados anteriormente.
        * Ejemplo:
        *   failed = 1;
        *   nueva comprobacion = 0;
        *   failed |= 0;
        *   failed sigue siendo 1.
        */
        failed |= !isfinite(residual) || residual > 1e-12;
        
        /*
        * El residuo completo de Frobenius solo se calculo para matrices con n <= 128.
        * Para matrices mayores, exact contiene -1, que indica que esa validacion fue omitida.
        */
        if (n <= 128)
            failed |= !isfinite(exact) || exact > 1e-12;

        /*
        * COMPROBACION DIRECTA DEL FACTOR L.
        * Recorremos exclusivamente el triangulo inferior, incluida la diagonal, porque alli almacenamos L.
        * Condiciones:
        * 1. Todos los elementos del triangulo inferior deben ser finitos.
        * 2. Los elementos diagonales deben ser positivos, como corresponde a Cholesky para matrices SPD.
        * Los elementos debajo de la diagonal pueden ser negativos o cero.
        */
        for (int i = 0; i < n; ++i)
            for (int j = 0; j <= i; ++j)
                failed |= !isfinite(full[(size_t)i * n + j]) || (i == j && full[(size_t)i * n + j] <= 0);

        /*
        * Tiempo transcurrido desde el inicio de validacion.
        * Incluye regeneracion de A, calculo de residuos y comprobaciones del factor.
        * No se incluye en application_s.
        */
        double validation = now() - v0;

        /*
        * SALIDA DE RESULTADOS EN FORMATO CSV.
        * Solo el rango 0 imprime las mediciones. CSV significa valores separados por comas.
        * El encabezado identifica cada columna para facilitar el analisis posterior con Python, pandas u otras herramientas.
        */
        puts(
            "N,P,allocation_s,generation_s,factor_s,gather_s,application_s,max_local_s,validation_s,projected_residual,exact_residual,valid");

        /*
        * Imprimimos una fila con los resultados.
        * N: Dimension de la matriz.
        * P: Cantidad de procesos MPI.
        * allocation_s = t1-t0: Preparacion y reserva de memoria.
        * generation_s = t2-t1: Generacion de la matriz SPD.
        * factor_s = t3-t2: Factorizacion de Cholesky.
        * gather_s = t4-t3: Recoleccion y reconstruccion en rango 0.
        * application_s = t4-t0: Intervalo total de aplicacion medido en P0.
        * max_local_s: Mayor intervalo t0-t4 entre todos los procesos.
        * validation_s: Tiempo de preparacion y comprobacion numerica.
        * projected_residual: Mayor residuo relativo entre los vectores de prueba.
        * exact_residual: Residuo relativo de Frobenius para n<=128. Vale -1 si no se realizo esa comprobacion.
        * valid: 1 si todos los controles fueron superados. 0 si se detecto algun fallo.
        * FORMATO:
        * %d:  Numero entero.
        * %.12g: Numero de punto flotante con hasta 12 cifras significativas.
        */
        printf("%d,%d,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%d\n", n, processes, t1 - t0,
               t2 - t1, t3 - t2, t4 - t3, t4 - t0, max_elapsed, validation, residual, exact, !failed);

        /*
        * Liberamos la matriz original regenerada y el espacio auxiliar utilizado para la validacion.
        * Estos buffers solo fueron reservados por rango 0.
        */
        free(original);
        free(check);
    }

/*
 * Al terminar la validacion, rango 0 puede haber detectado errores adicionales.
 * MPI_Allreduce habia combinado los fallos de la factorizacion, pero la validacion posterior fue realizada exclusivamente por rango 0.
 * Por eso difundimos el resultado definitivo.
 */
#ifdef USE_MPI
    MPI_Bcast(&failed, 1, MPI_INT, 0, MPI_COMM_WORLD);
#endif
    // A continuacion se liberan los restantes buffers reservados por cada proceso.
    free(full);
    free(packed);
    free(local);
    free(column);
    free(work);
    free(counts);
    free(offsets);
    
#ifdef USE_MPI
    MPI_Finalize(); //Cierra MPI; todos los rangos deben llegar a esta finalizacion.
#endif
    return failed ? 1 : 0; //Propaga el estado acumulado: cero indica que no hubo fallos.
}
