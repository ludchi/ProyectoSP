# Guía Paso a Paso: Ensamble Físico y Configuración de ESP32

Esta guía detalla las conexiones físicas, los archivos que necesitas cargar a la ESP32 y la configuración de la red MQTT para que el prototipo pase de "simulación en PC" a **Hardware Real**.

## 1. Tabla de Conexiones a detalle (Estilo Diagrama/Proteus)

Esta tabla describe la conexión **cable por cable** y especifica exactamente dónde necesitas agregar componentes electrónicos pasivos (resistencias, diodos) para proteger la ESP32 y asegurar la estabilidad, tal cual lo armarías en un esquemático de Proteus.

> [!CAUTION]
> **TIERRAS COMUNES:** Asegúrate de que todos los pines GND de todos los módulos y la ESP32 estén interconectados. (Excepto el circuito del solenoide si usas un relé optoacoplado para aislar, pero por simplicidad, los GND del relé van al ESP32 y el de la carga va a su fuente).

| Componente Módulo | Pin del Componente | Conexión / Destino | Componente Extra Requerido (Protección) | Explicación del circuito |
|---|---|---|---|---|
| **Alimentación ESP32** | VIN / 5V | N/A | Ninguno | Entrada de 5V (desde el USB o fuente externa regulada). |
| | GND | Bus GND Común | Ninguno | Nodo principal de tierra de todo el sistema. |
| | 3V3 | Bus 3.3V | Ninguno | Pin de salida de la ESP32 que proveerá energía a módulos lógicos. |
| **OLED SSD1306** | VCC | Bus 3.3V (Pin `3V3`) | Ninguno | Alimentación lógica. |
| | GND | Bus GND Común | Ninguno | Cierra circuito a tierra. |
| | SDA | ESP32 `GPIO 21` | Pull-ups 4.7kΩ (Opcional)* | Conexión directa. *(La mayoría de módulos OLED ya integran resistencias pull-up SMD a 3.3V. Solo agrega unas externas a 3.3V si el I2C falla).* |
| | SCL | ESP32 `GPIO 22` | Pull-ups 4.7kΩ (Opcional)* | Conexión directa. |
| **MAX30102 (Pulso)**| VIN / VCC | Bus 5V (Pin `VIN`) | Ninguno | **¡CRÍTICO!** Conectar a 5V (VIN). Si se conecta a 3.3V, el consumo de sus LEDs reiniciará el lector RFID. |
| | GND | Bus GND Común | Ninguno | Cierra circuito a tierra. |
| | SDA | ESP32 `GPIO 21` | Ninguno (Directo) | Va en el mismo bus I2C en paralelo al OLED. |
| | SCL | ESP32 `GPIO 22` | Ninguno (Directo) | Va en el mismo bus I2C en paralelo al OLED. |
| **RC522 (RFID)** | 3.3V | Bus 3.3V (Pin `3V3`) | Ninguno | **¡Estricto!** Conectar a 5V quema este lector. |
| | GND | Bus GND Común | Ninguno | Cierra circuito a tierra. |
| | SDA (SS/CS) | ESP32 `GPIO 17` | Ninguno | Cable directo (Chip Select SPI). ¡Cuidado, no confundir con el SDA del I2C! |
| | SCK | ESP32 `GPIO 18` | Ninguno | Cable directo (Reloj SPI). |
| | MOSI | ESP32 `GPIO 19` | Ninguno | Cable directo (Master Out Slave In). |
| | MISO | ESP32 `GPIO 16` | Ninguno | Cable directo (Master In Slave Out). |
| | RST | Bus 3.3V (Pin `3V3`) | Ninguno | Cable directo a 3.3V. Ya no lo controlamos por código para mayor estabilidad. |
| **HC-SR04 (Ultra)** | VCC | Bus 5V (Pin `VIN`) | Ninguno | Este sensor requiere 5V para un buen alcance acústico. |
| | GND | Bus GND Común | Ninguno | Cierra circuito a tierra. |
| | TRIG | ESP32 `GPIO 13` | Ninguno | Cable directo. El pulso 3.3V de la ESP32 basta para disparar el sensor. |
| | ECHO | ESP32 `GPIO 12` | **¡SÍ! Divisor de Tensión:**<br>• Resistor 1kΩ (Serie de ECHO a GPIO 12)<br>• Resistor 2kΩ (Derivación de GPIO 12 a GND) | **¡CRÍTICO!** El sensor envía un pulso de retorno de **5V**. El divisor baja el voltaje a ~3.3V para evitar quemar el pin GPIO 12. |
| **Módulo Relé (5V)** | VCC / DC+ | Bus 5V (Pin `VIN`) | Ninguno | Alimentación de la bobina electromagnética. |
| | GND / DC- | Bus GND Común | Ninguno | Cierra circuito lógico. |
| | IN / Señal | ESP32 `GPIO 26` | Ninguno | Cable directo. La señal 3.3V de la ESP32 activará el optoacoplador del relé. |
| | Bornera COM | Positivo 12V (Ext.) | **Fuente Externa 12V** | Usar una fuente independiente (ej. cargador 12V 2A). |
| | Bornera NO | Cable Solenoide (+) | Ninguno | Salida normalmente abierta hacia el solenoide. |
| **Solenoide 12V** | Cable 1 (Fase) | Relé (Bornera NO) | **Diodo Flyback (1N4007)** | Conectar el diodo **en paralelo** a los dos cables del solenoide, con la banda gris (cátodo) hacia el positivo. Evita reinicios por picos de la bobina. |
| | Cable 2 (Tierra) | Negativo 12V (Ext.) | Ninguno | Regreso de corriente hacia la fuente de 12V externa. |
| **Buzzer Activo** | VCC (+) / Pata larga| ESP32 `GPIO 27` | **Resistor 220Ω - 330Ω** | Conectar en serie el resistor entre el GPIO 27 y la pata positiva del buzzer para limitar la corriente (~10mA). |
| | GND (-) / Pata corta| Bus GND Común | Ninguno | Cierra circuito a tierra. |
| **ESP32-CAM (Cámara)** | 5V / VCC | Bus 5V (Pin `VIN` o Fuente 5V Ext.) | **Fuente de al menos 1A-2A** | Módulo independiente (no se conecta a los GPIO de la ESP32 principal). Requiere muy buena alimentación de 5V para que el Wi-Fi y la cámara no se reinicien. |
| | GND | Bus GND Común | Ninguno | Cierra circuito a tierra. |

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
