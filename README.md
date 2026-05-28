# Sistema de registro de Asistencias y Desgaste Laboral

Este repositorio contiene la integración total vía MQTT entre nodos ESP32 y un servidor Python, utilizando una capa de abstracción de hardware (HAL).

## Integrantes
- CASTRO LUNA CESAR ARMANDO
- EPINOZA BRAVO LUDWING
- LOZANO CARDONA ANGEL JOSUE

## Estructura del Repositorio
* `nodos_hardware/nodo_principal/`: Código MicroPython para la ESP32 encargada de los sensores RFID, MAX30102, HC-SR04 y los actuadores (OLED, Solenoide, Buzzer).
* `nodos_hardware/nodo_camara/`: Código independiente para la ESP32-CAM.
* `servidor_python/`: Script del servidor central que recibe telemetría y publica comandos.
* `docs/`: Documentación técnica incluyendo la Matriz de Tópicos MQTT y los Reportes de Análisis Individual.

## Cómo ejecutar la simulación en PC
Si deseas probar la lógica de comunicación sin el hardware físico, puedes ejecutar:
1. `python servidor_python/mqtt_server.py`
2. `python nodos_hardware/nodo_principal/mqtt_esp32.py`
