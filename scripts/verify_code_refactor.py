"""Regresion funcional contra los fuentes medidos; ejecutar en Linux/WSL con MPI y LAPACK.

Compara columnas CSV, valores no temporales y codigos de salida. Los tiempos
se comprueban finitos/no negativos, pero no se exige igualdad ni se mide speedup.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TARGETS = ['all', 'candidate', 'lapack', 'blocks', 'application', 'generation',
           'mpi-local', 'mpi-algorithms', 'mpi-total', 'mpi', 'test']
TIME_FIELDS = {'seconds', 'total', 'compute', 'reduce', 'broadcast'}
ENV = dict(os.environ, OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')
CHECKS = []


def execute(command, cwd=ROOT):
    result = subprocess.run([str(x) for x in command], cwd=cwd, env=ENV,
                            capture_output=True, text=True, timeout=120)
    return result


def build(directory):
    result = execute(['make', '-j4', *TARGETS], directory)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout + result.stderr


def compare(name, args, before, processes=None, expected=0):
    launcher = ['mpirun', '--oversubscribe', '--bind-to', 'none', '-np', str(processes)] if processes else []
    old = execute([*launcher, before/name, *args])
    new = execute([*launcher, ROOT/'build'/name, *args])
    assert old.returncode == new.returncode == expected, (name, args, processes, old.returncode, new.returncode, new.stderr)
    if old.stdout.startswith('N,'):
        a, b = csv.DictReader(io.StringIO(old.stdout)), csv.DictReader(io.StringIO(new.stdout))
        assert a.fieldnames == b.fieldnames, (name, 'CSV headers')
        aa, bb = list(a), list(b)
        assert len(aa) == len(bb), (name, 'CSV row count')
        for x, y in zip(aa, bb):
            for key in a.fieldnames:
                if key.endswith('_s') or key in TIME_FIELDS:
                    assert all(math.isfinite(float(v)) and float(v) >= 0 for v in (x[key], y[key])), (name, key)
                else:
                    assert x[key] == y[key], (name, key, x[key], y[key])
    else:
        assert old.stdout == new.stdout, (name, old.stdout, new.stdout)
    CHECKS.append(dict(program=name, args=args, processes=processes, exit_code=expected))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-build', type=Path, help='Reutilizar un directorio build anterior ya compilado')
    options = parser.parse_args()
    archive = ROOT/'archive/src_medidos_20260928'
    hashes = json.loads((archive/'sha256.json').read_text())
    for name, expected in hashes.items():
        assert hashlib.sha256((archive/name).read_bytes()).hexdigest() == expected
    with tempfile.TemporaryDirectory(prefix='cholesky-baseline-') as temp:
        work = Path(temp)
        if options.baseline_build:
            before = options.baseline_build.resolve()
        else:
            (work/'src').mkdir()
            for path in archive.glob('*'):
                if path.suffix in ('.c', '.h'):
                    shutil.copy2(path, work/'src'/path.name)
            shutil.copy2(archive/'Makefile', work/'Makefile')
            shutil.copytree(ROOT/'tests', work/'tests')
            # The archived Makefile names only the original four sequential tests.
            build(work)
            before = work/'build'
        log = build(ROOT)
        (ROOT/'docs/checks/refactor_build.log').write_text(log)
        print('Compilacion y cuatro pruebas secuenciales: PASS', flush=True)
        for program, args in [('cholesky_seq', ['7','2','17']), ('compare_seq',['7','2','17']),
                              ('compare_memory',['7','6','17']), ('compare_lapack',['7','2']),
                              ('compare_lapack',['--test'])]:
            compare(program,args,before)
        mpi_tests = ['compare_mpi','compare_mpi_local','compare_mpi_algorithms',
                     'compare_mpi_total','compare_application','compare_blocks']
        for processes in (1,2,3,4,6):
            for program in mpi_tests:
                compare(program,['--test'],before,processes)
            for n in (1,7,128):
                compare('cholesky_candidate_mpi',[str(n)],before,processes)
            compare('compare_generation',['7','2'],before,processes)
            print(f'Pruebas y candidato MPI P={processes}: PASS',flush=True)
        for n in (1,7,128,129):
            compare('cholesky_candidate_seq',[str(n)],before)
        ordinary = [('compare_mpi',['7','4']),('compare_mpi_local',['7','4']),
                    ('compare_mpi_algorithms',['7','2']),('compare_mpi_total',['7','6']),
                    ('compare_application',['7','6']),('compare_blocks',['7','7']),
                    ('compare_blocks',['7','2','pair'])]
        for program,args in ordinary:
            compare(program,args,before,3)
            if program in ('compare_mpi','compare_mpi_local','compare_mpi_algorithms'):
                compare(program,[*args,'profile'],before,3)
        print('CSV ordinarios, pair y perfiles: PASS',flush=True)
        for program in ['cholesky_seq','compare_seq','compare_memory']:
            compare(program,['0'],before,expected=1)
            compare(program,['abc'],before,expected=1)
        for program in ['cholesky_candidate_seq','compare_lapack']:
            compare(program,['0'],before,expected=2)
            compare(program,['abc'],before,expected=2)
        for program in [*mpi_tests,'compare_generation','cholesky_candidate_mpi']:
            compare(program,['0'],before,3,expected=2)
        for exit_code in (0,7):
            for directory in (before, ROOT/'build'):
                output = work/'external.csv'
                proc = execute([directory/'measure_command',output,'sh','-c',f'exit {exit_code}'])
                row = next(csv.DictReader(io.StringIO(output.read_text())))
                assert proc.returncode == int(row['exit_code']) == exit_code
                assert math.isfinite(float(row['external_s'])) and float(row['external_s']) >= 0
            CHECKS.append(dict(program='measure_command',exit_code=exit_code))
        # New regression: invalid Layout must be checked before reading its fields.
        contract = work/'left_contract.c'
        contract.write_text('#include "cholesky_mpi.h"\nint main(void) { double x=1; return cholesky_left_mpi(&x,&x,&x,0,0) != -1; }\n')
        compiled = execute(['mpicc','-std=c11','-I'+str(ROOT/'src'),contract,
                            ROOT/'src/cholesky_left_mpi.c',ROOT/'src/cholesky_mpi.c','-lm','-o',work/'left_contract'])
        assert compiled.returncode == 0, compiled.stderr
        assert execute([work/'left_contract']).returncode == 0
        report = dict(status='PASS', comparison_cases=len(CHECKS), processes=[1,2,3,4,6],
                      numeric_csv='Exact equality of exported non-time fields on tested cases',
                      null_layout_regression='PASS', timing='Finite/nonnegative only; no performance claim',
                      source_hash_mode='SHA-256 after CRLF to LF normalization for Git portability',
                      current_sources={p.name:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in sorted((ROOT/'src').glob('*')) if p.is_file()},
                      cases=CHECKS)
        (ROOT/'docs/checks/refactor_equivalence.json').write_text(json.dumps(report,indent=2))
        print(f'PASS: {len(CHECKS)} comparaciones y contrato de Layout nulo.',flush=True)


if __name__ == '__main__':
    main()
