//Import Firebase SDK
import { initializeApp } from "https://www.gstatic.com/firebasejs/9.15.0/firebase-app.js";
import {
  getDatabase,
  ref,
  onValue,
  update,
  set,
  push,
  get,
} from "https://www.gstatic.com/firebasejs/9.15.0/firebase-database.js";

import Swal from "sweetalert2";

export const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  databaseURL: import.meta.env.VITE_FIREBASE_DATABASE_URL,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
};

const isProduction = import.meta.env.VITE_NODE_ENV;

console.log(isProduction)

const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

let opcionSeleccionada = "1";
let opcionSeleccionadaEsp = "1";
let isTrainingModel = false;

let checkingAllData = {
  "medition-one": false,
  "medition-two": false,
  "medition-three": false,
  "medition-four": false,
  "medition-five": false,
  "medition-one-esp": false,
  "medition-two-esp": false,
  "medition-three-esp": false,
  "medition-four-esp": false,
  "medition-five-esp": false,
};

// Función para guardar las mediciones
function guardar() {
  const pas = document.getElementById("pas").value;
  const pad = document.getElementById("pad").value;

  if (pas === "" || pad === "") {
    Swal.fire(
      "Error",
      "Por favor, ingresa ambos valores (PAS y PAD).",
      "error"
    );
    return;
  }
  if (opcionSeleccionada == 1) {
    document.querySelector(".medition-one-completed").classList.add("checked");
    checkingAllData["medition-one"] = true;
  } else if (opcionSeleccionada == 2) {
    document.querySelector(".medition-two-completed").classList.add("checked");
    checkingAllData["medition-two"] = true;
  } else if (opcionSeleccionada == 3) {
    document
      .querySelector(".medition-three-completed")
      .classList.add("checked");
    checkingAllData["medition-three"] = true;
  } else if (opcionSeleccionada == 4) {
    document.querySelector(".medition-four-completed").classList.add("checked");
    checkingAllData["medition-four"] = true;
  } else {
    document.querySelector(".medition-five-completed").classList.add("checked");
    checkingAllData["medition-three"] = true;
  }
  const pasRef = set(
    ref(db, `sensor/data/medicion_${opcionSeleccionada}/pas`),
    parseInt(pas)
  );
  const padRef = set(
    ref(db, `sensor/data/medicion_${opcionSeleccionada}/pad`),
    parseInt(pad)
  );

  Promise.all([pasRef, padRef])
    .then(() => {
      console.log("PAS y PAD guardados correctamente.");
      Swal.fire({
        title: "¡Éxito!",
        text: "PAS y PAD guardados correctamente.",
        icon: "success",
        showConfirmButton: true,
      });
    })
    .catch((err) => {
      console.error("Error al guardar datos: ", err);
      Swal.fire("Error", "Ocurrió un error al guardar los datos.", "error"); // Opcional
    });
}

async function obtenerMedicion() {
  const medicionesRef = ref(db, "sensor/tomar_medicion");
  try {
    const snapshot = await get(medicionesRef);
    if (snapshot.exists()) {
      return snapshot.val();
    } else {
      console.log("No se encontró el valor.");
      return false;
    }
  } catch (err) {
    console.error("Error al obtener el valor: ", err);
    return false;
  }
}

async function verificarMedicion() {
  const estado = await obtenerMedicion();
  const heart = document.querySelector(".heart");

  if (estado == true) {
    // Insertar display none en el div heart
    heart.classList.remove("oculto");
  } else if (estado == false) {
    heart.classList.add("oculto");
  }
}

const refOnline = ref(db, "sensor/working_time_esp");
let ultimoTimestamp = null;

function verificarEstado() {
  if (!ultimoTimestamp) {
    console.log(" gray");
    return;
  }

  const ahora = Date.now();
  const diferencia = ahora - ultimoTimestamp;

  if (diferencia <= 15000) {
    console.log("🟢 En línea");
    document.querySelector(".esp-online").classList.remove("offline");
  } else {
    console.log("🔴 Desconectado");
    document.querySelector(".esp-online").classList.add("offline");
  }
}

onValue(refOnline, (snapshot) => {
  const valor = snapshot.val();
  if (valor) {
    ultimoTimestamp = valor;
  }
});

let countFirstPrediction = 0;

//Vamos hacer un fecth a http://127.0.0.1:8000/predict

//Vamos a hacer predicciones cada que se actualice firebase sensor/data_to_predict
onValue(ref(db, "sensor/data_to_predict"), (_) => {
  if (countFirstPrediction <= 2) {
    countFirstPrediction++;
    return;
  }

  const url = isProduction == "production" ?
  "https://deploy-ml-model-on-render.onrender.com/predict" : "http://127.0.0.1:8000/predict";
  if (countFirstPrediction >= 2) {
    fetch(url)
      .then((response) => response.json())
      .then((data) => {
        console.log(data.prediction[0] + ", " + data.prediction[1]);
        document.querySelector(".prediction-pas-value").textContent =
          data.prediction[0].toFixed(2) + " " + " mmHg";
        document.querySelector(".prediction-pad-value").textContent =
          data.prediction[1].toFixed(2) + " " + " mmHg";
      })
      .catch((error) => {
        console.error("Error al hacer la petición:", error);
      });
  }
});

