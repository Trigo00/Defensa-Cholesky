MPICC ?= mpicc
CFLAGS ?= -O3 -std=c11 -Wall -Wextra -Wpedantic
HISTORICAL := ../implementacion_final
TARGET := cholesky_app

.PHONY: all clean test
all: $(TARGET)

$(TARGET): cholesky_app.c matrix_io.c matrix_io.h $(HISTORICAL)/cholesky.c \
           $(HISTORICAL)/cholesky.h $(HISTORICAL)/cholesky_mpi.c $(HISTORICAL)/cholesky_mpi.h
	$(MPICC) $(CFLAGS) -I$(HISTORICAL) cholesky_app.c matrix_io.c \
		$(HISTORICAL)/cholesky.c $(HISTORICAL)/cholesky_mpi.c -o $@ -lm

test: $(TARGET)
	bash tests/run_tests.sh

clean:
	rm -f $(TARGET) tests/spd_L.txt tests/rejected_L.txt
