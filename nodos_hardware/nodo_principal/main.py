"""
OBJETIVO: Archivo principal de ejecución de la ESP32. Delega el control al script MQTT.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, EPINOZA BRAVO LUDWING, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

import mqtt_esp32

if __name__ == "__main__":
    mqtt_esp32.main()
