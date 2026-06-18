# Plan de Implementación Consolidado

A continuación se detalla el plan de implementación de las diferentes fases técnicas aplicadas al **Sistema de registro de Asistencias y Desgaste Laboral**, abarcando desde la capa de hardware (HAL), la comunicación (MQTT), el almacenamiento en la nube (Firebase), hasta el procesamiento avanzado con Inteligencia Artificial.

---

## Fase 1: Arquitectura HAL y Protocolo MQTT
**Objetivo:** Desacoplar la lógica de hardware de la lógica de red, permitiendo a la ESP32 principal comunicarse eficientemente y enviar telemetría a un servidor central.

### 1.1 Hardware Abstraction Layer (HAL)
Se diseñó el archivo `dispositivos.py` para abstraer el control de:
- **Sensores:** Lector RFID (RC522) y Sensor de Pulso (MAX30102).
- **Actuadores:** Pantalla OLED SSD1306, LED Rojo (Alerta Fatiga), LED Verde (OK) y Buzzer Pasivo (Confirmación Sonora).

Esta separación permite que el código principal (`mqtt_esp32.py` o `main.py`) llame a métodos limpios como `actuadores.mostrar_mensaje()` o `actuadores.alerta_fatiga()` sin lidiar con los buses I2C, SPI o GPIO directamente.

### 1.2 Protocolo de Comunicación (MQTT)
Se estandarizó una matriz jerárquica de tópicos para todo el proyecto:
- **Telemetría (Lectura):** `asistlab/sensor/[TIPO]/[ID_DISPOSITIVO]` (ej. `asistlab/sensor/resumen/esp32_01`)
- **Comandos (Escritura):** `asistlab/cmd/[TIPO]/[ID_DISPOSITIVO]` (ej. `asistlab/cmd/actuadores/esp32_01`)

El servidor Python (`mqtt_server.py`) actúa como el cerebro del sistema. Escucha los tópicos de los sensores y, dependiendo de la lógica de negocio (ej. "Registro Exitoso" o "Fatiga Detectada"), publica comandos de regreso a los actuadores correspondientes (OLED, LEDs y Buzzer).

---

## Fase 2: Integración en la Nube y Dashboard (Firebase)
**Objetivo:** Proveer almacenamiento persistente para la telemetría y crear una interfaz visual para control remoto, manteniendo la asincronía.

### 2.1 Backend (Servidor Python)
- Se integró `firebase-admin` en el archivo `firebase_config.py`.
- Las lecturas entrantes vía MQTT son registradas en la colección `telemetria`.
- El servidor establece un "Listener en tiempo real" (`on_snapshot` y `FieldFilter`) sobre la colección `comandos_remotos` de Firestore. Si detecta un comando pendiente, lo envía automáticamente hacia la ESP32 por MQTT.

### 2.2 Frontend (Dashboard AsistLab)
- Interfaz moderna (HTML/JS) que consume el SDK web de Firebase (v10).
- Permite observar los registros en tiempo real sin recargar la página.
- Botones de "Acciones Remotas" permiten al operador web abrir la puerta o disparar alarmas manualmente insertando documentos en Firestore.

---

## Fase 3: Inteligencia Artificial (Detección de Fatiga)
**Objetivo:** Utilizar la ESP32-CAM para detectar el "Desgaste Laboral" analizando el estado de vigilia de los empleados.

### 3.1 Modelo de IA (MediaPipe)
Se seleccionó **MediaPipe Face Landmarker** de Google, el cual es altamente preciso (~95% en buenas condiciones de luz). En el archivo `ai_processor.py`, la clase `FatigueDetector` extrae los landmarks faciales de los ojos y aplica la fórmula **Eye Aspect Ratio (EAR)**.
- Un EAR alto indica estado de vigilia (ojos abiertos).
- Un EAR bajo (<0.25) indica estado de fatiga o somnolencia.

### 3.2 Pipeline Extremo a Extremo
1. La **ESP32-CAM** (`camara_mqtt.py`) toma la fotografía, la codifica en Base64 y la publica en un tópico MQTT dedicado con QoS 0.
2. El **Servidor Python** intercepta el Base64, lo decodifica a una matriz de OpenCV y lo procesa con la IA.
3. Si el EAR es bajo, el servidor Python dispara de manera autónoma un comando MQTT hacia el **Buzzer de la ESP32 principal** alertando al empleado, y sube una `Alerta_IA` nivel *danger* a Firebase.
