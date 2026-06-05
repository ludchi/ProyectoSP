# Guía Paso a Paso: Ensamble Físico y Configuración de ESP32

Esta guía detalla las conexiones físicas, los archivos que necesitas cargar a la ESP32 y la configuración de la red MQTT para que el prototipo pase de "simulación en PC" a **Hardware Real**.

## 1. Tabla de Conexiones (Pinout Sugerido para ESP32)

> [!WARNING]
> Recuerda que el sensor HC-SR04 suele funcionar a 5V y su pin ECHO enviará 5V a la ESP32 (que soporta máximo 3.3V). Utiliza un divisor de voltaje (resistencias) en el pin ECHO para no dañar tu ESP32.

| Módulo | Pin del Módulo | Pin ESP32 | Notas |
|---|---|---|---|
| **Alimentación** | GND | `GND` | Une todos los GND de todos los módulos. |
| | VCC (5V) | `VIN` / `5V` | HC-SR04 y Módulo Relé (para solenoide). |
| | VCC (3.3V) | `3V3` | RC522, OLED, MAX30102. |
| **Bus I2C (Compartido)** | SDA | `GPIO 21` | Conectar aquí SDA del OLED y del MAX30102. |
| | SCL | `GPIO 22` | Conectar aquí SCL del OLED y del MAX30102. |
| **RFID RC522 (Bus SPI)** | SDA / SS | `GPIO 5` | |
| | SCK | `GPIO 18` | |
| | MOSI | `GPIO 23` | |
| | MISO | `GPIO 19` | |
| | RST | `GPIO 4` | |
| **Ultrasonido HC-SR04** | TRIG | `GPIO 13` | |
| | ECHO | `GPIO 12` | **¡Precaución!** Usar divisor de voltaje. |
| **Actuadores** | IN (Relé Solenoide)| `GPIO 26` | El relé manejará los 12V del solenoide. |
| | Señal Buzzer | `GPIO 27` | |

---

## 2. Archivos que debes guardar dentro de la ESP32

Actualmente tu código (`dispositivos.py` y `mqtt_esp32.py`) está hecho como una **simulación para PC** (usa clases `DummyMQTTClient` y valores aleatorios). Para el hardware real, debes conectar la placa mediante USB, abrir el IDE **Thonny** e instalar el firmware de **MicroPython**.

Una vez que tengas MicroPython, debes guardar **obligatoriamente** los siguientes archivos dentro de la memoria de la ESP32:

1. **`boot.py`**: Este archivo se ejecuta al encender. Aquí debes poner el código para conectarte a la red Wi-Fi.
2. **Librerías de Hardware**:
   - `umqttsimple.py`: Para la conexión MQTT.
   - `ssd1306.py`: Para controlar la pantalla OLED.
   - `mfrc522.py`: Para leer las tarjetas RFID.
   - `max30102.py`: Para leer el pulso cardíaco.
   - `hcsr04.py`: Para el ultrasonido.
3. **`main.py`**: Este será tu archivo principal. Debe contener la lógica real de tu `mqtt_esp32.py`, pero importando y usando las librerías mencionadas arriba en lugar de las clases "Dummy" y falsas.

---

## 3. ¿Cómo configurar MQTT?

La configuración de MQTT es el puente entre tu ESP32 física y tu servidor Python. 

**Paso A: Instalar un Broker**
Necesitas un programa que haga de "Broker" (el mensajero). Lo más estándar es instalar **Mosquitto MQTT** en tu computadora. 
* Si ya lo tienes, asegúrate de que el servicio esté corriendo en tu PC en el puerto `1883`.

**Paso B: Red Local (Wi-Fi)**
Tu ESP32 y la computadora donde corre el servidor Python **deben estar conectados al mismo módem o red Wi-Fi**.
1. Averigua la dirección IPv4 local de tu computadora (por ejemplo, `192.168.1.15`). En Windows puedes usar el comando `ipconfig` en la terminal.

**Paso C: Configurar IP en la ESP32**
Dentro del archivo `main.py` de tu ESP32, debes actualizar la constante del Broker apuntando a la IP de tu computadora:

```python
# En tu archivo main.py dentro de la ESP32
import network
from umqttsimple import MQTTClient

BROKER_IP = "192.168.1.15"  # <-- Cambia esto por la IPv4 de tu computadora
CLIENT_ID = "esp32_hardware"
TOPIC_BASE = "asistlab"

# El código debe conectarse usando umqttsimple:
# client = MQTTClient(CLIENT_ID, BROKER_IP)
# client.connect()
```

**Paso D: Iniciar en orden**
1. Ejecuta el servidor Python en tu PC (`python mqtt_server.py`).
2. Enciende la ESP32 (se conectará al Wi-Fi, luego al Broker MQTT de tu PC y empezará a enviar lecturas de sensores reales).
