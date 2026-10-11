#include "cholesky.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(condition) do { if (!(condition)) { \
    fprintf(stderr, "FAIL linea %d: %s\n", __LINE__, #condition); return 1; } } while (0)

int main(void) {
    const double known[] = {4,12,-16,12,37,-43,-16,-43,98};
    const double expected[] = {2,0,0,6,1,0,-8,5,3};
    double factor[9];
    memcpy(factor, known, sizeof known);
    CHECK(cholesky_right(factor, 3) == 0);
    for (size_t i=0; i<3; ++i)
        for (size_t j=0; j<=i; ++j) CHECK(factor[i*3+j] == expected[i*3+j]);
    CHECK(relative_residual(known, factor, 3) == 0.0);
    puts("PASS factor conocido 3x3");

    double scalar[] = {9}, identity[] = {1,0,0,0,1,0,0,0,1};
    CHECK(cholesky_right(scalar,1) == 0 && scalar[0] == 3);
    CHECK(cholesky_right(identity,3) == 0);
    CHECK(identity[0] == 1 && identity[4] == 1 && identity[8] == 1);
    puts("PASS escalar e identidad");

    const size_t sizes[] = {2,7,16,31};
    const uint64_t seeds[] = {0,42,2026};
    double max_residual = 0;
    for (size_t s=0; s<4; ++s) {
        size_t n=sizes[s], bytes=n*n*sizeof(double);
        double *a=malloc(bytes), *b=malloc(bytes);
        CHECK(a && b);
        for (size_t t=0; t<3; ++t) {
            generate_spd(a,n,seeds[t]); generate_spd(b,n,seeds[t]);
            CHECK(memcmp(a,b,bytes) == 0 && symmetric_finite(a,n));
            for (size_t i=0; i<n; ++i) {
                double sum=0;
                for (size_t j=0; j<n; ++j) if(i!=j) sum+=fabs(a[i*n+j]);
                CHECK(a[i*n+i] > sum);
            }
            CHECK(cholesky_right(b,n) == 0);
            double residual=relative_residual(a,b,n);
            CHECK(isfinite(residual) && residual < 1e-12);
            if (residual > max_residual) max_residual=residual;
        }
        free(a); free(b);
    }
    printf("PASS 12 matrices generadas; residuo maximo %.12g\n",max_residual);

    double indefinite[]={1,2,2,1}, semidefinite[]={1,1,1,1};
    double asymmetric[]={1,2,0,1}, nan_matrix[]={NAN}, inf_matrix[]={INFINITY};
    double negative[]={-1};
    CHECK(!symmetric_finite(asymmetric,2));
    CHECK(!symmetric_finite(nan_matrix,1) && !symmetric_finite(inf_matrix,1));
    CHECK(cholesky_right(indefinite,2) != 0 && cholesky_right(semidefinite,2) != 0);
    CHECK(cholesky_right(negative,1) != 0 && cholesky_right(nan_matrix,1) != 0);
    CHECK(cholesky_right(inf_matrix,1) != 0 && cholesky_right(NULL,0) != 0);
    puts("PASS rechazo de entradas y pivotes invalidos");

    double original[]={4}, wrong[]={1};
    CHECK(relative_residual(original,wrong,1) > 0.1);
    CHECK(!isfinite(relative_residual(original,nan_matrix,1)));
    puts("PASS el residuo detecta factores incorrectos y no finitos");
    return 0;
}
