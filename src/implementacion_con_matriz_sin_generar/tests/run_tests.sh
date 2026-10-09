#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
tmp=$(mktemp -d)
trap 'rm -f -- "$tmp/input.txt" "$tmp/result.txt" "$tmp/expected.txt" "$tmp/error.log"; rmdir -- "$tmp"' EXIT
printf '3 3\n4 12 -16\n12 37 -43\n-16 -43 98\n' > "$tmp/input.txt"
printf '3 3\n2 0 0\n6 1 0\n-8 5 3\n' > "$tmp/expected.txt"
sh ejecutar_demo.sh "$tmp/input.txt" "$tmp/result.txt"
diff -w "$tmp/expected.txt" "$tmp/result.txt"
echo 'PASS: factor conocido y validacion completa'
printf '2 2\n1 2\n2 1\n' > "$tmp/input.txt"
set +e
sh ejecutar_demo.sh "$tmp/input.txt" "$tmp/result.txt" > "$tmp/error.log" 2>&1
status=$?
set -e
if [ "$status" -ne 7 ]; then
    cat "$tmp/error.log"
    echo "FAIL: se esperaba rechazo numerico 7; recibido $status" >&2
    exit 1
fi
test ! -e "$tmp/result.txt"
echo 'PASS: matriz indefinida rechazada y resultado anterior eliminado'
printf 'resultado anterior\n' > "$tmp/result.txt"
rm -- "$tmp/input.txt"
if sh ejecutar_demo.sh "$tmp/input.txt" "$tmp/result.txt" > "$tmp/error.log" 2>&1; then
    echo 'FAIL: se acepto entrada ausente' >&2
    exit 1
fi
test ! -e "$tmp/result.txt"
echo 'PASS: entrada ausente no deja un resultado anterior'
