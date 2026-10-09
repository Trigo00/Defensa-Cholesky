# Funciones MPI utilizadas en el proyecto Cholesky paralelo

## 1. Alcance de este documento

Este documento describe las funciones, tipos, operaciones y constantes MPI del código conservado en `Defensa-Cholesky`, e incluye ejemplos conceptuales de comunicación punto a punto. Abarca:

- la implementación final right-looking;
- la aplicación que recibe una matriz externa;
- los bancos de pruebas y comparaciones experimentales;
- la variante left-looking utilizada para comparar algoritmos;
- ejemplos conceptuales de comunicación punto a punto, separados del código actual.

Es importante distinguir dos grupos:

1. **Código actual y experimental relevante:** utiliza principalmente operaciones colectivas: `MPI_Bcast`, `MPI_Reduce`, `MPI_Allreduce`, `MPI_Scatterv`, `MPI_Gather` y `MPI_Gatherv`.
2. **Ejemplos conceptuales:** explican `MPI_Send` y `MPI_Recv` como contraste con las colectivas. No representan archivos conservados ni llamadas del kernel final seleccionado.

El kernel final conserva el algoritmo Cholesky right-looking, distribución cíclica 1D de columnas y un vector local auxiliar. Para cada columna global `j`, su propietario calcula el pivote y la parte inferior de esa columna; después la difunde mediante `MPI_Bcast` para que todos los procesos actualicen sus columnas locales.

---

## 2. Modelo MPI utilizado

MPI ejecuta varias instancias del mismo programa. Cada instancia es un **proceso MPI** y posee memoria privada. Las variables normales de C no se comparten entre procesos.

En el proyecto:

- todos los procesos ejecutan el mismo binario;
- cada proceso obtiene un identificador llamado **rank**;
- el proceso de rank 0 actúa normalmente como raíz;
- el número total de procesos suele guardarse como `p` o `processes`;
- todos participan inicialmente en `MPI_COMM_WORLD`;
- la matriz distribuida se almacena por columnas asignadas a cada rank;
- las funciones colectivas deben ser invocadas por todos los procesos del comunicador, en el mismo orden compatible.

Por ejemplo, al ejecutar:

```sh
mpirun -np 4 ./cholesky_app A.txt L.txt --validate
```

se crean cuatro procesos con ranks `0`, `1`, `2` y `3`.

---

## 3. Resumen de las funciones documentadas

| Función | Clase | Finalidad dentro del proyecto |
|---|---|---|
| `MPI_Init` | Entorno | Inicializa MPI. |
| `MPI_Finalize` | Entorno | Finaliza MPI ordenadamente. |
| `MPI_Abort` | Errores | Termina todos los procesos del comunicador ante un fallo irrecuperable. |
| `MPI_Comm_rank` | Comunicador | Obtiene el rank del proceso. |
| `MPI_Comm_size` | Comunicador | Obtiene la cantidad de procesos. |
| `MPI_Get_processor_name` | Entorno | Registra el nombre del nodo que ejecuta un proceso. |
| `MPI_Wtime` | Medición | Reloj local usado en bancos experimentales y perfiles opcionales; el candidato mide sus fases con `CLOCK_MONOTONIC`. |
| `MPI_Barrier` | Sincronización | Hace que todos lleguen a un punto antes de continuar. |
| `MPI_Bcast` | Colectiva | Difunde un dato desde un propietario a todos. |
| `MPI_Reduce` | Colectiva | Combina valores y deja el resultado sólo en la raíz. |
| `MPI_Allreduce` | Colectiva | Combina valores y entrega el resultado a todos. |
| `MPI_Scatterv` | Colectiva | Distribuye cantidades variables desde la raíz. |
| `MPI_Gather` | Colectiva | Reúne cantidades iguales en la raíz. |
| `MPI_Gatherv` | Colectiva | Reúne cantidades variables en la raíz. |
| `MPI_Send` | Punto a punto | Envía un mensaje a un proceso específico; se incluye como ejemplo conceptual. |
| `MPI_Recv` | Punto a punto | Recibe un mensaje de un proceso específico; se incluye como ejemplo conceptual. |

---

## 4. Inicialización, identificación y finalización

### 4.1 `MPI_Init`

Prototipo conceptual:

```c
int MPI_Init(int *argc, char ***argv);
```

Inicializa el entorno MPI. Debe llamarse antes de usar casi cualquier otra función MPI.

Uso típico del proyecto:

```c
MPI_Init(&argc, &argv);
```

