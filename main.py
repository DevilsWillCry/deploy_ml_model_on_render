from fastapi import FastAPI
import pandas as pd
import numpy as np
import firebase_admin
from firebase_admin import credentials, initialize_app, db
import os
import json

from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error

import joblib

# Inicialización de variables
credentialsFirebase = {}
data = {}
firebase_json = os.getenv("FIREBASE_CREDENTIALS")

X = []
y_pas = []
y_pad = []
window_size = 20  # tamaño de la ventana

amp_pulso = []
t_cresta = []
t_descnd = []
pico_a_pico = []
min_a_min = []
area_pulso = []
value_max = []

pas = []
pad = []

# Cargar credenciales de Firebase
if firebase_json:
    print("✅ Variable cargada correctamente")
    try:
        credentialsFirebase = json.loads(firebase_json)
        credentialsFirebase["private_key"] = credentialsFirebase.get("private_key").replace("\\n", "\n")
        print("🔐 Contenido válido del JSON:")
        print("Proyecto:", credentialsFirebase.get("project_id"))
        print("Email:", credentialsFirebase.get("client_email"))
    except Exception as e:
        print("❌ Error al decodificar el JSON:", str(e))
else:
    print("⚠️ Variable de entorno no encontrada, intentando cargar archivo local...")
    try:
        with open("credentials-esp32.json") as f:
            credentialsFirebase = json.load(f)
            credentialsFirebase["private_key"] = credentialsFirebase.get("private_key").replace("\\n", "\n")
            print("✅ Archivo local cargado correctamente")
    except FileNotFoundError:
        print("❌ Archivo 'credentials-esp32.json' no encontrado")

# Inicializar Firebase si no está inicializado
if credentialsFirebase and not firebase_admin._apps:
    cred = credentials.Certificate(credentialsFirebase)
    initialize_app(cred, {
        'databaseURL': 'https://esp32-thesis-project-default-rtdb.firebaseio.com/'
    })
    ref = db.reference("/sensor/data")
    data = ref.get()


app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Servidor Funcionando ✅"}

@app.get("/create_csv")
def create_csv():
    datos = {
        "nombre": ["John", "Jane", "Bob"],
        "edad": [25, 30, 35],
        "ciudad": ["New York", "London", "Paris"]
    }
    df = pd.DataFrame(datos)
    df.to_csv("usuarios.csv", index=False)
    return {"message": "CSV creado con éxito"}

@app.get("/ver_csv")
def ver_csv():
    try:
        df = pd.read_csv("usuarios.csv")
        return df.to_dict(orient="records")
    except FileNotFoundError:
        return {"error": "El archivo CSV no existe"}

@app.get("/eliminar_csv")
def eliminar_csv():
    try:
        os.remove("usuarios.csv")
        return {"message": "CSV eliminado con éxito"}
    except FileNotFoundError:
        return {"error": "El archivo CSV no existe"}

def max_length(data):
    if data:
        max_length = 0
        for key, value in data.items():
            for _, subvalue in value.items():
                if isinstance(subvalue, list):
                    if len(subvalue) > max_length:
                        max_length = len(subvalue)
        return max_length


