#include "cholesky.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do { if(!(c)) { fprintf(stderr,"FAIL %d: %s\n",__LINE__,#c); return 1; } } while(0)

int main(void) {
    const double known[]={4,12,-16,12,37,-43,-16,-43,98};
    const double expected[]={2,0,0,6,1,0,-8,5,3};
    double a[9],column[3]; memcpy(a,known,sizeof a);
    CHECK(cholesky_right_buffered(a,3,column)==0);
    for(size_t i=0;i<3;++i) for(size_t j=0;j<=i;++j) CHECK(a[i*3+j]==expected[i*3+j]);
    CHECK(relative_residual(known,a,3)==0.0);
    double bad[]={1,2,2,1},semi[]={1,1,1,1},nan[]={NAN},inf[]={INFINITY},scalar[]={9};
    CHECK(cholesky_right_buffered(bad,2,column)!=0 && cholesky_right_buffered(semi,2,column)!=0);
    CHECK(cholesky_right_buffered(nan,1,column)!=0 && cholesky_right_buffered(inf,1,column)!=0);
    CHECK(cholesky_right_buffered(NULL,0,column)!=0 && cholesky_right_buffered(a,3,NULL)!=0);
    CHECK(cholesky_right_buffered(scalar,1,column)==0 && scalar[0]==3);

    const size_t sizes[]={2,7,16,31,65};
    const uint64_t seeds[]={0,42,2026};
    double max_residual=0.0;
    for(size_t s=0;s<5;++s) {
        size_t n=sizes[s],bytes=n*n*sizeof(double);
        double *original=malloc(bytes),*direct=malloc(bytes),*buffered=malloc(bytes);
        /* Centinelas detectan escrituras mas alla del workspace de n valores. */
        double *storage=malloc((n+2)*sizeof(double));
        CHECK(original && direct && buffered && storage);
        storage[0]=123456.0; storage[n+1]=-123456.0;
        for(size_t seed=0;seed<3;++seed) {
            generate_spd(original,n,seeds[seed]);
            memcpy(direct,original,bytes); memcpy(buffered,original,bytes);
            /* Envenenar el workspace: solo deben leerse entradas inicializadas. */
            for(size_t i=1;i<=n;++i) storage[i]=NAN;
            CHECK(cholesky_right(direct,n)==0);
            CHECK(cholesky_right_buffered(buffered,n,storage+1)==0);
            double residual=relative_residual(original,buffered,n);
            CHECK(isfinite(residual) && residual<1e-12);
            max_residual=fmax(max_residual,residual);
            for(size_t i=0;i<n;++i) for(size_t j=0;j<=i;++j)
                CHECK(fabs(direct[i*n+j]-buffered[i*n+j])<=1e-13*fmax(1.0,fabs(direct[i*n+j])));
            CHECK(storage[0]==123456.0 && storage[n+1]==-123456.0);
        }
        free(original);free(direct);free(buffered);free(storage);
    }
    printf("PASS right_buffered: factor conocido, errores, workspace y 15 matrices; r_max=%.12g\n",max_residual);
    return 0;
}