MPI puede inspeccionar o retirar de `argc` y `argv` argumentos pertenecientes al runtime. Después de esta llamada pueden consultarse el rank, el tamaño del comunicador y ejecutarse comunicaciones.

Reglas importantes:

- cada proceso debe llamar una vez a `MPI_Init`;
- no debe llamarse dos veces;
- las operaciones MPI se realizan después de inicializar y antes de finalizar;
- su retorno indica el estado de la llamada MPI, no si la matriz admite Cholesky.

En el proyecto aparece en los ejecutables MPI de experimentación, en el candidato final y en la aplicación con entrada externa.

### 4.2 `MPI_Comm_rank`

Prototipo conceptual:

```c
int MPI_Comm_rank(MPI_Comm comm, int *rank);
```

Obtiene el identificador del proceso dentro de un comunicador.

```c
int rank;
MPI_Comm_rank(MPI_COMM_WORLD, &rank);
```

Parámetros:

- `comm`: comunicador consultado;
- `rank`: dirección donde se guarda un entero entre `0` y `P-1`.

El rank no es necesariamente un número de núcleo ni identifica físicamente una computadora. Es una posición lógica dentro del comunicador.

En el proyecto se usa para:

- decidir qué proceso es la raíz (`rank == 0`);
- determinar qué columnas pertenecen al proceso;
- elegir el propietario de cada columna activa;
- evitar que todos impriman o escriban el mismo resultado;
- registrar el nodo correspondiente a cada proceso.

### 4.3 `MPI_Comm_size`

Prototipo conceptual:

```c
int MPI_Comm_size(MPI_Comm comm, int *size);
```

Obtiene la cantidad de procesos pertenecientes al comunicador.

```c
int processes;
MPI_Comm_size(MPI_COMM_WORLD, &processes);
```

En el reparto cíclico 1D, una columna global `j` pertenece al proceso:

```text
owner(j) = j mod processes
```

El número de procesos también interviene en el cálculo de cuántas columnas almacena cada rank y en la preparación de `counts` y `displs` para las colectivas variables.

### 4.4 `MPI_Finalize`

Prototipo conceptual:

```c
int MPI_Finalize(void);
```

Cierra ordenadamente el entorno MPI.

```c
MPI_Finalize();
```

Después de esta llamada no deben ejecutarse nuevas comunicaciones MPI. Cada ruta normal de salida debe alcanzarla. En la aplicación externa también se llama cuando una validación inicial falla, después de comunicar el estado a todos los procesos.

`MPI_Finalize` no reemplaza `free`: la memoria reservada por el programa sigue siendo responsabilidad del código C.

### 4.5 `MPI_Abort`

Prototipo conceptual:

```c
int MPI_Abort(MPI_Comm comm, int errorcode);
```

Solicita terminar todos los procesos asociados al comunicador.

```c
MPI_Abort(MPI_COMM_WORLD, 3);
```

Se utiliza en ejecutables experimentales ante errores irrecuperables, por ejemplo una reserva de memoria fallida cuando continuar dejaría a algunos ranks esperando una colectiva que otros nunca ejecutarían.

Diferencias frente a `MPI_Finalize`:

- `MPI_Finalize` es un cierre normal y coordinado;
- `MPI_Abort` es una terminación de emergencia;
- con `MPI_Abort` no debe suponerse que se vaciarán todos los buffers, se escribirán todos los archivos o se ejecutará limpieza normal;
- el código de error se entrega al entorno de ejecución, aunque su representación final puede depender de la implementación MPI.

---

## 5. Comunicadores y constantes relacionadas

### 5.1 `MPI_Comm`

`MPI_Comm` es el tipo que representa un comunicador. Un comunicador define un grupo de procesos y un contexto aislado de comunicación.

La estructura `Layout` del proyecto guarda uno:

```c
typedef struct {
    int n, p, rank, cyclic, cols, first, block;
    MPI_Comm comm;
} Layout;
```

Esto permite que el kernel utilice `d->comm` en lugar de depender rígidamente de una variable global.

### 5.2 `MPI_COMM_WORLD`

Es el comunicador predefinido que contiene todos los procesos iniciados para el trabajo MPI. Es el comunicador utilizado para construir los layouts del proyecto.

No es una función: es un manejador constante proporcionado por MPI.

---

## 6. Medición y sincronización

### 6.1 `MPI_Wtime`

Prototipo conceptual:

```c
double MPI_Wtime(void);
```

Devuelve tiempo de reloj de pared en segundos. Se utiliza tomando una diferencia:

```c
double start = MPI_Wtime();
/* trabajo medido */
double elapsed = MPI_Wtime() - start;
```

