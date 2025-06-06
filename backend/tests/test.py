import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline

data = {
    "name": {"first": "John", "last": "Doe"},
    "age": {"years": 30, "months": 6},
    "city": {"city": "New York", "state": "NY"}
    }

for key, value in data.items():
    print(key)
    for subkey, subvalue in value.items():
        print(f"  {subkey}: {subvalue}")





# Definir puntos de control para dos pulsos PPG (sin duplicar tiempos)
times_ctrl = np.array([0.0, 0.1, 0.2, 0.3, 0.35, 0.5, 0.6, 0.7, 0.8, 0.85, 1.1, 1.2, 1.5, 1.6, 2.0])
amps_ctrl  = np.array([0.0, 0.4, 1.0, 0.5, 0.7, 0.0, 0.2, 1.1, 0.6, 0.9, 0.0, 0.1, 0.8, 0.3, 0.0])

# Construir señal continua mediante interpolación cúbica
cs = CubicSpline(times_ctrl, amps_ctrl)
t = np.linspace(0, 2, 2000)
ppg = cs(t)

# Definir tiempos de interés para el primer y segundo pulso
# Primer pulso
t_min_prev = 0.0    # primer valle
t_pico_prev = 0.2   # primer pico (systolic)
t_notch_prev = 0.3  # dicrotic notch
t_second_prev = 0.35  # segundo onda
t_min_act = 0.5       # valle entre pulsos

# Segundo pulso
t_min_prev2 = t_min_act  # valle anterior del segundo pulso
t_pico_prev2 = 0.7      # pico del segundo pulso
t_notch_prev2 = 0.8     # dicrotic notch segundo
t_second_prev2 = 0.85   # segunda onda segundo
t_min_act2 = 1.1        # valle después del segundo pulso

# Calcular amplitudes en los puntos definidos
y_min_prev = np.interp(t_min_prev, t, ppg)
y_pico_prev = np.interp(t_pico_prev, t, ppg)
y_min_act = np.interp(t_min_act, t, ppg)
y_pico_prev2 = np.interp(t_pico_prev2, t, ppg)
y_min_act2 = np.interp(t_min_act2, t, ppg)

# Graficar
plt.figure(figsize=(12, 6))
plt.plot(t, ppg, color='blue', linewidth=2, label='Señal PPG')

# Primer pulso: marcar polos y valles
plt.scatter([t_min_prev, t_pico_prev, t_notch_prev, t_second_prev, t_min_act],
            [y_min_prev, y_pico_prev, np.interp(t_notch_prev, t, ppg), np.interp(t_second_prev, t, ppg), y_min_act],
            color=['red', 'green', 'purple', 'orange', 'red'], s=50)

plt.text(t_min_prev - 0.02, y_min_prev + 0.05, 'Valle\n(t_min_prev)', color='red', ha='right')
plt.text(t_pico_prev, y_pico_prev + 0.05, 'Systolic\n(t_pico_prev)', color='green', ha='center')
plt.text(t_notch_prev + 0.01, np.interp(t_notch_prev, t, ppg) - 0.05, 'Dicrotic\nNotch', color='purple', ha='left')
plt.text(t_second_prev + 0.01, np.interp(t_second_prev, t, ppg) + 0.05, 'Second\nWave', color='orange', ha='left')
plt.text(t_min_act - 0.02, y_min_act + 0.05, 'Valle\n(t_min_act)', color='red', ha='right')

# Segundo pulso: marcar polos y valles
plt.scatter([t_min_prev2, t_pico_prev2, t_notch_prev2, t_second_prev2, t_min_act2],
            [y_min_prev, y_pico_prev2, np.interp(t_notch_prev2, t, ppg), np.interp(t_second_prev2, t, ppg), y_min_act2],
            color=['red', 'green', 'purple', 'orange', 'red'], s=50)

plt.text(t_pico_prev2, y_pico_prev2 + 0.05, 'Systolic\n(t_pico_prev2)', color='green', ha='center')
plt.text(t_notch_prev2 + 0.01, np.interp(t_notch_prev2, t, ppg) - 0.05, 'Dicrotic\nNotch', color='purple', ha='left')
plt.text(t_second_prev2 + 0.01, np.interp(t_second_prev2, t, ppg) + 0.05, 'Second\nWave', color='orange', ha='left')
plt.text(t_min_act2 - 0.02, y_min_act2 + 0.05, 'Valle\n(t_min_act2)', color='red', ha='right')

# Anotar intervalos de características para primer pulso
# Amplitud: entre valle(t_min_prev) y pico(t_pico_prev)
plt.annotate('', xy=(t_pico_prev, y_pico_prev - 0.05), xytext=(t_pico_prev, y_min_prev + 0.05),
             arrowprops=dict(arrowstyle='<->', color='teal', lw=1.5))
plt.text(t_pico_prev + 0.03, (y_pico_prev + y_min_prev) / 2, 'amp_pulso', color='teal', va='center')

# t_cresta: distancia horizontal entre valle(t_min_prev) y pico(t_pico_prev)
plt.annotate('', xy=(t_pico_prev - 0.01, y_min_prev - 0.02), xytext=(t_min_prev + 0.01, y_min_prev - 0.02),
             arrowprops=dict(arrowstyle='<->', color='purple', lw=1.5))
plt.text((t_min_prev + t_pico_prev) / 2, y_min_prev - 0.08, 't_cresta', color='purple', ha='center')

# t_descnd: distancia entre pico(t_pico_prev) y valle(t_min_act)
plt.annotate('', xy=(t_min_act - 0.01, y_min_prev - 0.02), xytext=(t_pico_prev + 0.01, y_min_prev - 0.02),
             arrowprops=dict(arrowstyle='<->', color='brown', lw=1.5))
plt.text((t_pico_prev + t_min_act) / 2, y_min_prev - 0.14, 't_descnd', color='brown', ha='center')

# pico_a_pico: distancia horizontal entre pico(t_pico_prev) y pico(t_pico_prev2)
plt.annotate('', xy=(t_pico_prev2, y_min_prev - 0.15), xytext=(t_pico_prev, y_min_prev - 0.15),
             arrowprops=dict(arrowstyle='<->', color='darkcyan', lw=1.5))
plt.text((t_pico_prev + t_pico_prev2) / 2, y_min_prev - 0.23, 'pico_a_pico', color='darkcyan', ha='center')

# min_a_min: distancia entre valle(t_min_prev) y valle(t_min_act2)
plt.annotate('', xy=(t_min_act2, y_min_prev - 0.27), xytext=(t_min_prev, y_min_prev - 0.27),
             arrowprops=dict(arrowstyle='<->', color='olive', lw=1.5))
plt.text((t_min_prev + t_min_act2) / 2, y_min_prev - 0.35, 'min_a_min', color='olive', ha='center')

plt.title('Señal PPG Sintética (similar a imagen) con Marcado de Características')
plt.xlabel('Tiempo (s)')
plt.ylabel('Amplitud (AU)')
plt.ylim(-0.1, 1.3)
plt.grid(True)
plt.show()
