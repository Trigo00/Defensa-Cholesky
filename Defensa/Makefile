CC = gcc
MPICC = mpicc
CFLAGS = -O3 -std=c11 -Wall -Wextra -Wpedantic

.PHONY: all
all: build/cholesky_seq build/cholesky_mpi

build:
	mkdir -p build

build/cholesky_seq: codigo/main_candidate.c codigo/cholesky.c codigo/cholesky.h | build
	$(CC) $(CFLAGS) codigo/main_candidate.c codigo/cholesky.c -o $@ -lm

build/cholesky_mpi: codigo/main_candidate.c codigo/cholesky.c codigo/cholesky_mpi.c codigo/cholesky.h codigo/cholesky_mpi.h | build
	$(MPICC) $(CFLAGS) -DUSE_MPI codigo/main_candidate.c codigo/cholesky.c codigo/cholesky_mpi.c -o $@ -lm
