#!/usr/bin/env bash
set -eu

MPIEXEC=${MPIEXEC:-"mpirun -np 2"}
rm -f tests/spd_L.txt tests/rejected_L.txt

$MPIEXEC ./cholesky_app tests/spd_3x3.txt tests/spd_L.txt --validate
python3 - <<'PY'
from math import isclose

with open("tests/spd_L.txt", encoding="ascii") as source:
    tokens = source.read().split()
assert tokens[:2] == ["3", "3"]
actual = [float(value) for value in tokens[2:]]
expected = [2, 0, 0, 6, 1, 0, -8, 5, 3]
assert len(actual) == len(expected)
assert all(isclose(a, e, rel_tol=1e-13, abs_tol=1e-13) for a, e in zip(actual, expected))
PY

if $MPIEXEC ./cholesky_app tests/not_spd_2x2.txt tests/rejected_L.txt --validate; then
    echo "ERROR: se acepto una matriz que no es definida positiva" >&2
    exit 1
fi

test ! -e tests/rejected_L.txt
echo "Pruebas de aplicacion: OK"
