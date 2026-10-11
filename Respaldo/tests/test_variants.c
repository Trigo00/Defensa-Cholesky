#include "cholesky.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(c) do { if(!(c)) { fprintf(stderr,"FAIL %d: %s\n",__LINE__,#c); return 1; } } while(0)

int main(void) {
    int (*functions[2])(double*,size_t)={cholesky_left,cholesky_right};
    const double known[]={4,12,-16,12,37,-43,-16,-43,98};
    const double expected[]={2,0,0,6,1,0,-8,5,3};
    for(int v=0;v<2;++v) {
        double f[9]; memcpy(f,known,sizeof f);
        CHECK(functions[v](f,3)==0);
        for(size_t i=0;i<3;++i) for(size_t j=0;j<=i;++j) CHECK(f[i*3+j]==expected[i*3+j]);
        CHECK(relative_residual(known,f,3)==0);
        double bad[]={1,2,2,1}, semi[]={1,1,1,1}, nan[]={NAN}, inf[]={INFINITY}, scalar[]={9};
        CHECK(functions[v](bad,2)!=0 && functions[v](semi,2)!=0);
        CHECK(functions[v](nan,1)!=0 && functions[v](inf,1)!=0);
        CHECK(functions[v](NULL,0)!=0);
        CHECK(functions[v](scalar,1)==0 && scalar[0]==3);
    }
    size_t sizes[]={2,7,16,31};
    uint64_t seeds[]={0,42,2026};
    double max_residual=0;
    for(size_t s=0;s<4;++s) {
        size_t n=sizes[s],bytes=n*n*sizeof(double);
        double *a=malloc(bytes),*left=malloc(bytes),*right=malloc(bytes);
        CHECK(a && left && right);
        for(size_t seed=0;seed<3;++seed) {
            generate_spd(a,n,seeds[seed]);
            memcpy(left,a,bytes); memcpy(right,a,bytes);
            CHECK(cholesky_left(left,n)==0 && cholesky_right(right,n)==0);
            double rl=relative_residual(a,left,n),rr=relative_residual(a,right,n);
            CHECK(isfinite(rl) && rl<1e-12 && isfinite(rr) && rr<1e-12);
            max_residual=fmax(max_residual,fmax(rl,rr));
            for(size_t i=0;i<n;++i) for(size_t j=0;j<=i;++j)
                CHECK(fabs(left[i*n+j]-right[i*n+j])<1e-12*fmax(1.0,fabs(left[i*n+j])));
        }
        free(a);free(left);free(right);
    }
    printf("PASS left y right: factor conocido, pivotes invalidos y 12 matrices; r_max=%.12g\n",max_residual);
    return 0;
}