@app.get("/training_model")
def get_data():
    max_len = max_length(data)
    print(max_len)
    if data:
        for key, value in data.items():
            amp_pulso.extend(data[key]["amp_pulso"] + [np.nan] * (max_len - len(data[key]["amp_pulso"])))
            area_pulso.extend(data[key]["area_pulso"] + [np.nan] * (max_len - len(data[key]["area_pulso"])))
            t_cresta.extend(data[key]["t_cresta"] + [np.nan] * (max_len - len(data[key]["t_cresta"])))
            t_descnd.extend(data[key]["t_descnd"] + [np.nan] * (max_len - len(data[key]["t_descnd"])))
            pico_a_pico.extend(data[key]["pico_a_pico"] + [np.nan] * (max_len - len(data[key]["pico_a_pico"])))
            min_a_min.extend(data[key]["min_a_min"] + [np.nan] * (max_len - len(data[key]["min_a_min"])))
            value_max.extend(data[key]["value_max"] + [np.nan] * (max_len - len(data[key]["value_max"])))

            #Repetir para PAS y PAD para cada medición
            pas.extend([data[key]["pas"]] * max_len)
            pad.extend([data[key]["pad"]] * max_len)

        df = pd.DataFrame({
            "amp_pulso": amp_pulso,
            "area_pulso": area_pulso,
            "t_cresta": t_cresta,
            "t_descnd": t_descnd,
            "pico_a_pico": pico_a_pico,
            "min_a_min": min_a_min,
            "value_max": value_max,
            "pas": pas,
            "pad": pad
        })
        #Eliminar filas con valores nulos
        df = df.dropna()
        print(df)
        # Ver si hay valores atípicos utilizando el rango intercuartílico        
        """
        """
        Q1 = df.quantile(0.25)
        Q3 = df.quantile(0.75)
        IQR = Q3 - Q1
        df = df[~((df < (Q1 - 1.5 * IQR)) | (df > (Q3 + 1.5 * IQR))).any(axis=1)]

        print(df)
        
        # Escalar los datos
        scaler = StandardScaler()
        # Escalar todas las columnas excepto "pas" y "pad"
        columns_to_scale = df.columns.difference(["pas", "pad"])
        # Escalar todas las columnas excepto "pas" y "pad" usando StandardScaler
        df_scaled = df.copy()
        df_scaled[columns_to_scale] = scaler.fit_transform(df[columns_to_scale])
        
        # Dividir los datos en conjuntos de entrenamiento y prueba
        """
        X = df_scaled.drop(columns=["pas", "pad"], axis=1)
        y = df_scaled[["pas", "pad"]]
        """
        X = df.drop(columns=["pas", "pad"], axis=1)
        y = df[["pas", "pad"]]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Entrenar el modelo
        model = LinearRegression()
        model.fit(X_train, y_train)

        #Realizar predicciones
        y_pred = model.predict(X_test)
        
        print(df)
        print(df_scaled)
        # Ver las predicciones
        #print(y_pred)

        # Guardar el modelo
        joblib.dump(model, 'model4.joblib')
        # Guardar el scaler también
        joblib.dump(scaler, 'scaler4.joblib')

        return {"message": "Modelo entrenado y guardado con éxito"}

        # Cargar el modelo
        #model = joblib.load('model.joblib')

        # Evaluamos el modelo utilizando MAE
        mae = mean_absolute_error(y_test, y_pred)
        print(f'Mean Absolute Error: {mae}')


        # Nuevos datos (deben tener las mismas columnas que X_train, sin 'pas' ni 'pad')
        # amp_pulso, area_pulso, t_cresta, t_descnd, pico_a_pico, min_a_min, value_max

        # Nuevos datos con variaciones más agresivas (Ejemplo de variabilidad extrema en las características)
        """
        new_data_aggressive = [
            [10000.0, 1300.0, 0.200, 6.500, 6.000, 9.000, -1853200.0],  # Primer conjunto de datos con valores extremos
            [15000.0, 1700.0, 0.250, 7.000, 6.500, 9.500, -1852900.0],  # Segundo conjunto con variaciones grandes
            [11000.0, 1250.0, 0.100, 6.000, 6.200, 8.800, -1853100.0],  # Tercer conjunto con valores fuera del rango normal
            [14000.0, 1800.0, 0.300, 7.200, 6.800, 9.300, -1852800.0],  # Cuarto conjunto con variaciones notables
        ]

        # Escalar los nuevos datos utilizando el mismo escalador
        new_data_aggressive_scaled = scaler.transform(new_data_aggressive)

        # Hacer las predicciones con los nuevos datos
        new_pred_aggressive = model.predict(new_data_aggressive_scaled)

        # Mostrar las predicciones para PAS y PAD con los datos más agresivos
        print(f"Predicciones para PAS y PAD (con datos agresivos): {new_pred_aggressive}")
        """

    else:
        return {"error": "No se encontraron datos"}
    

@app.get("/predict")
def predict():
    # Cargar el modelo
    model = joblib.load('model2_no_escalada_quartil.joblib')
    scaler = joblib.load('scaler.joblib')

    # Hacer petición a Firebase al documento sensor/data_to_predict
    ref = db.reference("/sensor/data_to_predict")
    data = ref.get()

    # Obtener las variables
    amp_pulso = data["amp_pulso"]
    area_pulso = data["area_pulso"]
    t_cresta = data["t_cresta"]
    t_descnd = data["t_descnd"]
    pico_a_pico = data["pico_a_pico"]
    min_a_min = data["min_a_min"]
    value_max = data["value_max"]

    # Preparar los datos
    new_data = [[amp_pulso, area_pulso, t_cresta, t_descnd, pico_a_pico, min_a_min, value_max]]    
    new_data_scaled = scaler.transform(new_data)

    # Hacer predicciones.
    prediction = model.predict(new_data)

    # Mostrar las predicciones
    print(f"Predicciones para PAS y PAD: {prediction}")

    return {"prediction": [prediction[0][0], prediction[0][1]] }
    
    """


    # Hacer la predicción   
    new_pred = model.predict(new_data_scaled)

    # Mostrar las predicciones
    print(f"Predicciones para PAS y PAD: {new_pred}")


    # amp_pulso, area_pulso, t_cresta, t_descnd, pico_a_pico, min_a_min, value_max
    """