Características:

- es un reloj local al proceso;
- su origen absoluto no es importante; importa la diferencia entre dos lecturas del mismo proceso;
- no sincroniza procesos;
- no debe compararse directamente una marca absoluta de un rank con la de otro;
- incluye el tiempo transcurrido mientras el proceso espera dentro de una función MPI bloqueante.

En los bancos experimentales y perfiles que lo utilizan, permite medir:

- factorización;
- difusión de columnas;
- reducción de contribuciones en left-looking;
- distribución inicial;
- reunión final;
- validación y fases de aplicación en algunos bancos.

Algunos bancos reducen las duraciones locales con `MPI_Reduce(..., MPI_MAX, ...)`. Es necesario comprobar qué intervalo se reduce en cada programa. En `src/implementacion_final/main_candidate.c`, las fases usan `clock_gettime(CLOCK_MONOTONIC)` mediante `now()`: `factor_s` y `application_s` se publican desde el rango 0. Solo el tiempo local de aplicación se reduce para obtener `max_local_s`; no se reduce el tiempo de factorización. El candidato llama al kernel con perfil `NULL`, por lo que sus temporizadores opcionales con `MPI_Wtime` no se activan.

### 6.2 `MPI_Barrier`

Prototipo conceptual:

```c
int MPI_Barrier(MPI_Comm comm);
```

Es una operación colectiva de sincronización. Ningún proceso retorna de la barrera hasta que todos los procesos del comunicador han entrado en ella.

```c
MPI_Barrier(MPI_COMM_WORLD);
double start = MPI_Wtime();
```

En los benchmarks se coloca antes de iniciar un cronómetro para reducir el riesgo de que un rank empiece la región medida mientras otro todavía prepara la siguiente repetición.

Precauciones:

- no hace que los relojes físicos sean iguales;
- no mueve datos;
- no garantiza que todos salgan exactamente en el mismo instante;
- añade sincronización y, por tanto, no debe insertarse dentro del kernel salvo que el algoritmo lo necesite;
- una barrera innecesaria puede reducir el rendimiento;
- si un proceso no llega a ella, los demás quedan bloqueados.

El kernel final no introduce una barrera por cada columna. La propia secuencia de colectivas ya impone las dependencias necesarias.

---

## 7. Difusión de la columna activa

### 7.1 `MPI_Bcast`

Prototipo conceptual:

```c
int MPI_Bcast(void *buffer, int count, MPI_Datatype datatype,
              int root, MPI_Comm comm);
```

Difunde el mismo conjunto de datos desde el proceso raíz indicado hacia todos los procesos del comunicador. La raíz también participa.

Uso central del kernel right-looking:

```c
MPI_Bcast(column + j, n - j, MPI_DOUBLE, owner, d->comm);
```

Significado exacto:

- `column + j`: inicio de la porción útil de la columna activa;
- `n - j`: número de elementos transmitidos, desde la diagonal hasta la última fila;
- `MPI_DOUBLE`: cada elemento es un `double` de C;
- `owner`: rank propietario de la columna global `j`;
- `d->comm`: comunicador del layout.

Antes de la llamada, el propietario calcula el pivote `L[j,j]` y los valores `L[i,j]`. Después de la llamada, todos los procesos poseen esa columna temporal y pueden actualizar sus columnas locales futuras.

Esta comunicación expresa la dependencia fundamental del algoritmo: la actualización de la iteración `j` no puede hacerse sin conocer la columna `j` ya factorizada.

En caso de pivote inválido, el propietario coloca `NAN` en `column[j]` y lo difunde en el mismo mensaje. Así todos detectan el fallo después de la misma colectiva y retornan coherentemente, evitando que unos procesos continúen llamando colectivas mientras otros abandonan el kernel.

Reglas y riesgos:

- todos los procesos deben usar el mismo comunicador, raíz, tipo y cantidad compatible;
- todos deben llamar los `MPI_Bcast` en el mismo orden;
- el contenido inicial del buffer sólo es significativo en la raíz;
- al retornar, el buffer de cada proceso contiene los datos difundidos;
- `MPI_Bcast` es bloqueante respecto de la reutilización segura del buffer, aunque no implica una barrera global independiente;
- su tiempo puede incluir espera por un propietario que todavía estaba calculando.

También se utiliza para distribuir estados globales, tamaños o decisiones desde rank 0, por ejemplo:

```c
MPI_Bcast(&status, 1, MPI_INT, 0, MPI_COMM_WORLD);
MPI_Bcast(&n, 1, MPI_INT, 0, MPI_COMM_WORLD);
```

