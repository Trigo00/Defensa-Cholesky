#define _POSIX_C_SOURCE 200809L
#include "cholesky.h"
#include <lapacke.h>
#include <cblas.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <math.h>
#include <errno.h>
static double now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+1e-9*t.tv_nsec;}
static void *alloc(size_t n){void *p=malloc(n?n:1);if(!p){fputs("allocation failed\n",stderr);exit(3);}return p;}
static int number(const char *s){char *e;errno=0;long v=strtol(s,&e,10);return errno||!*s||*e||v<1||v>20000?-1:(int)v;}
/* Native column-major upper triangle aliases row-major lower triangle.
 * Symmetric A has identical storage after transpose; U^T is our L.
 * _work avoids LAPACKE row-major transpose and optional NaN scan. */
static int lapack(double *a,int n){return LAPACKE_dpotrf_work(LAPACK_COL_MAJOR,'U',n,a,n);}
static int run(int n,int reps,int test){
    size_t bytes=(size_t)n*n*sizeof(double);int failed=0;
    double *original=alloc(bytes),*reference=alloc(bytes),*w=alloc(n*sizeof(double));
    long double *check=alloc(2*(size_t)n*sizeof(long double));
    generate_spd(original,n,2026);memcpy(reference,original,bytes);
    failed|=cholesky_right_buffered(reference,n,w)!=0;
    for(int rep=0;rep<=reps;++rep)for(int pos=0;pos<2;++pos){
        int method=(pos+(rep?rep-1:0))%2;
        double start=now();double *a=alloc(bytes),*workspace=alloc(n*sizeof(double));double t1=now();
        generate_spd(a,n,2026);double t2=now();
        int status=method?lapack(a,n):cholesky_right_buffered(a,n,workspace);double end=now();
        double residual=projected_residual(original,a,n,8,91827,check),diff=0;
        for(int i=0;i<n;++i)for(int j=0;j<=i;++j){size_t k=(size_t)i*n+j;double v=fabs(a[k]-reference[k])/fmax(1.,fabs(reference[k]));if(!isfinite(v))diff=INFINITY;else if(v>diff)diff=v;}
        failed|=status!=0||!isfinite(residual)||residual>1e-12||diff>1e-12;
        if(test){double r=relative_residual(original,a,n);failed|=!isfinite(r)||r>1e-12;}
        if(rep&&!test)printf("%d,%d,%d,%s,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g\n",n,rep,pos+1,method?"lapack":"own",t1-start,t2-t1,end-t2,end-start,residual,diff);
        free(a);free(workspace);
    }
    free(original);free(reference);free(w);free(check);return failed;
}
int main(int argc,char **argv){
    openblas_set_num_threads(1);
    fprintf(stderr,"OpenBLAS threads=%d config=%s\n",openblas_get_num_threads(),openblas_get_config());
    if(openblas_get_num_threads()!=1)return 3;
    if(argc==2&&!strcmp(argv[1],"--test")){
        int failed=0;int ns[]={1,2,3,7,31,65,128};for(int i=0;i<7;++i)failed|=run(ns[i],0,1);
        double known[]={4,12,-16,12,37,-43,-16,-43,98};double expected[]={2,0,0,6,1,0,-8,5,3};
        failed|=lapack(known,3)!=0;
        for(int i=0;i<3;++i)for(int j=0;j<=i;++j)failed|=fabs(known[i*3+j]-expected[i*3+j])>1e-12;
        double bad[]={1,2,2,1};failed|=lapack(bad,2)<=0;
        printf("LAPACK tests: %s\n",failed?"FAIL":"PASS");return failed;
    }
    int n=argc>1?number(argv[1]):-1,reps=argc>2?number(argv[2]):6;
    if(n<1||reps<2||reps>28||reps%2||argc>3)return 2;
    puts("N,repetition,order,method,allocation_s,generation_s,factor_s,total_s,projected_residual,factor_difference");
    return run(n,reps,0);
}
