import pandas as pd
import json
from firebase_admin import db
from typing import Dict, Optional
from ..config.settings import settings
from ..utils.data_processing import normalize_data, validate_data_structure

class DataService:
    def __init__(self):
        self.ref = db.reference("/sensor/data")
        self.prediction_ref = db.reference("/sensor/data_to_predict")

    def get_raw_data(self) -> Dict:
        """Obtiene datos crudos de Firebase"""
        return self.ref.get()

    def get_prediction_data(self) -> Dict:
        """Obtiene datos para predicción de Firebase"""
        data = self.prediction_ref.get()
        if not data:
            raise ValueError("No hay datos para predicción en Firebase")
        return data

    def prepare_training_data(self) -> pd.DataFrame:
        """Prepara y normaliza los datos para entrenamiento"""
        raw_data = self.get_raw_data()
        
        if not raw_data:
            raise ValueError("No hay datos de entrenamiento disponibles")

        # Normalizar estructura de datos
        normalized_data = normalize_data(raw_data)
        validate_data_structure(normalized_data)

        # Procesar datos en DataFrame
        list_dfs = []
        for key, values in normalized_data.items():
            min_len = self._calculate_min_length(values)
            
            df_temp = pd.DataFrame({
                "amp_pulso": values["amp_pulso"][:min_len],
                "t_cresta": values["t_cresta"][:min_len],
                "t_descnd": values["t_descnd"][:min_len],
                "pico_a_pico": values["pico_a_pico"][:min_len],
                "min_a_min": values["min_a_min"][:min_len],
                "pas": [values["pas"]] * min_len,
                "pad": [values["pad"]] * min_len
            })
            list_dfs.append(df_temp)

        full_df = pd.concat(list_dfs, ignore_index=True)
        return full_df.dropna()

    def _calculate_min_length(self, values: Dict) -> int:
        """Calcula la longitud mínima entre las listas de características"""
        features = ["amp_pulso", "t_cresta", "t_descnd", "pico_a_pico", "min_a_min"]
        return min(len(values[feature]) for feature in features)

    def save_processed_data(self, df: pd.DataFrame, filename: str = "datos_procesados.csv"):
        """Guarda los datos procesados en un archivo CSV"""
        df.to_csv(filename, index=False)
        return filename