---

## 8. Reducciones

Una reducción combina un valor aportado por cada proceso utilizando una operación como máximo, mínimo o suma.

### 8.1 `MPI_Reduce`

Prototipo conceptual:

```c
int MPI_Reduce(const void *sendbuf, void *recvbuf, int count,
               MPI_Datatype datatype, MPI_Op op,
               int root, MPI_Comm comm);
```

Combina los datos de todos los procesos y deja el resultado únicamente en `root`.

Ejemplo de duración paralela:

```c
MPI_Reduce(&elapsed, &maximum, 1, MPI_DOUBLE,
           MPI_MAX, 0, MPI_COMM_WORLD);
```

Cada rank aporta su tiempo local. Rank 0 recibe el máximo, que representa la duración limitada por el proceso más lento.

Ejemplo de la variante left-looking:

```c
MPI_Reduce(partial, reduced, n - j - 1, MPI_DOUBLE,
           MPI_SUM, owner, d->comm);
```

Cada proceso calcula contribuciones parciales usando sus columnas anteriores. `MPI_SUM` las suma elemento a elemento y entrega el vector acumulado al propietario de la columna activa.

Otros usos experimentales:

- `MPI_MAX` para el máximo trabajo local;
- `MPI_SUM` para el trabajo total;
- reducción de varios tiempos almacenados en un arreglo;
- reducción al propietario dinámico de cada columna, no siempre a rank 0.

Observaciones:

- `recvbuf` sólo contiene un resultado válido en la raíz;
- para los demás ranks, normalmente se ignora el contenido de `recvbuf`;
- la operación se aplica elemento a elemento cuando `count > 1`;
- el tipo debe ser compatible con los buffers y con la operación;
- todos los procesos deben indicar la misma raíz para una invocación determinada.

### 8.2 `MPI_Allreduce`

Prototipo conceptual:

```c
int MPI_Allreduce(const void *sendbuf, void *recvbuf, int count,
                  MPI_Datatype datatype, MPI_Op op,
                  MPI_Comm comm);
```

Realiza una reducción y entrega el resultado a todos los procesos. Puede pensarse conceptualmente como una reducción seguida de una difusión, aunque la implementación MPI puede usar un algoritmo más eficiente.

Uso para propagar un error:

```c
MPI_Allreduce(&failed, &any, 1, MPI_INT, MPI_MAX, MPI_COMM_WORLD);
```

Si `failed` vale `0` o `1`, el máximo global vale `1` cuando al menos un proceso detectó un problema. Todos reciben la misma decisión y pueden tomar la misma ruta de control.

Usos del proyecto:

- comprobar si cualquier rank falló;
- comprobar si alguna reserva local de memoria falló;
- asegurar que todos observaron el mismo estado del kernel;
- comparar el mínimo y máximo de códigos de estado;
- con `MPI_MIN`, comprobar que una condición booleana sea verdadera en todos los procesos.

Ejemplo de consenso:

```c
MPI_Allreduce(&same, &all, 1, MPI_INT, MPI_MIN, d.comm);
```

Si los valores son `0` o `1`, `all` sólo vale `1` cuando todos aportaron `1`.

Diferencia práctica:

- use `MPI_Reduce` cuando sólo una raíz necesita el resultado;
- use `MPI_Allreduce` cuando todos deben conocerlo para mantener un flujo colectivo coherente.

---

## 9. Distribución y reunión de la matriz

### 9.1 ¿Por qué se usan variantes con `v`?

En una distribución cíclica, si `n` no es múltiplo de `P`, algunos procesos poseen una columna más que otros. Por lo tanto, no todos reciben o envían la misma cantidad de elementos.

Por eso el proyecto utiliza:

- `MPI_Scatterv` para distribución variable;
- `MPI_Gatherv` para reunión variable.

La letra `v` significa que los conteos y desplazamientos pueden variar por proceso.

### 9.2 `MPI_Scatterv`

Prototipo conceptual:

```c
int MPI_Scatterv(const void *sendbuf,
                 const int sendcounts[], const int displs[],
                 MPI_Datatype sendtype,
                 void *recvbuf, int recvcount,
                 MPI_Datatype recvtype,
                 int root, MPI_Comm comm);
```

Distribuye desde la raíz un segmento diferente a cada proceso.

Uso en la aplicación externa:

```c
MPI_Scatterv(packed, counts, offsets, MPI_DOUBLE,
             local, n * layout.cols, MPI_DOUBLE,
             0, MPI_COMM_WORLD);
```

Parámetros:

