"""
OBJETIVO: Script independiente para la ESP32-CAM. Captura y publica imágenes/eventos por MQTT.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, EPINOZA BRAVO LUDWING, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

import time
import json

class DummyCamaraMQTT:
    def publish(self, topic, payload):
        print(f"[ESP32-CAM] Publicando en {topic}: {payload}")

def main():
    print("=== NODO CAMARA INICIADO ===")
    client = DummyCamaraMQTT()
    topic_pub = "asistlab/sensor/camara/cam_01"
    
    # Bucle de simulación para eventos de cámara
    for i in range(3):
        time.sleep(3)
        evento = {"evento": "rostro_detectado", "confianza": 0.85 + (i * 0.05), "timestamp": time.time()}
        client.publish(topic_pub, json.dumps(evento))

if __name__ == "__main__":
    main()
