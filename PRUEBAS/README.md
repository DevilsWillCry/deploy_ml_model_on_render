# Pruebas de modelos para la estimación de PA (PAS / PAD)

Pipeline y pruebas realizadas el 2026-11-16 para documentar los hiperparámetros
del artículo y comparar Random Forest, SVR y regresión lineal con los datos de
`Datos_de_Pacientes/`.

## Contenido

| Archivo | Qué es |
|---|---|
| `comparar_modelos.py` | **Pipeline principal** de comparación de modelos (configurable por línea de comandos) |
| `experimentos/01_inspeccionar_modelos_guardados.py` | Prueba 1: hiperparámetros reales de los `.joblib` y calidad de los datos |
| `experimentos/02_mejoras_preprocesamiento.py` | Prueba 2: variantes de preprocesamiento e hiperparámetros |
| `experimentos/03_modelo_calibrado_poblacional.py` | Prueba 3: ¿las características explican los cambios de PA dentro de una persona? |
| `Model parameters - completado.csv` | Tablas 1–3 de hiperparámetros, completadas |
| `Model parameters - Hoja 1.csv`, imagen JPEG | Material original (plantilla y Tabla 7 de la tesis) |
| `resultados/` | Salidas de todas las pruebas (`pruebaNN_*.txt`, CSV de métricas, gráficas) |
| `resultados/obsoletos_15_pacientes/` | Corridas anteriores, hechas antes de detectar que Laura_Hening duplica a Julian_Murillo. No usar |
| `requirements.txt` | Versiones exactas del entorno usado |

## Cómo reproducir

```bash
python3 -m venv .venv && .venv/bin/pip install -r PRUEBAS/requirements.txt
# desde la raíz del proyecto:
.venv/bin/python PRUEBAS/experimentos/01_inspeccionar_modelos_guardados.py
.venv/bin/python PRUEBAS/experimentos/02_mejoras_preprocesamiento.py        # ~5 min
.venv/bin/python PRUEBAS/experimentos/03_modelo_calibrado_poblacional.py
# Prueba 4a: protocolo de la tesis (lento, ~15 min por el SVR sobre datos duplicados)
.venv/bin/python PRUEBAS/comparar_modelos.py --protocolo todos --modelos RF SVR LR DT MEDIA --graficas
# Prueba 4b: configuración recomendada (segundos)
.venv/bin/python PRUEBAS/comparar_modelos.py --protocolo todos --sin-duplicados --filtrar-invalidos \
    --nivel sesion --modelos RF SVR LR DT MEDIA --graficas
```

## Pipeline (`comparar_modelos.py`)

1. **Carga.** Lee `Datos_de_Pacientes/Data_*/datos_procesados.csv` con 5 características
   (`amp_pulso`, `t_cresta`, `t_descnd`, `pico_a_pico`, `min_a_min`) y las dos salidas (`pas`, `pad`).
   - Omite los CSV idénticos byte a byte a otro paciente. Hoy esto deja fuera a **Laura_Hening**,
     porque su archivo es copia del de Julian_Murillo. Quedan **14 pacientes**.
   - Define la sesión como cada par (PAS, PAD) de referencia: 5 sesiones por paciente.
2. **Limpieza (opcional).**
   - `--sin-duplicados` elimina filas idénticas. Cada latido único aparece repetido unas 40 veces.
   - `--filtrar-invalidos` descarta latidos con errores del firmware: `min_a_min = 0` y
     `t_descnd` ≈ 4 294 967 s (ver *Hallazgos*).
3. **Modelo.** Usa `Pipeline(StandardScaler → modelo)`. El escalado se ajusta solo con el
   entrenamiento de cada pliegue. Se entrena un modelo independiente para PAS y otro para PAD.
4. **Protocolo de validación** (`--protocolo`):
   - `kfold`: un modelo por paciente con `KFold(5, shuffle=True, random_state=42)` sobre filas.
     Es el protocolo del backend y de la tesis.
   - `sesion`: un modelo por paciente, *leave-one-session-out*. Se entrena con 4 sesiones y se
     predice la 5.ª, que el modelo no vio.
   - `general`: *leave-one-subject-out*. Se entrena con los otros 13 pacientes y se predice el excluido.
5. **Nivel** (`--nivel`):
   - `latido`: una predicción por fila.
   - `sesion`: una predicción por medición, igual a la mediana de las predicciones de los latidos de la sesión.
6. **Métricas.** MAE, MSE, RMSE y R² para PAS y PAD sobre las predicciones *out-of-fold* de cada
   paciente, resumidas como media ± desviación estándar entre pacientes, más el R² global
   (todas las predicciones juntas).

### Modelos e hiperparámetros

| Modelo | Configuración (scikit-learn 1.9.1) |
|---|---|
| RF | `RandomForestRegressor(n_estimators=100, criterion='squared_error', max_depth=None, min_samples_split=2, min_samples_leaf=1, max_features=1.0, bootstrap=True, random_state=42)`. Es idéntico a los modelos guardados (verificado en la prueba 1) |
| SVR | `SVR(kernel='rbf', C=100, epsilon=0.1, gamma='scale')`. Valores tomados de las notas de la tesis |
| LR | `LinearRegression()` (mínimos cuadrados ordinarios, con intercepto) |
| DT | `DecisionTreeRegressor(random_state=42)`. Se usó en versiones previas del backend |
| MEDIA | `DummyRegressor('mean')`. Línea base: predice la PA media del entrenamiento |

