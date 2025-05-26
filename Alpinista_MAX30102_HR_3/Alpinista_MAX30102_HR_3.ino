#include <heartRate.h>
#include <MAX30105.h>
#include <spo2_algorithm.h>

#include <WiFi.h>
#include <WebServer.h>
#include <Preferences.h>

#include <Firebase_ESP_Client.h>
#include "addons/TokenHelper.h"
#include "addons/RTDBHelper.h"

#include "time.h" 
#include "secrets.h"

#include <cmath>

#define PIN_SWITCH 13  // D13

bool signupOk = false;

// Configuración Firebase
#define API_KEY KEY
#define DATABASE_URL URL

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
std::vector<double> datos;
std::vector<double> amp_pulso_data;
std::vector<double> t_cresta_data;
std::vector<double> t_descnd_data;
std::vector<double> pico_a_pico_data;
std::vector<double> min_a_min_data;
std::vector<double> area_pulso_data;

int countGlobal = 0;
int countAmp_Pulso = 0;
int countT_Cresta = 0;
int countT_descnd = 0;
int countPico_A_Pico = 0;
int countMin_A_Min = 0;
int countArea_Pulso = 0;

unsigned long lastUpdateTime = 0;
const unsigned long updateInterval = 10000; 

bool ReadyToPredict = false;


MAX30105 particleSensor;

Preferences prefs;
WebServer server(80);

const char* ssid_ap = "Configurar_ESP32";
const char* pass_ap = "12345678";

const char* form_html = R"rawliteral(
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Configurar WiFi</title></head>
<body>
  <h2>Configuración WiFi ESP32</h2>
  <form action="/guardar" method="post">
    SSID: <input type="text" name="ssid"><br><br>
    Contraseña: <input type="password" name="pass"><br><br>
    <input type="submit" value="Guardar">
  </form>
</body>
</html>
)rawliteral";

void handleRoot() {
  server.send(200, "text/html", form_html);
}

void handleGuardar() {
  String ssid = server.arg("ssid");
  String pass = server.arg("pass");
  // && pass.length() > 0
  if (ssid.length() > 0) {
    prefs.begin("wifi", false);
    prefs.putString("ssid", ssid);
    prefs.putString("pass", pass);
    prefs.end();

    server.send(200, "text/html", "<h2>Guardado exitosamente. Reiniciando...</h2>");
    delay(2000);
    ESP.restart();
  } else {
    server.send(200, "text/html", "<h2>Error: SSID o contraseña vacíos.</h2>");
  }
}


void iniciarAP() {
  WiFi.softAP(ssid_ap, pass_ap);
  IPAddress IP = WiFi.softAPIP();
  Serial.print("🛜 Modo AP activo. IP: ");
  Serial.println(IP);

  server.on("/", handleRoot);
  server.on("/guardar", HTTP_POST, handleGuardar);
  server.begin();
  Serial.println("🌐 Servidor web iniciado en modo AP");

  // Espera aquí bloqueando hasta recibir y guardar los datos
  while (true) {
    server.handleClient();
    delay(10);
  }
}

// --- Configuración Savitzky–Golay (ventana 7, polinomio orden 2) ---
const int SG_N = 7;
float sg_buf[SG_N] = {0};
int sg_idx = 0;
// Coeficientes pre‑calculados para ventana 7, orden 2
const float sg_coeff[SG_N] = {-2, 3, 6, 7, 6, 3, -2};
const float sg_norm = 21.0f;  // suma de coeficientes

float savitzkyGolay(float x) {
  sg_buf[sg_idx] = x;
  float y = 0;
  // Convolución circular
  for (int i = 0; i < SG_N; i++) {
    int idx = (sg_idx + i) % SG_N;
    y += sg_coeff[i] * sg_buf[idx];
  }
  sg_idx = (sg_idx + 1) % SG_N;
  return y / sg_norm;
}

