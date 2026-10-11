#define _GNU_SOURCE
#include "cholesky.h"
#include "cholesky_mpi.h"
#include <errno.h>
#include <math.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { RIGHT=0, LEFT=1, SEQUENTIAL=2 };
static void *allocate(size_t bytes) {
    void *p=malloc(bytes ? bytes : 1);
    if (!p) { fprintf(stderr,"Memoria insuficiente\n");MPI_Abort(MPI_COMM_WORLD,3); }
    return p;
}
static int number(const char *s,int max) {
    char *end;errno=0;long x=strtol(s,&end,10);
    return errno || !*s || *end || x<1 || x>max ? -1 : (int)x;
}
static void configure(Layout *d,int rank) {
    const int q=d->n/d->p,rem=d->n%d->p;
    d->rank=rank;d->cols=q+(rank<rem);d->first=rank;
}
static void pack(const double *full,double *packed,const int *displs,Layout d) {
    for (int r=0;r<d.p;++r) {
        configure(&d,r);
        for (int i=0;i<d.n;++i) for (int c=0;c<d.cols;++c)
            packed[displs[r]+i*d.cols+c]=full[(size_t)i*d.n+layout_global(&d,c)];
    }
}
static void unpack(double *full,const double *packed,const int *displs,Layout d) {
    for (int r=0;r<d.p;++r) {
        configure(&d,r);
        for (int i=0;i<d.n;++i) for (int c=0;c<d.cols;++c)
            full[(size_t)i*d.n+layout_global(&d,c)]=packed[displs[r]+i*d.cols+c];
    }
}
static int run_case(int n,int reps,int test) {
    int rank,p;MPI_Comm_rank(MPI_COMM_WORLD,&rank);MPI_Comm_size(MPI_COMM_WORLD,&p);
    const size_t bytes=(size_t)n*n*sizeof(double);
    double *original=NULL,*packed=NULL,*factor=NULL,*reference=NULL,*seqwork=NULL;
    if (!rank) {
        original=allocate(bytes);packed=allocate(bytes);factor=allocate(bytes);
        reference=allocate(bytes);seqwork=allocate((size_t)n*sizeof(double));
        generate_spd(original,(size_t)n,2026);
        if (test==1) { double known[9]={4,12,-16,12,37,-43,-16,-43,98};memcpy(original,known,sizeof known); }
        else if (test==2) original[0]=-1; else if (test==3) original[0]=NAN;
        memcpy(reference,original,bytes);
        if (test<2 && cholesky_right_buffered(reference,(size_t)n,seqwork)) MPI_Abort(MPI_COMM_WORLD,4);
    }
    Layout d=layout_create(n,1,MPI_COMM_WORLD);
    int *counts=allocate((size_t)p*sizeof(int));int *displs=allocate((size_t)p*sizeof(int));int offset=0;
    for (int r=0;r<p;++r) { counts[r]=n*(n/p+(r<n%p));displs[r]=offset;offset+=counts[r]; }
    double *local=allocate((size_t)n*d.cols*sizeof(double));
    double *column=allocate((size_t)n*sizeof(double));
    double *rightwork=allocate((size_t)(d.cols?d.cols:1)*sizeof(double));
    double *partial=allocate((size_t)n*sizeof(double));double *reduced=allocate((size_t)n*sizeof(double));
    const int orders[6][3]={{0,1,2},{0,2,1},{1,0,2},{1,2,0},{2,0,1},{2,1,0}};
    int failed=0;
    for (int rep=0;rep<=reps;++rep) for (int position=0;position<3;++position) {
        const int algorithm=rep ? orders[(rep-1)%6][position] : position;
        MPI_Barrier(d.comm);
        double t0=MPI_Wtime(),t1=t0,t2=t0,t3=t0;int status=0;
        if (algorithm==SEQUENTIAL) {
            if (!rank) {
                memcpy(factor,original,bytes);t1=MPI_Wtime();
                status=cholesky_right_buffered(factor,(size_t)n,seqwork);t2=MPI_Wtime();t3=t2;
            }
            MPI_Bcast(&status,1,MPI_INT,0,d.comm);
        } else {
            if (!rank) pack(original,packed,displs,d);
            MPI_Scatterv(packed,counts,displs,MPI_DOUBLE,local,n*d.cols,MPI_DOUBLE,0,d.comm);
            t1=MPI_Wtime();
            status=algorithm==LEFT
                ? cholesky_left_mpi(local,partial,reduced,&d,NULL)
                : cholesky_mpi_local(local,column,rightwork,&d,NULL);
            t2=MPI_Wtime();
            MPI_Gatherv(local,n*d.cols,MPI_DOUBLE,packed,counts,displs,MPI_DOUBLE,0,d.comm);
            if (!rank) unpack(factor,packed,displs,d);
            t3=MPI_Wtime();
        }
        double local_times[4]={t1-t0,t2-t1,t3-t2,t3-t0},maximum[4]={0};
        MPI_Reduce(local_times,maximum,4,MPI_DOUBLE,MPI_MAX,0,d.comm);
        int min_status,max_status;
        MPI_Allreduce(&status,&min_status,1,MPI_INT,MPI_MIN,d.comm);
        MPI_Allreduce(&status,&max_status,1,MPI_INT,MPI_MAX,d.comm);
        if (min_status!=max_status || min_status!=(test>=2?-1:0)) failed=1;
        double residual=0.0,difference=0.0;
        if (!rank && test<2) {
            residual=relative_residual(original,factor,(size_t)n);
            for (int i=0;i<n;++i) for (int j=0;j<=i;++j) {
                double delta=fabs(factor[(size_t)i*n+j]-reference[(size_t)i*n+j])/fmax(1.0,fabs(reference[(size_t)i*n+j]));
                if (!isfinite(delta)) difference=INFINITY;else if (delta>difference) difference=delta;
            }
            if (!isfinite(residual)||residual>1e-12||difference>1e-12) failed=1;
        }
        if (rep>0 && !test && !rank) {
            const char *name=algorithm==RIGHT?"right":algorithm==LEFT?"left":"sequential";
            printf("%d,%d,%d,%d,%s,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g\n",n,p,rep,position+1,name,maximum[0],maximum[1],maximum[2],maximum[3],residual,difference);
        }
    }
    int any;MPI_Allreduce(&failed,&any,1,MPI_INT,MPI_MAX,d.comm);
    free(original);free(packed);free(factor);free(reference);free(seqwork);free(counts);free(displs);
    free(local);free(column);free(rightwork);free(partial);free(reduced);return any;
}
int main(int argc,char **argv) {
    MPI_Init(&argc,&argv);int rank,p;MPI_Comm_rank(MPI_COMM_WORLD,&rank);MPI_Comm_size(MPI_COMM_WORLD,&p);int failed=0;
    if (argc==2 && !strcmp(argv[1],"--test")) {
        int sizes[]={1,2,3,7,16,31};for (int i=0;i<6;++i) failed|=run_case(sizes[i],1,-1);
        failed|=run_case(3,1,1);failed|=run_case(3,1,2);failed|=run_case(3,1,3);
        if (!rank) printf("MPI total P=%d: %s\n",p,failed?"FAIL":"PASS");
    } else {
        int n=argc>1?number(argv[1],20000):-1;int reps=argc>2?number(argv[2],600):12;
        if (n<1||reps<1||reps%6||argc>3) { if (!rank) fprintf(stderr,"Uso: compare_mpi_total N [repeticiones multiplo de 6=12]\n");MPI_Finalize();return 2; }
        char host[MPI_MAX_PROCESSOR_NAME];int len;MPI_Get_processor_name(host,&len);cpu_set_t mask;CPU_ZERO(&mask);sched_getaffinity(0,sizeof mask,&mask);
        fprintf(stderr,"rank=%d P=%d host=%s cpu=%d affinity_count=%d\n",rank,p,host,sched_getcpu(),CPU_COUNT(&mask));
        if (!rank) puts("N,P,repetition,order,algorithm,input_s,factor_s,gather_s,total_s,relative_residual,factor_difference");
        failed=run_case(n,reps,0);
    }
    MPI_Finalize();return failed?1:0;
}
