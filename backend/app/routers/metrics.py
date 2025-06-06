from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, List
import json
import joblib
import numpy as np
from datetime import datetime

from ..services.model_service import ModelService
from ..services.data_service import DataService
from ..utils.visualization import MedicalVisualizer
from ..repositories.firebase_repository import FirebaseRepository
from ..core.schemas import MetricsResponse, GraphResponse, FeatureImportanceResponse

router = APIRouter(
    prefix="/api/metrics",
    tags=["Model Metrics & Analytics"]
)

@router.get("/performance", response_model=MetricsResponse)
async def get_model_metrics():
    """
    Obtiene métricas de rendimiento del modelo (R2, MAE, MSE) tanto para PAS como PAD.
    """
    try:
        with open('models/metrics.json') as f:
            metrics = json.load(f)
            
        # Calcular promedio ponderado
        pas_r2 = metrics['pas']['R2']
        pad_r2 = metrics['pad']['R2']
        weighted_avg = ((pas_r2 * 0.6) + (pad_r2 * 0.4)) * 100  # Ponderación clínica
        
        return {
            "result": weighted_avg,
            "details": metrics,
            "timestamp": datetime.utcnow().isoformat()
        }
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Metrics not found. Train the model first."
        )

@router.get("/feature-importance", response_model=FeatureImportanceResponse, summary="Feature Importance Analysis")
async def feature_importance_analysis(
    model_service: ModelService = Depends()
) -> Dict[str, List[float]]:
    """
    Devuelve la importancia de características del modelo en formato JSON.
    """
    try:
        model = joblib.load('models/model_pas.joblib')
        features = ['amp_pulso', 't_cresta', 't_descnd', 'pico_a_pico', 'min_a_min']
        importance = model.feature_importances_.tolist()
        
        return {
            "features": features,
            "importance": importance,
            "normalized": (importance / np.sum(importance)).tolist()
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error loading model: {str(e)}"
        )

@router.get("/graphs", response_model=GraphResponse)
async def get_performance_graphs(
    visualizer: MedicalVisualizer = Depends(), # Dependencia de la clase de visualización
    model_service: ModelService = Depends() # Dependencia del servicio del modelo
) -> Dict[str, str]:
    """
    Genera y devuelve URLs de gráficos de desempeño del modelo.
    """
    try:
        #
        y_true_pas, y_pred_pas = model_service.get_evaluation_data('pas')
        
        fig_pas = visualizer.create_scatter_plot(
            y_true_pas, 
            y_pred_pas,
            title="Desempeño del Modelo en la Estimación de la PAS",
            xlabel="PAS Real (mmHg)",
            ylabel="PAS Predicho (mmHg)",
            pa="pas"
        )
        
        url_pas = visualizer.save_and_upload_plot(fig_pas, "pas_performance")
        
        # Gráfico para PAD
        y_true_pad, y_pred_pad = model_service.get_evaluation_data('pad')
        
        fig_pad = visualizer.create_scatter_plot(
            y_true_pad, 
            y_pred_pad,
            title="Desempeño del Modelo en la Estimación de la PAD",
            xlabel="PAD Real (mmHg)",
            ylabel="PAD Predicho (mmHg)",
            color='tab:green',
            pa="pad"
        )
        
        url_pad = visualizer.save_and_upload_plot(fig_pad, "pad_performance")
        
        return {
            "pas": url_pas,
            "pad": url_pad
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating graphs: {str(e)}"
        )

@router.get("/historical")
async def get_historical_metrics(
    firebase: FirebaseRepository = Depends(),
    days: int = 7
) -> Dict[str, List[Dict]]:
    """
    Obtiene métricas históricas de los últimos N días.
    """
    try:
        historical_data = firebase.get_last_n_records(days * 24)  # Asumiendo 1 registro/hora
        
        return {
            "timeline": historical_data,
            "stats": {
                "avg_pas": np.mean([d['pas'] for d in historical_data]),
                "avg_pad": np.mean([d['pad'] for d in historical_data]),
                "total_records": len(historical_data)
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving historical data: {str(e)}"
        )