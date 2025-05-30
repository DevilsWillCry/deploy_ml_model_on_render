from fastapi import APIRouter, Depends
from ..services.model_service import ModelService
from ..services.data_service import DataService
from ..core.schemas import PredictionResponse

router = APIRouter(prefix="/api/model", tags=["model"])

@router.get("/train")
async def train_model(data_service: DataService = Depends(), model_service: ModelService = Depends()):
    df = data_service.prepare_training_data()
    return model_service.train_models(df)

@router.get("/predict", response_model=PredictionResponse)
async def predict(data_service: DataService = Depends(), model_service: ModelService = Depends()):
    data = data_service.get_prediction_data()
    return {"prediction": model_service.predict(data)}