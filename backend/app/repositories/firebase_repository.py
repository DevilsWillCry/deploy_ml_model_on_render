import json
import logging
from typing import Dict, Optional, List
import firebase_admin
from firebase_admin import credentials, db, exceptions
from ..config.settings import settings
from ..utils.data_processing import normalize_data

class FirebaseRepository:
    def __init__(self):
        self._initialize_firebase()
        self.logger = logging.getLogger(__name__)

    def _initialize_firebase(self) -> None:
        """Inicializa la conexión con Firebase solo si no existe"""
        if firebase_admin._apps:
            return

        try:
            creds = self._load_credentials()
            if creds:
                firebase_admin.initialize_app(
                    creds,
                    {'databaseURL': 'https://esp32-thesis-project-default-rtdb.firebaseio.com/'}
                )
        except Exception as e:
            self.logger.error(f"Error inicializando Firebase: {str(e)}")
            raise

    def _load_credentials(self) -> Optional[credentials.Certificate]:
        """Carga las credenciales desde variables de entorno o archivo"""
        try:
            if settings.FIREBASE_CREDENTIALS:
                creds_dict = json.loads(settings.FIREBASE_CREDENTIALS)
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
                return credentials.Certificate(creds_dict)
            
            with open("credentials-esp32.json") as f:
                return credentials.Certificate(json.load(f))
                
        except json.JSONDecodeError as e:
            self.logger.error(f"Error decodificando credenciales: {str(e)}")
            raise ValueError("Formato inválido para credenciales Firebase")
        except FileNotFoundError:
            self.logger.error("Archivo de credenciales no encontrado")
            raise
        except Exception as e:
            self.logger.error(f"Error inesperado cargando credenciales: {str(e)}")
            raise

    def get_training_data(self) -> Dict:
        """Obtiene datos crudos para entrenamiento desde Firebase"""
        try:
            ref = db.reference("/sensor/data")
            data = ref.get()
            return normalize_data(data) if data else {}
        except exceptions.FirebaseError as e:
            self.logger.error(f"Error obteniendo datos de entrenamiento: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error inesperado: {str(e)}")
            raise

    def get_prediction_data(self) -> Dict:
        """Obtiene datos para predicción en tiempo real"""
        try:
            ref = db.reference("/sensor/data_to_predict")
            data = ref.get()
            if not data:
                raise ValueError("No hay datos disponibles para predicción")
            return data
        except exceptions.FirebaseError as e:
            self.logger.error(f"Error obteniendo datos para predicción: {str(e)}")
            raise
        except ValueError as e:
            self.logger.warning(str(e))
            raise

    def save_metrics(self, metrics: Dict[str, float]) -> None:
        """Guarda métricas del modelo en Firebase"""
        try:
            ref = db.reference("/sensor/metrics")
            ref.set(metrics)
        except exceptions.FirebaseError as e:
            self.logger.error(f"Error guardando métricas: {str(e)}")
            raise

    def update_model_status(self, status: bool) -> None:
        """Actualiza el estado del modelo en Firebase"""
        try:
            ref = db.reference("/sensor/model_is_trained")
            ref.set(status)
        except exceptions.FirebaseError as e:
            self.logger.error(f"Error actualizando estado del modelo: {str(e)}")
            raise
    # Verificar conexión a Firebase
    def check_connection(self) -> bool:
        try:
            db.reference("/sensor/data").get()
            return True
        except exceptions.FirebaseError:
            return False