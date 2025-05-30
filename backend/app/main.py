from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config.firebase import initialize_firebase
from .routers import health, model, metrics

app = FastAPI()

# Configuración CORS
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://vitapressure.vercel.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar Firebase
initialize_firebase()

# Incluir routers
app.include_router(health.router)
app.include_router(model.router)
app.include_router(metrics.router)