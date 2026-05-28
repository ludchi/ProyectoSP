# Matriz de Tópicos MQTT
**Proyecto:** `asistlab` | **ID Principal:** `esp32_01` | **ID Cámara:** `cam_01`

| Tipo de Nodo | Tópico | Dirección | Payload / Función |
| :--- | :--- | :--- | :--- |
| **sensor** | `asistlab/sensor/rfid/esp32_01` | ESP32 → Python | UID detectado |
| **sensor** | `asistlab/sensor/ultrasonido/esp32_01` | ESP32 → Python | Distancia (cm) |
| **sensor** | `asistlab/sensor/pulso/esp32_01` | ESP32 → Python | BPM y HRV (ms) para desgaste |
| **sensor** | `asistlab/sensor/camara/cam_01` | CAM → Python | Evento de captura / Frame codificado |
| **sensor** | `asistlab/sensor/resumen/esp32_01` | ESP32 → Python | JSON con el consolidado base |
| **actuador** | `asistlab/actuador/oled/esp32_01` | ESP32 → Python | Último mensaje mostrado |
| **actuador** | `asistlab/actuador/buzzer/esp32_01` | ESP32 → Python | Tono emitido actual |
| **actuador** | `asistlab/actuador/solenoide/esp32_01` | ESP32 → Python | Estado de la puerta (Abierta/Cerrada) |
| **comando** | `asistlab/cmd/oled/esp32_01` | Python → ESP32 | Instrucción de texto para pantalla |
| **comando** | `asistlab/cmd/buzzer/esp32_01` | Python → ESP32 | Emitir tono (ok, alerta, error) |
| **comando** | `asistlab/cmd/solenoide/esp32_01` | Python → ESP32 | Activar solenoide para el check-in |
| **comando** | `asistlab/cmd/camara/cam_01` | Python → CAM | Orden para tomar foto |
| **comando** | `asistlab/cmd/safe/esp32_01` | Python → ESP32 | **OBLIGATORIO:** Apagar hardware de emergencia |
