import json
from typing import Dict, List, Any
import numpy as np
import pandas as pd

def normalize_data(raw_data: Dict[str, Any]) -> Dict[str, Dict[str, List[float]]]:
    """
    Normaliza la estructura de datos crudos de Firebase convirtiendo todos los valores a listas.
    
    Args:
        raw_data: Datos crudos obtenidos de Firebase
        
    Returns:
        Diccionario con datos normalizados donde cada valor es una lista numérica
        
    Raises:
        ValueError: Si los datos tienen estructura inválida
    """
    normalized = {}
    
    if not raw_data:
        raise ValueError("Los datos de entrada están vacíos")
    
    for key, value in raw_data.items():
        if not isinstance(value, dict):
            continue
            
        normalized[key] = {}
        for subkey, subvalue in value.items():
            # Conservar PAS/PAD como valores simples
            if subkey in ["pas", "pad"]:
                normalized[key][subkey] = float(subvalue) if subvalue is not None else 0.0
                continue
                
            # Convertir a lista si no lo es
            if not isinstance(subvalue, list):
                if isinstance(subvalue, dict):
                    subvalue = list(subvalue.values())
                else:
                    subvalue = [subvalue]
            
            # Filtrar valores nulos y convertir a float
            cleaned_values = [
                float(x) if x is not None else 0.0 
                for x in subvalue 
                if x is not None
            ]
            
            normalized[key][subkey] = cleaned_values
            
    return normalized

def validate_data_structure(data: Dict[str, Dict[str, List[float]]]) -> bool:
    """
    Valida que los datos tengan la estructura esperada para el entrenamiento.
    
    Args:
        data: Datos normalizados a validar
        
    Returns:
        True si la estructura es válida
        
    Raises:
        ValueError: Si faltan campos requeridos o hay inconsistencias
    """
    required_fields = ["amp_pulso", "t_cresta", "t_descnd", "pico_a_pico", "min_a_min", "pas", "pad"]
    
    for key, values in data.items():
        # Verificar campos requeridos
        missing_fields = [field for field in required_fields if field not in values]
        if missing_fields:
            raise ValueError(f"Registro {key} falta campos: {missing_fields}")
        
        # Verificar que las listas no estén vacías
        for field in required_fields[:5]:  # Solo los campos de lista
            if not values[field]:
                raise ValueError(f"Registro {key} tiene lista vacía para {field}")
                
        # Verificar que PAS/PAD sean valores numéricos válidos
        if not (0 <= values["pas"] <= 300):
            raise ValueError(f"Valor PAS inválido en registro {key}: {values['pas']}")
        if not (0 <= values["pad"] <= 300):
            raise ValueError(f"Valor PAD inválido en registro {key}: {values['pad']}")
    
    return True

def remove_outliers_iqr(df, column: str, threshold: float = 1.5) -> pd.DataFrame:
    """
    Elimina outliers usando el método IQR.
    
    Args:
        df: DataFrame de pandas
        column: Columna a procesar
        threshold: Umbral para considerar outliers
        
    Returns:
        DataFrame sin outliers
    """
    q1 = df[column].quantile(0.25)
    q3 = df[column].quantile(0.75)
    iqr = q3 - q1
    
    lower_bound = q1 - (threshold * iqr)
    upper_bound = q3 + (threshold * iqr)
    
    return df[(df[column] >= lower_bound) & (df[column] <= upper_bound)]

def calculate_statistics(data: List[float]) -> Dict[str, float]:
    """
    Calcula estadísticas básicas para una lista de valores.
    
    Args:
        data: Lista de valores numéricos
        
    Returns:
        Diccionario con estadísticas
    """
    if not data:
        return {}
        
    np_array = np.array(data)
    
    return {
        "mean": float(np.mean(np_array)),
        "median": float(np.median(np_array)),
        "std": float(np.std(np_array)),
        "min": float(np.min(np_array)),
        "max": float(np.max(np_array)),
        "count": len(data)
    }

def add_gaussian_noise(X, y, noise_std=0.01, factor=2):
    """
    Genera un nuevo conjunto con ruido para regresión.

    Añade un ruido gaussiano a los datos X y repite los valores de y
    para que coincidan con el nuevo tamaño de X.

    Args:
        X: Array de características
        y: Array de etiquetas
        noise_std: Desviación estándar del ruido gaussiano (default 0.01)
        factor: Número de veces que se multiplica el conjunto (default 2)

    Returns:
        X_noisy: Array de características con ruido
        y_repeated: Array de etiquetas repetido para coincidir con X_noisy
    """
    X_noisy = np.vstack([X + np.random.normal(0, noise_std, X.shape) for _ in range(factor)])
    y_repeated = np.hstack([y for _ in range(factor)])
    return np.vstack([X, X_noisy]), np.hstack([y, y_repeated])

def save_metrics_to_json(metrics: Dict[str, Any], filename: str) -> None:
    """
    Guarda métricas en archivo JSON con formato consistente.
    
    Args:
        metrics: Diccionario con métricas
        filename: Nombre del archivo de salida
    """
    with open(filename, 'w') as f:
        json.dump(metrics, f, indent=4)