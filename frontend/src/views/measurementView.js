import Swal from "sweetalert2";
import { MeasurementViewModel } from "../viewmodels/MeasurementViewModel.js";
import { FirebaseService } from "../core/firebase.service.js";
export class MeasurementView {
  constructor() {
    this.viewModel = new MeasurementViewModel();
    this.initDOMReferences();
    this.setupEventListeners();
    this.setupMeasurementListener();
  }

  initDOMReferences() {
    this.pasInput = document.getElementById("pas");
    this.padInput = document.getElementById("pad");
    this.guardarBtn = document.getElementById("guardarBtn");
    this.tomarBtn = document.getElementById("tomarBtn");
    this.startPredictionsBtn = document.querySelector(".start-predictions");
    this.meditionSelect = document.getElementById("opciones");
    this.meditionSelectEsp = document.getElementById("opciones-esp");
    this.heartElement = document.querySelector(".heart");
    this.loaderElement = document.querySelector(".loader");
  }

  setupEventListeners() {
    this.guardarBtn.addEventListener("click", () => this.saveHandler());
    this.tomarBtn.addEventListener("click", () =>
      this.takeMeasurementHandler()
    );
    this.startPredictionsBtn.addEventListener("click", () => {
      this.startPredictionsHandler();
    });
    this.meditionSelect.addEventListener("change", (e) => {
      this.viewModel.opcionSeleccionada = e.target.value;
    });
    this.meditionSelectEsp.addEventListener("change", (e) => {
      this.viewModel.opcionSeleccionadaEsp = e.target.value;
    });
  }

  setupMeasurementListener() {
    // Listener para estado de medición
    FirebaseService.listen("sensor/tomar_medicion", (snapshot) => {
      const isMedicionTaked = snapshot.val();

      if (isMedicionTaked) {
        this.tomarBtn.style.display = "none";
        this.loaderElement.style.display = "block";
      } else {
        this.tomarBtn.style.display = "block";
        this.loaderElement.style.display = "none";
      }
    });

    // Listener para verificar estado de medición
    FirebaseService.listen("sensor/working_time_esp", (snapshot) => {
      const valor = snapshot.val();
      if (valor) {
        this.viewModel.ultimoTimestamp = valor;
        this.checkConnectionStatus();
      }
    });

    // Verificar estado cada 3 segundos
    setInterval(() => this.checkConnectionStatus(), 3000);

    // Verificar medición cada segundo
    setInterval(() => this.checkMeasurementStatus(), 1000);
  }

  checkConnectionStatus() {
    if (!this.viewModel.ultimoTimestamp) return;

    const ahora = Date.now();
    const diferencia = ahora - this.viewModel.ultimoTimestamp;
    const espOnlineElement = document.querySelector(".esp-online");

    if (diferencia <= 15000) {
      espOnlineElement?.classList.remove("offline");
    } else {
      espOnlineElement?.classList.add("offline");
    }
  }

  async checkMeasurementStatus() {
    try {
      const estado = await FirebaseService.getValue("sensor/tomar_medicion");

      if (estado === true) {
        this.heartElement.classList.remove("oculto");
      } else if (estado === false) {
        this.heartElement.classList.add("oculto");
      }
    } catch (error) {
      console.error("Error verificando medición:", error);
    }
  }

  async saveHandler() {
    try {
      await this.viewModel.saveMeasurement(
        this.pasInput.value,
        this.padInput.value
      );
      Swal.fire("¡Éxito!", "PAS y PAD guardados correctamente.", "success");
    } catch (error) {
      Swal.fire("Error", error.message, "error");
    }
  }

  async takeMeasurementHandler() {
    const result = await Swal.fire({
      title: "¿Estás seguro?",
      text: "Se enviará la señal para tomar la medición.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: "Sí, enviar",
      cancelButtonText: "Cancelar",
    });

    if (result.isConfirmed) {
      try {
        await this.viewModel.takeMeasurement();
        let timerInterval;
        Swal.fire({
          title: "¡Éxito!",
          html: "Esta alerta se cerrará en <b></b> milisegundos.",
          icon: "success",
          timer: 1000,
          timerProgressBar: true,
          didOpen: () => {
            const timer = Swal.getPopup().querySelector("b");
            timerInterval = setInterval(() => {
              timer.textContent = `${Swal.getTimerLeft()}`;
            }, 100);
          },
          willClose: () => {
            clearInterval(timerInterval);
          },
        });
      } catch (error) {
        Swal.fire("Error", error.message, "error");
      }
    }
  }

  async startPredictionsHandler() {
    const result = await Swal.fire({
      title: "¿Estás seguro?",
      text: "Se enviarán las mediciones para predicciones.",
      icon: "question",
      showCancelButton: true,
      confirmButtonText: "Sí, enviar",
      cancelButtonText: "Cancelar",
    });

    if (result.isConfirmed) {
      try {
        await this.viewModel.startPredictions();
        document.querySelector(".container").classList.add("next-page");
        document.querySelector(".arrow-r").style.visibility = "visible";
      } catch (error) {
        Swal.fire("Error", error.message, "error");
      }
    }
  }
}
