CC = gcc
CFLAGS = -O3 -std=c11 -Wall -Wextra -Wpedantic
LDLIBS = -lm
MPICC = mpicc

.PHONY: candidate
candidate: build/cholesky_candidate_mpi build/cholesky_candidate_seq build/measure_command
FINAL = src/implementacion_final
EXPERIMENTS = src/experimentos
INCLUDES = -I$(FINAL) -I$(EXPERIMENTS)

build/cholesky_candidate_mpi: $(FINAL)/main_candidate.c $(FINAL)/cholesky.c $(FINAL)/cholesky_mpi.c $(FINAL)/cholesky.h $(FINAL)/cholesky_mpi.h | build
	$(MPICC) $(CFLAGS) -DUSE_MPI $(INCLUDES) $(FINAL)/main_candidate.c $(FINAL)/cholesky.c $(FINAL)/cholesky_mpi.c -o $@ $(LDLIBS)
build/cholesky_candidate_seq: $(FINAL)/main_candidate.c $(FINAL)/cholesky.c $(FINAL)/cholesky.h | build
	$(CC) $(CFLAGS) $(INCLUDES) $(FINAL)/main_candidate.c $(FINAL)/cholesky.c -o $@ $(LDLIBS)
build/measure_command: $(EXPERIMENTS)/measure_command.c | build
	$(CC) $(CFLAGS) $< -o $@

.PHONY: lapack test-lapack
lapack: build/compare_lapack
build/compare_lapack: src/experimentos/compare_lapack.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos src/experimentos/compare_lapack.c src/implementacion_final/cholesky.c -llapacke -lopenblas src/experimentos/bench_utils.c -o $@ $(LDLIBS)
test-lapack: lapack
	OPENBLAS_NUM_THREADS=1 ./build/compare_lapack --test