setInterval(verificarEstado, 3000);

const refCheckEndMedition = ref(db, "sensor/tomar_medicion");

onValue(refCheckEndMedition, (snapshot) => {
  const valor = snapshot.val();
  if (!valor && checkInitialState) {
    Swal.fire({
      title: "¡Éxito!",
      text: "Medición tomada correctamente.",
      icon: "success",
      showConfirmButton: true,
    });
    if (opcionSeleccionadaEsp == 1) {
      document
        .querySelector(".medition-one-completed-esp")
        .classList.add("checked");
      checkingAllData["medition-one-esp"] = true;
    } else if (opcionSeleccionadaEsp == 2) {
      document
        .querySelector(".medition-two-completed-esp")
        .classList.add("checked");
      checkingAllData["medition-two-esp"] = true;
    } else if (opcionSeleccionadaEsp == 3) {
      document
        .querySelector(".medition-three-completed-esp")
        .classList.add("checked");
      checkingAllData["medition-three-esp"] = true;
    } else if (opcionSeleccionadaEsp == 4) {
      document
        .querySelector(".medition-four-completed-esp")
        .classList.add("checked");
      checkingAllData["medition-three-esp"] = true;
    } else {
      document
        .querySelector(".medition-five-completed-esp")
        .classList.add("checked");
      checkingAllData["medition-three-esp"] = true;
    }
  }
});

let isMedicionTaked = false;

async function tomarMediciones() {
  // set nodo_actual para saber que medicion tomar: medicion_1, medicion_2, medicion_3.
  set(ref(db, `sensor/nodo_actual`), `medicion_${opcionSeleccionadaEsp}`)
    .then(() => {
      console.log(
        "Nodo actual guardado correctamente." + opcionSeleccionadaEsp
      );
    })
    .catch((err) => {
      console.error("Error al guardar el nodo actual: ", err);
    });

  isMedicionTaked = await obtenerMedicion();
  //Enviar un booleano para tomar las mediciones
  Swal.fire({
    title: "¿Estás seguro?",
    text: "Se enviará la señal para tomar la medición.",
    icon: "warning",
    showCancelButton: true,
    confirmButtonColor: "#3085d6",
    cancelButtonColor: "#d33",
    confirmButtonText: "Sí, enviar",
    cancelButtonText: "Cancelar",
  }).then((result) => {
    if (result.isConfirmed) {
      set(ref(db, `sensor/tomar_medicion`), !isMedicionTaked)
        .then(() => {
          console.log("Tomando medición....");
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
        })
        .catch((err) => {
          console.error("Error al enviar la toma, intente de nuevo: ", err);
          Swal.fire("Error", "Hubo un problema al enviar la señal.", "error");
        });
    }
  });
}

//Monitorear obtenerMedicion para activar loader.
onValue(ref(db, "sensor/tomar_medicion"), (snapshot) => {
  isMedicionTaked = snapshot.val();
  if (isMedicionTaked) {
    document.querySelector("#tomarBtn").style.display = "none";
    document.querySelector(".loader").style.display = "block";
  } else {
    document.querySelector("#tomarBtn").style.display = "block";
    document.querySelector(".loader").style.display = "none";
  }
});

let checkInitialState = false;
// Inicializar algunas variable al cargar el DOM.
document.addEventListener("DOMContentLoaded", function () {
  document.querySelector(".heart").classList.add("oculto");
  document.getElementById("pas").value = "";
  document.getElementById("pad").value = "";

  set(ref(db, `sensor/model_is_trained`), false)
    .then(() => {
      console.log("model_trained guardado correctamente.");
    })
    .catch((err) => {
      console.error("Error al guardar model_trained: ", err);
    });
  // set tomar_medicion a false
  set(ref(db, `sensor/tomar_medicion`), false)
    .then(() => {
      console.log("tomar_medicion guardado correctamente.");
      checkInitialState = true;
    })
    .catch((err) => {
      console.error("Error al guardar tomar_medicion: ", err);
    });

  // set start_predictions a false
  set(ref(db, `sensor/start_predictions`), false)
    .then(() => {
      console.log("start_predictions guardado correctamente.");
    })
    .catch((err) => {
      console.error("Error al guardar start_predictions: ", err);
    });
});

// Asignar la función de guardar al botón
document.getElementById("guardarBtn").addEventListener("click", guardar);

// Asignar la función de tomar mediciones al botón
document.getElementById("tomarBtn").addEventListener("click", tomarMediciones);

// Añadir eventlistener para obtener las opciones del select
document.getElementById("opciones").addEventListener("change", function () {
  opcionSeleccionada = this.value;
});

// Añadir eventlistener para obtener las opciones del select
document.getElementById("opciones-esp").addEventListener("change", function () {
  opcionSeleccionadaEsp = this.value;
});

