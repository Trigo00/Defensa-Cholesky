#include "cholesky.h"
#include "cholesky_mpi.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <errno.h>
static void *alloc(size_t bytes){void *a=malloc(bytes?bytes:1);if(!a)MPI_Abort(MPI_COMM_WORLD,3);return a;}
static int number(const char *s){char *e;errno=0;long x=strtol(s,&e,10);return errno||!*s||*e||x<1||x>20000?-1:(int)x;}
static int mapping_test(int n) {
    int bad=0;const int blocks[]={1,2,4,8,16,32,64};
    for(int v=0;v<7;++v){
        Layout d=layout_block_create(n,blocks[v],MPI_COMM_WORLD),old=layout_create(n,1,MPI_COMM_WORLD);
        int count=0;
        for(int k=0;k<n;++k){
            bad|=layout_before(&d,k)!=count;
            int owner=(k/blocks[v])%d.p;
            bad|=layout_owner(&d,k)!=owner;
            if(owner==d.rank){bad|=layout_global(&d,count)!=k;++count;}
            if(blocks[v]==1) bad|=layout_owner(&d,k)!=layout_owner(&old,k)||layout_before(&d,k)!=layout_before(&old,k);
        }
        bad|=count!=d.cols||layout_before(&d,n)!=count;
        if(blocks[v]==1)bad|=d.cols!=old.cols;
    }
    int any;MPI_Allreduce(&bad,&any,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);return any;
}
static int run(int n,int reps,int testing,int pair){
    int rank,p;MPI_Comm_rank(MPI_COMM_WORLD,&rank);MPI_Comm_size(MPI_COMM_WORLD,&p);
    size_t bytes=(size_t)n*n*sizeof(double);int failed=mapping_test(n);
    double *original=NULL,*ref=NULL;long double *check=NULL;
    if(!rank){original=alloc(bytes);ref=alloc(bytes);check=alloc(2*(size_t)n*sizeof(long double));double *w=alloc(n*sizeof(double));
        generate_spd(original,n,2026);memcpy(ref,original,bytes);failed|=cholesky_right_buffered(ref,n,w)!=0;free(w);}
    const int blocks[]={1,2,4,8,16,32,64};
    int variants=pair?2:7;
    for(int rep=0;rep<=reps;++rep)for(int pos=0;pos<variants;++pos){
        int index=(pos+(rep?rep-1:0))%variants;
        int b=pair?(index?4:1):blocks[index];
        MPI_Barrier(MPI_COMM_WORLD);double t[5];t[0]=MPI_Wtime();
        Layout d=layout_block_create(n,b,MPI_COMM_WORLD);
        int *columns=alloc(d.cols*sizeof(int)),*counts=alloc(p*sizeof(int)),*displs=alloc(p*sizeof(int));
        for(int c=0;c<d.cols;++c)columns[c]=layout_global(&d,c);
        int offset=0;for(int r=0;r<p;++r){Layout other=d;other.rank=r;counts[r]=n*layout_before(&other,n);displs[r]=offset;offset+=counts[r];}
        double *local=alloc((size_t)n*d.cols*sizeof(double)),*col=alloc(n*sizeof(double)),*work=alloc(d.cols*sizeof(double));
        double *packed=rank?NULL:alloc(bytes),*full=rank?NULL:alloc(bytes);
        t[1]=MPI_Wtime();generate_spd_selected(local,n,2026,columns,d.cols);t[2]=MPI_Wtime();
        int bad=cholesky_mpi_local(local,col,work,&d,NULL)!=0;t[3]=MPI_Wtime();
        MPI_Gatherv(local,n*d.cols,MPI_DOUBLE,packed,counts,displs,MPI_DOUBLE,0,d.comm);
        if(!rank)for(int r=0;r<p;++r){Layout other=d;other.rank=r;int m=counts[r]/n;
            for(int i=0;i<n;++i)for(int c=0;c<m;++c)full[(size_t)i*n+layout_global(&other,c)]=packed[displs[r]+(size_t)i*m+c];}
        t[4]=MPI_Wtime();
        unsigned long long updates=0;for(int c=0;c<d.cols;++c){unsigned long long k=columns[c];updates+=k*(n-k);}
        unsigned long long maxwork=0,sumwork=0;MPI_Reduce(&updates,&maxwork,1,MPI_UNSIGNED_LONG_LONG,MPI_MAX,0,d.comm);MPI_Reduce(&updates,&sumwork,1,MPI_UNSIGNED_LONG_LONG,MPI_SUM,0,d.comm);
        if(!rank){double res=projected_residual(original,full,n,8,91827,check),diff=0;
            for(int i=0;i<n;++i)for(int j=0;j<=i;++j){size_t k=(size_t)i*n+j;double v=fabs(full[k]-ref[k])/fmax(1.,fabs(ref[k]));if(!isfinite(v))diff=INFINITY;else if(v>diff)diff=v;}
            bad|=!isfinite(res)||res>1e-12||diff>1e-12;
            if(testing){double exact=relative_residual(original,full,n);bad|=!isfinite(exact)||exact>1e-12;}
            if(rep&&!testing)printf("%d,%d,%d,%d,%d,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g,%.12g\n",n,p,rep,pos+1,b,t[1]-t[0],t[2]-t[1],t[3]-t[2],t[4]-t[3],t[4]-t[0],res,diff,sumwork?(double)maxwork*p/sumwork:1.);
        }
        int any;MPI_Allreduce(&bad,&any,1,MPI_INT,MPI_MAX,d.comm);failed|=any;
        free(columns);free(counts);free(displs);free(local);free(col);free(work);free(packed);free(full);
    }
    free(original);free(ref);free(check);int any;MPI_Allreduce(&failed,&any,1,MPI_INT,MPI_MAX,MPI_COMM_WORLD);return any;
}
int main(int argc,char **argv){MPI_Init(&argc,&argv);int rank;MPI_Comm_rank(MPI_COMM_WORLD,&rank);int result=0;
    if(argc==2&&!strcmp(argv[1],"--test")){int sizes[]={1,2,3,7,31,65};for(int i=0;i<6;++i)result|=run(sizes[i],0,1,0);if(!rank)printf("block tests: %s\n",result?"FAIL":"PASS");}
    else{int n=argc>1?number(argv[1]):-1,reps=argc>2?number(argv[2]):7;
        int pair=argc==4&&!strcmp(argv[3],"pair");
        if(n<1||reps<1||reps>28||reps%(pair?2:7)||argc>4||(argc==4&&!pair)){MPI_Finalize();return 2;}
        if(!rank)puts("N,P,repetition,order,block,allocation_s,generation_s,factor_s,gather_s,total_s,projected_residual,factor_difference,work_imbalance");
        result=run(n,reps,0,pair);}
    MPI_Finalize();return result;
}
