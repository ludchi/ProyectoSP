"""
OBJETIVO: Integración de IA para Simulación de ESP32-CAM y Transmisión MQTT
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, ESPINOZA BRAVO LUDWIG, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

import time
import json
import base64
import os

class DummyCamaraMQTT:
    def publish(self, topic, payload):
        # Truncamos el payload si es muy largo para no saturar la consola
        preview = payload[:50] + "..." if len(payload) > 50 else payload
        print(f"[ESP32-CAM] Publicando en {topic}: {preview}")

def image_to_base64(image_path):
    if not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

def main():
    print("=== NODO CAMARA INICIADO (Modo IA) ===")
    client = DummyCamaraMQTT()
    topic_pub = "asistlab/sensor/camara/cam_01"
    
    # Suponemos que test_face.jpg está en la carpeta data
    test_img_path = "../../servidor_python/data/test_face.jpg"
    
    # Bucle de simulación para eventos de cámara
    for i in range(3):
        time.sleep(3)
        b64_img = image_to_base64(test_img_path)
        
        if b64_img:
            evento = {
                "evento": "frame_capturado", 
                "imagen_b64": b64_img,
                "timestamp": time.time()
            }
            client.publish(topic_pub, json.dumps(evento))
        else:
            print(f"[ESP32-CAM] Error: Imagen {test_img_path} no encontrada.")

if __name__ == "__main__":
    main()
