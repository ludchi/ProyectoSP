# Sistema de registro de Asistencias y Desgaste Laboral

## Objetivo
Consolidar un sistema robusto de extremo a extremo que permita el registro de asistencias y el monitoreo del desgaste laboral (mediante medición de pulso/oxígeno y distancia), integrando nodos de hardware (ESP32) mediante MQTT, procesamiento de IA en un servidor Python y registro final en Firebase, encapsulado en un prototipo físico con apariencia de producto terminado.

## Integrantes
- CASTRO LUNA CESAR ARMANDO - [Código]
- EPINOZA BRAVO LUDWING - [Código]
- LOZANO CARDONA ANGEL JOSUE - [Código]

## Estructura del Repositorio
* `nodos_hardware/nodo_principal/`: Código MicroPython para la ESP32 encargada de los sensores RFID, MAX30102, HC-SR04 y los actuadores (OLED, Solenoide, Buzzer).
* `nodos_hardware/nodo_camara/`: Código independiente para la ESP32-CAM.
* `servidor_python/`: Script del servidor central que recibe telemetría y publica comandos.
* `frontend/`: Código de la interfaz web para visualización del dashboard.
* `docs/`: Documentación técnica incluyendo la Matriz de Tópicos MQTT y los Reportes de Análisis Individual.
* `hardware/`: **(NUEVO)** Carpeta para subir fotos del proceso de soldadura y los diseños de la carcasa (STLs o planos).

## Cómo ejecutar la simulación en PC
Si deseas probar la lógica de comunicación sin el hardware físico, puedes ejecutar:
1. `python servidor_python/mqtt_server.py`
2. `python nodos_hardware/nodo_principal/mqtt_esp32.py`
