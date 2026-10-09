#define _GNU_SOURCE
#include "cholesky.h"
#include "cholesky_mpi.h"
#include <errno.h>
#include <math.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void *allocate(size_t bytes) {
    void *p=malloc(bytes ? bytes : 1);
    if (!p) { fprintf(stderr,"Memoria insuficiente\n"); MPI_Abort(MPI_COMM_WORLD,3); }
    return p;
}
static int number(const char *s,int max) {
    char *end;errno=0;long x=strtol(s,&end,10);
    return errno || !*s || *end || x<1 || x>max ? -1 : (int)x;
}
static void pack_for_rank(const double *full,double *packed,int offset,
                          Layout d,int rank) {
    const int q=d.n/d.p,rem=d.n%d.p;
    d.rank=rank;d.cols=q+(rank<rem);d.first=rank; /* cíclico */
    for (int i=0;i<d.n;++i) for (int c=0;c<d.cols;++c)
        packed[offset+i*d.cols+c]=full[(size_t)i*d.n+layout_global(&d,c)];
}
static void unpack_rank(double *full,const double *packed,int offset,
                        Layout d,int rank) {
    const int q=d.n/d.p,rem=d.n%d.p;
    d.rank=rank;d.cols=q+(rank<rem);d.first=rank;
    for (int i=0;i<d.n;++i) for (int c=0;c<d.cols;++c)
        full[(size_t)i*d.n+layout_global(&d,c)]=packed[offset+i*d.cols+c];
}

