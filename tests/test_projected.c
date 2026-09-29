#include "cholesky.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr,"FAIL line %d\n",__LINE__); return 1; } } while(0)
int main(void) {
    const size_t sizes[]={1,3,7,31,128};
    for (size_t s=0;s<sizeof sizes/sizeof sizes[0];++s) {
        size_t n=sizes[s];
        double *a=malloc(n*n*sizeof *a), *l=malloc(n*n*sizeof *l), *col=malloc(n*sizeof *col);
        long double *work=malloc(2*n*sizeof *work);
        CHECK(a && l && col && work);
        generate_spd(a,n,2026); memcpy(l,a,n*n*sizeof *a);
        for (int p=1;p<=8;++p) for (int rank=0;rank<p;++rank) {
            size_t m=n/p+((size_t)rank<n%(size_t)p);
            generate_spd_columns(l,n,2026,rank,p);
            for(size_t i=0;i<n;++i) for(size_t c=0;c<m;++c)
                CHECK(l[i*m+c]==a[i*n+rank+c*p]);
        }
        memcpy(l,a,n*n*sizeof *a);
        CHECK(cholesky_right_buffered(l,n,col)==0);
        double r=projected_residual(a,l,n,8,91827,work);
        CHECK(isfinite(r) && r<1e-12 && relative_residual(a,l,n)<1e-12);
        CHECK(r==projected_residual(a,l,n,8,91827,work));
        if(n>1) { l[1]=NAN; CHECK(projected_residual(a,l,n,8,91827,work)==r); }
        l[(n-1)*n]+=1;
        CHECK(projected_residual(a,l,n,8,91827,work)>1e-6);
        l[0]=NAN; CHECK(isinf(projected_residual(a,l,n,8,91827,work)));
        free(a);free(l);free(col);free(work);
    }
    CHECK(isinf(projected_residual(NULL,NULL,0,0,0,NULL)));
    puts("PASS projected: correct factors, reproducibility, ignored upper triangle, corruption and NaN");
    return 0;
}
