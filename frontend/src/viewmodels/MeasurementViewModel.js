import Swal from 'sweetalert2';
import { FirebaseService } from '../core/firebase.service.js';

export class MeasurementViewModel {
    constructor() {
        this.opcionSeleccionada = "1";
        this.opcionSeleccionadaEsp = "1";
        this.checkingAllData = {
            "medition-one": false,
            "medition-two": false,
            "medition-three": false,
            "medition-four": false,
            "medition-five": false,
            "medition-one-esp": false,
            "medition-two-esp": false,
            "medition-three-esp": false,
            "medition-four-esp": false,
            "medition-five-esp": false
        };
    }

    async saveMeasurement(pas, pad, medition) {
        if (!pas || !pad) {
            throw new Error("Por favor, ingresa ambos valores (PAS y PAD).");
        }

        const path = `sensor/data/medicion_${this.opcionSeleccionada}`;
        try {
            await Promise.all([
                FirebaseService.setValue(`${path}/pas`, parseInt(pas)),
                FirebaseService.setValue(`${path}/pad`, parseInt(pad))
            ]);

            console.log(this.getMeditionName(medition));
            
            this.checkingAllData[`medition-${this.getMeditionName(medition)}`] = true;

            document.querySelector(`.medition-${this.getMeditionName(medition)}-completed`).classList.add("checked");

            console.log(this.checkingAllData);
            return true;
        } catch (error) {
            throw new Error("Error al guardar datos: " + error.message);
        }
    }

    async saveMeasurementEsp(medition) {
        console.log(this.getMeditionName(medition));
        document.querySelector(`.medition-${this.getMeditionName(medition)}-completed`).classList.add("checked");
        return true;
    }   

    getMeditionName(medition) {
        const names = ["one", "two", "three", "four", "five"];
        if(medition == "measurement") return names[parseInt(this.opcionSeleccionada) - 1];    
        else return names[parseInt(this.opcionSeleccionadaEsp) - 1] + "-esp";
    }

    async takeMeasurement() {
        try {
            await FirebaseService.setValue('sensor/nodo_actual', `medicion_${this.opcionSeleccionadaEsp}`);
            const currentStatus = await FirebaseService.getValue('sensor/tomar_medicion');
            await FirebaseService.setValue('sensor/tomar_medicion', !currentStatus);
            return true;
        } catch (error) {
            throw new Error("Error al tomar medición: " + error.message);
        }
    }

    async startPredictions() {
        const completed = Object.values(this.checkingAllData).every(Boolean) || true;
        if (!completed) throw new Error("Por favor, complete todas las mediciones.");
        
        try {
            await FirebaseService.setValue('sensor/model_is_trained', false);
            await FirebaseService.setValue('sensor/start_predictions', true);
            return true;
        } catch (error) {
            throw new Error("Error al iniciar predicciones: " + error.message);
        }
    }
}