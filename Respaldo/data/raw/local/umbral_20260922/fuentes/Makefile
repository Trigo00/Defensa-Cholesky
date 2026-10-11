CC = gcc
CFLAGS = -O3 -std=c11 -Wall -Wextra -Wpedantic
LDLIBS = -lm
MPICC = mpicc

.PHONY: mpi-local test-mpi-local
mpi-local: build/compare_mpi_local

build/compare_mpi_local: src/compare_mpi_local.c src/cholesky_mpi.c src/cholesky_mpi.h src/cholesky.c src/cholesky.h Makefile | build
	$(MPICC) $(CFLAGS) -Isrc src/compare_mpi_local.c src/cholesky_mpi.c src/cholesky.c -o $@ $(LDLIBS)

test-mpi-local: mpi-local
	@for p in 1 2 3 4; do timeout 60 mpirun --bind-to core --map-by core -np $$p ./build/compare_mpi_local --test || exit 1; done

.PHONY: mpi test-mpi
mpi: build/compare_mpi

build/compare_mpi: src/compare_mpi.c src/cholesky_mpi.c src/cholesky_mpi.h src/cholesky.c src/cholesky.h Makefile | build
	$(MPICC) $(CFLAGS) -Isrc src/compare_mpi.c src/cholesky_mpi.c src/cholesky.c -o $@ $(LDLIBS)

test-mpi: mpi
	@for p in 1 2 3 4; do timeout 60 mpirun --bind-to core --map-by core -np $$p ./build/compare_mpi --test || exit 1; done

.PHONY: all test sanitize
all: build/cholesky_seq build/compare_seq build/compare_memory

build:
	mkdir -p build

build/cholesky_seq: src/main.c src/cholesky.c src/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc src/main.c src/cholesky.c -o $@ $(LDLIBS)

build/test_cholesky: tests/test_cholesky.c src/cholesky.c src/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc tests/test_cholesky.c src/cholesky.c -o $@ $(LDLIBS)

build/compare_seq: src/compare_seq.c src/cholesky.c src/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc src/compare_seq.c src/cholesky.c -o $@ $(LDLIBS)

build/test_variants: tests/test_variants.c src/cholesky.c src/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc tests/test_variants.c src/cholesky.c -o $@ $(LDLIBS)

build/compare_memory: src/compare_memory.c src/cholesky.c src/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc src/compare_memory.c src/cholesky.c -o $@ $(LDLIBS)

build/test_buffered: tests/test_buffered.c src/cholesky.c src/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc tests/test_buffered.c src/cholesky.c -o $@ $(LDLIBS)

test: build/test_cholesky build/test_variants build/test_buffered
	./build/test_cholesky
	./build/test_variants
	./build/test_buffered

sanitize: | build
	$(CC) -O1 -g -std=c11 -Wall -Wextra -Wpedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc tests/test_cholesky.c src/cholesky.c -o build/test_sanitize $(LDLIBS)
	./build/test_sanitize
	$(CC) -O1 -g -std=c11 -Wall -Wextra -Wpedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc tests/test_variants.c src/cholesky.c -o build/test_variants_sanitize $(LDLIBS)
	./build/test_variants_sanitize
	$(CC) -O1 -g -std=c11 -Wall -Wextra -Wpedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc tests/test_buffered.c src/cholesky.c -o build/test_buffered_sanitize $(LDLIBS)
	./build/test_buffered_sanitize
