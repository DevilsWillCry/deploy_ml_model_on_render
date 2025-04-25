#include <heartRate.h>
#include <MAX30105.h>
#include <spo2_algorithm.h>
#include <WiFi.h>
#include <Preferences.h>
#include <Firebase_ESP_Client.h>
#include "addons/TokenHelper.h"
#include "addons/RTDBHelper.h"
#include "time.h" 

bool signupOk = false;

// Configuración Firebase
#define API_KEY "AIzaSyAYM09lYHkW8Otq1CC8AD3DRi0G2UqyZr0"
#define DATABASE_URL "https://esp32-thesis-project-default-rtdb.firebaseio.com/"

// Instancia de Firebase
FirebaseData fbdo;
FirebaseAuth auth;
FirebaseConfig config;


// Parámetros del algoritmo
int periodo = 20, intervalo = 10000;
int ascenso_max  = round(0.09F * 1000.0F / periodo); // 0.6*0.15 = 0.09
int cuenta_ascenso = 0, cuenta_pulsos = 0;
bool primer_pulso = false, possible_min = false;
float PPI_value = 1.0F, refractory = 0.35F;
float value_min, value_max, amp_pulso, amp_pulso_n, t_cresta, t_descnd,
      pico_a_pico, min_a_min, t_cresta_n, t_descnd_n, area_pulso;
unsigned long t_pico_act, t_min_act, t_pico_prev, t_min_prev;
unsigned long t_previo, t_actual;
long muestra_actual, muestra_previa;
int pinPrint = 1;

uint32_t irValue = 0;
unsigned long tiempoInicio = 0;
bool tomandoDatos = 0;
std::vector<float> datos;
std::vector<float> amp_pulso_data;
std::vector<float> t_cresta_data;
std::vector<float> t_descnd_data;
std::vector<float> pico_a_pico_data;
std::vector<float> min_a_min_data;
std::vector<float> area_pulso_data;
int countGlobal = 0;
int countAmp_Pulso = 0;
int countT_Cresta = 0;
int countT_descnd = 0;
int countPico_A_Pico = 0;
int countMin_A_Min = 0;
int countArea_Pulso = 0;

MAX30105 particleSensor;

Preferences prefs;

void setup() {
  Serial.begin(115200);

  prefs.begin("wifi", false);
  String ssid = prefs.getString("ssid", "");
  String pass = prefs.getString("pass", "");

  bool conectado = false;

  if (ssid != "") {
    Serial.println("Intentando conectar con credenciales guardadas...");
    WiFi.begin(ssid.c_str(), pass.c_str());

    int intentos = 0;
    while (WiFi.status() != WL_CONNECTED && intentos < 10) {
      delay(1000);
      Serial.print(".");
      intentos++;
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\nConectado con credenciales guardadas");
      conectado = true;
    } else {
      Serial.println("\nError al conectar con credenciales guardadas");
    }
  }

  if (!conectado) {
    Serial.println("Esperando SmartConfig...");
    WiFi.beginSmartConfig();

    while (!WiFi.smartConfigDone()) {
      delay(500);
      Serial.print(".");
    }
    Serial.println("\nSmartConfig recibido");
    Serial.printf("SSID: %s\nPASS: %s\n", WiFi.SSID().c_str(), WiFi.psk().c_str());

    // Guardar para la próxima vez
    prefs.putString("ssid", WiFi.SSID());
    prefs.putString("pass", WiFi.psk());

    Serial.println("Conectando con nuevas credenciales...");
    WiFi.begin(WiFi.SSID().c_str(), WiFi.psk().c_str());
    while (WiFi.status() != WL_CONNECTED) {
      delay(500);
      Serial.print(".");
    }
    Serial.println("\nConectado exitosamente");
  }

  // Firebase
  config.api_key        = API_KEY;
  config.database_url   = DATABASE_URL;
  if (Firebase.signUp(&config, &auth, "", "")) signupOk = true;
  Firebase.begin(&config, &auth);

  // 🔄 Configurar NTP para obtener hora real
  configTime(0, 0, "pool.ntp.org");  // GMT
  Serial.println("\nEsperando sincronización de hora...");
  time_t now;
  while (time(&now) < 100000) {  // Espera hasta que la hora sea válida
    delay(1000);
    Serial.print(".");
  }

  // Sensor PPG
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println(F("MAX30105 no found"));
    while (1);
  }
  particleSensor.setup(200, 1, 2, 400, 69, 16384);
}

bool IsWifiActived = false;
unsigned long countOnline = 0;

