#include "cholesky.h"
#include "cholesky_mpi.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
static void *alloc(size_t bytes) {
    void *p=malloc(bytes?bytes:1);
    if(!p) MPI_Abort(MPI_COMM_WORLD,2);
    return p;
}
int main(int argc,char **argv) {
    MPI_Init(&argc,&argv);
    int rank,p; MPI_Comm_rank(MPI_COMM_WORLD,&rank); MPI_Comm_size(MPI_COMM_WORLD,&p);
    int n=argc>1?atoi(argv[1]):512, reps=argc>2?atoi(argv[2]):6;
    if(n<1 || n>20000 || reps<2 || reps%2) { MPI_Finalize(); return 2; }
    Layout d=layout_create(n,1,MPI_COMM_WORLD);
    size_t bytes=(size_t)n*n*sizeof(double);
    double *full=rank?NULL:alloc(bytes), *packed=rank?NULL:alloc(bytes);
    double *local=alloc((size_t)n*d.cols*sizeof(double));
    double *expected=alloc((size_t)n*d.cols*sizeof(double));
    int *counts=alloc(p*sizeof(int)), *displs=alloc(p*sizeof(int));
    int offset=0;
    for(int r=0;r<p;++r) {counts[r]=n*(n/p+(r<n%p));displs[r]=offset;offset+=counts[r];}
    /* Independent legacy reference, created outside measurements. */
    if(!rank) {
        generate_spd(full,n,2026);
        for(int r=0;r<p;++r) {
            int m=counts[r]/n;
            for(int i=0;i<n;++i) for(int c=0;c<m;++c)
                packed[displs[r]+i*m+c]=full[(size_t)i*n+r+c*p];
        }
    }
    MPI_Scatterv(packed,counts,displs,MPI_DOUBLE,expected,n*d.cols,MPI_DOUBLE,0,d.comm);
    if(!rank) puts("N,P,repetition,method,generation_s,distribution_s,total_s,identical");
    int failed=0;
    for(int rep=0;rep<=reps;++rep) for(int pos=0;pos<2;++pos) {
        int distributed=(rep+pos)%2;
        MPI_Barrier(d.comm);
        double start=MPI_Wtime(),middle,end;
        if(distributed) {
            generate_spd_columns(local,n,2026,rank,p);
            middle=MPI_Wtime();end=middle;
        } else {
            if(!rank) generate_spd(full,n,2026);
            middle=MPI_Wtime();
            if(!rank) for(int r=0;r<p;++r) {
                int m=counts[r]/n;
                for(int i=0;i<n;++i) for(int c=0;c<m;++c)
                    packed[displs[r]+i*m+c]=full[(size_t)i*n+r+c*p];
            }
            MPI_Scatterv(packed,counts,displs,MPI_DOUBLE,local,n*d.cols,MPI_DOUBLE,0,d.comm);
            end=MPI_Wtime();
        }
        double times[3]={middle-start,end-middle,end-start},maximum[3];
        MPI_Reduce(times,maximum,3,MPI_DOUBLE,MPI_MAX,0,d.comm);
        int same=memcmp(local,expected,(size_t)n*d.cols*sizeof(double))==0, all;
        MPI_Allreduce(&same,&all,1,MPI_INT,MPI_MIN,d.comm);
        failed|=!all;
        if(rep && !rank) printf("%d,%d,%d,%s,%.12g,%.12g,%.12g,%d\n",n,p,rep,
            distributed?"distributed":"centralized",maximum[0],maximum[1],maximum[2],all);
    }
    free(full);free(packed);free(local);free(expected);free(counts);free(displs);
    MPI_Finalize();return failed;
}
