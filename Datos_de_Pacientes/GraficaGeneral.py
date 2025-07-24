import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import matplotlib.pyplot as plt

# Configuración inicial (igual a tu código original)
base_path = (os.getcwd()).replace('\\', '/') + "/"
print("Path de los archivos: ", base_path)

# Cargar datos (igual a tu código original)
paciente_path = {}
for f in os.listdir(base_path):
    if os.path.isdir(base_path + f):
        for g in os.listdir(base_path + f):
            if g.endswith('datos_procesados.csv'):
                paciente_path[f.replace("Data_", "")] = base_path + f + '/' + g

# Diccionario para almacenar los modelos y resultados
modelos_pacientes = {}

# Entrenar un modelo por paciente
for nombre_paciente, path in paciente_path.items():
    # Cargar datos del paciente
    df_paciente = pd.read_csv(path, index_col=0)
    
    # Preparar datos (ajusta las columnas según necesites)
    X = df_paciente.drop(columns=['pas', 'pad'])  # Ajustar columnas
    y = df_paciente['pad']  # Columna objetivo
    
    # Dividir en train/test (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    
    # Entrenar modelo
    model = RandomForestRegressor(
        n_estimators=100,
        random_state=42,
    )
    model.fit(X_train, y_train)
    
    # Predecir y calcular métricas
    y_pred = model.predict(X_test)
    
    # Almacenar resultados
    modelos_pacientes[nombre_paciente] = {
        'modelo': model,
        'X_test': X_test,
        'y_test': y_test,
        'y_pred': y_pred,
        'r2': r2_score(y_test, y_pred),
        'mse': mean_squared_error(y_test, y_pred),
        'mae': mean_absolute_error(y_test, y_pred)
    }

# Crear gráfica combinada
plt.figure(figsize=(14, 8))
colors = plt.cm.get_cmap('tab10', len(modelos_pacientes))
count = 0

for i, (nombre_paciente, resultados) in enumerate(modelos_pacientes.items()):
    count+=1
    plt.scatter(
        resultados['y_test'],
        resultados['y_pred'],
        color=colors(i),
        alpha=0.7,
        label=f"Paciente {str(count)} (R²={resultados['r2']:.2f} MAE={resultados['mae']:.2f} MSE={resultados['mse']:.2f})",
        s=80
    )

# Línea de perfecta predicción
min_val = min(min(r['y_test'].min() for r in modelos_pacientes.values()),
              min(r['y_pred'].min() for r in modelos_pacientes.values()))
max_val = max(max(r['y_test'].max() for r in modelos_pacientes.values()),
              max(r['y_pred'].max() for r in modelos_pacientes.values()))
plt.plot([min_val, max_val], [min_val, max_val], 'k--', lw=2, label='Predicción perfecta')

# Ajustes estéticos
plt.xlabel('Valor Real de PAD (mmHg)', fontsize=12)
plt.ylabel('Valor Predicho de PAD (mmHg)', fontsize=12)
plt.title('Comparación de Modelos Individuales por sujeto', fontsize=14)
plt.legend(fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True, alpha=0.3)
plt.tight_layout()

# Mostrar métricas promedio
r2_promedio = np.mean([r['r2'] for r in modelos_pacientes.values()])
mse_promedio = np.mean([r['mse'] for r in modelos_pacientes.values()])
plt.text(
    x=0.95 * max_val,
    y=0.1 * max_val,
    s=f"R² promedio = {r2_promedio:.2f}\nMSE promedio = {mse_promedio:.2f}",
    ha='right',
    bbox=dict(facecolor='white', alpha=0.8)
)

plt.show()

# Imprimir métricas por paciente
print("\nMétricas por paciente:")
for nombre, resultados in modelos_pacientes.items():
    print(f"\nPaciente: {nombre}")
    print(f"R²: {resultados['r2']:.3f}")
    print(f"MSE: {resultados['mse']:.3f}")
    print(f"MAE: {resultados['mae']:.3f} mmHg")
    print(f"RMSE: {np.sqrt(resultados['mse']):.3f} mmHg")