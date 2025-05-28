from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

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

import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

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


IS_RENDER = os.path.exists("/etc/secrets/credentials_cloudinary")
# Cargar variables desde el archivo correspondiente
if IS_RENDER:
    load_dotenv("/etc/secrets/credentials_cloudinary")
else:
    load_dotenv()  # Carga .env local

# Configurar Cloudinary (esto va para ambos casos)
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)

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

origins = ["http://localhost:5173", "http://127.0.0.1:5173", "https://vitapressure.vercel.app"]

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


def normalizar_datos(data):
    
    # If data is not a list convert it to one
    for(key, value) in data.items():
        for (subkey, subvalue) in value.items():
            if not isinstance(subvalue, list) and subkey != "pad" and subkey != "pas":
                subvalue = list(subvalue.values())
                # Check if subvalue have no none values and not take it
                for i in range(len(subvalue)):
                    if subvalue[i] is None:
                        #delete the value
                        subvalue.remove(subvalue[i])
                data[key][subkey] = subvalue
    return data
            

@app.get("/training_model")
def get_data():
    # Confirm if data is not empty and firebase is connected
    if not data:
        return {"message": "No hay datos"}

    if not firebase_admin._apps:
        return {"message": "Firebase no conectado"}

    ref = db.reference("/sensor/data")
    data = ref.get()

    newData = normalizar_datos(data)
    
    if not newData:
        return {"message": "No hay datos"}

    lista_dfs = []

    for key, valores in newData.items():
        # Calcular la longitud mínima entre las listas
        lengths = [
            len(valores["amp_pulso"]),
            len(valores["t_cresta"]),
            len(valores["t_descnd"]),
            len(valores["pico_a_pico"]),
            len(valores["min_a_min"])
        ]
        min_len = min(lengths)

        # Crear DataFrame truncando todas las listas al mismo tamaño
        df_temp = pd.DataFrame({
            "amp_pulso": valores["amp_pulso"][:min_len],
            "t_cresta": valores["t_cresta"][:min_len],
            "t_descnd": valores["t_descnd"][:min_len],
            "pico_a_pico": valores["pico_a_pico"][:min_len],
            "min_a_min": valores["min_a_min"][:min_len]
        })

        # Repetir pas y pad para cada fila
        df_temp["pas"] = [valores["pas"]] * min_len
        df_temp["pad"] = [valores["pad"]] * min_len

        lista_dfs.append(df_temp)

    # Concatenar todos los DataFrames
    df = pd.concat(lista_dfs, ignore_index=True)

    # Eliminar filas con datos incompletos
    df = df.dropna()

    df.to_csv("datos_procesados.csv", index=False)

    # Eliminar outliers con IQR
    '''
    Q1 = df.quantile(0.25)
    Q3 = df.quantile(0.75)
    IQR = Q3 - Q1
    df = df[~((df < (Q1 - 1.5 * IQR)) | (df > (Q3 + 1.5 * IQR))).any(axis=1)]
    '''

    X = df.drop(columns=["pas", "pad"], axis=1)
    y_pas = df["pas"]
    y_pad = df["pad"]

    # Escalar los datos
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Dividir los datos en conjuntos de entrenamiento y prueba PAS
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y_pas, test_size=0.2, random_state=42)

    # Dividir los datos en conjuntos de entrenamiento y prueba PAD
    X_train_pad, X_test_pad, y_train_pad, y_test_pad = train_test_split(X_scaled, y_pad, test_size=0.2, random_state=42)

    # Training RandomForest Regressor for PAS
    model_pas = RandomForestRegressor(n_estimators=100, random_state=42)
    model_pas.fit(X_train, y_train)

    # Training RandomForest Regressor for PAD
    model_pad = RandomForestRegressor(n_estimators=100, random_state=42)
    model_pad.fit(X_train_pad, y_train_pad)

    # Realizar predicciones
    y_pred = model_pas.predict(X_test)
    y_pred_pad = model_pad.predict(X_test_pad)

    #Realizar predicciones sobre los datos y_train
    y_train_pred = model_pas.predict(X_train)
    y_train_pad_pred = model_pad.predict(X_train_pad)


    #Save metrics in a JSON file
    metrics_pas = {
        "MAE": mean_absolute_error(y_test, y_pred),
        "MSE": mean_squared_error(y_test, y_pred),
        "R2": r2_score(y_test, y_pred)
    }
    with open("metrics_pas.json", "w") as f:
        json.dump(metrics_pas, f)

    # Save metrics in JSON file to PAD
    metrics_pad = {
        "MAE": mean_absolute_error(y_test_pad, y_pred_pad),
        "MSE": mean_squared_error(y_test_pad, y_pred_pad),
        "R2": r2_score(y_test_pad, y_pred_pad)
    }
    with open("metrics_pad.json", "w") as f:
        json.dump(metrics_pad, f)

    # Graficar PAS
    plt.figure(figsize=(12, 5))

    plt.subplot(1, 1, 1)
    plt.scatter(y_test, y_pred, alpha=0.5, color='blue')
    plt.plot([y_test.min(), y_test.max()], [y_test.min(), y_test.max()], 'r--')  # línea ideal
    plt.xlabel("PAS Real")
    plt.ylabel("PAS Predicho")
    plt.title("Dispersión PAS: Real vs Predicho")
    plt.savefig('dispersion_prueba_pas.png')
    plt.close()


    # Graficar PAS entrenamiento
    plt.figure(figsize=(8, 6))
    plt.scatter(y_train, y_train_pred, alpha=0.5, color='green')
    plt.plot([y_train.min(), y_train.max()], [y_train.min(), y_train.max()], 'r--')
    plt.xlabel("PAS Real (entrenamiento)")
    plt.ylabel("PAS Predicho (entrenamiento)")
    plt.title("Dispersión PAS: Entrenamiento vs Predicción")
    #plt.savefig("dispersión_entrenamiento_pas.png", dpi=300, bbox_inches='tight')
    #plt.close()


    # Graficar PAD
    plt.figure(figsize=(12, 5))

    plt.subplot(1, 1, 1)
    plt.scatter(y_test_pad, y_pred_pad, alpha=0.5, color='blue')
    plt.plot([y_test_pad.min(), y_test_pad.max()], [y_test_pad.min(), y_test_pad.max()], 'r--')  # linea ideal
    plt.xlabel("PAD Real")
    plt.ylabel("PAD Predicho")
    plt.title("Dispersión PAD: Real vs Predicho")
    plt.savefig('dispersion_prueba_pad.png')
    plt.close()


    joblib.dump(model_pas, 'model_pas.joblib')
    joblib.dump(model_pad, 'model_pad.joblib')

    joblib.dump(scaler, 'scaler.joblib')


    #Send metrics to Firebase
    ref = db.reference("/sensor/model_is_trained")
    ref.set(True)

    return {"message": "Modelo entrenado y guardado con éxito"}

