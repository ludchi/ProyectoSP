# Sistema Integral de Registro de Asistencias y Detección de Desgaste Laboral (AsistLab)

**🌐 Dashboard Web en Vivo:** [https://sadl-a3713.web.app](https://sadl-a3713.web.app)

## 📌 Objetivo General
Desarrollar un sistema IoT físico empotrado, conectado a la nube y orquestado por Inteligencia Artificial, orientado a la seguridad industrial. El sistema reemplaza el clásico checador de reloj por una validación de doble factor (RFID + Biometría), midiendo variables fisiológicas (BPM) con el sensor MAX30102 para calcular el estrés mediante el diferencial cardíaco de la jornada. 

Adicionalmente, integra un nodo de visión computacional (ESP32-CAM) que procesa fotogramas en milisegundos en un servidor perimetral local utilizando **MediaPipe Face Landmarker**, diagnosticando posibles episodios de microsueños o fatiga (mediante la tasa de apertura ocular EAR) y alertando visual y acústicamente al instante.

## 👥 Equipo de Desarrollo
- **CASTRO LUNA CESAR ARMANDO** (Hardware HAL y Ensamble)
- **ESPINOZA BRAVO LUDWIG** (Backend, IA y Comunicaciones MQTT)
- **LOZANO CARDONA ANGEL JOSUE** (Frontend Reactivo, UX y Modelado 3D)

---

## 🏗️ Estructura del Repositorio
* `nodos_hardware/nodo_principal/`: Firmware en **MicroPython** implementando una capa HAL (CajaSensores y CajaActuadores) aislando los buses SPI e I2C del cliente MQTT. Controla RFID, Pulso, OLED, LEDs y Buzzer.
* `nodos_hardware/nodo_camara/`: Firmware en **C++ (Arduino)** para la ESP32-CAM. Captura frames asíncronos y los empuja a la red local codificados en Base64 vía MQTT.
* `servidor_python/`: **Cerebro Central Perimetral**. Escucha la red local, aplica bloqueos Anti-Spam (5 minutos), analiza rostros con OpenCV/MediaPipe y sube datos limpios a Firestore.
* `panel_web/`: Aplicación Frontend web moderna (`HTML/JS/CSS Vanilla`) que consume el SDK de Firebase (v10) con `onSnapshot` para reflejar asistencias y alertas instantáneamente (cero polling).
* `docs/`: Documentos de ingeniería (Guía de Ensamble, Plan de Implementación, Logs, Reportes Técnicos y Walkthroughs).

---

## 🛠️ Materiales y Tecnologías
**Hardware:**
- Microcontrolador Maestro ESP32 y Esclavo ESP32-CAM.
- RFID RC522 (Control de Identidad).
- MAX30102 (Huella Cardíaca).
- Actuadores: Pantalla OLED SSD1306, LED Verde, LED Rojo y Buzzer Pasivo.

**Software:**
- **MQTT (Mosquitto):** Protocolo de transporte asíncrono para telemetría a baja latencia.
- **Python (OpenCV, MediaPipe):** Extracción de coordenadas faciales en 3D para el cálculo matemático del EAR (Eye Aspect Ratio).
- **Firebase (Firestore + Hosting):** Base de datos NoSQL reactiva en la nube y hosting web estático.

---

## 🚀 Instalación y Ejecución

1. **Dependencias del Servidor:**
   Asegúrate de tener un Broker MQTT local activo (ej. Eclipse Mosquitto en el puerto 1883).
   ```bash
   pip install -r requirements.txt
   ```
2. **Hardware:**
   Carga el script `main.py` en la ESP32 principal y el `.ino` en la cámara, apuntando ambos a tu red WiFi local y la IP de la computadora que servirá como host.
3. **Ejecutar el Servidor de Inteligencia:**
   ```bash
   python servidor_python/mqtt_server.py
   ```

---

## ⚙️ Arquitectura Lógica End-to-End
1. **Doble Factor (Capa de Sensores):** El empleado escanea su RFID. Si el servidor lo valida y no está en "Cooldown Anti-Spam", la OLED indica que coloque el dedo en el MAX30102.
2. **Cola Asíncrona (Capa de Servidor):** El servidor obtiene el pulso y entra en espera activa (hasta 120 segundos) sin bloquear la red, pidiéndole al empleado que mire a la cámara.
3. **Visión Computacional:** Cuando el empleado mira, el servidor perimetral intercepta la imagen MQTT de la ESP32-CAM y ejecuta MediaPipe. 
   - **Registro Normal (Vigilia):** Se emite un comando MQTT. La ESP32 enciende el LED Verde, toca un beep corto y se registra en Firebase.
   - **Registro Anómalo (Fatiga):** Si el EAR < 0.25, el servidor lanza alerta por MQTT: La ESP32 activa el LED Rojo, hace sonar 3 beeps graves, y Firestore etiqueta el registro en rojo para Recursos Humanos.
4. **Calculo de Desgaste (Salida):** Al checar salida, Firebase retorna el pulso original de entrada, calcula el diferencial de estrés y grafica la tendencia laboral del día en el Dashboard.
