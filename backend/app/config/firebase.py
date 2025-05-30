import firebase_admin
from firebase_admin import credentials, db
import json
import os
from ..config.settings import settings

def initialize_firebase():
    if not firebase_admin._apps:
        creds = None
        if settings.FIREBASE_CREDENTIALS:
            creds = json.loads(settings.FIREBASE_CREDENTIALS)
            creds["private_key"] = creds.get("private_key").replace("\\n", "\n")
            print("✅ Variable cargada correctamente")
        else:
            with open("credentials-esp32.json") as f:
                creds = json.load(f)
                creds["private_key"] = creds.get("private_key").replace("\\n", "\n")
                print("✅ Archivo local cargado correctamente")
        if creds:
            cred = credentials.Certificate(creds)
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://esp32-thesis-project-default-rtdb.firebaseio.com/'
            })