@app.get("/predict")
def predict():
    # Cargar el modelo
    model_pas = joblib.load('model_pas.joblib')
    model_pad = joblib.load('model_pad.joblib')


    # Cargar el scaler
    scaler = joblib.load('scaler.joblib')
    
    # Leer datos de Firebase
    ref = db.reference("/sensor/data_to_predict")
    data = ref.get()

    # Variables esperadas por el modelo (en orden)
    columnas = ["amp_pulso", "t_cresta", "t_descnd", "pico_a_pico", "min_a_min"]

    # Crear DataFrame con nombres de columnas
    new_data = pd.DataFrame([[data[col] for col in columnas]], columns=columnas)

    # Escalar los datos
    new_data_scaled = scaler.transform(new_data)

    # Hacer predicción
    prediction_pas = model_pas.predict(new_data_scaled)

    prediction_pad = model_pad.predict(new_data_scaled)

    print(f"Predicciones para PAS y PAD: {prediction_pas}, {prediction_pad}")

    # return {"prediction": [float(prediction[0][0]), float(prediction[0][1])] }

    return {"prediction": [float(prediction_pas), float(prediction_pad)]}


@app.get("/metrics")
def metrics():
    #Show Metrics open a JSONFile called metrics_pas.json and metrics_pad.json
    with open('metrics_pas.json', 'r') as f:
        metrics_pas = json.load(f)

    with open('metrics_pad.json', 'r') as f:
        metrics_pad = json.load(f)

    promedio = ((metrics_pas["R2"] + metrics_pad["R2"]) / 2) * 100

    print(promedio)

    return {"result": promedio}


@app.get("/show-graphs")
def show_graphs():
    upload_pas = cloudinary.uploader.upload("dispersion_prueba_pas.png")
    upload_pad = cloudinary.uploader.upload("dispersion_prueba_pad.png")

    return {"pas": upload_pas["url"], "pad": upload_pad["url"]}
    
    
    