#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

#define WARMUP 5
#define ITERS_ALPHA 50
#define ITERS_BETA 10
#define MSG_SIZE_BETA (1024 * 1024 * 4) // 4 MB
#define MICRO_GEMM_SIZE 256

// Función Hash para generación descentralizada de la matriz SPD
double generate_element(int i, int j, int N) {
    if (i == j) return (double)N + 1.0; 
    int min_idx = (i < j) ? i : j;
    int max_idx = (i > j) ? i : j;
    double val = (min_idx * 31.0 + max_idx * 17.0) / (N * 100.0);
    return val;
}

// -----------------------------------------------------------------------------
// KERNELS MATEMÁTICOS LOCALES (Simulando BLAS Nivel 3)
// -----------------------------------------------------------------------------
void local_potrf(double* A, int b, int lda) {
    for (int j = 0; j < b; j++) {
        double sum = 0.0;
        for (int k = 0; k < j; k++) sum += A[j*lda + k] * A[j*lda + k];
        A[j*lda + j] = sqrt(A[j*lda + j] - sum);
        for (int i = j + 1; i < b; i++) {
            sum = 0.0;
            for (int k = 0; k < j; k++) sum += A[i*lda + k] * A[j*lda + k];
            A[i*lda + j] = (A[i*lda + j] - sum) / A[j*lda + j];
        }
    }
}

void local_trsm(double* B, double* L, int m, int b, int ldb, int ldl) {
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < b; j++) {
            double sum = 0.0;
            for (int k = 0; k < j; k++) sum += B[i*ldb + k] * L[j*ldl + k];
            B[i*ldb + j] = (B[i*ldb + j] - sum) / L[j*ldl + j];
        }
    }
}

void local_gemm_syrk(double* C, double* A, double* B_mat, int m, int n, int k_dim, int ldc, int lda, int ldb) {
    for (int i = 0; i < m; i++) {
        for (int j = 0; j < n; j++) {
            double sum = 0.0;
            for (int p = 0; p < k_dim; p++) sum += A[i*lda + p] * B_mat[j*ldb + p];
            C[i*ldc + j] -= sum;
        }
    }
}

// -----------------------------------------------------------------------------
// VERIFICACIÓN DE CORRECTITUD
// -----------------------------------------------------------------------------
double check_correctness(double* L_global, int N) {
    double max_err = 0.0;
    for (int i = 0; i < N; i++) {
        for (int j = 0; j <= i; j++) {
            double sum = 0.0;
            for (int k = 0; k <= j; k++) {
                sum += L_global[i*N + k] * L_global[j*N + k];
            }
            double orig = generate_element(i, j, N);
            double err = fabs(sum - orig);
            if (err > max_err) max_err = err;
        }
    }
    return max_err;
}

// -----------------------------------------------------------------------------
// 1. ESTRATEGIA SECUENCIAL (Línea Base)
// -----------------------------------------------------------------------------
void cholesky_sequential(int N, double* time_comp) {
    double* A = (double*)malloc(N * N * sizeof(double));
    for (int i = 0; i < N; i++) {
        for (int j = 0; j <= i; j++) {
            A[i*N + j] = generate_element(i, j, N);
            A[j*N + i] = A[i*N + j];
        }
    }
    double t_start = MPI_Wtime();
    local_potrf(A, N, N);
    *time_comp = MPI_Wtime() - t_start;

    double err = check_correctness(A, N);
    printf(">> Secuencial Residuo max: %e\n", err);
    free(A);
}

