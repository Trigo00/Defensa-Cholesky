import os

OUT_DIR = r"C:\Users\Nicolas\.gemini\antigravity\brain\7839c84b-6f43-42cf-a7d7-64ddbe09dac7"

files = [
    ("Bloque 0: Fundamentos y Variante Right-Looking", "cholesky_fundamentals.md"),
    ("Bloque 1: Framework de Benchmarking y Rendimiento Base", "benchmarking_framework.md"),
    ("Bloque 2: Distribuciones 1D y Desbalance Estructural", "block2_1d_distributions.md"),
    ("Bloque 3: Criterios de Escala e Isoeficiencia", "block3_decision_rule.md"),
    ("Bloque 4: Balanceo de Carga en Entornos Heterogéneos", "block4_load_balancing.md"),
    ("Bloque 5: Límites de Optimización (Amdahl y Gustafson)", "block5_optimization_cutoff.md"),
    ("Bloque 6: Topologías 1D vs 2D (ScaLAPACK)", "block6_1d_vs_2d.md"),
    ("Bloque 7: Módulo Auto-Tuner y Decisión en Runtime", "block7_auto_tuner.md"),
    ("Bloque 8: Conclusiones y Resumen Ejecutivo", "informe_final_hpc.md")
]

with open(os.path.join(OUT_DIR, 'Documentacion_Completa_Cholesky.md'), 'w', encoding='utf-8') as outfile:
    outfile.write("# Documentación Completa del Proyecto: Factorización de Cholesky Distribuida\n\n")
    
    for title, filename in files:
        filepath = os.path.join(OUT_DIR, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as infile:
                content = infile.read()
                # Escribir el contenido del bloque
                outfile.write(f"{content}\n\n")
                outfile.write("---\n\n")

print("Documento completo compilado con éxito.")
