from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import pandas as pd
import numpy as np
import firebase_admin
from firebase_admin import credentials, initialize_app, db
import os
import json

from sklearn.preprocessing import StandardScaler

from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.tree import DecisionTreeRegressor


from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
from sklearn.metrics import mean_squared_error
from sklearn.metrics import r2_score

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

origins = ["http://localhost:5173", "http://127.0.0.1:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Servidor Funcionando ✅"}

def max_length(data):
    #/*************  ✨ Windsurf Command ⭐  *************#
    """
    Returns the maximum length of the lists in the given data
    if data is not empty.

    Args:
        data (dict): a dictionary with lists as values

    Returns:
        int: the maximum length of the lists in the dictionary
    """
    #*******  f8a2129a-65dd-4d18-9996-7bed9180ec2b  *******#
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
        Q1 = df.quantile(0.25)
        Q3 = df.quantile(0.75)
        IQR = Q3 - Q1
        df = df[~((df < (Q1 - 1.5 * IQR)) | (df > (Q3 + 1.5 * IQR))).any(axis=1)]
        

        X = df.drop(columns=["pas", "pad"], axis=1)
        y = df[["pas", "pad"]]

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Entrenar el modelo
        model = DecisionTreeRegressor(random_state=42)
        model.fit(X_train, y_train)

        #Realizar predicciones
        y_pred = model.predict(X_test)
        
        # Ver las predicciones
        #print(y_pred)

        # Evaluamos el modelo utilizando MAE
        mae = mean_absolute_error(y_test, y_pred)
        print(f'Mean Absolute Error: {mae}')

        # Evaluamos el modelo utilizando MSE
        mse = mean_squared_error(y_test, y_pred)
        print(f'Mean Squared Error: {mse}')

        # Evaluamos el modelo utilizando R2
        r2 = r2_score(y_test, y_pred)
        print(f'R2: {r2}')

        # Guardar el modelo
        joblib.dump(model, 'model4.joblib')

        return {"message": "Modelo entrenado y guardado con éxito"}


        """

        # Escalar los datos
        scaler = StandardScaler()

        # Escalar todas las columnas excepto "pas" y "pad"
        columns_to_scale = df.columns.difference(["pas", "pad"])

        # Escalar todas las columnas excepto "pas" y "pad" usando StandardScaler
        df_scaled = df.copy()
        df_scaled[columns_to_scale] = scaler.fit_transform(df[columns_to_scale])
        
        # Dividir los datos en conjuntos de entrenamiento y prueba
        
        X = df_scaled.drop(columns=["pas", "pad"], axis=1)
        y = df_scaled[["pas", "pad"]]

        # Guardar el scaler también
        joblib.dump(scaler, 'scaler4.joblib')
        """

    else:
        return {"error": "No se encontraron datos"}
    

@app.get("/predict")
def predict():
    # Cargar el modelo
    model = joblib.load('model4.joblib')
    
    """
    scaler = joblib.load('scaler.joblib')
    new_data_scaled = scaler.transform(new_data)
    """

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

    # Hacer predicciones.
    prediction = model.predict(new_data)

    # Mostrar las predicciones
    print(f"Predicciones para PAS y PAD: {prediction}")

    return {"prediction": [prediction[0][0], prediction[0][1]] }
