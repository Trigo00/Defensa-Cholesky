"""Entrada compatible: genera la edicion vigente del informe."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('generar_informe_decisiones.py')), run_name='__main__')