// -----------------------------------------------------------------------------
// 2. ESTRATEGIA PRINCIPAL: 1D BLOCK-CYCLIC
// -----------------------------------------------------------------------------
void cholesky_1d_block_cyclic(int N, int rank, int size, int b, double* t_comp, double* t_comm) {
    int num_blocks = N / b;
    int local_cols = 0;
    for (int j = 0; j < num_blocks; j++) {
        if (j % size == rank) local_cols++;
    }
    
    // Asignación de memoria local
    double* A_local = (double*)malloc(N * local_cols * b * sizeof(double));
    int col_offset = 0;
    for (int j = 0; j < num_blocks; j++) {
        if (j % size == rank) {
            for (int r = 0; r < N; r++) {
                for (int c = 0; c < b; c++) {
                    A_local[r * (local_cols * b) + (col_offset * b + c)] = generate_element(r, j * b + c, N);
                }
            }
            col_offset++;
        }
    }
    
    double* panel_buffer = (double*)malloc(N * b * sizeof(double));
    *t_comp = 0; *t_comm = 0;

    // Bucle Right-Looking
    for (int k = 0; k < num_blocks; k++) {
        int owner = k % size;
        int active_rows = N - k * b;
        
        // Paso A y C: Factorización y actualización del panel (solo el dueño)
        if (rank == owner) {
            int local_k = k / size;
            double* diag_block = &A_local[(k * b) * (local_cols * b) + local_k * b];
            
            double tc = MPI_Wtime();
            local_potrf(diag_block, b, local_cols * b);
            if (active_rows > b) {
                double* sub_panel = &A_local[((k + 1) * b) * (local_cols * b) + local_k * b];
                local_trsm(sub_panel, diag_block, active_rows - b, b, local_cols * b, local_cols * b);
            }
            *t_comp += MPI_Wtime() - tc;
            
            // Empaquetar panel para enviar
            for (int r = 0; r < active_rows; r++) {
                for (int c = 0; c < b; c++) {
                    panel_buffer[r * b + c] = A_local[(k * b + r) * (local_cols * b) + local_k * b + c];
                }
            }
        }
        
        // Paso B: Comunicación global
        double tm = MPI_Wtime();
        MPI_Bcast(panel_buffer, active_rows * b, MPI_DOUBLE, owner, MPI_COMM_WORLD);
        *t_comm += MPI_Wtime() - tm;
        
        // Paso E: Actualización de la submatriz (Symmetric Rank-k)
        double tc = MPI_Wtime();
        for (int j = k + 1; j < num_blocks; j++) {
            if (j % size == rank) {
                int local_j = j / size;
                int rows_to_update = N - j * b;
                
                double* target = &A_local[(j * b) * (local_cols * b) + local_j * b];
                double* A_panel = &panel_buffer[(j * b - k * b) * b]; 
                double* B_panel = &panel_buffer[(j * b - k * b) * b]; 

                local_gemm_syrk(target, A_panel, B_panel, rows_to_update, b, b, local_cols * b, b, b);
            }
        }
        *t_comp += MPI_Wtime() - tc;
    }

    // Verificación final
    if (N <= 2048) {
        double* L_global = NULL;
        if (rank == 0) L_global = (double*)malloc(N * N * sizeof(double));
        
        for (int j = 0; j < num_blocks; j++) {
            int owner = j % size;
            int local_j = j / size;
            for (int r = 0; r < N; r++) {
                for (int c = 0; c < b; c++) {
                    double val = 0.0;
                    if (rank == owner) val = A_local[r * (local_cols * b) + local_j * b + c];
                    if (rank == owner && owner != 0) MPI_Send(&val, 1, MPI_DOUBLE, 0, 0, MPI_COMM_WORLD);
                    else if (rank == 0 && owner != 0) MPI_Recv(&val, 1, MPI_DOUBLE, owner, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                    if (rank == 0) L_global[r * N + j * b + c] = val;
                }
            }
        }
        if (rank == 0) {
            double err = check_correctness(L_global, N);
            printf(">> 1D Block-Cyclic Residuo max: %e\n", err);
            free(L_global);
        }
    }
    
    free(A_local);
    free(panel_buffer);
}

// -----------------------------------------------------------------------------
// PROGRAMA PRINCIPAL
// -----------------------------------------------------------------------------
int main(int argc, char** argv) {
    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    if (argc < 2) {
        if (rank == 0) printf("Uso: %s <N_Matriz>\n", argv[0]);
        MPI_Finalize();
        return 1;
    }

    int N = atoi(argv[1]);
    int b = 64; 
    
    if (N % b != 0) {
        if (rank == 0) printf("Error: N (%d) debe ser multiplo de b (%d).\n", N, b);
        MPI_Finalize();
        return 1;
    }
    
    // Auto-Tuner Físico
    double alpha = 5e-6; 
    double beta = 1e-9;
    double gflops = 1e9;
    
    if (size >= 2) {
        char* buf = (char*)malloc(MSG_SIZE_BETA);
        double t_s, t_e;
        
        // Latencia (alfa)
        MPI_Barrier(MPI_COMM_WORLD);
        t_s = MPI_Wtime();
        for (int i = 0; i < ITERS_ALPHA + WARMUP; i++) {
            if (i == WARMUP) t_s = MPI_Wtime();
            if (rank == 0) {
                MPI_Send(buf, 1, MPI_BYTE, 1, 0, MPI_COMM_WORLD);
                MPI_Recv(buf, 1, MPI_BYTE, 1, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            } else if (rank == 1) {
                MPI_Recv(buf, 1, MPI_BYTE, 0, 0, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                MPI_Send(buf, 1, MPI_BYTE, 0, 0, MPI_COMM_WORLD);
            }
        }
        t_e = MPI_Wtime();
        if (rank == 0) alpha = (t_e - t_s) / (2.0 * ITERS_ALPHA);
        
        // Ancho de banda (beta)
        MPI_Barrier(MPI_COMM_WORLD);
        t_s = MPI_Wtime();
        for (int i = 0; i < ITERS_BETA + WARMUP; i++) {
            if (i == WARMUP) t_s = MPI_Wtime();
            if (rank == 0) {
                MPI_Send(buf, MSG_SIZE_BETA, MPI_BYTE, 1, 1, MPI_COMM_WORLD);
                MPI_Recv(buf, MSG_SIZE_BETA, MPI_BYTE, 1, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
            } else if (rank == 1) {
                MPI_Recv(buf, MSG_SIZE_BETA, MPI_BYTE, 0, 1, MPI_COMM_WORLD, MPI_STATUS_IGNORE);
                MPI_Send(buf, MSG_SIZE_BETA, MPI_BYTE, 0, 1, MPI_COMM_WORLD);
            }
        }
        t_e = MPI_Wtime();
        if (rank == 0) {
            double t_msg = (t_e - t_s) / (2.0 * ITERS_BETA);
            beta = (t_msg - alpha) / MSG_SIZE_BETA;
        }
        MPI_Bcast(&alpha, 1, MPI_DOUBLE, 0, MPI_COMM_WORLD);
        MPI_Bcast(&beta, 1, MPI_DOUBLE, 0, MPI_COMM_WORLD);
        free(buf);
    }
    
    // Micro-GEMM para GFLOPS
    double* mA = (double*)malloc(MICRO_GEMM_SIZE * MICRO_GEMM_SIZE * sizeof(double));
    double* mB = (double*)malloc(MICRO_GEMM_SIZE * MICRO_GEMM_SIZE * sizeof(double));
    double* mC = (double*)malloc(MICRO_GEMM_SIZE * MICRO_GEMM_SIZE * sizeof(double));
    for(int i=0; i<MICRO_GEMM_SIZE*MICRO_GEMM_SIZE; i++) { mA[i]=1; mB[i]=2; mC[i]=0; }
    double tg_start = MPI_Wtime();
    local_gemm_syrk(mC, mA, mB, MICRO_GEMM_SIZE, MICRO_GEMM_SIZE, MICRO_GEMM_SIZE, MICRO_GEMM_SIZE, MICRO_GEMM_SIZE, MICRO_GEMM_SIZE);
    double tg_end = MPI_Wtime();
    gflops = (2.0 * pow(MICRO_GEMM_SIZE, 3.0)) / (tg_end - tg_start) / 1e9;
    free(mA); free(mB); free(mC);
    
    int strategy = 2; // Por defecto 1D Block-Cyclic
    
    if (rank == 0) {
        double flops = pow((double)N, 3.0) / 3.0;
        double t_seq = flops / (gflops * 1e9);
        double num_msgs = (double)N / b;
        double vol_1d = (pow((double)N, 2.0) / 2.0) * 8.0;
        double t_comm_1d = (num_msgs * alpha + vol_1d * beta) * log2((double)size);
        double t_1d = (t_seq / size) + t_comm_1d;
        
        double Pr = sqrt((double)size); 
        double vol_2d = (pow((double)N, 2.0) / (2.0 * Pr)) * 8.0;
        double t_comm_2d = (num_msgs * alpha + vol_2d * beta) * log2(Pr);
        double t_2d = (t_seq / size) + t_comm_2d;

        if (t_seq <= t_1d && t_seq <= t_2d) {
            strategy = 1; // Secuencial gana
            printf("[Auto-Tuner] Problema demasiado pequeño. Se usará Ejecución Secuencial.\n");
        } else if (t_2d < t_1d && size >= 32) {
            printf("[Auto-Tuner] ALERTA: El modelo analítico sugiere que 2D-Block-Cyclic sería óptimo para este volumen de red.\n");
            printf("[Auto-Tuner] Sin embargo, cayendo en fallback a 1D-Block-Cyclic (Límite del alcance del proyecto actual).\n");
            strategy = 2;
        } else {
            strategy = 2; // 1D gana o es suficientemente competitivo
        }
    }
    
    MPI_Bcast(&strategy, 1, MPI_INT, 0, MPI_COMM_WORLD);
    
    double t_comp = 0, t_comm = 0;
    MPI_Barrier(MPI_COMM_WORLD);
    double t_total_start = MPI_Wtime();
    
    if (strategy == 1) {
        if (rank == 0) cholesky_sequential(N, &t_comp);
    } else {
        cholesky_1d_block_cyclic(N, rank, size, b, &t_comp, &t_comm);
    }
    
    MPI_Barrier(MPI_COMM_WORLD);
    double t_total = MPI_Wtime() - t_total_start;
    
    if (rank == 0) {
        // Output parseable: RESULT, N, P, Estrategia, T_total, T_comp, T_comm
        printf("RESULT,%d,%d,%d,%.6f,%.6f,%.6f\n", N, size, strategy, t_total, t_comp, t_comm);
    }

    MPI_Finalize();
    return 0;
}
