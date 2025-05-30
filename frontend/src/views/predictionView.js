import Swal from "sweetalert2";
import { PredictionViewModel } from "../viewmodels/PredictionViewModel.js";
import { FirebaseService } from "../core/firebase.service.js";

export class PredictionView {
  constructor() {
    this.viewModel = new PredictionViewModel();
    this.initDOMReferences();
    this.setupEventListeners();
    this.setupPredictionListener();
    this.setupTrainingListeners();
  }

  initDOMReferences() {
    this.pasElement = document.querySelector(".prediction-pas-value");
    this.padElement = document.querySelector(".prediction-pad-value");
    this.advancedOptionsBtn = document.querySelector(".advanced-options");
    this.closeGraphsBtn = document.querySelector(".close-graphs-button");
    this.graphContainer = document.querySelector(".prediction-graph");
    this.loaderImages = document.querySelector(".loader-images");
    this.predictionContent = document.querySelector(".prediction-content");
    this.loaderPrediction = document.querySelector(".loader-prediction");
    this.confidenceElement = document.querySelector(".confidence");
    this.startPredictionsBtn = document.querySelector(".start-predictions");
  }

  setupEventListeners() {
    this.advancedOptionsBtn?.addEventListener("click", () => this.showGraphs());
    this.closeGraphsBtn?.addEventListener("click", () => this.hideGraphs());
  }

  setupPredictionListener() {
    this.viewModel.setupPredictionListener((data, error) => {
      if (error) {
        console.error("Error en predicción:", error);
        return;
      }

      this.pasElement.textContent = data.pas;
      this.padElement.textContent = data.pad;
    });
  }

  setupTrainingListeners() {
    // Listener para inicio de entrenamiento
    FirebaseService.listen("sensor/start_predictions", (snapshot) => {
      if (snapshot.val()) {
        this.predictionContent.style.display = "none";
        this.loaderPrediction.style.display = "block";

        // Simular delay para entrenamiento
        setTimeout(async () => {
          try {
            await this.viewModel.trainingModel();
          } catch (error) {
            Swal.fire({
              title: "Error",
              text: "Error al entrenar el modelo.",
              icon: "error",
              showConfirmButton: true,
            });
            console.error("Error al entrenar el modelo:", error);
          }
        }, 5000);
      }
    });

    // Listener para finalización de entrenamiento
    FirebaseService.listen("sensor/model_is_trained", async (snapshot) => {
      if (snapshot.val()) {
        this.startPredictionsBtn.style.display = "none";
        this.predictionContent.style.display = "flex";
        this.loaderPrediction.style.display = "none";
        this.viewModel.isTrainingModel = false;

        try {
          const metrics = await this.viewModel.getMetrics();
          this.confidenceElement.textContent = `Nivel de confianza del modelo: ${metrics.result.toFixed(
            2
          )}%`;
        } catch (error) {
          Swal.fire({
            title: "Error",
            text: "Error al obtener las métricas.",
            icon: "error",
            showConfirmButton: true,
          });
          console.error("Error al obtener métricas:", error);
        }
      }
    });
  }

  async showGraphs() {
    this.advancedOptionsBtn.style.display = "none";
    this.loaderImages.style.display = "block";
    this.graphContainer.innerHTML = "";

    try {
      const graphs = await this.viewModel.getGraphs();
      this.renderGraphs(graphs);
    } catch (error) {
      Swal.fire("Error", "Error al mostrar gráficos", "error");
    } finally {
      this.loaderImages.style.display = "none";
    }
  }

  renderGraphs(graphs) {
    const pasImg = this.createImage(
      graphs.pas,
      "Graph PAS",
      "Relación entre PAS Real y PAS Predicho",
      "pas"
    );
    const padImg = this.createImage(
      graphs.pad,
      "Graph PAD",
      "Relación entre PAD Real y PAD Predicho",
      "pad"

    );

    this.graphContainer.append(pasImg, padImg);
    this.graphContainer.classList.add("visible-prediction-graph");
  }

  createImage(src, title, text, pa) {
    const img = document.createElement("img");
    img.src = src;
    img.classList.add(`${pa}-graph`);
    img.addEventListener("click", () => {
      Swal.fire({
        title,
        text,
        imageUrl: src,
        imageAlt: title,
        customClass: {
          popup: "my-swal-popup",
          content: "my-swal-content",
          image: "my-swal-image",
        },
      });
    });
    return img;
  }

  hideGraphs() {
    this.graphContainer.classList.remove("visible-prediction-graph");
    this.advancedOptionsBtn.style.display = "block";
  }
}