.PHONY: blocks test-blocks
blocks: build/compare_blocks
build/compare_blocks: src/experimentos/compare_blocks.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky.h src/implementacion_final/cholesky_mpi.h Makefile | build
	$(MPICC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos src/experimentos/compare_blocks.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky_mpi.c src/experimentos/bench_utils.c -o $@ $(LDLIBS)
test-blocks: blocks
	@for p in 1 3 6; do timeout 90 mpirun --bind-to core --map-by core -np $$p ./build/compare_blocks --test || exit 1; done

.PHONY: application test-application
application: build/compare_application
build/compare_application: src/experimentos/compare_application.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky.h src/implementacion_final/cholesky_mpi.h Makefile | build
	$(MPICC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos src/experimentos/compare_application.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky_mpi.c src/experimentos/bench_utils.c -o $@ $(LDLIBS)
test-application: application
	@for p in 1 3 6; do timeout 90 mpirun --bind-to core --map-by core -np $$p ./build/compare_application --test > build/application_test_p$$p.csv || exit 1; done

.PHONY: generation
generation: build/compare_generation
build/compare_generation: src/experimentos/compare_generation.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky.h src/implementacion_final/cholesky_mpi.h Makefile | build
	$(MPICC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos src/experimentos/compare_generation.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky_mpi.c -o $@ $(LDLIBS)

.PHONY: mpi-local test-mpi-local
mpi-local: build/compare_mpi_local

build/compare_mpi_local: src/experimentos/compare_mpi_local.c src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h Makefile | build
	$(MPICC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos src/experimentos/compare_mpi_local.c src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky.c src/experimentos/bench_utils.c -o $@ $(LDLIBS)

test-mpi-local: mpi-local
	@for p in 1 2 3 4; do timeout 60 mpirun --bind-to core --map-by core -np $$p ./build/compare_mpi_local --test || exit 1; done

.PHONY: mpi-algorithms test-mpi-algorithms
mpi-algorithms: build/compare_mpi_algorithms

build/compare_mpi_algorithms: src/experimentos/compare_mpi_algorithms.c src/experimentos/cholesky_left_mpi.c src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h Makefile | build
	$(MPICC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos src/experimentos/compare_mpi_algorithms.c src/experimentos/cholesky_left_mpi.c src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky.c src/experimentos/bench_utils.c -o $@ $(LDLIBS)

test-mpi-algorithms: mpi-algorithms
	@for p in 1 2 3 4; do timeout 60 mpirun --bind-to core --map-by core -np $$p ./build/compare_mpi_algorithms --test || exit 1; done

.PHONY: mpi-total test-mpi-total
mpi-total: build/compare_mpi_total

build/compare_mpi_total: src/experimentos/compare_mpi_total.c src/experimentos/cholesky_left_mpi.c src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h Makefile | build
	$(MPICC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos src/experimentos/compare_mpi_total.c src/experimentos/cholesky_left_mpi.c src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky.c src/experimentos/bench_utils.c -o $@ $(LDLIBS)

test-mpi-total: mpi-total
	@for p in 1 2 3 4; do timeout 60 mpirun --bind-to core --map-by core -np $$p ./build/compare_mpi_total --test || exit 1; done

.PHONY: mpi test-mpi
mpi: build/compare_mpi

build/compare_mpi: src/experimentos/compare_mpi.c src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky_mpi.h src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h Makefile | build
	$(MPICC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos src/experimentos/compare_mpi.c src/implementacion_final/cholesky_mpi.c src/implementacion_final/cholesky.c src/experimentos/bench_utils.c -o $@ $(LDLIBS)

test-mpi: mpi
	@for p in 1 2 3 4; do timeout 60 mpirun --bind-to core --map-by core -np $$p ./build/compare_mpi --test || exit 1; done

.PHONY: all test sanitize
all: build/cholesky_seq build/compare_seq build/compare_memory

build:
	mkdir -p build

build/cholesky_seq: src/experimentos/main.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos src/experimentos/main.c src/implementacion_final/cholesky.c src/experimentos/bench_utils.c -o $@ $(LDLIBS)

build/test_cholesky: tests/test_cholesky.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos tests/test_cholesky.c src/implementacion_final/cholesky.c -o $@ $(LDLIBS)

build/compare_seq: src/experimentos/compare_seq.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos src/experimentos/compare_seq.c src/implementacion_final/cholesky.c src/experimentos/bench_utils.c -o $@ $(LDLIBS)

build/test_variants: tests/test_variants.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos tests/test_variants.c src/implementacion_final/cholesky.c -o $@ $(LDLIBS)

build/compare_memory: src/experimentos/compare_memory.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos src/experimentos/compare_memory.c src/implementacion_final/cholesky.c src/experimentos/bench_utils.c -o $@ $(LDLIBS)

build/test_buffered: tests/test_buffered.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos tests/test_buffered.c src/implementacion_final/cholesky.c -o $@ $(LDLIBS)

build/test_projected: tests/test_projected.c src/implementacion_final/cholesky.c src/implementacion_final/cholesky.h Makefile | build
	$(CC) $(CFLAGS) -Isrc/implementacion_final -Isrc/experimentos tests/test_projected.c src/implementacion_final/cholesky.c -o $@ $(LDLIBS)

test: build/test_cholesky build/test_variants build/test_buffered build/test_projected
	./build/test_cholesky
	./build/test_variants
	./build/test_buffered
	./build/test_projected

sanitize: | build
	$(CC) -O1 -g -std=c11 -Wall -Wextra -Wpedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc/implementacion_final -Isrc/experimentos tests/test_cholesky.c src/implementacion_final/cholesky.c -o build/test_sanitize $(LDLIBS)
	./build/test_sanitize
	$(CC) -O1 -g -std=c11 -Wall -Wextra -Wpedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc/implementacion_final -Isrc/experimentos tests/test_variants.c src/implementacion_final/cholesky.c -o build/test_variants_sanitize $(LDLIBS)
	./build/test_variants_sanitize
	$(CC) -O1 -g -std=c11 -Wall -Wextra -Wpedantic -fsanitize=address,undefined -fno-omit-frame-pointer -Isrc/implementacion_final -Isrc/experimentos tests/test_buffered.c src/implementacion_final/cholesky.c -o build/test_buffered_sanitize $(LDLIBS)
	./build/test_buffered_sanitize

# Shared benchmark utilities: edits must invalidate the affected executables.
build/cholesky_seq build/compare_seq build/compare_memory build/compare_mpi build/compare_mpi_local build/compare_mpi_algorithms build/compare_mpi_total build/compare_application build/compare_blocks build/compare_lapack: src/experimentos/bench_utils.h src/experimentos/bench_utils.c