void loop() {
  if(!IsWifiActived){
    if (WiFi.status() == WL_CONNECTED ) {
        Serial.println("ONLINE");
        if (!Firebase.RTDB.setBool(&fbdo, "sensor/service_on", true)) {
            Serial.println("Error al establecer: " + fbdo.errorReason());
        }
        IsWifiActived = true;
        countOnline = millis();

        time_t now;
        time(&now); 
        if (!Firebase.RTDB.setDouble(&fbdo, "sensor/working_time_esp", now*1000 )) {
            Serial.println("Error al establecer: " + fbdo.errorReason());
        }
    }
  } else if ((millis() - countOnline) >= 10000){
    IsWifiActived = false;
    countOnline = 0;
  }
  uint32_t irValue = particleSensor.getIR();
  bool dedoPresente = irValue > 5000;

  if (!dedoPresente) {
    Serial.println("Esperando que se coloque el dedo...");
    delay(500); // evitar spam de mensajes
    return; // Salir del loop actual
  }


  pinPrint = analogRead(36);
 // Guardamos el valor anterior
  muestra_previa = muestra_actual;
  // ... y leemos la nueva
  muestra_actual = 120000 - 10*particleSensor.getIR();

  // #1: Se calcula e imprime por pantalla el HR promedio con base en el intervalo seleccionado
  t_actual = millis();
  if (t_actual - t_previo >= intervalo){
    t_previo = t_actual;   
    cuenta_pulsos = 0; 
  }

  // Adaptación del algoritmo del Alpinista (Argüello, 2019)
  if (muestra_actual > muestra_previa){
    cuenta_ascenso++;

    if (possible_min == false && (millis() - t_pico_act)/float(1000) > 0.45*PPI_value){
      possible_min = true;
      value_min = muestra_previa;
      t_min_act = millis();
    }
  }
  else {
    if (cuenta_ascenso >= ascenso_max) {
      // Si no se ha detectado el primer pulso...
      if (primer_pulso == false){
        primer_pulso = true;
        value_max = muestra_previa;
        t_pico_act = millis();
        
        // Tras detectar el máximo (pico sistólico) se actualiza el valor mínimo
        t_min_prev = t_min_act;
        
        cuenta_pulsos++;           
        ascenso_max = round(float(0.6)*0.15*1000/periodo);
      }
      else{
        // En cambio, si ya se ha detectado el primer pulso, se obtiene el tiempo transcurrido
        // desde el último pico detectado
        if ((millis() - t_pico_act)/float(1000) > float(1.2)*PPI_value || cuenta_ascenso > round((float(1.75)*ascenso_max)/(0.6))){
          value_max = muestra_previa;
          // Actualizo tiempo del pico detectado más recientemente        
          t_pico_prev = t_pico_act;
          t_pico_act = millis();

          // Se calculan las características...
          amp_pulso = value_max - value_min;            
          amp_pulso_n = abs(float(amp_pulso)/value_max);    
          t_cresta = (t_pico_act - t_min_act)/float(1000);  
          t_descnd = (t_min_act - t_pico_prev)/float(1000);  
          pico_a_pico = (t_pico_act - t_pico_prev)/float(1000); 
          PPI_value = pico_a_pico;
          min_a_min = (t_min_act - t_min_prev)/float(1000); 
          t_cresta_n = float(t_cresta)/min_a_min; 
          t_descnd_n = float(t_descnd)/min_a_min; 
          area_pulso = float(amp_pulso)/min_a_min; 

          // Actualizo tiempo de ocurrencia del mínimo
          t_min_prev = t_min_act;
          
          // Parámetros para cálculo de HR
          cuenta_pulsos++;
          ascenso_max = round(float(0.6)*0.15*1000/periodo);
          refractory = 0.35;
          primer_pulso = false;   // Línea crítica, se comenta para procesamiento off-line, aunque funciona en on-line
        }
        else{
          if ((millis() - t_pico_act)/float(1000) > refractory){
            value_max = muestra_previa;
            // Actualizo tiempo del pico detectado más recientemente
            t_pico_prev = t_pico_act;
            t_pico_act = millis();

            // Se calculan las características...
            amp_pulso = value_max - value_min;            
            amp_pulso_n = abs(float(amp_pulso)/value_max);    
            t_cresta = (t_pico_act - t_min_act)/float(1000); 
            t_descnd = (t_min_act - t_pico_prev)/float(1000);  
            pico_a_pico = (t_pico_act - t_pico_prev)/float(1000); 
            PPI_value = pico_a_pico;
            min_a_min = (t_min_act - t_min_prev)/float(1000); 
            t_cresta_n = float(t_cresta)/min_a_min; 
            t_descnd_n = float(t_descnd)/min_a_min; 
            area_pulso = float(amp_pulso)/min_a_min;  

            // Actualizo tiempo de ocurrencia del mínimo
            t_min_prev = t_min_act;

            cuenta_pulsos++;          
            refractory = float(0.75)*PPI_value;
            ascenso_max = round(float(0.6)*cuenta_ascenso);   //Actualizo umbral
          }
        }
      }   
    }
    cuenta_ascenso = 0;
    possible_min = false;
  }

  // #4: Se comenta si se habilitan partes 1, 2 y 3
  if(dedoPresente && !tomandoDatos){
     if (Firebase.ready() && signupOk) {
        if(Firebase.RTDB.getBool(&fbdo, "sensor/tomar_medicion")){
          if (fbdo.boolData() && !tomandoDatos){
            tomandoDatos = true;
            tiempoInicio = millis();
            Serial.println(tiempoInicio);
          }
        }
      }
  }
  if (pinPrint <= 512 ){
    if (tomandoDatos){
      if(value_max != 0 && amp_pulso != 0){
        datos.push_back(value_max);
        amp_pulso_data.push_back(amp_pulso);
        t_cresta_data.push_back(t_cresta);
        t_descnd_data.push_back(t_descnd);
        pico_a_pico_data.push_back(pico_a_pico);
        min_a_min_data.push_back(min_a_min);
        area_pulso_data.push_back(area_pulso);
      }

      if (millis() - tiempoInicio >= 30000){
        Serial.println("Tiempo Completado.");
        tomandoDatos = false;
        countGlobal = 0;
        countAmp_Pulso = 0;
        countT_Cresta = 0;
        countT_descnd = 0;
        countPico_A_Pico = 0;
        countMin_A_Min = 0;
        countArea_Pulso = 0;
        
        if (!Firebase.RTDB.setBool(&fbdo, "sensor/tomar_medicion", false)) {
            Serial.println("Error al establecer: " + fbdo.errorReason());
        } 
      }

      if(datos.size() >= 50 || amp_pulso_data.size() >= 50 || t_cresta_data.size() >= 50 || t_descnd_data.size() >= 50 || pico_a_pico_data.size() >= 50 || min_a_min_data.size() >= 50 || area_pulso_data.size() >= 50){
        enviarLote();
      }

    }
  } 
    
  // Se regula la tasa de muestreo porque la señal sale bastante ruidosa
  t_muestreo(periodo);

}

