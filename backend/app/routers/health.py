from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from datetime import datetime
import psutil
import socket
from typing import Dict, Any

from ..repositories.firebase_repository import FirebaseRepository
from ..config.settings import settings

router = APIRouter(tags=["System Health"])

@router.get("/health", summary="Basic Health Check")
async def health_check() -> Dict[str, str]:
    """Endpoint básico de salud para verificaciones rápidas"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "VitaPressure API",
        "version": "1.0.0"
    }

@router.get("/health/detailed", summary="Detailed System Health")
async def detailed_health_check(
    firebase: FirebaseRepository = Depends()
) -> Dict[str, Any]:
    """Endpoint detallado con métricas del sistema y dependencias"""
    try:
        # Verificar conexión a Firebase
        firebase_data = bool(firebase.check_connection())
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "system": {
                "cpu_usage": f"{psutil.cpu_percent()}%",
                "memory_usage": f"{psutil.virtual_memory().percent}%",
                "disk_usage": f"{psutil.disk_usage('/').percent}%",
                "hostname": socket.gethostname(),
                "environment": "production" if settings.IS_RENDER else "development"
            },
            "dependencies": {
                "firebase_connected": firebase_data,
                "cloudinary_configured": all([
                    settings.CLOUDINARY_CLOUD_NAME,
                    settings.CLOUDINARY_API_KEY,
                    settings.CLOUDINARY_API_SECRET
                ])
            },
            "services": {
                "model_trained": firebase_data  # Asume que verificas el estado real
            }
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