static int run_case(int n,int reps,int profile_mode,int test) {
    int rank,p;MPI_Comm_rank(MPI_COMM_WORLD,&rank);MPI_Comm_size(MPI_COMM_WORLD,&p);
    const size_t bytes=(size_t)n*n*sizeof(double);
    double *original=NULL,*packed=NULL,*factor=NULL,*reference=NULL,*seqwork=NULL;
    if (!rank) {
        original=allocate(bytes);packed=allocate(bytes);factor=allocate(bytes);
        reference=allocate(bytes);seqwork=allocate((size_t)n*sizeof(double));
        generate_spd(original,(size_t)n,2026);
        if (test==1) { double known[9]={4,12,-16,12,37,-43,-16,-43,98};memcpy(original,known,sizeof known); }
        else if (test==2) original[0]=-1;
        else if (test==3) original[0]=NAN;
        memcpy(reference,original,bytes);
        if (test<2 && cholesky_right_buffered(reference,(size_t)n,seqwork)) MPI_Abort(MPI_COMM_WORLD,4);
    }
    int *counts=allocate((size_t)p*sizeof(int));int *displs=allocate((size_t)p*sizeof(int));
    Layout d=layout_create(n,1,MPI_COMM_WORLD);
    int offset=0;
    for (int r=0;r<p;++r) { counts[r]=n*(n/p+(r<n%p));displs[r]=offset;offset+=counts[r]; }
    int failed=0;
    for (int rep=0;rep<=reps;++rep) for (int position=0;position<2;++position) {
        const int algorithm=(rep+position)%2; /* 0 right, 1 left; orden alternado */
        if (!rank) for (int r=0;r<p;++r) pack_for_rank(original,packed,displs[r],d,r);
        double *local=allocate((size_t)n*d.cols*sizeof(double));
        double *column=allocate((size_t)n*sizeof(double));
        double *workspace=allocate((size_t)(d.cols ? d.cols : 1)*sizeof(double));
        double *partial=allocate((size_t)n*sizeof(double));
        double *reduced=allocate((size_t)n*sizeof(double));
        MPI_Scatterv(packed,counts,displs,MPI_DOUBLE,local,n*d.cols,MPI_DOUBLE,0,d.comm);
        MPI_Barrier(d.comm);
        Profile rp={0};LeftProfile lp={0};double start=MPI_Wtime();
        int status=algorithm
            ? cholesky_left_mpi(local,partial,reduced,&d,profile_mode ? &lp : NULL)
            : cholesky_mpi_local(local,column,workspace,&d,profile_mode ? &rp : NULL);
        double elapsed=MPI_Wtime()-start,maximum=0.0;
        MPI_Reduce(&elapsed,&maximum,1,MPI_DOUBLE,MPI_MAX,0,d.comm);
        int minimum_status,maximum_status;
        MPI_Allreduce(&status,&minimum_status,1,MPI_INT,MPI_MIN,d.comm);
        MPI_Allreduce(&status,&maximum_status,1,MPI_INT,MPI_MAX,d.comm);
        if (minimum_status!=maximum_status || status!=(test>=2 ? -1 : 0)) failed=1;
        MPI_Gatherv(local,n*d.cols,MPI_DOUBLE,packed,counts,displs,MPI_DOUBLE,0,d.comm);
        double residual=0.0,difference=0.0;
        if (!rank && test<2) {
            for (int r=0;r<p;++r) unpack_rank(factor,packed,displs[r],d,r);
            residual=relative_residual(original,factor,(size_t)n);
            for (int i=0;i<n;++i) for (int j=0;j<=i;++j) {
                double delta=fabs(factor[(size_t)i*n+j]-reference[(size_t)i*n+j])/fmax(1.0,fabs(reference[(size_t)i*n+j]));
                if (!isfinite(delta)) difference=INFINITY; else if (delta>difference) difference=delta;
            }
            if (!isfinite(residual) || residual>1e-12 || difference>1e-12) failed=1;
        }
        if (rep>0 && !test && !profile_mode && !rank)
            printf("%d,%d,%d,%d,%s,%.12g,%.12g,%.12g\n",n,p,rep,position+1,algorithm?"left":"right",maximum,residual,difference);
        if (rep>0 && profile_mode) {
            double values[5]={elapsed,algorithm?lp.compute:rp.compute,
                              algorithm?lp.reduce:0.0,
                              algorithm?lp.broadcast:rp.broadcast,
                              (double)(algorithm?lp.products:rp.updates)};
            double *all=!rank ? allocate((size_t)p*5*sizeof(double)) : NULL;
            MPI_Gather(values,5,MPI_DOUBLE,all,5,MPI_DOUBLE,0,d.comm);
            if (!rank) {
                for (int r=0;r<p;++r)
                    printf("%d,%d,%d,%s,%d,%.12g,%.12g,%.12g,%.12g,%.0f\n",n,p,rep,algorithm?"left":"right",r,all[5*r],all[5*r+1],all[5*r+2],all[5*r+3],all[5*r+4]);
                free(all);
            }
        }
        free(local);free(column);free(workspace);free(partial);free(reduced);
    }
    int any;MPI_Allreduce(&failed,&any,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);
    free(original);free(packed);free(factor);free(reference);free(seqwork);free(counts);free(displs);
    return any;
}
int main(int argc,char **argv) {
    MPI_Init(&argc,&argv);int rank,p;MPI_Comm_rank(MPI_COMM_WORLD,&rank);MPI_Comm_size(MPI_COMM_WORLD,&p);int failed=0;
    if (argc==2 && !strcmp(argv[1],"--test")) {
        int sizes[]={1,2,3,7,16,31};for (int i=0;i<6;++i) failed|=run_case(sizes[i],1,0,-1);
        failed|=run_case(3,1,0,1);failed|=run_case(3,1,0,2);failed|=run_case(3,1,0,3);
        if (!rank) printf("MPI left/right P=%d: %s\n",p,failed?"FAIL":"PASS");
    } else {
        int n=argc>1?number(argv[1],46340):-1;int reps=argc>2?number(argv[2],1000):8;
        int profile_mode=argc==4 && !strcmp(argv[3],"profile");
        if (n<1 || reps<1 || reps%2 || argc>4 || (argc==4 && !profile_mode)) { if (!rank) fprintf(stderr,"Uso: compare_mpi_algorithms N [repeticiones pares=8] [profile]\n");MPI_Finalize();return 2; }
        char host[MPI_MAX_PROCESSOR_NAME];int len;MPI_Get_processor_name(host,&len);
        cpu_set_t mask;CPU_ZERO(&mask);sched_getaffinity(0,sizeof mask,&mask);
        fprintf(stderr,"rank=%d P=%d host=%s cpu=%d affinity_count=%d\n",rank,p,host,sched_getcpu(),CPU_COUNT(&mask));
        if (!rank) puts(profile_mode?"N,P,repetition,algorithm,rank,total,compute,reduce,broadcast,work":"N,P,repetition,order,algorithm,seconds,relative_residual,factor_difference");
        failed=run_case(n,reps,profile_mode,0);
    }
    MPI_Finalize();return failed?1:0;
}