// Ocultar botón .start_predictions cuando strat-predictions sea true
onValue(ref(db, "sensor/start_predictions"), (snapshot) => {
  if (snapshot.val()) {
    document.querySelector(".start-predictions").style.display = "none";
  } else {
    document.querySelector(".start-predictions").style.display = "block";
  }
});

// Evento para start-predictions
let count = 0;
document
  .querySelector(".start-predictions")
  .addEventListener("click", function () {
    for (let key in checkingAllData) {
      if (checkingAllData[key]) {
        count++;
      }
    }
    if (count >= 0) {
      count = 0;
      Swal.fire({
        title: "¿Estás seguro?",
        text: "Se enviarán las mediciones para tomar predicciones.",
        icon: "question",
        showCancelButton: true,
        confirmButtonColor: "#3085d6",
        cancelButtonColor: "#d33",
        confirmButtonText: "Sí, enviar",
        cancelButtonText: "Cancelar",
      }).then((result) => {
        if (result.isConfirmed) {
          isTrainingModel = true;
          // set model_is_trained a false
          set(ref(db, `sensor/model_is_trained`), false)
            .then(() => {
              console.log("model_trained guardado correctamente.");
            })
            .catch((err) => {
              console.error("Error al guardar model_trained: ", err);
            });
          set(ref(db, `sensor/start_predictions`), true)
            .then(() => {
              console.log("start-predictions guardado correctamente.");
              document.querySelector(".container").classList.add("next-page");
              document.querySelector(".arrow-r").style.visibility = "visible";
            })
            .catch((err) => {
              console.error("Error al guardar start-predictions: ", err);
            });
        }
      });
    } else {
      Swal.fire({
        title: "Error",
        text: "Por favor, complete todas las mediciones.",
        icon: "error",
        showConfirmButton: true,
      });
    }
  });

const container = document.querySelector(".container");
const containerPredictions = document.querySelector(".container-predictions");
const arrowLeft = document.querySelector("#arrow-l");
const arrowRight = document.querySelector(".arrow-r");

// Funciones auxiliares
function mostrar(contenedor) {
  contenedor.classList.add("visible");
}

function ocultar(contenedor) {
  contenedor.classList.remove("visible");
}

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

const avancedOptionesButton = document.querySelector(".advanced-options");

avancedOptionesButton?.addEventListener("click", () => {
  const url = isProduction == "production" ?
    "https://deploy-ml-model-on-render.onrender.com/show-graphs" : "http://127.0.0.1:8000/show-graphs";
  fetch(url)
    .then((response) => response.json())
    .then((data) => {
      console.log(data);
      // Insert graph png into img tags to pas and pad in prediction-graph
      document.querySelector(".pas-graph").src = data.pas;
      document.querySelector(".pad-graph").src = data.pad;
    })
    .catch((error) => {
      //Use SweetAlert 2
      Swal.fire({
        title: "Error",
        text: "Error al mostrar los gráficos.",
        icon: "error",
        showConfirmButton: true,
      });
      console.error("Error al mostrar los gráficos:", error);
    });
});




onValue(ref(db, "sensor/start_predictions"), (snapshot) => {
  if (snapshot.val() && isTrainingModel) {
    document.querySelector(".prediction-content").style.display = "none";
    document.querySelector(".loader-prediction").style.display = "block";
    setTimeout(() => {
      const url = isProduction == "production" ?
        "https://deploy-ml-model-on-render.onrender.com/training_model" : "http://127.0.0.1:8000/training_model";
      fetch(url)
        .then((response) => response.json())
        .then((data) => {
          console.log(data);
        })
        .catch((error) => {
          //Use SweetAlert 2
          Swal.fire({
            title: "Error",
            text: "Error al entrenar el modelo.",
            icon: "error",
            showConfirmButton: true,
          });
          console.error("Error al entrenar el modelo:", error);
        });
    }, 5000);
  }
});

onValue(ref(db, "sensor/model_is_trained"), (snapshot) => {
  if (snapshot.val()) {
    document.querySelector(".prediction-content").style.display = "flex";
    document.querySelector(".loader-prediction").style.display = "none";
    isTrainingModel = false;
    const urlMetrics = isProduction == "production" ?
      "https://deploy-ml-model-on-render.onrender.com/metrics" : "http://127.0.0.1:8000/metrics";
    fetch(urlMetrics)
      .then((response) => response.json())
      .then((data) => {
        console.log(data.result);
        document.querySelector(".confidence").textContent = "Nivel de confianza del modelo: " + data.result.toFixed(2) + "%";
      })
      .catch((error) => {
        //Use SweetAlert 2
        Swal.fire({
          title: "Error",
          text: "Error al obtener las metricas.",
          icon: "error",
          showConfirmButton: true,
        });
        console.error("Error al obtener las metricas:", error);
      });
  }
});

//Lamar cada 5 segundos.
setInterval(verificarMedicion, 1000);
