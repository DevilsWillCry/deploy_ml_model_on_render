"""
Prueba 2 - ¿Qué cambios de preprocesamiento / hiperparámetros mejoran el
modelo personalizado al predecir una sesión NUEVA?

Protocolo: por paciente, "leave-one-session-out" (se entrena con 4 de sus 5
sesiones y se predice la sesión restante). Se reportan dos MAE:
  * sesión : |mediana de las predicciones de los latidos - PA de referencia|
             (una predicción por medición, como operaría el dispositivo)
  * latido : MAE de cada latido individual

Variantes probadas:
  * dedup   : eliminar filas idénticas (cada latido se repite ~40 veces)
  * invalidos: eliminar latidos con errores del firmware (min_a_min = 0 y
              t_descnd desbordado a ~4.29e6 s); ~30 % de los latidos únicos
  * filtro  : eliminar latidos con tiempos fisiológicamente imposibles
              (intervalos fuera de 0.33-1.5 s, t_cresta fuera de 0.03-0.6 s,
               t_descnd fuera de 0.1-1.4 s)
  * extra   : variables derivadas (FC = 60/min_a_min, t_cresta/t_descnd,
              t_cresta/min_a_min)
  * sin amp : quitar amp_pulso (depende del contacto con el sensor)
  * distintos hiperparámetros de RF, ExtraTrees, LR, Ridge, SVR
  * Media de entrenamiento: línea base que ignora las características

ADVERTENCIA: elegir hiperparámetros con esta tabla sería ajustarlos sobre los
datos de prueba. Sirve para explorar, no para reportar el modelo final.

Uso (desde la raíz del proyecto, tarda unos minutos):
    python PRUEBAS/experimentos/02_mejoras_preprocesamiento.py
"""

from pathlib import Path
import hashlib
import warnings

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import ExtraTreesRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR

warnings.filterwarnings("ignore")

RAIZ = Path(__file__).resolve().parents[2]
F = ["amp_pulso", "t_cresta", "t_descnd", "pico_a_pico", "min_a_min"]

PACIENTES, _vistos = {}, set()
for f in sorted((RAIZ / "Datos_de_Pacientes").glob("Data_*/datos_procesados.csv")):
    huella = hashlib.md5(f.read_bytes()).hexdigest()
    if huella in _vistos:  # Laura_Hening es copia exacta de Julian_Murillo
        print(f"AVISO: se omite {f.parent.name} (CSV duplicado de otro paciente)")
        continue
    _vistos.add(huella)
    d = pd.read_csv(f)
    d["s"] = d.groupby(["pas", "pad"], sort=False).ngroup()  # id de sesión
    PACIENTES[f.parent.name] = d


def filtro_invalidos(d):
    """Errores del firmware: min_a_min = 0 y t_descnd desbordado (~4.29e6 s)."""
    return d[(d.min_a_min > 0) & (d.t_descnd < 1e5) & (d.amp_pulso > 0)]


def filtro_fisiologico(d):
    m = (d.min_a_min.between(0.33, 1.5) & d.pico_a_pico.between(0.33, 1.5)
         & d.t_cresta.between(0.03, 0.6) & d.t_descnd.between(0.1, 1.4))
    return d[m]


def caracteristicas(d, extra):
    X = d[F].copy()
    if extra:
        X["fc"] = 60 / d.min_a_min
        X["ratio"] = d.t_cresta / d.t_descnd
        X["tc_rel"] = d.t_cresta / d.min_a_min
    return X


def evaluar(nombre, fabrica, dedup=False, invalidos=False, filtro=False, extra=False, sin_amp=False):
    err_ses = {"pas": [], "pad": []}
    err_lat = {"pas": [], "pad": []}
    for d in PACIENTES.values():
        if dedup:
            d = d.drop_duplicates()
        if invalidos:
            d = filtro_invalidos(d)
        if filtro:
            d = filtro_fisiologico(d)
        for s in d.s.unique():
            tr, te = d[d.s != s], d[d.s == s]
            if len(te) == 0 or tr.s.nunique() < 2:
                continue
            Xtr, Xte = caracteristicas(tr, extra), caracteristicas(te, extra)
            if sin_amp:
                Xtr, Xte = Xtr.drop(columns="amp_pulso"), Xte.drop(columns="amp_pulso")
            for t in ["pas", "pad"]:
                pred = fabrica().fit(Xtr, tr[t]).predict(Xte)
                err_ses[t].append(abs(np.median(pred) - te[t].iloc[0]))
                err_lat[t].append(mean_absolute_error(te[t], pred))
    print(f"{nombre:55s} sesión PAS {np.mean(err_ses['pas']):5.2f} PAD {np.mean(err_ses['pad']):5.2f} | "
          f"latido PAS {np.mean(err_lat['pas']):5.2f} PAD {np.mean(err_lat['pad']):5.2f} | "
          f"n={len(err_ses['pas'])}", flush=True)


def escalado(fabrica_modelo):
    return lambda: make_pipeline(StandardScaler(), fabrica_modelo())


def RF(**k):
    return escalado(lambda: RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1, **k))


def main():
    print("MAE en mmHg (leave-one-session-out por paciente)\n")
    evaluate_list = [
        ("RF base (como backend)", RF(), {}),
        ("RF dedup", RF(), dict(dedup=True)),
        ("RF dedup+invalidos", RF(), dict(dedup=True, invalidos=True)),
        ("RF filtro", RF(), dict(filtro=True)),
        ("RF dedup+filtro", RF(), dict(dedup=True, filtro=True)),
        ("RF dedup+filtro+extra", RF(), dict(dedup=True, filtro=True, extra=True)),
        ("RF dedup+filtro sin amp", RF(), dict(dedup=True, filtro=True, sin_amp=True)),
    ]
    for k in [dict(min_samples_leaf=3), dict(min_samples_leaf=5), dict(max_depth=4),
              dict(max_features="sqrt"), dict(max_features="sqrt", min_samples_leaf=3),
              dict(max_features=0.5, min_samples_leaf=5)]:
        evaluate_list.append((f"RF dedup+filtro {k}", RF(**k), dict(dedup=True, filtro=True)))
    evaluate_list += [
        ("ExtraTrees dedup+filtro leaf=3",
         escalado(lambda: ExtraTreesRegressor(n_estimators=200, min_samples_leaf=3, random_state=42, n_jobs=-1)),
         dict(dedup=True, filtro=True)),
        ("LR base", escalado(LinearRegression), {}),
        ("LR dedup+invalidos", escalado(LinearRegression), dict(dedup=True, invalidos=True)),
        ("LR dedup+filtro", escalado(LinearRegression), dict(dedup=True, filtro=True)),
        ("Ridge(alpha=10) dedup+filtro", escalado(lambda: Ridge(alpha=10)), dict(dedup=True, filtro=True)),
        ("SVR(rbf, C=100, eps=0.1) base", escalado(lambda: SVR(C=100, epsilon=0.1)), {}),
        ("SVR(rbf, C=100, eps=0.1) dedup+filtro", escalado(lambda: SVR(C=100, epsilon=0.1)),
         dict(dedup=True, filtro=True)),
        ("SVR(rbf, C=100, eps=0.1) dedup+invalidos", escalado(lambda: SVR(C=100, epsilon=0.1)),
         dict(dedup=True, invalidos=True)),
        ("Media de entrenamiento (línea base)", DummyRegressor, dict(dedup=True)),
    ]
    for nombre, fabrica, opciones in evaluate_list:
        evaluar(nombre, fabrica, **opciones)


if __name__ == "__main__":
    main()
