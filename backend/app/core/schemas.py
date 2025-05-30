from pydantic import BaseModel

class PredictionResponse(BaseModel):
    prediction: list[float]

class MetricsResponse(BaseModel):
    result: float

class GraphResponse(BaseModel):
    pas: str
    pad: str

class FeatureImportanceResponse(BaseModel):
    features: list[str]
    importance: list[float]
    normalized: list[float]