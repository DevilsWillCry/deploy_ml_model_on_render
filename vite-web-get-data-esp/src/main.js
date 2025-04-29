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

const app = initializeApp(firebaseConfig);
const db = getDatabase(app);

let opcionSeleccionada = "1";
let opcionSeleccionadaEsp = "1";

let checkingAllData = {
  "medition-one" : false,
  "medition-two" : false,
  "medition-three" : false,
  "medition-one-esp" : false,
  "medition-two-esp" : false,
  "medition-three-esp" : false

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
    ); // Opcional
    return;
  }
  if(opcionSeleccionada == 1){
    document.querySelector(".medition-one-completed").classList.add("checked");
    checkingAllData["medition-one"] = true;
  }else if (opcionSeleccionada == 2){
    document.querySelector(".medition-two-completed").classList.add("checked");
    checkingAllData["medition-two"] = true;
  }else {
    document.querySelector(".medition-three-completed").classList.add("checked");
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

  if (diferencia <= 10000) {
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

//Vamos hacer un fecth a http://127.0.0.1:8000/predict

/*
const url = "http://127.0.0.1:8000/predict";

async function fetchPredictions() {
  const response = await fetch(url);
  const data = await response.json();
  print(data);
  return data;
}

const predictions = await fetchPredictions();

setInterval(fetchPredictions, 5000);

*/



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
    if(opcionSeleccionadaEsp == 1){
      document.querySelector(".medition-one-completed-esp").classList.add("checked");
      checkingAllData["medition-one-esp"] = true;
    }else if (opcionSeleccionadaEsp == 2){
      document.querySelector(".medition-two-completed-esp").classList.add("checked");
      checkingAllData["medition-two-esp"] = true;
    }else {
      document.querySelector(".medition-three-completed-esp").classList.add("checked");
      checkingAllData["medition-three-esp"] = true;
    }
  }
});

let isMedicionTaked = false;

async function tomarMediciones() {
  // set nodo_actual para saber que medicion tomar: medicion_1, medicion_2, medicion_3.
  set(ref(db, `sensor/nodo_actual`), `medicion_${opcionSeleccionadaEsp}`)
    .then(() => {
      console.log("Nodo actual guardado correctamente." + opcionSeleccionadaEsp);
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

// Evento para start-predictions
document.querySelector(".start-predictions").addEventListener("click", function () {
      let count = 0;
      for (let key in checkingAllData) {
        if (checkingAllData[key]) {
          count++;
        }
      }
      if(count == 1){
        Swal.fire({
          title: "¿Estás seguro?",
          text: "Se enviarán las mediciones para tomar predicciones.",
          icon: "warning",
          showCancelButton: true,
          confirmButtonColor: "#3085d6",
          cancelButtonColor: "#d33",
          confirmButtonText: "Sí, enviar",
          cancelButtonText: "Cancelar",
        }).then((result) => {
          if (result.isConfirmed) {
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
      }else{
        Swal.fire({
          title: "Error",
          text: "Por favor, complete todas las mediciones.",
          icon: "error",
          showConfirmButton: true,
        });
      }
      
  });

  const container = document.querySelector(".container");
  

  container.addEventListener("animationend", function (e) {
    if (container.classList.contains("next-page")) {
      console.log("La animación next-page ha terminado");
      container.classList.add("oculto");
      const containerPredictions = document.querySelector(".container-predictions");
      containerPredictions.style.display = "flex";
    }
  });

  const containerPredictions = document.querySelector(".container-predictions");
  document.querySelector("#arrow-l").addEventListener("click", function () {
    containerPredictions.classList.add("prev-page");

  });

  containerPredictions.addEventListener("animationend", function (e) {
    if (containerPredictions.classList.contains("prev-page")) {
      console.log("La animación prev-page ha terminado");
      containerPredictions.classList.add("oculto");
      const container = document.querySelector(".container");
      container.style.display = "flex";
      container.classList.remove("oculto");
      container.classList.remove("next-page");
    }
  });


  const arrowR = document.querySelector(".arrow-r");

  arrowR.addEventListener("click", function () {
    containerPredictions.style.display = "none";
    container.classList.add("next-page");
    if(container.classList.contains("next-page")){
      document.querySelector(".next-page").addEventListener("animationend", function (e) {
        container.style.display = "none";
        containerPredictions.style.display = "flex";
      }, { once: true });
    }
    containerPredictions.classList.remove("oculto");
    containerPredictions.classList.remove("prev-page");

  });

//Lamar cada 5 segundos.
setInterval(verificarMedicion, 1000);
