"""Etapa 1: referencia didáctica; no es una implementación HPC optimizada."""

import math


def cholesky(a):
    """Devuelve L sin modificar A. Requiere una matriz real simétrica SPD."""
    n = len(a)
    if n == 0 or any(len(row) != n for row in a):
        raise ValueError("La matriz debe ser cuadrada y no vacía")
    if any(not math.isfinite(x) for row in a for x in row):
        raise ValueError("La matriz debe contener valores finitos")
    # En esta referencia exigimos simetría exacta de los datos de entrada.
    if any(a[i][j] != a[j][i] for i in range(n) for j in range(i)):
        raise ValueError("La matriz debe ser simétrica")

    lower = [[0.0] * n for _ in range(n)]
    for j in range(n):
        pivot = a[j][j] - sum(lower[j][k] ** 2 for k in range(j))
        if not math.isfinite(pivot) or pivot <= 0:
            raise ValueError(f"Pivote no positivo o no finito en columna {j}")
        lower[j][j] = math.sqrt(pivot)
        for i in range(j + 1, n):
            previous = sum(lower[i][k] * lower[j][k] for k in range(j))
            lower[i][j] = (a[i][j] - previous) / lower[j][j]
            if not math.isfinite(lower[i][j]):
                raise ValueError("Resultado no finito")
    return lower


def generate_spd(n, seed=2026):
    """Simetría + dominancia diagonal estricta + diagonal positiva => SPD."""
    import random

    if n < 1:
        raise ValueError("N debe ser positivo")
    rng = random.Random(seed)
    a = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i):
            a[i][j] = a[j][i] = rng.uniform(-1.0, 1.0)
    for i in range(n):
        a[i][i] = 1.0 + sum(abs(x) for x in a[i])
    return a


def relative_residual(a, lower):
    """||A - LL^T||_F / ||A||_F; se ejecuta fuera del tiempo medido."""
    n = len(a)
    errors = []
    for i in range(n):
        for j in range(n):
            reconstructed = math.fsum(
                lower[i][k] * lower[j][k] for k in range(min(i, j) + 1)
            )
            errors.append(a[i][j] - reconstructed)
    norm_a = math.hypot(*(x for row in a for x in row))
    result = math.hypot(*errors) / norm_a
    if not math.isfinite(result):
        raise ValueError("Residuo no finito")
    return result
