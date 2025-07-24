import Swal from "sweetalert2";
import { MeasurementViewModel } from "../viewmodels/MeasurementViewModel.js";
import { FirebaseService } from "../core/firebase.service.js";

let currentLanguage = localStorage.getItem("language");

export class MeasurementView {
  constructor() {
    this.viewModel = new MeasurementViewModel();
    this.initDOMReferences();
    this.setupEventListeners();
    this.setupMeasurementListener();
    this.count = 0;
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
    this.inputLanguage = document.getElementById("language-toggle");
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
    this.inputLanguage.addEventListener("change", () => {
      currentLanguage = localStorage.getItem("language");
    });
  }

  setupMeasurementListener() {
    // Listener para estado de medición
    FirebaseService.listen("sensor/tomar_medicion", (snapshot) => {
      const isMedicionTaked = snapshot.val();
      if (isMedicionTaked) {
        this.tomarBtn.style.display = "none";
        this.loaderElement.style.display = "block";
        this.count++;
      } else {
        this.tomarBtn.style.display = "block";
        this.loaderElement.style.display = "none";
        if(this.count > 0){
          if(this.viewModel.saveMeasurementEsp("measurement-esp")){
            Swal.fire(currentLanguage === "es" ? "¡Éxito!" : "Success", currentLanguage === "es" ? "PAS y PAD guardados correctamente." : "PAS and PAD saved successfully.", "success");
          }
        }
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
        this.padInput.value,
        "measurement"
      );
      Swal.fire(currentLanguage === "es" ? "¡Éxito!" : "Success", currentLanguage === "es" ? "PAS y PAD guardados correctamente." : "PAS and PAD saved successfully.", "success");
    } catch (error) {
      Swal.fire("Error", error.message, "error");
    }
  }

  async takeMeasurementHandler() {
    const result = await Swal.fire({
      title: currentLanguage === "es" ? "¿Estar seguro?" : "Are you sure?",
      text: currentLanguage === "es" ? "Se enviarán las mediciones." : "Measurements will be sent.",
      icon: "warning",
      showCancelButton: true,
      confirmButtonText: currentLanguage === "es" ? "Enviar" : "Send",
      cancelButtonText: currentLanguage === "es" ? "Cancelar" : "Cancel",
    });

    if (result.isConfirmed) {
      try {
        await this.viewModel.takeMeasurement();
        let timerInterval;
        Swal.fire({
          title: currentLanguage === "es" ? "Exito" : "Success",
          html: currentLanguage === "es" ? "Mediciones enviadas correctamente en <b></b> ms." : "Measurements sent successfully in <b></b> ms.",
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
      title: currentLanguage === "es" ? "¿Estar seguro?" : "Are you sure?",
      text: currentLanguage === "es" ? "Se enviarán las mediciones para predicciones." : "Measurements will be sent for predictions.",
      icon: "question",
      showCancelButton: true,
      confirmButtonText: currentLanguage === "es" ? "Enviar" : "Send",
      cancelButtonText: currentLanguage === "es" ? "Cancelar" : "Cancel",
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