void setup() {
  Serial.begin(115200);  

  pinMode(PIN_SWITCH, INPUT_PULLUP);

  prefs.begin("wifi", true);
  String ssid = prefs.getString("ssid", "");
  String pass = prefs.getString("pass", "");
  prefs.end();

  if (ssid != "") {
    WiFi.begin(ssid.c_str(), pass.c_str());
    Serial.print("🔌 Conectando a WiFi");

    unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 10000) {
      Serial.print(".");
      delay(500);
    }

    if (WiFi.status() == WL_CONNECTED) {
      Serial.println("\n✅ Conectado exitosamente");
    } else {
      Serial.println("\n❌ Fallo en la conexión. Iniciando modo AP...");
      iniciarAP();
    }
  } else {
    Serial.println("No hay credenciales guardadas. Iniciando modo AP...");
    iniciarAP(); // Si no conecta, iniciar AP para configurar
  }

  // 🔄 Configurar NTP para obtener hora real
  configTime(0, 0, "pool.ntp.org");  // UTC (puedes ajustar GMT si quieres)
  Serial.println("Esperando sincronización de hora...");
  time_t now;
  while (time(&now) < 100000) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nHora sincronizada correctamente");

  // Firebase
  config.api_key        = API_KEY;
  config.database_url   = DATABASE_URL;
  config.timeout.serverResponse = 10000;
  if (Firebase.signUp(&config, &auth, "", "")) signupOk = true;
  Firebase.begin(&config, &auth);

  // Reconexión automática WiFi
  Firebase.reconnectWiFi(true);


  // Sensor PPG
  if (!particleSensor.begin(Wire, I2C_SPEED_FAST)) {
    Serial.println(F("MAX30105 no found"));
    while (1);
  }

  byte ledBrightness = 200; //Options: 0=Off to 255=50mA 50, 100, 150, 200, 255
  byte sampleAverage = 1; //Options: 1, 2, 4, 8, 16, 32
  byte ledMode = 2; //Options: 1, 2, 3
  int sampleRate = 400; //Options: 50, 100, 200, 400, 800, 1000, 1600
  int pulseWidth = 69; //Options: 69, 118, 215, 411
  int adcRange = 16384; //Options: 2048, 4096, 8192, 16384
  particleSensor.setup(ledBrightness, sampleAverage, ledMode, sampleRate, pulseWidth, adcRange);

  // Crea la tarea que enviará a Firebase cada 10 segundos
  // xTaskCreate(enviarFirebaseTask, "EnviarFirebaseTask", 8192, NULL, 1, NULL);
}

bool IsWifiActived = false;
unsigned long countOnline = 0;