- `packed`: buffer global empaquetado en rank 0 por propietario;
- `counts[r]`: cantidad de `double` enviada al rank `r`;
- `offsets[r]`: posición inicial del segmento de `r`, medida en elementos de `sendtype`;
- `MPI_DOUBLE`: tipo del buffer de envío;
- `local`: matriz local que recibe el proceso;
- `n * layout.cols`: cantidad recibida por ese rank;
- segundo `MPI_DOUBLE`: tipo de recepción;
- `0`: raíz que posee `packed`, `counts` y `offsets` significativos;
- comunicador: conjunto de participantes.

Para un rank con `m` columnas locales, el almacenamiento contiene `n*m` valores organizados por filas locales:

```text
local[i*m + c]
```

donde `c` es el índice de columna local y su columna global se obtiene mediante `layout_global`.

La colectiva no decide el reparto por sí sola. El programa primero debe empaquetar la matriz global en el orden esperado por cada proceso. `MPI_Scatterv` sólo mueve los segmentos descritos.

Riesgos frecuentes:

- confundir desplazamientos en bytes con desplazamientos en elementos: aquí se miden en `double`;
- calcular un `recvcount` distinto de `sendcounts[rank]` sin tipos derivados compatibles;
- desbordar el tipo `int` usado por conteos clásicos de MPI;
- usar la matriz densa por filas directamente sin empaquetarla según los propietarios;
- modificar `packed` antes de que la llamada bloqueante haya terminado.

### 9.3 `MPI_Gatherv`

Prototipo conceptual:

```c
int MPI_Gatherv(const void *sendbuf, int sendcount,
                MPI_Datatype sendtype,
                void *recvbuf, const int recvcounts[],
                const int displs[], MPI_Datatype recvtype,
                int root, MPI_Comm comm);
```

Realiza el recorrido inverso: cada proceso envía una cantidad potencialmente diferente y la raíz reúne todos los segmentos.

Uso típico:

```c
MPI_Gatherv(local, n * layout.cols, MPI_DOUBLE,
            packed, counts, offsets, MPI_DOUBLE,
            0, MPI_COMM_WORLD);
```

Después de esta llamada, rank 0 posee los segmentos agrupados por rank. Todavía debe desempaquetarlos para reconstruir la matriz densa global en su orden de columnas original.

En el proyecto se usa para:

- recuperar el factor `L` distribuido;
- reconstruir el resultado para validación;
- medir el costo de reunión y reconstrucción;
- comparar tiempo del kernel con tiempo de aplicación completa.

El triángulo inferior contiene `L`. La aplicación final coloca ceros en el triángulo superior al guardar el archivo, porque los valores superiores no forman parte del factor.

### 9.4 `MPI_Gather`

Prototipo conceptual:

```c
int MPI_Gather(const void *sendbuf, int sendcount,
               MPI_Datatype sendtype,
               void *recvbuf, int recvcount,
               MPI_Datatype recvtype,
               int root, MPI_Comm comm);
```

Reúne en la raíz la misma cantidad de elementos desde cada proceso.

Ejemplo experimental:

```c
MPI_Gather(values, 4, MPI_DOUBLE,
           all, 4, MPI_DOUBLE,
           0, MPI_COMM_WORLD);
```

Cada rank envía cuatro valores de perfil y rank 0 recibe `4*P` valores ordenados por rank.

Diferencia frente a `MPI_Gatherv`:

- `MPI_Gather` exige bloques de igual tamaño;
- `MPI_Gatherv` admite tamaños y desplazamientos diferentes;
- el factor distribuido requiere `Gatherv` cuando el número de columnas no es igual para todos;
- los perfiles de tamaño fijo pueden usar `Gather`.

---

## 10. Comunicación punto a punto como referencia conceptual

Los siguientes ejemplos explican la comunicación punto a punto como contraste con las colectivas del proyecto. Son ejemplos conceptuales; no remiten a un archivo de la entrega actual ni describen la estrategia del kernel final.

### 10.1 `MPI_Send`

Prototipo conceptual:

```c
int MPI_Send(const void *buf, int count, MPI_Datatype datatype,
             int dest, int tag, MPI_Comm comm);
```

Envía un mensaje bloqueante al proceso `dest`.

Ejemplo conceptual:

```c
MPI_Send(&val, 1, MPI_DOUBLE, 0, 0, MPI_COMM_WORLD);
```

Parámetros:

- `buf`: datos enviados;
- `count`: cantidad de elementos;
- `datatype`: tipo MPI de cada elemento;
- `dest`: rank destino;
- `tag`: etiqueta que ayuda a distinguir mensajes;
- `comm`: comunicador.

