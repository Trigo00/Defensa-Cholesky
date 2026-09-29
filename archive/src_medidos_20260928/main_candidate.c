#define _POSIX_C_SOURCE 200809L
#include "cholesky.h"
#ifdef USE_MPI
#include "cholesky_mpi.h"
#endif
#include <errno.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static double now(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC,&t);
    return t.tv_sec+t.tv_nsec*1e-9;
}
static void *reserve(size_t count,size_t size) {
    void *p=malloc((count?count:1)*size);
    if(!p) {
        fputs("No se pudo reservar memoria\n",stderr);
#ifdef USE_MPI
        MPI_Abort(MPI_COMM_WORLD,3);
#endif
        exit(3);
    }
    return p;
}
int main(int argc,char **argv) {
    int rank=0,processes=1;
#ifdef USE_MPI
    MPI_Init(&argc,&argv);
    MPI_Comm_rank(MPI_COMM_WORLD,&rank); MPI_Comm_size(MPI_COMM_WORLD,&processes);
#endif
    char *end=NULL; errno=0;
    long value=argc==2?strtol(argv[1],&end,10):0;
    if(argc!=2 || errno || !end || *end || value<1 || value>20000) {
        if(!rank) fputs("Uso: cholesky_candidate N (1..20000)\n",stderr);
#ifdef USE_MPI
        MPI_Finalize();
#endif
        return 2;
    }
    int n=(int)value,failed=0; size_t cells=(size_t)n*n;
    double *full=NULL,*packed=NULL,*local=NULL,*column=NULL,*work=NULL;
    int *counts=NULL,*offsets=NULL;
#ifdef USE_MPI
    MPI_Barrier(MPI_COMM_WORLD);
#endif
    double t0=now();
    if(!rank) full=reserve(cells,sizeof(double));
#ifdef USE_MPI
    Layout d=layout_create(n,1,MPI_COMM_WORLD);
    if(!rank) packed=reserve(cells,sizeof(double));
    local=reserve((size_t)n*d.cols,sizeof(double));
    column=reserve(n,sizeof(double)); work=reserve(d.cols,sizeof(double));
    counts=reserve(processes,sizeof(int)); offsets=reserve(processes,sizeof(int));
    int offset=0;
    for(int r=0;r<processes;++r) {
        counts[r]=n*(n/processes+(r<n%processes)); offsets[r]=offset; offset+=counts[r];
    }
#else
    work=reserve(n,sizeof(double));
#endif
    double t1=now();
#ifdef USE_MPI
    generate_spd_columns(local,n,2026,rank,processes);
#else
    generate_spd(full,n,2026);
#endif
    double t2=now();
#ifdef USE_MPI
    failed=cholesky_mpi_local(local,column,work,&d,NULL)!=0;
#else
    failed=cholesky_right_buffered(full,n,work)!=0;
#endif
    double t3=now();
#ifdef USE_MPI
    MPI_Gatherv(local,n*d.cols,MPI_DOUBLE,packed,counts,offsets,MPI_DOUBLE,0,MPI_COMM_WORLD);
    if(!rank) for(int r=0;r<processes;++r) {
        int m=n/processes+(r<n%processes);
        for(int i=0;i<n;++i) for(int c=0;c<m;++c)
            full[(size_t)i*n+r+c*processes]=packed[offsets[r]+(size_t)i*m+c];
    }
#endif
    double t4=now(),elapsed=t4-t0,max_elapsed=elapsed;
#ifdef USE_MPI
    MPI_Reduce(&elapsed,&max_elapsed,1,MPI_DOUBLE,MPI_MAX,0,MPI_COMM_WORLD);
    int any; MPI_Allreduce(&failed,&any,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD); failed=any;
#endif
    if(!rank) {
        double v0=now();
        double *original=reserve(cells,sizeof(double));
        long double *check=reserve(2*(size_t)n,sizeof(long double));
        generate_spd(original,n,2026);
        double residual=projected_residual(original,full,n,8,91827,check);
        double exact=n<=128?relative_residual(original,full,n):-1;
        failed|=!isfinite(residual)||residual>1e-12;
        if(n<=128) failed|=!isfinite(exact)||exact>1e-12;
        for(int i=0;i<n;++i) for(int j=0;j<=i;++j)
            failed|=!isfinite(full[(size_t)i*n+j]) || (i==j && full[(size_t)i*n+j]<=0);
        double validation=now()-v0;
        puts("N,P,allocation_s,generation_s,factor_s,gather_s,application_s,max_local_s,validation_s,projected_residual,exact_residual,valid");
        printf("%d,%d,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%d\n",n,processes,t1-t0,t2-t1,t3-t2,t4-t3,t4-t0,max_elapsed,validation,residual,exact,!failed);
        free(original);free(check);
    }
#ifdef USE_MPI
    MPI_Bcast(&failed,1,MPI_INT,0,MPI_COMM_WORLD);
#endif
    free(full);free(packed);free(local);free(column);free(work);free(counts);free(offsets);
#ifdef USE_MPI
    MPI_Finalize();
#endif
    return failed?1:0;
}
