# Guía Paso a Paso: Ensamble Físico y Configuración de ESP32

Esta guía detalla las conexiones físicas, los archivos que necesitas cargar a la ESP32 y la configuración de la red MQTT para que el prototipo pase de "simulación en PC" a **Hardware Real**.

## 1. Tabla de Conexiones a detalle

Esta tabla describe la conexión **cable por cable**. El diseño final se ha simplificado eliminando el relé, solenoide, buzzer y sensor ultrasónico para enfocarse únicamente en el registro biométrico y de asistencias.

> [!CAUTION]
> **TIERRAS COMUNES:** Asegúrate de que todos los pines GND de todos los módulos y las ESP32 estén interconectados para evitar lecturas flotantes.

| Componente Módulo | Pin del Componente | Conexión / Destino | Componente Extra Requerido (Protección) | Explicación del circuito |
|---|---|---|---|---|
| **Alimentación ESP32** | VIN / 5V | N/A | Ninguno | Entrada de 5V (desde el USB o fuente externa regulada). |
| | GND | Bus GND Común | Ninguno | Nodo principal de tierra de todo el sistema. |
| | 3V3 | Bus 3.3V | Ninguno | Pin de salida de la ESP32 que proveerá energía a módulos lógicos. |
| **OLED SSD1306** | VCC | Bus 3.3V (Pin `3V3`) | Ninguno | Alimentación lógica. |
| | GND | Bus GND Común | Ninguno | Cierra circuito a tierra. |
| | SDA | ESP32 `GPIO 21` | Pull-ups 4.7kΩ (Opcional)* | Conexión directa. *(La mayoría de módulos OLED ya integran resistencias pull-up SMD a 3.3V).* |
| | SCL | ESP32 `GPIO 22` | Pull-ups 4.7kΩ (Opcional)* | Conexión directa. |
| **MAX30102 (Pulso)**| VIN / VCC | Bus 5V (Pin `VIN`) | Ninguno | **¡CRÍTICO!** Conectar a 5V (VIN). Si se conecta a 3.3V, el consumo de sus LEDs reiniciará el lector RFID y la pantalla OLED. |
| | GND | Bus GND Común | Ninguno | Cierra circuito a tierra. |
| | SDA | ESP32 `GPIO 21` | Ninguno (Directo) | Va en el mismo bus I2C en paralelo al OLED. |
| | SCL | ESP32 `GPIO 22` | Ninguno (Directo) | Va en el mismo bus I2C en paralelo al OLED. |
| **RC522 (RFID)** | 3.3V | Bus 3.3V (Pin `3V3`) | Ninguno | **¡Estricto!** Conectar a 5V quema este lector. |
| | GND | Bus GND Común | Ninguno | Cierra circuito a tierra. |
| | SDA (SS/CS) | ESP32 `GPIO 17` | Ninguno | Cable directo (Chip Select SPI). |
| | SCK | ESP32 `GPIO 18` | Ninguno | Cable directo (Reloj SPI). |
| | MOSI | ESP32 `GPIO 19` | Ninguno | Cable directo (Master Out Slave In). |
| | MISO | ESP32 `GPIO 16` | Ninguno | Cable directo (Master In Slave Out). |
| | RST | Bus 3.3V (Pin `3V3`) | Ninguno | Cable directo a 3.3V para mayor estabilidad. |
| **ESP32-CAM (Cámara)** | 5V / VCC | Bus 5V (Pin `VIN` o Fuente 5V Ext.) | **Fuente de al menos 1A-2A** | Módulo independiente. Requiere muy buena alimentación de 5V para que el Wi-Fi no se desconecte durante la transmisión MQTT. |
| | GND | Bus GND Común | Ninguno | Cierra circuito a tierra. |
| **LED Rojo (Fatiga)** | Ánodo (Pata Larga) | ESP32 `GPIO 2` | Resistencia 220Ω | Indicador visual cuando la IA detecta fatiga en el registro. |
| | Cátodo (Pata Corta)| Bus GND Común | Ninguno | Cierra circuito a tierra. |
| **LED Verde (Registro OK)**| Ánodo (Pata Larga) | ESP32 `GPIO 4` | Resistencia 220Ω | Indicador visual de registro exitoso sin fatiga. |
| | Cátodo (Pata Corta)| Bus GND Común | Ninguno | Cierra circuito a tierra. |
| **Buzzer Pasivo** | Pin Positivo (+) | ESP32 `GPIO 15` | Ninguno | Emite beeps cortos (registro OK) o largos y graves (fatiga). |
| | Pin Negativo (-) | Bus GND Común | Ninguno | Cierra circuito a tierra. |

---

## 2. Archivos que debes guardar dentro de la ESP32 (MicroPython)

Actualmente tu código (`dispositivos.py` y `mqtt_esp32.py`) está en Python estándar simulando el hardware para PC. Para la placa real física (ESP32 Principal), debes conectar por USB, abrir el IDE **Thonny** y guardar estos archivos dentro de la ESP32:

1. **`boot.py`**: Para conectarte a la red Wi-Fi.
2. **Librerías de Hardware**:
   - `umqttsimple.py`: Para MQTT.
   - `ssd1306.py`: Para la pantalla OLED.
   - `mfrc522.py`: Para el RFID.
   - `max30102.py`: Para el pulso cardíaco.
3. **`main.py`**: Este será tu archivo principal. Debe contener la lógica de tu `mqtt_esp32.py`, pero adaptada para MicroPython real.

> [!NOTE]
> La **ESP32-CAM** usa su propio programa (C++/Arduino), sube el archivo `.ino` que tienes en la carpeta `nodo_camara` a través de Arduino IDE.

---

## 3. Configuración de MQTT

El servidor de Python y Mosquitto son el "Cerebro".

**Paso A: Instalar Mosquitto**
Tener corriendo el servicio en la PC en el puerto `1883`.

**Paso B: Red Local**
Tu ESP32, la ESP32-CAM y la computadora del servidor Python **deben estar conectados al mismo Wi-Fi**. Asegúrate de obtener la IP IPv4 de tu computadora (ej. `192.168.1.15`).

**Paso C: Iniciar el Sistema**
1. Ejecuta el servidor central: `python servidor_python/mqtt_server.py`.
2. Enciende la ESP32-CAM (empezará a mandar Base64 a `asistlab/sensor/camara/cam_01`).
3. Enciende la ESP32 principal (enviará el UID de la tarjeta y el BPM cuando escanees).