## Resultados (14 pacientes)

### Prueba 1. Modelos guardados y calidad de datos (`resultados/prueba01_inspeccion.txt`)

- Los 28 modelos guardados (14 pacientes × PAS/PAD) más los 2 de Laura comparten exactamente la
  configuración RF de la tabla anterior.
- Tamaño de los 3 000 árboles:
  - Profundidad entre 6 y 21 (media 10.5).
  - Hojas entre 14 y 62 (media 34.4).
  - Nodos entre 27 y 123 (media 67.8).
- Cada paciente tiene de 1 800 a 3 600 filas, pero solo **41 a 98 latidos únicos**, 5 sesiones
  y 4 o 5 valores de PA distintos.
- Alrededor del **30 % de los latidos únicos es inválido** por el error del firmware.

### Prueba 4a. Protocolo de la tesis frente a protocolos honestos, con datos sin limpiar (`resultados/prueba04a_original_tesis.txt`)

MAE en mmHg, PAS / PAD:

| Modelo | kfold (tesis) | sesión nueva | general |
|---|---|---|---|
| RF | 0.05 / 0.03 | 8.23 / 5.01 | 13.06 / 7.52 |
| SVR | 1.83 / 1.01 | 12.26 / 7.87 | 11.47 / 6.53 |
| LR | 5.14 / 2.95 | 7.89 / 4.57 | 16.00 / 6.91 |
| DT | 0.05 / 0.03 | 8.49 / 5.27 | 14.86 / 8.56 |
| MEDIA | 5.65 / 3.26 | **7.12 / 4.09** | 13.08 / 6.03 |

Con KFold, RF y DT obtienen un error casi nulo porque las filas repetidas caen a la vez en
entrenamiento y en prueba. Al predecir una sesión nueva, la ventaja desaparece.

### Prueba 4b. Configuración recomendada (`resultados/prueba04b_recomendado.txt`)

Sin duplicados, sin latidos inválidos y con una predicción por medición. MAE en mmHg, PAS / PAD:

| Modelo | Personalizado (sesión nueva) | General (otros pacientes) |
|---|---|---|
| RF | 7.17 / 4.27 | 10.22 / 6.85 |
| SVR | 7.14 / 4.57 | 10.12 / 6.73 |
| LR | 7.28 / 4.35 | 13.52 / 6.43 |
| DT | 7.42 / 4.44 | 11.59 / 7.54 |
| MEDIA | **7.02 / 4.20** | 13.11 / 6.28 |

### Prueba 2. Variantes de preprocesamiento (`resultados/prueba02_preprocesamiento.txt`)

Ninguna variante (deduplicar, filtrar, variables derivadas, quitar `amp_pulso`, cambiar
hiperparámetros del RF, ExtraTrees, Ridge, SVR) baja el MAE por sesión de forma consistente por
debajo de la línea base MEDIA (7.02 / 4.14). La mejor variante de RF queda en 6.86 / 4.21.

### Prueba 3. Información intra-sujeto (`resultados/prueba03_calibrado.txt`)

- Correlación entre los desvíos de las características y los de la PA, dentro de cada paciente:
  |r| ≤ 0.21 en todos los casos.
- Un modelo "calibrado" (PA media del paciente + cambio aprendido con la población) no supera a la
  media del paciente: 7.22 / 4.23 frente a 7.00 / 4.19.

## Hallazgos para el artículo

1. **Hiperparámetros:** están documentados en `Model parameters - completado.csv`.
2. **Personalizado frente a general:** se cumple. El RF personalizado tiene un MAE de 7.17 / 4.27 y
   el general de 10.22 / 6.85.
3. **RF frente a SVR y LR:** con validación por sesión nueva, la diferencia no es significativa y
   ningún modelo supera a predecir la PA media del paciente. Los R² ≈ 1 de la tesis se deben a la
   validación KFold sobre filas repetidas.
4. **Datos:**
   - `Data_Laura_Hening/datos_procesados.csv` es copia de `Data_Julian_Murillo/datos_procesados.csv`.
     Los datos originales de Laura no están en el repositorio.
   - Error del firmware en `extraccion_caracteristicas/Alpinista_MAX30102_HR_3/Alpinista_MAX30102_HR_3.ino:324-327`:
     si no se detecta un mínimo nuevo entre dos picos, `min_a_min = 0` y
     `t_descnd = (t_min_act - t_pico_prev)` se desborda en `unsigned long`, dando ≈ 4.29·10⁶ s.
5. **Qué mejoraría los resultados:**
   - Más sesiones por paciente, con un rango amplio de PA (reposo, ejercicio, recuperación).
   - Corregir el firmware.
   - Incorporar más rasgos de la onda; por ejemplo, `area_pulso` ya se calcula pero no se guarda en el CSV.
