"""
Prueba 3 - ¿Contienen las características fiduciales información sobre los
CAMBIOS de PA dentro de una misma persona?

1. Descarta latidos con errores del firmware y agrega cada sesión a un solo
   vector (mediana de sus latidos únicos válidos; amp_pulso en escala
   logarítmica) -> 70 sesiones (14 pacientes x 5; se omite Laura_Hening
   porque su CSV es copia del de Julian_Murillo).
2. Correlación intra-sujeto: se resta a cada variable la media del paciente
   y se correlacionan los desvíos de las características con los de PAS/PAD.
3. Modelo "calibrado + poblacional": para predecir una sesión de un paciente
     PA_pred = PA media del paciente (sus otras sesiones)
               + f(desvío de las características respecto a su media)
   donde f se entrena con los desvíos de TODOS los demás pacientes más las
   otras sesiones del propio paciente. Se compara contra predecir solo la
   media del paciente.

Uso (desde la raíz del proyecto):
    python PRUEBAS/experimentos/03_modelo_calibrado_poblacional.py
"""

from pathlib import Path
import hashlib
import warnings

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import RobustScaler

warnings.filterwarnings("ignore")

RAIZ = Path(__file__).resolve().parents[2]
F = ["amp_pulso", "t_cresta", "t_descnd", "pico_a_pico", "min_a_min"]


def cargar_sesiones():
    filas, vistos = [], set()
    for f in sorted((RAIZ / "Datos_de_Pacientes").glob("Data_*/datos_procesados.csv")):
        huella = hashlib.md5(f.read_bytes()).hexdigest()
        if huella in vistos:  # Laura_Hening es copia exacta de Julian_Murillo
            print(f"AVISO: se omite {f.parent.name} (CSV duplicado de otro paciente)")
            continue
        vistos.add(huella)
        d = pd.read_csv(f).drop_duplicates()
        # descarta latidos con errores del firmware (min_a_min = 0, t_descnd desbordado)
        d = d[(d.min_a_min > 0) & (d.t_descnd < 1e5) & (d.amp_pulso > 0)]
        d["s"] = d.groupby(["pas", "pad"], sort=False).ngroup()
        g = d.groupby("s").agg(**{c: (c, "median") for c in F}, pas=("pas", "first"), pad=("pad", "first"))
        g["p"] = f.parent.name.replace("Data_", "")
        filas.append(g.reset_index())
    S = pd.concat(filas, ignore_index=True)
    S["amp_pulso"] = np.log(S["amp_pulso"].clip(lower=1))
    return S


def centrar(df, medias=None):
    df = df.copy()
    for c in F + ["pas", "pad"]:
        df[c] = df[c] - (medias[c] if medias is not None else df.groupby("p")[c].transform("mean"))
    return df


def evaluar(S, nombre, fabrica):
    err = {"pas": [], "pad": []}
    for i, r in S.iterrows():
        propias = S[(S.p == r.p) & (S.index != i)]
        mu = propias[F + ["pas", "pad"]].mean()
        x = (r[F] - mu[F]).astype(float).to_numpy().reshape(1, -1)
        entrenamiento = pd.concat([centrar(S[S.p != r.p]), centrar(propias, mu)])
        # recorte a los percentiles 1-99 del entrenamiento (evita extrapolaciones
        # absurdas de los modelos lineales ante valores atípicos del sensor)
        lo, hi = entrenamiento[F].quantile(0.01).to_numpy(), entrenamiento[F].quantile(0.99).to_numpy()
        Xtr = np.clip(entrenamiento[F].to_numpy(), lo, hi)
        x = np.clip(x, lo, hi)
        for t in ["pas", "pad"]:
            m = fabrica().fit(Xtr, entrenamiento[t].to_numpy())
            err[t].append(abs(mu[t] + m.predict(x)[0] - r[t]))
    print(f"{nombre:42s} MAE PAS {np.mean(err['pas']):5.2f} ± {np.std(err['pas']):4.2f}   "
          f"PAD {np.mean(err['pad']):5.2f} ± {np.std(err['pad']):4.2f}")


def main():
    S = cargar_sesiones()
    print(f"Sesiones: {len(S)}  |  pacientes: {S.p.nunique()}\n")

    print("Correlación intra-sujeto (desvíos respecto a la media de cada paciente):")
    print(centrar(S)[F + ["pas", "pad"]].corr().loc[F, ["pas", "pad"]].round(2).to_string())

    print("\nMAE por sesión (mmHg), leave-one-session-out:")
    evaluar(S, "Solo media del paciente (línea base)", DummyRegressor)
    for a in [1, 10, 100]:
        evaluar(S, f"Calibrado + Ridge(alpha={a})",
                lambda a=a: make_pipeline(RobustScaler(), Ridge(alpha=a)))
    evaluar(S, "Calibrado + RF (leaf=5)",
            lambda: RandomForestRegressor(200, min_samples_leaf=5, random_state=42, n_jobs=-1))
    evaluar(S, "Calibrado + RF (leaf=10, max_features=0.5)",
            lambda: RandomForestRegressor(200, min_samples_leaf=10, max_features=0.5, random_state=42, n_jobs=-1))


if __name__ == "__main__":
    main()
