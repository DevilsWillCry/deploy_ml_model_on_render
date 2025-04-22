from fastapi import FastAPI
import pandas as pd 
import firebase_admin
import os
import json
from firebase_admin import credentials, initialize_app, db




# Credenciales de Firebase, comprobación en el servidor de Render.
# Inicialización de la app de Firebase (solo una vez)
credentialsFirebase = {}
data = {}
firebase_json = os.getenv("FIREBASE_CREDENTIALS")

if firebase_json:
    print("✅ Variable cargada correctamente")
    try:
        credentialsFirebase = json.loads(firebase_json)
        credentialsFirebase["private_key"] = credentialsFirebase.get("private_key").replace("\\n", "\n")
        print("🔐 Contenido válido del JSON:")
        print("Proyecto:", credentialsFirebase.get("project_id"))
        print("Email:", credentialsFirebase.get("client_email"))
    except:
        print("❌ Error al decodificar el JSON")
else:
    print("❌ Variable de entorno no encontrada")



if not firebase_admin._apps:
    
    cred = credentials.Certificate(credentialsFirebase)
    initialize_app(cred, {
        'databaseURL': 'https://esp32-thesis-project-default-rtdb.firebaseio.com/'
    })
    ref = db.reference("/sensor")
    data = ref.get()

if data != {}:
    print("✅ Datos cargados correctamente")
    print(type(data))
    print(data)

app = FastAPI()

@app.get("/")
def read_root():
    return {"message":"Servidor Funcionando✅"}



@app.get("/create_csv")
def create_csv():
    datos = {
        "nombre": ["John", "Jane", "Bob"],
        "edad": [25, 30, 35],
        "ciudad": ["New York", "London", "Paris"]
    }

    df = pd.DataFrame(datos)
    df.to_csv("usuarios.csv", index=False)
    return {"message": "CSV creado con éxito"}



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
        return {"message": "CSV eliminado con éxito"}
    except FileNotFoundError:
        return {"error": "El archivo CSV no existe"}


#Vamos hacer una petición a la base datos a realtime DB firebase
