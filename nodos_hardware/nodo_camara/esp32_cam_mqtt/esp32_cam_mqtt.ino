#include "esp_camera.h"
#include <WiFi.h>
#include <PubSubClient.h>
#include <base64.h>

// ===========================
// CONFIGURACIÓN DE RED Y MQTT
// ===========================
const char* ssid = "INFINITUM90AF";
const char* password = "ZacnYPtK3g";
const char* mqtt_server = "192.168.1.168"; // IP de tu computadora (Mosquitto)

const char* mqtt_topic_cam = "asistlab/sensor/camara/cam_01";
const char* client_id = "esp32_cam_01";

WiFiClient espClient;
PubSubClient client(espClient);

// ===========================
// CONFIGURACIÓN DE PINES (AI THINKER)
// ===========================
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Conectando a ");
  Serial.println(ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi conectado");
  Serial.println("Dirección IP: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Intentando conexión MQTT...");
    if (client.connect(client_id)) {
      Serial.println("conectado al Broker!");
    } else {
      Serial.print("falló, rc=");
      Serial.print(client.state());
      Serial.println(" intentando en 5 segundos");
      delay(5000);
    }
  }
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); // Desactivar el detector de caídas de voltaje
  
  Serial.begin(115200);
  Serial.setDebugOutput(true);
  Serial.println();

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  
  // ¡CRUCIAL! Ampliar el buffer de MQTT para que quepan las fotos (hasta 20KB)
  client.setBufferSize(20480);

  // Inicialización de cámara
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  
  // Para enviar por MQTT, la imagen debe ser pequeña
  config.frame_size = FRAMESIZE_QVGA; // 320x240
  config.jpeg_quality = 30; // Mayor número = Más comprimida (Menos peso en bytes)
  config.fb_count = 1;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Error al inicializar cámara con código 0x%x", err);
    return;
  }
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Tomar una foto cada 5 segundos
  delay(5000);

  camera_fb_t * fb = NULL;
  fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println("Error al capturar la imagen");
    return;
  }

  Serial.println("Foto capturada, codificando a Base64...");
  
  // Codificar a base64
  String encoded = base64::encode(fb->buf, fb->len);
  
  Serial.print("Enviando a MQTT... Tamaño B64: ");
  Serial.print(encoded.length());
  Serial.print(" | Memoria RAM Libre: ");
  Serial.println(ESP.getFreeHeap());

  // Usar beginPublish para transmitir en trozos y evitar desbordar el buffer de golpe
  if (client.beginPublish(mqtt_topic_cam, encoded.length(), false)) {
    const int CHUNK_SIZE = 1024;
    for (int i = 0; i < encoded.length(); i += CHUNK_SIZE) {
      String chunk = encoded.substring(i, i + CHUNK_SIZE);
      client.print(chunk);
    }
    
    if (client.endPublish()) {
      Serial.println("Imagen enviada con éxito");
    } else {
      Serial.println("Fallo al finalizar el envío.");
    }
  } else {
    Serial.println("Fallo al enviar la imagen (El tamaño superó el buffer ampliado).");
  }

  // Liberar memoria explícitamente
  encoded = "";
  esp_camera_fb_return(fb);
}
