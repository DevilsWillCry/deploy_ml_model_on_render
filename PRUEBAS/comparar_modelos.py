"""
Comparación de modelos para la estimación de presión arterial (PAS / PAD)
a partir de características fiduciales PPG, usando los datos de
Datos_de_Pacientes/*/datos_procesados.csv.

Modelos (hiperparámetros explícitos para poder reportarlos en el artículo):
  - RF  : RandomForestRegressor  (mismo que el backend: model_service.py)
  - SVR : SVR(kernel='rbf', C=100, epsilon=0.1, gamma='scale')
  - LR  : LinearRegression() (mínimos cuadrados ordinarios, 5 variables)
  - DT  : DecisionTreeRegressor (usado en versiones previas del backend)
  - MEDIA: DummyRegressor (predice la PA media del entrenamiento). Es la línea
           base mínima: un modelo útil debe tener MENOR error que ella.

Todos los modelos van dentro de un Pipeline(StandardScaler -> modelo), de modo
que el escalado se ajusta SOLO con los datos de entrenamiento de cada pliegue.

Protocolos de evaluación (--protocolo):
  kfold    : modelo personalizado por paciente, KFold(5, shuffle, rs=42) sobre
             todas las filas. Es el protocolo del backend / tesis.
             OJO: las filas repetidas caen en train y test a la vez, por lo que
             mide memorización más que predicción de una medición nueva.
  sesion   : modelo personalizado por paciente, "leave-one-session-out": se
             entrena con 4 de las 5 sesiones del paciente y se predice la sesión
             restante (una medición nunca vista).
  general  : modelo general "leave-one-subject-out": se entrena con los otros
             pacientes y se predice el paciente excluido. Sirve de contraste
             frente al modelo personalizado.
  todos    : ejecuta los tres.

Métricas: MAE, MSE, RMSE y R² para PAS y PAD, calculadas por paciente sobre
las predicciones fuera de pliegue (out-of-fold), y luego resumidas como
media ± desviación estándar entre pacientes. También se reporta el R² global
(todas las predicciones de todos los pacientes juntas).

Nivel de evaluación (--nivel):
  latido : una predicción por fila/latido (como en la tesis).
  sesion : una predicción por medición = mediana de las predicciones de los
           latidos de esa sesión, comparada con la PA de referencia. Es como
           debería operar el dispositivo (promediar varios latidos).

Calidad de datos:
  * Se omiten CSV idénticos a otro paciente (Laura_Hening = copia de Julian_Murillo).
  * --filtrar-invalidos descarta latidos con errores del firmware (~30 % de los
    latidos únicos): min_a_min = 0 y t_descnd desbordado a ~4.29e6 s.

Configuración recomendada (sin filas duplicadas + una predicción por medición):
    python PRUEBAS/comparar_modelos.py --protocolo sesion --sin-duplicados --filtrar-invalidos --nivel sesion

Uso (desde la raíz del proyecto):
    python PRUEBAS/comparar_modelos.py
    python PRUEBAS/comparar_modelos.py --protocolo sesion --modelos RF SVR LR
    python PRUEBAS/comparar_modelos.py --protocolo todos --graficas
"""

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupKFold, KFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVR
from sklearn.tree import DecisionTreeRegressor

RAIZ = Path(__file__).resolve().parent.parent
DIR_DATOS = RAIZ / "Datos_de_Pacientes"
DIR_SALIDA = Path(__file__).resolve().parent / "resultados"

FEATURES = ["amp_pulso", "t_cresta", "t_descnd", "pico_a_pico", "min_a_min"]
TARGETS = ["pas", "pad"]
SEMILLA = 42


