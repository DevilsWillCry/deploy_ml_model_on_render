import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.utils.validation import check_is_fitted
from sklearn.exceptions import NotFittedError
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from typing import Dict, List, Optional, Tuple
import json
from ..utils.data_processing import add_gaussian_noise
import os
from sklearn.model_selection import KFold

from ..repositories.firebase_repository import FirebaseRepository
class ModelService:
    def __init__(self):
        self.scaler = StandardScaler()
        self.model_pas = RandomForestRegressor(n_estimators=100, random_state=42)
        self.model_pad = RandomForestRegressor(n_estimators=100, random_state=42)
        self.models_dir = "models"
        os.makedirs(self.models_dir, exist_ok=True)
        self._load_models() # Intenta cargar modelos existentes al iniciar
        self.evaluation_data = {}

    def _load_models(self):
        """Carga modelos pre-entrenados verificando su estado"""
        try:
            if all(os.path.exists(os.path.join(self.models_dir, f)) 
                  for f in ["scaler.joblib", "model_pas.joblib", "model_pad.joblib"]):
                
                self.scaler = joblib.load(os.path.join(self.models_dir, "scaler.joblib"))
                self.model_pas = joblib.load(os.path.join(self.models_dir, "model_pas.joblib"))
                self.model_pad = joblib.load(os.path.join(self.models_dir, "model_pad.joblib"))
                
                # Verificar que están entrenados
                self._verify_models()
                
        except Exception as e:
            print(f"Advertencia: {str(e)} - Se usarán nuevos modelos")
            self._initialize_new_models()

    def _verify_models(self):
        """Verifica que los modelos estén correctamente entrenados"""
        try:
            check_is_fitted(self.model_pas)
            check_is_fitted(self.model_pad)
            if not hasattr(self.scaler, 'mean_'):
                raise NotFittedError("Scaler no está ajustado")
        except NotFittedError:
            raise ValueError("Modelos cargados pero no entrenados")
    
    def _initialize_new_models(self):
        """Reinicializa modelos nuevos"""
        self.scaler = StandardScaler()
        self.model_pas = RandomForestRegressor(n_estimators=100, random_state=42)
        self.model_pad = RandomForestRegressor(n_estimators=100, random_state=42)
    
    def is_trained(self) -> bool:
        """Verifica si los modelos están listos para predecir"""
        try:
            self._verify_models()
            return True
        except:
            return False

    def train_models(self, df: pd.DataFrame):
        kf = KFold(n_splits=5, shuffle=True, random_state=42)

        # Separación de variables
        X = df.drop(columns=["pas", "pad"], axis=1)
        y_pas = df["pas"].values
        y_pad = df["pad"].values

        # Escalado
        X_scaled = self.scaler.fit_transform(X)

        pas_errors = []
        pad_errors = []

        for fold, (train_index, test_index) in enumerate(kf.split(X_scaled), 1):
            X_train, X_test = X_scaled[train_index], X_scaled[test_index]
            y_train_pas, y_test_pas = y_pas[train_index], y_pas[test_index]
            y_train_pad, y_test_pad = y_pad[train_index], y_pad[test_index]

            # PAS
            self.model_pas.fit(X_train, y_train_pas)
            y_pred_pas = self.model_pas.predict(X_test)
            mae_pas = mean_absolute_error(y_test_pas, y_pred_pas)
            pas_errors.append(mae_pas)

            # PAD
            self.model_pad.fit(X_train, y_train_pad)
            y_pred_pad = self.model_pad.predict(X_test)
            mae_pad = mean_absolute_error(y_test_pad, y_pred_pad)
            pad_errors.append(mae_pad)

            print(f"Fold {fold} - MAE PAS: {mae_pas:.2f}, MAE PAD: {mae_pad:.2f}")

        # Imprimir información de evaluación
        print("\n--- Validación cruzada finalizada ---")
        print(f"MAE PAS promedio (5-fold): {sum(pas_errors)/len(pas_errors):.2f}")
        print(f"MAE PAD promedio (5-fold): {sum(pad_errors)/len(pad_errors):.2f}")
        print("Cantidad de datos en y_test_pas:", len(y_test_pas))
        print("Valores únicos en y_test_pas:", np.unique(y_test_pas))
        print("Cantidad de datos en y_test_pad:", len(y_test_pad))
        print("Valores únicos en y_test_pad:", np.unique(y_test_pad))

        # Entrenamiento final con todos los datos disponibles
        self.model_pas.fit(X_scaled, y_pas)
        self.model_pad.fit(X_scaled, y_pad)


        # Almacenar evaluaciones
        joblib.dump({'y_true': y_test_pas, 'y_pred': y_pred_pas}, 'models/eval_pas.joblib')
        joblib.dump({'y_true': y_test_pad, 'y_pred': y_pred_pad}, 'models/eval_pad.joblib')

        # Actualizar estado en Firebase
        firebase_repository = FirebaseRepository()
        firebase_repository.update_model_status(True)

        # Guardar métricas y modelos
        self._save_metrics(y_test_pas, y_pred_pas, y_test_pad, y_pred_pad)
        self._save_models()

        return {"message": "Modelo entrenado y guardado con éxito"}

    
    def predict(self, data: Dict[str, float]) -> List[float]:
        """Realiza predicción solo con modelos entrenados"""
        if not self.is_trained():
            raise ValueError("Los modelos no están entrenados. Ejecuta train_models() primero.")
        
        try:
            columnas = ["amp_pulso", "t_cresta", "t_descnd", "pico_a_pico", "min_a_min"]
            new_data = pd.DataFrame([[data[col] for col in columnas]], columns=columnas)
            new_data_scaled = self.scaler.transform(new_data)
            
            return [
                float(self.model_pas.predict(new_data_scaled)[0]),
                float(self.model_pad.predict(new_data_scaled)[0])
            ]
        except Exception as e:
            raise ValueError(f"Error en predicción: {str(e)}")
        
    def get_evaluation_data(self, bp_type: str):
        try:
            data = joblib.load(f'models/eval_{bp_type}.joblib')
            return data['y_true'], data['y_pred']
        except FileNotFoundError:
            raise ValueError("Primero debe entrenar el modelo")
    
    def _save_metrics(self, y_test, y_pred, y_test_pad, y_pred_pad):
        metrics = {
            "pas": {
                "MAE": mean_absolute_error(y_test, y_pred),
                "MSE": mean_squared_error(y_test, y_pred),
                "R2": r2_score(y_test, y_pred)
            },
            "pad": {
                "MAE": mean_absolute_error(y_test_pad, y_pred_pad),
                "MSE": mean_squared_error(y_test_pad, y_pred_pad),
                "R2": r2_score(y_test_pad, y_pred_pad)
            }
        }
        with open("models/metrics.json", "w") as f:
            json.dump(metrics, f)
    
    def _save_models(self):
        joblib.dump(self.model_pas, 'models/model_pas.joblib')
        joblib.dump(self.model_pad, 'models/model_pad.joblib')
        joblib.dump(self.scaler, 'models/scaler.joblib')