Que sea bloqueante significa que al retornar el programa puede reutilizar de forma segura el buffer de envío. No garantiza necesariamente que el receptor ya haya terminado de procesar el mensaje.

### 10.2 `MPI_Recv`

Prototipo conceptual:

```c
int MPI_Recv(void *buf, int count, MPI_Datatype datatype,
             int source, int tag, MPI_Comm comm,
             MPI_Status *status);
```

Recibe un mensaje que coincida con origen, etiqueta y comunicador.

Ejemplo conceptual:

```c
MPI_Recv(&val, 1, MPI_DOUBLE, owner, 0,
         MPI_COMM_WORLD, MPI_STATUS_IGNORE);
```

`source` indica el rank esperado. El `tag` debe coincidir con el del envío. Si el mensaje correspondiente no llega, la llamada permanece bloqueada.

### 10.3 Etiquetas y emparejamiento

Un envío y una recepción se emparejan considerando:

- comunicador;
- rank origen;
- rank destino;
- etiqueta.

Por ejemplo, pueden utilizarse etiquetas `0` y `1` para separar clases de mensajes.

### 10.4 Riesgo de deadlock

Dos procesos pueden quedar bloqueados si ambos ejecutan primero un `MPI_Send` cuyo protocolo necesita que el receptor publique antes un `MPI_Recv`. Un programa que use este patrón debe organizar un orden compatible de envíos y recepciones.

El kernel final evita esta lógica punto a punto para la columna activa utilizando una colectiva `MPI_Bcast`, que expresa directamente que un propietario debe entregar la misma columna a todos.

---

## 11. Información del nodo

### 11.1 `MPI_Get_processor_name`

Prototipo conceptual:

```c
int MPI_Get_processor_name(char *name, int *resultlen);
```

Obtiene un nombre para el procesador o nodo donde se ejecuta el proceso.

Uso del proyecto:

```c
char host[MPI_MAX_PROCESSOR_NAME];
int len;
MPI_Get_processor_name(host, &len);
```

Se utiliza en programas experimentales para registrar la ubicación de los ranks y ayudar a auditar si una ejecución ocurrió dentro de un nodo o entre nodos.

Consideraciones:

- el contenido exacto depende del sistema y de la implementación MPI;
- dos ranks pueden devolver el mismo nombre si comparten nodo;
- no identifica el núcleo ni demuestra afinidad;
- `resultlen` informa la longitud válida del nombre;
- el buffer debe tener al menos `MPI_MAX_PROCESSOR_NAME` caracteres.

`MPI_MAX_PROCESSOR_NAME` es una constante, no una función.

---

## 12. Tipos MPI usados

Los tipos MPI describen el formato de los elementos transmitidos. Deben corresponder con el tipo real del buffer de C.

### `MPI_DOUBLE`

Corresponde a `double`. Se usa para:

- valores de la matriz;
- columnas de `L`;
- pivotes;
- tiempos;
- residuos o perfiles expresados en punto flotante.

### `MPI_INT`

Corresponde a `int`. Se usa para:

- estados de error;
- condiciones booleanas representadas como `0` o `1`;
- tamaño `n` difundido por la aplicación.

### `MPI_UNSIGNED_LONG_LONG`

Corresponde a `unsigned long long`. Aparece en experimentos para reducir contadores de trabajo o actualizaciones.

Cuando la variable C original es `uint64_t`, su compatibilidad exacta con `unsigned long long` depende de la plataforma. En el entorno medido coincidía con el uso realizado, pero en código completamente portable conviene usar el tipo MPI de ancho fijo correspondiente cuando la implementación lo ofrezca o declarar la variable con el tipo C exacto asociado.

### `MPI_BYTE`

Representa bytes sin interpretación numérica. Se incluye como referencia conceptual; no forma parte del intercambio de columnas del kernel final, que usa `MPI_DOUBLE`.

Con `MPI_BYTE`, `count` expresa bytes. No se realizan conversiones de representación. Es útil para datos opacos, pero no debe sustituir tipos numéricos cuando se espera portabilidad entre arquitecturas diferentes.

---

## 13. Operaciones de reducción usadas

### `MPI_MAX`

Selecciona el máximo elemento a elemento. Se usa para:

- tiempo máximo entre ranks;
- detectar si algún flag de error vale `1`;
- máximo trabajo local;
- máximo código de estado.

### `MPI_MIN`

Selecciona el mínimo elemento a elemento. Se usa para:

- comprobar que todos los flags booleanos valgan `1`;
- comparar el mínimo código de estado con el máximo y detectar desacuerdo.

### `MPI_SUM`

Suma elemento a elemento. Se usa para:

- acumular contribuciones parciales en el algoritmo left-looking experimental;
- sumar contadores de trabajo;
- obtener trabajo total entre procesos.

Estas constantes representan operaciones predefinidas de MPI; no son funciones.

---

## 14. Constantes auxiliares

### `MPI_STATUS_IGNORE`

Se pasa a `MPI_Recv` cuando el programa no necesita inspeccionar la información del mensaje recibido:

```c
MPI_Recv(buffer, count, type, source, tag,
         communicator, MPI_STATUS_IGNORE);
```

Si se proporcionara un `MPI_Status`, podrían consultarse datos como el origen real, la etiqueta o la cantidad recibida. En el ejemplo, origen y etiqueta ya están fijados y no se consulta el estado recibido.

### `MPI_MAX_PROCESSOR_NAME`

Tamaño máximo requerido para el buffer entregado a `MPI_Get_processor_name`.

---

## 15. Flujo MPI del kernel final right-looking

El flujo esencial puede resumirse así:

```text
Todos los ranks
    |
    +-- crean el mismo Layout
    |      rank, P, columnas locales, comunicador
    |
    +-- para j = 0 ... n-1
           |
           +-- owner = propietario cíclico de j
           |
           +-- sólo owner calcula L[j,j] y L[j+1:n,j]
           |
           +-- MPI_Bcast de la columna desde owner
           |
           +-- todos verifican el pivote difundido
           |
           +-- cada rank actualiza únicamente sus columnas futuras
```

No se reparte el cálculo de una misma entrada entre varios ranks en el kernel right-looking seleccionado. Se reparte la propiedad de las columnas. La comunicación principal del kernel es una difusión por columna.

El vector `local_column` no es una primitiva MPI. Es una optimización de acceso a memoria local: copia los valores de la columna difundida que corresponden a las columnas propias futuras, para reutilizarlos de forma contigua durante las actualizaciones.

---

## 16. Flujo MPI de la aplicación con matriz externa

```text
MPI_Init
   |
rank 0 lee y valida A
   |
MPI_Bcast del estado y n
   |
todos crean el Layout cíclico
   |
MPI_Allreduce de fallos de memoria
   |
rank 0 empaqueta A por propietario
   |
MPI_Scatterv
   |
cholesky_mpi_local
   +-- MPI_Bcast por cada columna
   |
MPI_Allreduce del estado del kernel
   |
MPI_Gatherv
   |
rank 0 reconstruye, valida y escribe L
   |
MPI_Bcast del estado final
   |
MPI_Finalize
```

La lectura, validación completa y escritura se centralizan en rank 0. El cálculo de Cholesky se realiza con la misma representación distribuida y el mismo kernel que en los experimentos.

---

## 17. Colectivas: reglas que el proyecto debe respetar

Para todas las colectivas utilizadas se aplican estas reglas:

1. Todos los procesos del comunicador deben participar.
2. Deben ejecutar las colectivas en un orden compatible.
3. Deben coincidir comunicador, raíz y tipos relevantes.
4. Los conteos deben describir memoria válida.
5. Ningún proceso debe abandonar una iteración mientras otros avanzan hacia la siguiente colectiva.

Ejemplo de error peligroso:

```c
if (rank == 0)
    MPI_Bcast(...); /* incorrecto: los demás ranks no participan */
```

Ejemplo correcto:

```c
/* La raíz prepara el dato. */
if (rank == 0)
    value = 123;

/* Todos llaman la colectiva. */
MPI_Bcast(&value, 1, MPI_INT, 0, MPI_COMM_WORLD);
```

El kernel comunica el fallo del pivote dentro de la propia columna difundida precisamente para conservar el mismo flujo colectivo en todos los ranks.

---

## 18. Bloqueo, sincronización y progreso

Las llamadas usadas por el proyecto son bloqueantes. Al retornar, el programa puede reutilizar los buffers correspondientes según el contrato de la función.

Sin embargo, **bloqueante no significa barrera**:

- un `MPI_Bcast` garantiza la disponibilidad del buffer difundido al retornar;
- no debe interpretarse automáticamente como una barrera independiente para cualquier otro trabajo;
- `MPI_Reduce` sólo garantiza el resultado en la raíz;
- `MPI_Allreduce` deja el resultado disponible en todos;
- `MPI_Send` puede retornar antes de que el receptor procese el mensaje, dependiendo del protocolo interno.