# --------------------------------------------------------------------------
# Modelos
# --------------------------------------------------------------------------
def crear_modelo(nombre: str):
    """Devuelve un Pipeline(StandardScaler, modelo) nuevo, sin entrenar."""
    if nombre == "RF":
        modelo = RandomForestRegressor(
            n_estimators=100,
            criterion="squared_error",
            max_depth=None,
            min_samples_split=2,
            min_samples_leaf=1,
            max_features=1.0,
            bootstrap=True,
            random_state=SEMILLA,
            n_jobs=-1,  # solo paraleliza, no cambia el resultado
        )
    elif nombre == "SVR":
        modelo = SVR(kernel="rbf", C=100, epsilon=0.1, gamma="scale")
    elif nombre == "LR":
        modelo = LinearRegression(fit_intercept=True)
    elif nombre == "DT":
        modelo = DecisionTreeRegressor(random_state=SEMILLA)
    elif nombre == "MEDIA":
        modelo = DummyRegressor(strategy="mean")
    else:
        raise ValueError(f"Modelo desconocido: {nombre}")
    return make_pipeline(StandardScaler(), modelo)


MODELOS_DISPONIBLES = ["RF", "SVR", "LR", "DT", "MEDIA"]


# --------------------------------------------------------------------------
# Datos
# --------------------------------------------------------------------------
def latidos_validos(df: pd.DataFrame) -> pd.Series:
    """Latidos sin errores del firmware (Alpinista_MAX30102_HR_3.ino:324-327).
    Si el ESP32 no detecta un mínimo nuevo entre dos picos, min_a_min = 0 y la
    resta unsigned long de t_descnd se desborda a ~4 294 967 s (2^32 / 1000)."""
    return (df["min_a_min"] > 0) & (df["t_descnd"] < 1e5) & (df["amp_pulso"] > 0)


def cargar_pacientes(sin_duplicados: bool, filtrar_invalidos: bool = False) -> pd.DataFrame:
    """Une los CSV de todos los pacientes en un DataFrame con columnas
    paciente, sesion, FEATURES, pas, pad.

    Omite los CSV idénticos byte a byte a uno ya cargado (p. ej. el de
    Laura_Hening es una copia del de Julian_Murillo)."""
    import hashlib

    frames, vistos = [], {}
    for csv in sorted(DIR_DATOS.glob("Data_*/datos_procesados.csv")):
        nombre = csv.parent.name.replace("Data_", "")
        huella = hashlib.md5(csv.read_bytes()).hexdigest()
        if huella in vistos:
            print(f"AVISO: se omite {nombre}: su datos_procesados.csv es idéntico al de {vistos[huella]}")
            continue
        vistos[huella] = nombre
        df = pd.read_csv(csv)  # sin index_col: la 1ª columna es amp_pulso
        faltan = set(FEATURES + TARGETS) - set(df.columns)
        if faltan:
            raise ValueError(f"{csv} no tiene las columnas {faltan}")
        df = df[FEATURES + TARGETS].dropna()
        # Cada sesión (medicion_k) tiene un único par (pas, pad) de referencia.
        df["sesion"] = df.groupby(["pas", "pad"], sort=False).ngroup()
        if sin_duplicados:
            df = df.drop_duplicates()
        if filtrar_invalidos:
            df = df[latidos_validos(df)]
        df.insert(0, "paciente", nombre)
        frames.append(df)
    if not frames:
        raise FileNotFoundError(f"No hay datos_procesados.csv en {DIR_DATOS}")
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------
# Protocolos: devuelven predicciones out-of-fold para un paciente
# --------------------------------------------------------------------------
def oof_personalizado(df_pac: pd.DataFrame, modelo: str, target: str, splitter, groups=None):
    X = df_pac[FEATURES].to_numpy()
    y = df_pac[target].to_numpy()
    pred = np.empty_like(y, dtype=float)
    for tr, te in splitter.split(X, y, groups):
        m = crear_modelo(modelo).fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return y, pred, df_pac["sesion"].to_numpy()


