from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# Enums para valores predefinidos
class BloodPressureCategory(str, Enum):
    NORMAL = "normal"
    ELEVATED = "elevated"
    HYPERTENSION_STAGE_1 = "hypertension_stage_1"
    HYPERTENSION_STAGE_2 = "hypertension_stage_2"
    HYPERTENSIVE_CRISIS = "hypertensive_crisis"

class SensorType(str, Enum):
    MAX30102 = "MAX30102"
    ESP32 = "ESP32"
    SIMULATED = "simulated"

# Modelos base
class SensorData(BaseModel):
    """Datos crudos del sensor"""
    amp_pulso: List[float] = Field(..., description="Amplitud del pulso en mV")
    t_cresta: List[float] = Field(..., description="Tiempo de cresta en ms")
    t_descnd: List[float] = Field(..., description="Tiempo de descenso en ms")
    pico_a_pico: List[float] = Field(..., description="Valores pico a pico")
    min_a_min: List[float] = Field(..., description="Valores mínimo a mínimo")
    
    @validator('*', each_item=True)
    def validate_values(cls, v):
        if not isinstance(v, (int, float)):
            raise ValueError("Todos los valores deben ser numéricos")
        return round(float(v), 4)

class BloodPressureMeasurement(BaseModel):
    """Medición de presión arterial"""
    pas: float = Field(..., gt=30, lt=300, description="Presión arterial sistólica (mmHg)")
    pad: float = Field(..., gt=20, lt=200, description="Presión arterial diastólica (mmHg)")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    category: BloodPressureCategory = Field(None, description="Categoría clínica")
    
    @validator('category', always=True)
    def set_category(cls, v, values):
        pas, pad = values.get('pas'), values.get('pad')
        if pas is None or pad is None:
            return None
            
        if pas >= 180 or pad >= 120:
            return BloodPressureCategory.HYPERTENSIVE_CRISIS
        elif pas >= 140 or pad >= 90:
            return BloodPressureCategory.HYPERTENSION_STAGE_2
        elif pas >= 130 or pad >= 80:
            return BloodPressureCategory.HYPERTENSION_STAGE_1
        elif pas >= 120:
            return BloodPressureCategory.ELEVATED
        else:
            return BloodPressureCategory.NORMAL

# Modelos para la API
class TrainingRequest(BaseModel):
    """Esquema para solicitud de entrenamiento"""
    sensor_type: SensorType
    data: List[Dict[str, SensorData]] = Field(..., min_items=10)
    test_size: float = Field(0.2, ge=0.1, le=0.3)

class PredictionResult(BaseModel):
    """Resultado de predicción del modelo"""
    pas: float = Field(..., description="Valor predicho para PAS")
    pad: float = Field(..., description="Valor predicho para PAD")
    confidence: float = Field(..., ge=0, le=1, description="Confianza del modelo")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ModelMetrics(BaseModel):
    """Métricas de rendimiento del modelo"""
    mae: float = Field(..., ge=0, description="Error absoluto medio")
    mse: float = Field(..., ge=0, description="Error cuadrático medio")
    r2: float = Field(..., ge=-1, le=1, description="Coeficiente de determinación")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

# Modelos para Firebase
class FirebaseSensorData(SensorData):
    """Adaptador para datos de Firebase"""
    pas: float
    pad: float
    
    class Config:
        extra = "allow"  # Permite campos adicionales de Firebase

class HistoricalData(BaseModel):
    """Datos históricos para análisis"""
    measurements: List[BloodPressureMeasurement]
    stats: Dict[str, float]