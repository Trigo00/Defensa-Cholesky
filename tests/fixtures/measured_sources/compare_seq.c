#define _POSIX_C_SOURCE 200809L
#include "cholesky.h"
#include <errno.h>
#include <inttypes.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static int number(const char *s, uint64_t *value) {
    if (!*s) return 0;
    for (const char *p=s; *p; ++p) if (*p<'0' || *p>'9') return 0;
    char *end;
    errno=0;
    unsigned long long parsed=strtoull(s,&end,10);
    if (errno || *end || parsed>UINT64_MAX) return 0;
    *value=(uint64_t)parsed;
    return 1;
}

static double now(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC,&t)) { perror("clock_gettime"); exit(1); }
    return (double)t.tv_sec + (double)t.tv_nsec*1e-9;
}

int main(int argc,char **argv) {
    uint64_t input=0,reps=7,seed=2026;
    if (argc<2 || argc>4 || !number(argv[1],&input)
        || (argc>2 && !number(argv[2],&reps))
        || (argc>3 && !number(argv[3],&seed))
        || !input || input>SIZE_MAX || !reps || reps>10000) {
        fprintf(stderr,"Uso: %s N [repeticiones=7] [semilla=2026]\n",argv[0]);
        return 1;
    }
    size_t n=(size_t)input;
    if(n>SIZE_MAX/n || n*n>SIZE_MAX/sizeof(double)) return 1;
    size_t bytes=n*n*sizeof(double);
    double *a=malloc(bytes),*factor=malloc(bytes);
    if(!a || !factor) { free(a); free(factor); return 1; }
    generate_spd(a,n,seed);
    if(!symmetric_finite(a,n)) { free(a); free(factor); return 1; }
    int (*variants[2])(double*,size_t)={cholesky_left,cholesky_right};
    const char *names[2]={"left","right"};
    puts("N,repetition,order,variant,seed,seconds,relative_residual");
    /* rep=0: un calentamiento por variante. Luego alternamos el orden. */
    for(uint64_t rep=0;rep<=reps;++rep) {
        int first=rep==0 ? 0 : (int)((rep-1)%2);
        for(int order=0;order<2;++order) {
            int variant=(first+order)%2;
            memcpy(factor,a,bytes);
            double start=now();
            int status=variants[variant](factor,n);
            double elapsed=now()-start;
            double residual=status==0 ? relative_residual(a,factor,n) : INFINITY;
            if(status || !isfinite(residual) || residual>1e-12) {
                fprintf(stderr,"Fallo: %s N=%zu rep=%" PRIu64 " r=%g\n",names[variant],n,rep,residual);
                free(a); free(factor); return 1;
            }
            if(rep) printf("%zu,%" PRIu64 ",%d,%s,%" PRIu64 ",%.12g,%.12g\n",
                           n,rep,order+1,names[variant],seed,elapsed,residual);
        }
    }
    free(a); free(factor); return 0;
}
