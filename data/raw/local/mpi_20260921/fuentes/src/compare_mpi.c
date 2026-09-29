#define _GNU_SOURCE
#include "cholesky.h"
#include "cholesky_mpi.h"
#include <errno.h>
#include <limits.h>
#include <math.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void *allocate(size_t bytes) {
    void *p=malloc(bytes ? bytes : sizeof(double));
    if (!p) { fprintf(stderr,"Memoria insuficiente\n"); MPI_Abort(MPI_COMM_WORLD,3); }
    return p;
}
static int number(const char *s, int max) {
    char *end; errno=0;
    long x=strtol(s,&end,10);
    return errno || *end || !*s || x<1 || x>max ? -1 : (int)x;
}

/* root es el unico que conserva A completa. La conversion a columnas
 * locales, Scatterv, Gatherv y validacion quedan fuera del cronometro. */
static int run_case(int n, int reps, int mode, int test) {
    int rank,p; MPI_Comm_rank(MPI_COMM_WORLD,&rank); MPI_Comm_size(MPI_COMM_WORLD,&p);
    size_t bytes=(size_t)n*n*sizeof(double);
    double *original=NULL,*packed=NULL,*factor=NULL,*ref=NULL,*work=NULL;
    if (!rank) {
        original=allocate(bytes); packed=allocate(bytes); factor=allocate(bytes);
        ref=allocate(bytes); work=allocate((size_t)n*sizeof(double));
        generate_spd(original,n,2026);
        if (test==1) { /* Matriz con factor conocido. */
            double known[9]={4,12,-16,12,37,-43,-16,-43,98};
            memcpy(original,known,sizeof known);
        } else if (test==2) original[0]=-1;
        else if (test==3) original[0]=NAN;
        memcpy(ref,original,bytes);
        if (test<2 && cholesky_right_buffered(ref,n,work)) MPI_Abort(MPI_COMM_WORLD,4);
    }
    int *counts=allocate((size_t)p*sizeof(int)), *displs=allocate((size_t)p*sizeof(int));
    int failed=0;
    /* Calentamiento y repeticiones, alternando cual reparto se ejecuta primero. */
    for (int rep=0;rep<=reps;++rep) for (int order=0;order<2;++order) {
        int cyclic=(rep+order)%2;
        Layout d=layout_create(n,cyclic,MPI_COMM_WORLD);
        double *local=allocate((size_t)n*d.cols*sizeof(double));
        double *column=allocate((size_t)n*sizeof(double));
        int offset=0;
        for (int r=0;r<p;++r) {
            Layout other=d; other.rank=r;
            int q=n/p,rem=n%p;
            other.cols=q+(r<rem);
            other.first=cyclic ? r : r*q+(r<rem ? r : rem);
            counts[r]=n*other.cols; displs[r]=offset;
            if (!rank) for (int i=0;i<n;++i) for (int c=0;c<other.cols;++c)
                packed[offset+i*other.cols+c]=original[(size_t)i*n+layout_global(&other,c)];
            offset+=counts[r];
        }
        MPI_Scatterv(packed,counts,displs,MPI_DOUBLE,local,n*d.cols,MPI_DOUBLE,0,MPI_COMM_WORLD);
        MPI_Barrier(MPI_COMM_WORLD);
        Profile prof={0};
        double start=MPI_Wtime();
        int status=cholesky_mpi(local,column,&d,mode ? &prof : NULL);
        double elapsed=MPI_Wtime()-start, maximum=0;
        MPI_Reduce(&elapsed,&maximum,1,MPI_DOUBLE,MPI_MAX,0,MPI_COMM_WORLD);
        int status_min,status_max;
        MPI_Allreduce(&status,&status_min,1,MPI_INT,MPI_MIN,MPI_COMM_WORLD);
        MPI_Allreduce(&status,&status_max,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);
        if (status_min!=status_max || status!=(test>=2 ? -1 : 0)) failed=1;
        MPI_Gatherv(local,n*d.cols,MPI_DOUBLE,packed,counts,displs,MPI_DOUBLE,0,MPI_COMM_WORLD);
        double residual=0,difference=0;
        if (!rank && test<2) {
            for (int r=0;r<p;++r) {
                Layout other=d; other.rank=r; other.cols=counts[r]/n;
                int q=n/p,rem=n%p;
                other.first=cyclic ? r : r*q+(r<rem ? r : rem);
                for (int i=0;i<n;++i) for (int c=0;c<other.cols;++c)
                    factor[(size_t)i*n+layout_global(&other,c)]=packed[displs[r]+i*other.cols+c];
            }
            residual=relative_residual(original,factor,n);
            for (int i=0;i<n;++i) for (int j=0;j<=i;++j) {
                double delta=fabs(factor[(size_t)i*n+j]-ref[(size_t)i*n+j])/fmax(1,fabs(ref[(size_t)i*n+j]));
                if (!isfinite(delta)) difference=INFINITY;
                else if (delta>difference) difference=delta;
            }
            if (test==1) {
                double knownL[9]={2,0,0,6,1,0,-8,5,3};
                for (int i=0;i<n;++i) for (int j=0;j<=i;++j)
                    if (fabs(factor[i*n+j]-knownL[i*n+j])>1e-13) failed=1;
            }
            if (!isfinite(residual) || residual>1e-12 || difference>1e-13) failed=1;
        }
        if (rep>0 && !test) {
            if (!mode && !rank)
                printf("%d,%d,%d,%d,%s,%.12g,%.12g,%.12g\n",n,p,rep,order+1,cyclic?"cyclic":"contiguous",maximum,residual,difference);
            if (mode) {
                double values[4]={elapsed,prof.compute,prof.broadcast,(double)prof.updates};
                double *all=!rank ? allocate((size_t)p*4*sizeof(double)) : NULL;
                MPI_Gather(values,4,MPI_DOUBLE,all,4,MPI_DOUBLE,0,MPI_COMM_WORLD);
                if (!rank) for (int r=0;r<p;++r)
                    printf("%d,%d,%d,%s,%d,%.12g,%.12g,%.12g,%.0f\n",n,p,rep,cyclic?"cyclic":"contiguous",r,all[4*r],all[4*r+1],all[4*r+2],all[4*r+3]);
                free(all);
            }
        }
        free(local); free(column);
    }
    int any; MPI_Allreduce(&failed,&any,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);
    free(original);free(packed);free(factor);free(ref);free(work);free(counts);free(displs);
    return any;
}
int main(int argc,char **argv) {
    MPI_Init(&argc,&argv);
    int rank,p; MPI_Comm_rank(MPI_COMM_WORLD,&rank); MPI_Comm_size(MPI_COMM_WORLD,&p);
    int failed=0;
    if (argc==2 && !strcmp(argv[1],"--test")) {
        int sizes[]={1,2,7,16,31};
        for (int k=0;k<5;++k) failed|=run_case(sizes[k],1,0,-1);
        failed|=run_case(3,1,0,1);
        failed|=run_case(3,1,0,2);
        failed|=run_case(3,1,0,3);
        if (!rank) printf("MPI P=%d: %s (ambos repartos, SPD, factor conocido y fallos colectivos)\n",p,failed?"FAIL":"PASS");
    } else {
        int n=argc>1 ? number(argv[1],46340) : -1;
        int reps=argc>2 ? number(argv[2],1000) : 8;
        int mode=argc==4 && !strcmp(argv[3],"profile");
        if (n<1 || reps<1 || argc>4 || (argc==4 && !mode)) {
            if (!rank) fprintf(stderr,"Uso: compare_mpi N [repeticiones=8] [profile]\n");
            MPI_Finalize();return 2;
        }
        char host[MPI_MAX_PROCESSOR_NAME]; int len;
        MPI_Get_processor_name(host,&len);
        cpu_set_t mask; CPU_ZERO(&mask); sched_getaffinity(0,sizeof mask,&mask);
        fprintf(stderr,"rank=%d P=%d host=%s cpu=%d affinity_count=%d\n",rank,p,host,sched_getcpu(),CPU_COUNT(&mask));
        if (!rank) puts(mode ? "N,P,repetition,distribution,rank,total,compute,broadcast,updates" : "N,P,repetition,order,distribution,seconds,relative_residual,factor_difference");
        failed=run_case(n,reps,mode,0);
    }
    MPI_Finalize();return failed ? 1 : 0;
}