Las esperas internas forman parte del tiempo transcurrido observado tanto con `MPI_Wtime` como con `CLOCK_MONOTONIC`. Por eso un tiempo atribuido a `MPI_Bcast` o `MPI_Reduce` puede contener tanto transferencia como espera por procesos atrasados. No equivale directamente a “tiempo puro de red”.

---

## 19. Relación con las mediciones del proyecto

El proyecto utilizó distintos alcances temporales:

- **tiempo del kernel:** incluye cálculo distribuido y las colectivas internas del algoritmo;
- **tiempo de aplicación:** puede incluir preparación, distribución, factorización y reunión;
- **tiempo externo:** incluye además arranque del comando, runtime MPI, validación, salida y cierre, según la campaña.

En el candidato `src/implementacion_final/main_candidate.c`, `now()` consulta `clock_gettime(CLOCK_MONOTONIC)`. El CSV contiene estas mediciones:

| Campo | Intervalo y proceso que lo informa |
|---|---|
| `allocation_s` | `t1-t0` en rango 0: reservas y preparación del reparto. |
| `generation_s` | `t2-t1` en rango 0: generación de sus columnas; no es el máximo entre procesos. |
| `factor_s` | `t3-t2` en rango 0: llamada al kernel, incluidas comunicaciones y esperas internas. |
| `gather_s` | `t4-t3` en rango 0: reunión y reconstrucción del factor completo. |
| `application_s` | `t4-t0` en rango 0: desde las reservas hasta disponer de L completa. |
| `max_local_s` | Máximo de `t4-t0` entre procesos, obtenido con `MPI_Reduce` y `MPI_MAX`. |
| `validation_s` | Intervalo posterior en rango 0, separado del tiempo de aplicación. |

La barrera inicial precede a `t0`. La reducción que produce `max_local_s` ocurre después de `t4`, fuera de `application_s`. No se reducen las fases por separado: `max_local_s` no es el máximo de `factor_s` ni debe sumarse a `application_s`.

Los bancos experimentales tienen fronteras de medición propias y varios usan `MPI_Wtime`; sus máximos y perfiles deben interpretarse según el código de cada banco. En particular, la curva formal de strong scaling N=8192 usa `factor_s` del rango 0 y referencia MPI P=1 de la misma campaña. La aplicación con matriz externa valida y escribe L, pero no publica estas columnas temporales del candidato.

Una colectiva puede medir espera por desbalance. Por ejemplo, si el propietario de una columna tarda más, los demás pueden esperar dentro de `MPI_Bcast`. Ese tiempo es real para la ejecución, pero no puede interpretarse automáticamente como ancho de banda consumido.

---

## 20. Funciones MPI que no utiliza el kernel final

El inventario no muestra en el kernel final:

- comunicación no bloqueante como `MPI_Isend`, `MPI_Irecv` o `MPI_Ibcast`;
- tipos derivados creados con `MPI_Type_*`;
- topologías MPI;
- comunicadores creados con `MPI_Comm_split`;
- RMA o memoria de una cara;
- MPI-IO;
- operaciones persistentes;
- reparto bidimensional de procesos;
- ScaLAPACK.

Esto concuerda con el alcance del proyecto: una implementación explícita y verificable basada en distribución cíclica 1D y colectivas bloqueantes.

---

## 21. Resumen para exposición oral

La explicación breve del uso de MPI en el proyecto es:

> Inicializamos MPI, obtenemos el rank y la cantidad de procesos, y distribuimos las columnas de la matriz de forma cíclica. En cada iteración de Cholesky, el proceso propietario calcula la columna activa y la difunde con `MPI_Bcast`. Cada proceso usa esa columna para actualizar únicamente su parte local. En el candidato medimos las fases con `CLOCK_MONOTONIC`: los tiempos de factorización y aplicación publicados corresponden al rango 0. Como control adicional, reducimos el tiempo local de aplicación con `MPI_Reduce` y `MPI_MAX` para obtener `max_local_s`. La validación se mide después y por separado. Otros bancos experimentales usan `MPI_Wtime`. Los errores globales se propagan con `MPI_Allreduce`. En la aplicación con entrada externa, rank 0 distribuye la matriz mediante `MPI_Scatterv` y recupera el factor mediante `MPI_Gatherv`. Finalmente todos cierran con `MPI_Finalize`.

La idea clave es que MPI no cambia la fórmula numérica de Cholesky: organiza qué proceso posee cada columna, cómo se comparte la columna ya calculada y cómo se combinan estados o resultados distribuidos.

