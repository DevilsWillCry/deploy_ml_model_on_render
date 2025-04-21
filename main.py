from fastapi import FastAPI
import pandas as pd 

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