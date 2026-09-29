import pandas as pd
import matplotlib.pyplot as plt
import sys
import os

if len(sys.argv) < 2:
    print("Uso: python plot_real_data.py <archivo_csv>")
    sys.exit(1)

csv_file = sys.argv[1]
df = pd.read_csv(csv_file)

# Filtrar datos de Secuencial (Estrategia 1) y Paralelo 1D (Estrategia 2)
seq_df = df[df['estrategia'] == 1].set_index('N')['tiempo_total']
par_df = df[df['estrategia'] == 2]

output_dir = r"C:\Users\Nicolas\.gemini\antigravity\brain\7839c84b-6f43-42cf-a7d7-64ddbe09dac7"

# 1. Gráfico de Tiempo vs N
plt.figure(figsize=(10, 6))
plt.plot(seq_df.index, seq_df.values, marker='o', label='Secuencial (P=1)', linewidth=2)

for p in sorted(par_df['P'].unique()):
    data_p = par_df[par_df['P'] == p]
    plt.plot(data_p['N'], data_p['tiempo_total'], marker='s', label=f'1D Block-Cyclic (P={p})')

plt.title('Tiempo de Ejecución Real vs Tamaño de Matriz (N)')
plt.xlabel('Tamaño de Matriz N')
plt.ylabel('Tiempo Total (s)')
plt.yscale('log')
plt.grid(True, which="both", ls="--")
plt.legend()
plt.savefig(os.path.join(output_dir, 'real_tiempo_vs_n.png'))
plt.close()

# 2. Gráfico de Speedup
plt.figure(figsize=(10, 6))
for n in sorted(par_df['N'].unique()):
    if n not in seq_df:
        continue
    t_seq = seq_df[n]
    data_n = par_df[par_df['N'] == n].sort_values('P')
    
    speedups = [t_seq / t for t in data_n['tiempo_total']]
    ps = data_n['P'].tolist()
    
    # Agregar P=1 (Secuencial) como base
    ps.insert(0, 1)
    speedups.insert(0, 1.0)
    
    plt.plot(ps, speedups, marker='o', label=f'N={n}')

# Línea ideal
max_p = par_df['P'].max()
plt.plot([1, max_p], [1, max_p], 'k--', label='Speedup Ideal')

plt.title('Speedup Real (T_secuencial / T_paralelo)')
plt.xlabel('Cantidad de Procesos (P)')
plt.ylabel('Speedup')
plt.xticks([1] + sorted(par_df['P'].unique()))
plt.grid(True)
plt.legend()
plt.savefig(os.path.join(output_dir, 'real_speedup.png'))
plt.close()

print("Gráficos reales generados con éxito.")