def predecir(datos: pd.DataFrame, protocolo: str, modelo: str, target: str):
    """Itera por paciente y devuelve dict paciente -> (y_real, y_pred)."""
    salida = {}
    for paciente, df_pac in datos.groupby("paciente", sort=True):
        if protocolo == "kfold":
            kf = KFold(n_splits=5, shuffle=True, random_state=SEMILLA)
            salida[paciente] = oof_personalizado(df_pac, modelo, target, kf)
        elif protocolo == "sesion":
            n_ses = df_pac["sesion"].nunique()
            gkf = GroupKFold(n_splits=n_ses)
            salida[paciente] = oof_personalizado(
                df_pac, modelo, target, gkf, groups=df_pac["sesion"].to_numpy()
            )
        elif protocolo == "general":
            train = datos[datos["paciente"] != paciente]
            m = crear_modelo(modelo).fit(train[FEATURES].to_numpy(), train[target].to_numpy())
            salida[paciente] = (df_pac[target].to_numpy(), m.predict(df_pac[FEATURES].to_numpy()),
                                df_pac["sesion"].to_numpy())
        else:
            raise ValueError(protocolo)
    return salida


def agregar_por_sesion(salida):
    """Una predicción por sesión: mediana de las predicciones de sus latidos."""
    agregada = {}
    for paciente, (y, p, ses) in salida.items():
        df = pd.DataFrame({"y": y, "p": p, "s": ses}).groupby("s").agg(y=("y", "first"), p=("p", "median"))
        agregada[paciente] = (df["y"].to_numpy(), df["p"].to_numpy(), df.index.to_numpy())
    return agregada


# --------------------------------------------------------------------------
# Métricas
# --------------------------------------------------------------------------
def metricas(y, p):
    mse = mean_squared_error(y, p)
    return {
        "MAE": mean_absolute_error(y, p),
        "MSE": mse,
        "RMSE": float(np.sqrt(mse)),
        "R2": r2_score(y, p),
    }


def evaluar(datos, protocolos, modelos, nivel="latido"):
    filas_pac, filas_res, preds = [], [], {}
    for protocolo in protocolos:
        for modelo in modelos:
            t0 = time.time()
            for target in TARGETS:
                res = predecir(datos, protocolo, modelo, target)
                if nivel == "sesion":
                    res = agregar_por_sesion(res)
                preds[(protocolo, modelo, target)] = res
                por_pac = []
                for paciente, (y, p, _) in res.items():
                    m = metricas(y, p)
                    por_pac.append(m)
                    filas_pac.append({"protocolo": protocolo, "nivel": nivel, "modelo": modelo,
                                      "target": target.upper(), "paciente": paciente, **m})
                y_all = np.concatenate([v[0] for v in res.values()])
                p_all = np.concatenate([v[1] for v in res.values()])
                fila = {"protocolo": protocolo, "nivel": nivel, "modelo": modelo, "target": target.upper()}
                for k in ["MAE", "MSE", "RMSE", "R2"]:
                    vals = [d[k] for d in por_pac]
                    fila[f"{k}_media"] = np.mean(vals)
                    fila[f"{k}_std"] = np.std(vals)
                fila["R2_global"] = r2_score(y_all, p_all)
                filas_res.append(fila)
            print(f"  [{protocolo:7s}] {modelo:3s} listo en {time.time() - t0:5.1f} s")
    return pd.DataFrame(filas_pac), pd.DataFrame(filas_res), preds


def imprimir_tabla(resumen: pd.DataFrame):
    for protocolo, df_p in resumen.groupby("protocolo", sort=False):
        print(f"\n=== Protocolo: {protocolo}  (media ± desv. estándar entre pacientes) ===")
        print(f"{'Modelo':6s} {'Var':4s} {'MAE (mmHg)':>16s} {'MSE (mmHg²)':>18s} "
              f"{'RMSE (mmHg)':>16s} {'R² (pac.)':>14s} {'R² global':>10s}")
        for _, r in df_p.iterrows():
            print(f"{r.modelo:6s} {r.target:4s} "
                  f"{r.MAE_media:7.2f} ± {r.MAE_std:6.2f} "
                  f"{r.MSE_media:8.2f} ± {r.MSE_std:7.2f} "
                  f"{r.RMSE_media:7.2f} ± {r.RMSE_std:6.2f} "
                  f"{r.R2_media:6.2f} ± {r.R2_std:5.2f} "
                  f"{r.R2_global:10.2f}")