void loop() {

  /*
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
  */
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
  float muestra_bruta = 120000.0f - 10.0f * irValue;

  float filtrada_sg  = savitzkyGolay(muestra_bruta);
  muestra_actual     = filtrada_sg;

  // #1: Se calcula e imprime por pantalla el HR promedio con base en el intervalo seleccionado
  t_actual = millis();
  if (t_actual - t_previo >= intervalo){
    t_previo = t_actual;
    if (pinPrint > 512){
      Serial.print("...y la frecuencia cardíaca promedio, al cabo de ");
      Serial.print(intervalo/1000);
      Serial.print(" segundos es = ");
      Serial.print(6*cuenta_pulsos);
      Serial.println(" bpm.");
    }    
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
          
          // #2: Cálculo de la frecuencia cardíaca instantánea
          if (pinPrint > 512){
            Serial.print("La frecuencia cardíaca instantánea es = ");
            Serial.print(float(60)/PPI_value);
            Serial.println(" bpm.");
          }
          
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
            t_cresta = (t_pico_act - t_min_act)/float(1000); 
            t_descnd = (t_min_act - t_pico_prev)/float(1000);  
            pico_a_pico = (t_pico_act - t_pico_prev)/float(1000); 
            PPI_value = pico_a_pico;
            min_a_min = (t_min_act - t_min_prev)/float(1000); 

            t_cresta_n = float(t_cresta)/min_a_min; 
            t_descnd_n = float(t_descnd)/min_a_min; 
            amp_pulso_n = abs(float(amp_pulso)/value_max);    
            
            area_pulso = float(amp_pulso)/min_a_min;  

            // Actualizo tiempo de ocurrencia del mínimo
            t_min_prev = t_min_act;

            // #3: Cálculo de la frecuencia cardíaca instantánea
            if (pinPrint > 512){
              Serial.print("La frecuencia cardíaca instantánea es = ");
              Serial.print(float(60)/PPI_value);
              Serial.println(" bpm.");
            }
            
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
  // Cambiar !ReadyToPredict negado.
  if(dedoPresente && !tomandoDatos && !ReadyToPredict && digitalRead(PIN_SWITCH) == HIGH){
     // Variable de prueba, eliminar después ReadyToPredict = true;
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

    if (digitalRead(PIN_SWITCH) == LOW && !tomandoDatos) {
      ReadyToPredict = true;
      /*      
      Serial.print(t_cresta);
      Serial.print(", ");
      Serial.print(t_descnd);
      Serial.print(", ");
      Serial.print(pico_a_pico);
      Serial.print(", ");
      Serial.print(min_a_min);
      Serial.print(", ");
      Serial.println(area_pulso);
      Serial.print(amp_pulso);
      Serial.print(",");
      Serial.print(t_cresta);
      Serial.print(",");
      Serial.print(t_descnd);
      Serial.print(",");
      Serial.print(pico_a_pico);
      Serial.print(",");
      Serial.print(min_a_min);
      Serial.print(",");
      */
      Serial.print(muestra_actual);
      Serial.print(",");
      Serial.print(value_max);
      Serial.print(",");
      Serial.println(value_min);

    } else {
        ReadyToPredict = false; 
        Serial.println("🔘 Switch LIBERADO");
    }

    if (tomandoDatos){
      /*
      datos.push_back(value_max);
      */
      amp_pulso_data.push_back(amp_pulso);
      t_cresta_data.push_back(t_cresta);
      t_descnd_data.push_back(t_descnd);
      pico_a_pico_data.push_back(pico_a_pico);
      min_a_min_data.push_back(min_a_min);
      area_pulso_data.push_back(area_pulso);

      if (millis() - tiempoInicio >= (30 * 1000)){
        Serial.println("Tiempo Completado.");
        tomandoDatos = false;
        /*
        */
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
      /*
      || datos.size() >= 50
      */
      if(area_pulso_data.size() >= 100 || amp_pulso_data.size() >= 100 || t_cresta_data.size() >= 100 || t_descnd_data.size() >= 100 || pico_a_pico_data.size() >= 100 || min_a_min_data.size() >= 100){
        enviarLote();
      }

    } else if(ReadyToPredict && !tomandoDatos && dedoPresente){
      Serial.print("Listo para predecir: ");
      Serial.print(ReadyToPredict);
      Serial.print(", ");
      Serial.print("Tomando Datos: ");
      Serial.println(tomandoDatos);

      unsigned long currentMillis = millis();
      if(currentMillis - lastUpdateTime >= updateInterval){
          lastUpdateTime = currentMillis;

          FirebaseJson json_prediction;
          json_prediction.add("amp_pulso", amp_pulso);
          json_prediction.add("area_pulso", area_pulso);
          json_prediction.add("t_cresta", t_cresta);
          json_prediction.add("t_descnd", t_descnd);
          json_prediction.add("pico_a_pico", pico_a_pico);
          json_prediction.add("min_a_min", min_a_min);
          /*
          json_prediction.add("value_max", value_max);
          */

          if (!Firebase.RTDB.setJSON(&fbdo, "sensor/data_to_predict", &json_prediction)) {
          Serial.println("Error al establecer: " + fbdo.errorReason());
          } else {
          Serial.println("Datos enviados a Firebase");
          } 

          if(Firebase.RTDB.getBool(&fbdo, "sensor/tomar_medicion")){
            if (fbdo.boolData()){
              ReadyToPredict = false;
            }
          }
      }
     }

  } 
  // Se regula la tasa de muestreo porque la señal sale bastante ruidosa
  t_muestreo(periodo);

}


void enviarFirebaseTask(void * parameter) {
  for (;;) {
    if (WiFi.status() == WL_CONNECTED) {
      if (Firebase.ready() && signupOk) {
        if (!Firebase.RTDB.setBool(&fbdo, "/sensor/service_on", true)) {
          Serial.println("Error al escribir en Firebase: " + fbdo.errorReason());
        } else {
          Serial.println("Dato enviado correctamente");
        }
        time_t now;
        time(&now);
        if (!Firebase.RTDB.setDouble(&fbdo, "/sensor/working_time_esp", now * 1000)) {
          Serial.println("Error al escribir tiempo en Firebase: " + fbdo.errorReason());
        }
      } else {
        Serial.println("Firebase no está listo o signupOk false");
      }
    } else {
      Serial.println("WiFi no conectado");
    }

    vTaskDelay(10000 / portTICK_PERIOD_MS); // Esperar 10 segundos antes de siguiente envío
  }
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

int obtenerContadorDesdeFirebase(FirebaseData* fbdo, const String& nodo_actual, const String& nombre_variable) {
  String path = "/sensor/data/" + nodo_actual + "/" + nombre_variable;
  
  if (Firebase.RTDB.getJSON(fbdo, path)) {
    FirebaseJson* json = fbdo->jsonObjectPtr();
    FirebaseJsonData result;
    int maxKey = 0;

    // Recorremos las claves actuales
    size_t len = json->iteratorBegin();
    for (size_t i = 0; i < len; i++) {
      String key, value;
      int type;
      json->iteratorGet(i, type, key, value);
      int k = key.toInt();
      if (k >= maxKey) maxKey = k + 1;  // +1 para la siguiente disponible
    }
    json->iteratorEnd();
    return maxKey;
  }

  return 0;  // Si no existe, empezamos desde 0
}

void enviarJsonAFirebase(FirebaseData* fbdo, String nodo_actual, String nombre_variable, std::vector<double>& datos_vector, int& contador) {
  if (datos_vector.empty()) return;

  FirebaseJson json;
  for (double dato : datos_vector) {
    json.add(String(contador++), dato);
  }
  

  if (!Firebase.RTDB.updateNode(fbdo, "/sensor/data/" + nodo_actual + "/" + nombre_variable, &json)) {
    Serial.println("❌ Error al enviar '" + nombre_variable + "': " + fbdo->errorReason());
  }
  datos_vector.clear();
}


void enviarLote() {
  String nodo_actual = obtenerRutaMedicion();
  if (nodo_actual == "medicion_5"){
    ReadyToPredict = true;
  }
  if (nodo_actual == "") {
    Serial.println("❌ Error obteniendo nodo actual. Cancelando envío.");
    return;
  }

  enviarJsonAFirebase(&fbdo, nodo_actual, "amp_pulso", amp_pulso_data, countAmp_Pulso);
  enviarJsonAFirebase(&fbdo, nodo_actual, "area_pulso", area_pulso_data, countArea_Pulso);
  enviarJsonAFirebase(&fbdo, nodo_actual, "t_cresta", t_cresta_data, countT_Cresta);
  enviarJsonAFirebase(&fbdo, nodo_actual, "t_descnd", t_descnd_data, countT_descnd);
  enviarJsonAFirebase(&fbdo, nodo_actual, "pico_a_pico", pico_a_pico_data, countPico_A_Pico);
  enviarJsonAFirebase(&fbdo, nodo_actual, "min_a_min", min_a_min_data, countMin_A_Min);
  /*
  enviarJsonAFirebase(&fbdo, nodo_actual, "value_max", datos, countGlobal);
  */
  
}


void t_muestreo(uint32_t t_muestreo)
{
  uint32_t micros_now = (uint16_t)micros();
 
  while (t_muestreo > 0) {
    if (((uint16_t)micros() - micros_now) >= 1000) {
      t_muestreo--;
      micros_now += 1000;
    }
  }  
}


