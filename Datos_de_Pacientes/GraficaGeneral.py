import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor
from sklearn.linear_model import LinearRegression
from sklearn.svm import SVR
from sklearn.model_selection import KFold
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
import matplotlib.pyplot as plt

# Configuración inicial
base_path = (os.getcwd()).replace('\\', '/') + "/"
print("Path de los archivos: ", base_path)

# Cargar datos
paciente_path = {}
for f in os.listdir(base_path):
    if os.path.isdir(base_path + f):
        for g in os.listdir(base_path + f):
            if g.endswith('datos_procesados.csv'):
                paciente_path[f.replace("Data_", "")] = base_path + f + '/' + g

# Diccionario para almacenar resultados
modelos_pacientes = {}

# KFold
kf = KFold(n_splits=5, shuffle=True, random_state=42)

# Entrenar por paciente
for nombre_paciente, path in paciente_path.items():
    df = pd.read_csv(path, index_col=0)
    X = df.drop(columns=['pas', 'pad'])
    y = df['pas'] #! Cambiar a pas o pad
    
    r2_scores, mse_scores, mae_scores, rmse_scores = [], [], [], []
    y_tests, y_preds = [], []

    for train_idx, test_idx in kf.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]

        #! Cambiar modelo para pruebas
        model = RandomForestRegressor(
            n_estimators=100,       # más árboles para captar más patrones
            max_depth=None,         # sin límite: deja crecer los árboles completos
            min_samples_leaf=1,     # aprende hasta el último detalle
            random_state=42
        )
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        # Guardar métricas por fold
        r2_scores.append(r2_score(y_test, y_pred))
        mse_scores.append(mean_squared_error(y_test, y_pred))
        mae_scores.append(mean_absolute_error(y_test, y_pred))
        rmse_scores.append(np.sqrt(mean_squared_error(y_test, y_pred)))

        y_tests.extend(y_test)
        y_preds.extend(y_pred)

    # Guardar promedios por paciente
    modelos_pacientes[nombre_paciente] = {
        'r2': np.mean(r2_scores),
        'mse': np.mean(mse_scores),
        'mae': np.mean(mae_scores),
        'rmse': np.mean(rmse_scores),
        'y_test': np.array(y_tests),
        'y_pred': np.array(y_preds)
    }

# Gráfica combinada
plt.figure(figsize=(14, 8))
colors = plt.cm.get_cmap('tab10', len(modelos_pacientes))
count = 0

for i, (nombre_paciente, resultados) in enumerate(modelos_pacientes.items()):
    count += 1
    plt.scatter(
        resultados['y_test'],
        resultados['y_pred'],
        color=colors(i),
        alpha=0.7,
        label=f"Paciente {count} (R²={resultados['r2']:.2f}, MAE={resultados['mae']:.2f}, MSE={resultados['mse']:.2f})",
        s=80
    )

# Línea de predicción perfecta
min_val = min(min(r['y_test']) for r in modelos_pacientes.values())
max_val = max(max(r['y_test']) for r in modelos_pacientes.values())
plt.plot([min_val, max_val], [min_val, max_val], 'k--', lw=2, label='Predicción perfecta')

# Estética
plt.xlabel('Valor Real de PAD (mmHg)', fontsize=12)
plt.ylabel('Valor Predicho de PAD (mmHg)', fontsize=12)
plt.title('Modelo SVM por paciente', fontsize=14)
plt.legend(fontsize=10, bbox_to_anchor=(1.05, 1), loc='upper left')
plt.grid(True, alpha=0.3)
plt.tight_layout()

# Métricas promedio globales
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
print("\nMétricas por paciente con validación cruzada:")
for nombre, r in modelos_pacientes.items():
    print(f"\nPaciente: {nombre}")
    print(f"R² promedio: {r['r2']:.3f}")
    print(f"MSE promedio: {r['mse']:.3f}")
    print(f"MAE promedio: {r['mae']:.3f} mmHg")
    print(f"RMSE promedio: {r['rmse']:.3f} mmHg")
