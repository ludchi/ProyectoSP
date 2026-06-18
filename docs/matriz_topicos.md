# Matriz de Tópicos MQTT
**Proyecto:** `asistlab` | **ID Principal:** `esp32_01` | **ID Cámara:** `cam_01`

| Tipo de Nodo | Tópico | Dirección | Payload / Función |
| :--- | :--- | :--- | :--- |
| **sensor** | `asistlab/sensor/rfid/esp32_01` | ESP32 → Python | UID detectado |
| **sensor** | `asistlab/sensor/resumen/esp32_01` | ESP32 → Python | JSON con el consolidado base (UID y BPM) |
| **sensor** | `asistlab/sensor/camara/cam_01` | CAM → Python | Evento de captura / Frame codificado en Base64 |
| **comando** | `asistlab/cmd/oled/esp32_01` | Python → ESP32 | Instrucción de texto para pantalla |
| **comando** | `asistlab/cmd/actuadores/esp32_01` | Python → ESP32 | Acciones de alerta y confirmación (`registro_ok`, `registro_fatiga`, `apagar`) |
