"""
Prueba 1 - Inspección de los modelos y datos guardados (solo lectura).

Responde a:
  * ¿Qué hiperparámetros tienen realmente los Random Forest entrenados?
    (se leen de Datos_de_Pacientes/*/model_pas.joblib y model_pad.joblib)
  * ¿Qué tamaño alcanzaron los árboles? (profundidad, hojas, nodos)
  * ¿Cuántas filas únicas y cuántas sesiones tiene cada paciente?

Uso (desde la raíz del proyecto):
    python PRUEBAS/experimentos/01_inspeccionar_modelos_guardados.py
"""

from pathlib import Path
import hashlib
import warnings

import joblib
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")  # avisos de versión al cargar los .joblib

RAIZ = Path(__file__).resolve().parents[2]
DIR_DATOS = RAIZ / "Datos_de_Pacientes"
PARAMS = ["n_estimators", "criterion", "max_depth", "min_samples_split", "min_samples_leaf",
          "max_features", "bootstrap", "max_samples", "max_leaf_nodes",
          "min_impurity_decrease", "random_state"]


def main():
    print("=== Hiperparámetros y tamaño de los árboles por modelo guardado ===")
    profundidades, hojas, nodos, configs = [], [], [], set()
    for f in sorted(DIR_DATOS.glob("Data_*/model_pa*.joblib")):
        m = joblib.load(f)
        p = m.get_params()
        configs.add(tuple((k, p[k]) for k in PARAMS))
        d = [e.get_depth() for e in m.estimators_]
        h = [e.get_n_leaves() for e in m.estimators_]
        n = [e.tree_.node_count for e in m.estimators_]
        profundidades += d; hojas += h; nodos += n
        print(f"{f.parent.name.replace('Data_', ''):20s} {f.stem:10s} {type(m).__name__}  "
              f"profundidad {min(d)}-{max(d)} (media {np.mean(d):.1f})  "
              f"hojas media {np.mean(h):.1f}  nodos media {np.mean(n):.1f}")

    print("\nConfiguraciones distintas encontradas:", len(configs))
    for c in configs:
        for k, v in c:
            print(f"  {k:24s} = {v}")

    print(f"\nTotal de árboles: {len(profundidades)}")
    for nombre, a in [("Profundidad", profundidades), ("Hojas", hojas), ("Nodos", nodos)]:
        a = np.array(a)
        print(f"  {nombre:12s} min {a.min():4d}  max {a.max():4d}  media {a.mean():6.1f}  mediana {np.median(a):5.1f}")

    print("\n=== Estructura de los datos por paciente ===")
    huellas = {}
    for f in sorted(DIR_DATOS.glob("Data_*/datos_procesados.csv")):
        h = hashlib.md5(f.read_bytes()).hexdigest()
        if h in huellas:
            print(f"!! {f.parent.name}: datos_procesados.csv IDÉNTICO al de {huellas[h]}")
        huellas.setdefault(h, f.parent.name)
        d = pd.read_csv(f)
        u = d.drop_duplicates()
        invalidos = ((u.min_a_min <= 0) | (u.t_descnd >= 1e5) | (u.amp_pulso <= 0)).sum()
        print(f"{f.parent.name.replace('Data_', ''):20s} filas {len(d):5d}  "
              f"filas únicas {len(u):4d}  inválidas (firmware) {invalidos:3d}  "
              f"sesiones (pares PAS/PAD) {len(d[['pas', 'pad']].drop_duplicates())}  "
              f"PAS {sorted(int(v) for v in d.pas.unique())}  PAD {sorted(int(v) for v in d.pad.unique())}")


if __name__ == "__main__":
    main()
