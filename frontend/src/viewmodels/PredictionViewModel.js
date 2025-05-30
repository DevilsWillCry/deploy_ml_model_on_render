import { ApiService } from "../core/api.service.js";
import { FirebaseService } from "../core/firebase.service.js";

export class PredictionViewModel {
  constructor() {
    this.isTrainingModel = false;
    this.predictionCount = 0;
  }

  async getPrediction() {
    return ApiService.get("/api/model/predict");
  }

  async getMetrics() {
    return ApiService.get("/api/metrics/performance");
  }

  async getGraphs() {
    return ApiService.get("/api/metrics/graphs");
  }

   async trainingModel() {
        return ApiService.get('/api/model/train');
    }

  setupPredictionListener(callback) {
    FirebaseService.listen("sensor/data_to_predict", async () => {
      if (this.predictionCount < 2) {
        this.predictionCount++;
        return;
      }

      try {
        const prediction = await this.getPrediction();
        callback({
          pas: prediction.prediction[0].toFixed(2) + " mmHg",
          pad: prediction.prediction[1].toFixed(2) + " mmHg",
        });
      } catch (error) {
        console.error("Error en predicción: ", error);
        callback(null, error);
      }
    });
  }
}
