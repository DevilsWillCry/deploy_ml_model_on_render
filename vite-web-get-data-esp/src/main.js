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

console.log('Database URL:', import.meta.env.VITE_FIREBASE_DATABASE_URL);


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


// Función para guardar las mediciones
function guardar() {
  const pas = document.getElementById("pas").value;
  const pad = document.getElementById("pad").value;
  
  if (pas === "" || pad === "") {
    alert("Por favor, ingresa ambos valores (PAS y PAD).");
    return;
  }
  
  // Sobrescribir los valores directamente
  set(ref(db, `sensor/medicion_${opcionSeleccionada}/pas`), parseInt(pas))
  .then(() => {
    console.log("PAS guardado correctamente.");
  })
  .catch((err) => {
    console.error("Error al guardar PAS: ", err);
  });
  
  set(ref(db, `sensor/medicion_${opcionSeleccionada}/pad`), parseInt(pad))
  .then(() => {
    console.log("PAD guardado correctamente.");
    alert("Mediciones guardadas exitosamente.");
  })
  .catch((err) => {
    console.error("Error al guardar PAD: ", err);
  });
}

async function obtenerMedicion() {
  const medicionesRef = ref(db, "sensor/tomar_medicion");
  try{
    const snapshot = await get(medicionesRef);
    if (snapshot.exists()) {
      return snapshot.val();
    } else {
      console.log("No se encontró el valor.");
      return false;
    }
  }
  catch(err){
    console.error("Error al obtener el valor: ", err);
    return false;
  }
}

let isMedicionTaked = false;

async function tomarMediciones() {
  // set nodo_actual para saber que medicion tomar: medicion_1, medicion_2, medicion_3.
  set(ref(db, `sensor/nodo_actual`), `medicion_${opcionSeleccionadaEsp}`)
    .then(() => {
      console.log("Nodo actual guardado correctamente.");
    })
    .catch((err) => {
      console.error("Error al guardar el nodo actual: ", err);
    });
  
  isMedicionTaked = await obtenerMedicion();
  console.log(isMedicionTaked); 
  //Enviar un booleano para tomar las mediciones
  set(ref(db, `sensor/tomar_medicion`), !isMedicionTaked)
    .then(() => {
      alert("Tomando medición....");
    })
    .catch((err) => {
      console.error("Error al enviar la toma, intente de nuevo: ", err);
    });
  
}


// Asignar la función de guardar al botón
document.getElementById("guardarBtn").addEventListener("click", guardar);

// Asignar la función de tomar mediciones al botón
document.getElementById("tomarBtn").addEventListener("click", tomarMediciones);

// Añadir eventlistener para obtener las opciones del select
document.getElementById("opciones").addEventListener("change", function () {
  opcionSeleccionada = this.value;
});

document.getElementById("opciones-esp").addEventListener("change", function () {
  opcionSeleccionadaEsp = this.value;
  console.log(opcionSeleccionadaEsp);
});

