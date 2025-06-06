//src/main.js

import { FirebaseService } from "./core/firebase.service.js";
import { MeasurementView } from "./views/measurementView.js";
import { PredictionView } from "./views/predictionView.js";

const container = document.querySelector(".container");
const containerPredictions = document.querySelector(".container-predictions");
const arrowLeft = document.querySelector("#arrow-l");
const arrowRight = document.querySelector(".arrow-r");

// Al terminar la animación de salida de container
container.addEventListener("animationend", () => {
  if (container.classList.contains("next-page")) {
    container.classList.add("hidden-container");
    container.classList.remove("visible-container");

    containerPredictions.classList.add("visible");
  }

  if (container.classList.contains("next-page")) {
    container.classList.remove("next-page");
  }
});

// Al terminar la animación de salida de containerPredictions
containerPredictions.addEventListener("animationend", () => {
  if (containerPredictions.classList.contains("prev-page")) {
    containerPredictions.classList.add("hidden-container-predictions");
    containerPredictions.classList.remove("visible");

    container.classList.add("visible-container");
  }

  if (containerPredictions.classList.contains("prev-page")) {
    containerPredictions.classList.remove("prev-page");
  }
});

// Al hacer clic en volver
arrowLeft.addEventListener("click", () => {
  containerPredictions.classList.add("prev-page");
  containerPredictions.classList.remove("visible");
  containerPredictions.classList.add("hidden-container-predictions");

  container.classList.add("visible-container");
  container.classList.remove("next-page");
  container.classList.remove("hidden-container");
});

// Al hacer clic en avanzar
arrowRight.addEventListener("click", () => {
  container.classList.add("next-page");
  container.classList.add("hidden-container");
  container.classList.remove("visible-container");

  containerPredictions.classList.add("visible");
  containerPredictions.classList.remove("prev-page");
  containerPredictions.classList.remove("hidden-container-predictions");
});

document.addEventListener("DOMContentLoaded", () => {
  // Inicialización de Firebase
  FirebaseService.initialize();

  // Configuración inicial
  Promise.all([
    FirebaseService.setValue("sensor/model_is_trained", false),
    FirebaseService.setValue("sensor/tomar_medicion", false),
    FirebaseService.setValue("sensor/start_predictions", false),
  ])
    .then(() => {
      console.log("Firebase inicializado correctamente");
    })
    .catch((error) => {
      console.error("Error inicializando Firebase:", error);
    });

  // Inicializar vistas
  new MeasurementView();
  new PredictionView();

  // Ocultar elementos iniciales
  document.querySelector(".heart")?.classList.add("oculto");
  document.getElementById("pas").value = "";
  document.getElementById("pad").value = "";
});