def graficar(preds, protocolos, modelos, carpeta: Path, sufijo: str = ""):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for protocolo in protocolos:
        fig, ejes = plt.subplots(len(TARGETS), len(modelos),
                                 figsize=(4 * len(modelos), 4 * len(TARGETS)), squeeze=False)
        for i, target in enumerate(TARGETS):
            for j, modelo in enumerate(modelos):
                ax = ejes[i][j]
                res = preds[(protocolo, modelo, target)]
                for paciente, (y, p, _) in res.items():
                    ax.scatter(y, p, s=6, alpha=0.3)
                y_all = np.concatenate([v[0] for v in res.values()])
                p_all = np.concatenate([v[1] for v in res.values()])
                lo, hi = y_all.min(), y_all.max()
                ax.plot([lo, hi], [lo, hi], "k--", lw=1)
                m = metricas(y_all, p_all)
                ax.set_title(f"{modelo} - {target.upper()}\nMAE={m['MAE']:.2f}  R²={m['R2']:.2f}",
                             fontsize=10)
                ax.set_xlabel("Real (mmHg)")
                ax.set_ylabel("Predicho (mmHg)")
                ax.grid(alpha=0.3)
        fig.suptitle(f"Real vs predicho - protocolo '{protocolo}'")
        fig.tight_layout()
        ruta = carpeta / f"dispersion_{protocolo}{sufijo}.png"
        fig.savefig(ruta, dpi=200)
        plt.close(fig)
        print(f"  Gráfica: {ruta}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--protocolo", choices=["kfold", "sesion", "general", "todos"], default="todos")
    ap.add_argument("--modelos", nargs="+", choices=MODELOS_DISPONIBLES, default=["RF", "SVR", "LR"])
    ap.add_argument("--sin-duplicados", action="store_true",
                    help="Elimina filas idénticas dentro de cada paciente antes de evaluar")
    ap.add_argument("--filtrar-invalidos", action="store_true",
                    help="Descarta latidos con errores del firmware (min_a_min=0, t_descnd desbordado, amp<=0)")
    ap.add_argument("--nivel", choices=["latido", "sesion"], default="latido",
                    help="latido: una predicción por fila; sesion: mediana por medición")
    ap.add_argument("--graficas", action="store_true", help="Guarda gráficas real vs predicho")
    args = ap.parse_args()

    protocolos = ["kfold", "sesion", "general"] if args.protocolo == "todos" else [args.protocolo]

    datos = cargar_pacientes(args.sin_duplicados, args.filtrar_invalidos)
    print(f"Pacientes: {datos.paciente.nunique()}  |  filas: {len(datos)}  |  "
          f"filas únicas: {len(datos.drop_duplicates())}  |  sin_duplicados={args.sin_duplicados}  |  "
          f"filtrar_invalidos={args.filtrar_invalidos}")

    if args.nivel == "sesion" and "kfold" in protocolos:
        print("Aviso: con --nivel sesion el protocolo kfold no tiene sentido (mezcla sesiones); se omite.")
        protocolos = [p for p in protocolos if p != "kfold"]

    por_paciente, resumen, preds = evaluar(datos, protocolos, args.modelos, args.nivel)
    imprimir_tabla(resumen)

    DIR_SALIDA.mkdir(exist_ok=True)
    sufijo = (("_sin_duplicados" if args.sin_duplicados else "")
              + ("_validos" if args.filtrar_invalidos else "")
              + ("_nivel_sesion" if args.nivel == "sesion" else ""))
    por_paciente.to_csv(DIR_SALIDA / f"metricas_por_paciente{sufijo}.csv", index=False)
    resumen.to_csv(DIR_SALIDA / f"metricas_resumen{sufijo}.csv", index=False)
    print(f"\nCSV guardados en {DIR_SALIDA}")
    if args.graficas:
        graficar(preds, protocolos, args.modelos, DIR_SALIDA, sufijo)


if __name__ == "__main__":
    main()