String obtenerRutaMedicion() {
  String nodoDestino = "medicion_1";  // valor por defecto
  if (Firebase.RTDB.getString(&fbdo, "sensor/nodo_actual")) {
    nodoDestino = fbdo.stringData();
  } else {
    Serial.println("❌ Error obteniendo nodo actual: " + fbdo.errorReason());
  }
  return nodoDestino;
}

void enviarJsonAFirebase(FirebaseData* fbdo, String nodo_actual, String nombre_variable, std::vector<float>& datos_vector, int& contador) {
  if (datos_vector.empty()) return;

  FirebaseJson json;
  for (size_t i = 0; i < datos_vector.size(); i++) {
    json.add(String(contador++), datos_vector[i]);
  }

  if (!Firebase.RTDB.updateNode(fbdo, "/sensor/data/" + nodo_actual + "/" + nombre_variable, &json)) {
    Serial.println("❌ Error al enviar '" + nombre_variable + "': " + fbdo->errorReason());
  }

  datos_vector.clear();
}


void enviarLote() {
  String nodo_actual = obtenerRutaMedicion();
  if (nodo_actual == "") {
    Serial.println("❌ Error obteniendo nodo actual. Cancelando envío.");
    return;
  }

  enviarJsonAFirebase(&fbdo, nodo_actual, "value_max", datos, countGlobal);
  enviarJsonAFirebase(&fbdo, nodo_actual, "amp_pulso", amp_pulso_data, countAmp_Pulso);
  enviarJsonAFirebase(&fbdo, nodo_actual, "t_cresta", t_cresta_data, countT_Cresta);
  enviarJsonAFirebase(&fbdo, nodo_actual, "t_descnd", t_descnd_data, countT_descnd);
  enviarJsonAFirebase(&fbdo, nodo_actual, "pico_a_pico", pico_a_pico_data, countPico_A_Pico);
  enviarJsonAFirebase(&fbdo, nodo_actual, "min_a_min", min_a_min_data, countMin_A_Min);
  enviarJsonAFirebase(&fbdo, nodo_actual, "area_pulso", area_pulso_data, countArea_Pulso);
}


void t_muestreo(uint32_t periodo_us) {
  static uint32_t t_ultima_muestra = micros();
  while ((micros() - t_ultima_muestra) < periodo_us) {
    // Espera sin bloquear totalmente
    delayMicroseconds(10);
  }
  t_ultima_muestra = micros();
}

