#include "cholesky_mpi.h"
#include <math.h>
#include <stddef.h>

Layout layout_create(int n, int cyclic, MPI_Comm comm) {
    Layout d = {.n=n, .cyclic=cyclic, .comm=comm};
    MPI_Comm_rank(comm, &d.rank); MPI_Comm_size(comm, &d.p);
    int q=n/d.p, r=n%d.p;
    d.cols=q+(d.rank<r);
    d.first=cyclic ? d.rank : d.rank*q+(d.rank<r ? d.rank : r);
    return d;
}
int layout_owner(const Layout *d, int k) {
    if (d->cyclic) return k%d->p;
    int q=d->n/d->p, r=d->n%d->p, boundary=(q+1)*r;
    return k<boundary ? k/(q+1) : r+(k-boundary)/q;
}
int layout_global(const Layout *d, int t) {
    return d->first+t*(d->cyclic ? d->p : 1);
}
int layout_before(const Layout *d, int k) {
    int count;
    if (k<=d->first) return 0;
    count=d->cyclic ? (k-1-d->first)/d->p+1 : k-d->first;
    return count<d->cols ? count : d->cols;
}
int cholesky_mpi(double *a, double *column, const Layout *d, Profile *prof) {
    int n=d->n, m=d->cols;
    if (prof) *prof=(Profile){0};
    for (int j=0;j<n;++j) {
        double t=prof ? MPI_Wtime() : 0;
        int owner=layout_owner(d,j);
        if (d->rank==owner) {
            int c=layout_before(d,j);
            double pivot=a[(size_t)j*m+c];
            column[j]=NAN; /* Un mismo mensaje transporta pivote/estado. */
            if (isfinite(pivot) && pivot>0) {
                column[j]=a[(size_t)j*m+c]=sqrt(pivot);
                for (int i=j+1;i<n;++i)
                    column[i]=a[(size_t)i*m+c]/=column[j];
            } else {
                for (int i=j+1;i<n;++i) column[i]=0;
            }
        }
        if (prof) { prof->compute+=MPI_Wtime()-t; t=MPI_Wtime(); }
        MPI_Bcast(column+j,n-j,MPI_DOUBLE,owner,d->comm);
        if (prof) { prof->broadcast+=MPI_Wtime()-t; t=MPI_Wtime(); }
        if (!isfinite(column[j]) || column[j]<=0) return -1;
        int begin=layout_before(d,j+1);
        for (int i=j+1;i<n;++i) {
            double lij=column[i];
            int end=layout_before(d,i+1);
            for (int c=begin;c<end;++c)
                a[(size_t)i*m+c]-=lij*column[layout_global(d,c)];
        }
        if (prof) prof->compute+=MPI_Wtime()-t;
    }
    if (prof) for (int c=0;c<m;++c) {
        uint64_t k=(uint64_t)layout_global(d,c);
        prof->updates+=k*(n-k);
    }
    return 0;
}

/* Variante experimental: mismo algoritmo, lectura interna contigua. */
int cholesky_mpi_local(double *a, double *column, double *local_column, const Layout *d, Profile *prof) {
    int n=d->n, m=d->cols;
    if (prof) *prof=(Profile){0};
    for (int j=0;j<n;++j) {
        double t=prof ? MPI_Wtime() : 0;
        int owner=layout_owner(d,j);
        if (d->rank==owner) {
            int c=layout_before(d,j);
            double pivot=a[(size_t)j*m+c];
            column[j]=NAN; /* Un mismo mensaje transporta pivote/estado. */
            if (isfinite(pivot) && pivot>0) {
                column[j]=a[(size_t)j*m+c]=sqrt(pivot);
                for (int i=j+1;i<n;++i)
                    column[i]=a[(size_t)i*m+c]/=column[j];
            } else {
                for (int i=j+1;i<n;++i) column[i]=0;
            }
        }
        if (prof) { prof->compute+=MPI_Wtime()-t; t=MPI_Wtime(); }
        MPI_Bcast(column+j,n-j,MPI_DOUBLE,owner,d->comm);
        if (prof) { prof->broadcast+=MPI_Wtime()-t; t=MPI_Wtime(); }
        if (!isfinite(column[j]) || column[j]<=0) return -1;
        int begin=layout_before(d,j+1);
        /* Copia incluida en el kernel: solo valores de columnas futuras
         * propias. Cada uno se reutiliza en varias filas inferiores. */
        for (int c=begin;c<m;++c)
            local_column[c]=column[layout_global(d,c)];
        for (int i=j+1;i<n;++i) {
            double lij=column[i];
            int end=layout_before(d,i+1);
            for (int c=begin;c<end;++c)
                a[(size_t)i*m+c]-=lij*local_column[c];
        }
        if (prof) prof->compute+=MPI_Wtime()-t;
    }
    if (prof) for (int c=0;c<m;++c) {
        uint64_t k=(uint64_t)layout_global(d,c);
        prof->updates+=k*(n-k);
    }
    return 0;
}
