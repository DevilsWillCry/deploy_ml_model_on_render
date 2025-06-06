import matplotlib.pyplot as plt
import numpy as np
import cloudinary
import cloudinary.uploader
from io import BytesIO
from typing import Tuple, Dict
from matplotlib.figure import Figure
from ..config.settings import settings
import json

# Configuración de estilos profesionales para gráficos médicos
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'font.size': 12,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'figure.figsize': (10, 6),
    'figure.dpi': 300,
    'font.family': 'sans-serif',
    'figure.facecolor': 'white'
})

class MedicalVisualizer:

    def __init__(self) -> None:
        # Configurración de Cloudinary para las variables de entorno
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
            secure=True
        )
    @staticmethod
    def create_scatter_plot(y_true: np.ndarray, 
                          y_pred: np.ndarray,
                          title: str = "Real vs Predicho",
                          xlabel: str = "Valor Real",
                          ylabel: str = "Valor Predicho",
                          color: str = 'tab:blue',
                          pa: str = None) -> Figure:
        """
        Crea un gráfico de dispersión profesional para resultados médicos.
        
        Args:
            y_true: Valores reales
            y_pred: Valores predichos
            title: Título del gráfico
            xlabel: Etiqueta eje X
            ylabel: Etiqueta eje Y
            color: Color de los puntos
            
        Returns:
            Objeto Figure de matplotlib
        """
        fig, ax = plt.subplots()
        
        # Gráfico principal
        scatter = ax.scatter(y_true, y_pred, alpha=0.4, color=color, edgecolors='w', linewidth=0.5)
        
        # Línea de referencia perfecta
        lims = [
            min(min(y_true), min(y_pred)) - 5,
            max(max(y_true), max(y_pred)) + 5
        ]
        ax.plot(lims, lims, 'r--', alpha=0.75, label='Línea ideal')
        
        # Ajustes estéticos
        ax.set_xlim(lims)
        ax.set_ylim(lims)
        ax.set_title(title, pad=20)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.grid(True, linestyle='--', alpha=0.6)
        
        # Texto con métricas
        with open('models/metrics.json', 'r') as f: metrics = json.load(f)

        mae = metrics[pa]['MAE']
        r2 = metrics[pa]['R2']
        stats_text = f"MAE: {mae:.4f}\nR²: {r2:.4f}"
        ax.text(0.05, 0.95, stats_text, transform=ax.transAxes,
                verticalalignment='top', bbox=dict(boxstyle='round', alpha=0.2, facecolor='white'))
        
        plt.tight_layout()
        return fig

    @staticmethod
    def save_and_upload_plot(fig: Figure, filename: str) -> str:
        """
        Guarda y sube un gráfico a Cloudinary.
        
        Args:
            fig: Figura de matplotlib
            filename: Nombre del archivo
            
        Returns:
            URL pública de la imagen
        """
        # Guardar en buffer de memoria
        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=300)
        buf.seek(0)

        # Guardar en disco
        fig.savefig(f'models/{filename}.png', bbox_inches='tight', dpi=300)
        
        # Subir a Cloudinary
        upload_result = cloudinary.uploader.upload(
            buf,
            public_id=f"medical_plots/{filename}",
            overwrite=True,
            resource_type="image"
        )
        plt.close(fig)
        return upload_result['secure_url']

    @staticmethod
    def create_comparison_plot(y_train: np.ndarray, 
                             y_train_pred: np.ndarray,
                             y_test: np.ndarray,
                             y_test_pred: np.ndarray,
                             title: str = "Comparación Entrenamiento vs Prueba") -> Figure:
        """
        Crea un gráfico comparativo entre datos de entrenamiento y prueba.
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        
        # Subgráfico de entrenamiento
        ax1.scatter(y_train, y_train_pred, color='tab:green', alpha=0.6)
        ax1.set_title('Datos de Entrenamiento')
        ax1.set_xlabel('Valor Real')
        ax1.set_ylabel('Valor Predicho')
        
        # Subgráfico de prueba
        ax2.scatter(y_test, y_test_pred, color='tab:blue', alpha=0.6)
        ax2.set_title('Datos de Prueba')
        ax2.set_xlabel('Valor Real')
        
        # Líneas ideales
        for ax in (ax1, ax2):
            lims = [
                min(min(y_train), min(y_test)) - 5,
                max(max(y_train), max(y_test)) + 5
            ]
            ax.plot(lims, lims, 'r--')
            ax.set_xlim(lims)
            ax.set_ylim(lims)
            ax.grid(True, linestyle='--', alpha=0.6)
        
        fig.suptitle(title, y=1.02)
        plt.tight_layout()
        return fig

    @staticmethod
    def plot_feature_importance(features: list, importance: np.ndarray) -> Figure:
        """
        Crea un gráfico de barras horizontal mostrando la importancia de características.
        """
        fig, ax = plt.subplots()
        y_pos = np.arange(len(features))
        
        ax.barh(y_pos, importance, align='center', color='tab:cyan')
        ax.set_yticks(y_pos)
        ax.set_yticklabels(features)
        ax.invert_yaxis()
        ax.set_xlabel('Importancia')
        ax.set_title('Importancia de Características')
        ax.grid(True, axis='x', linestyle='--', alpha=0.6)
        
        plt.tight_layout()
        return fig