"""
OBJETIVO: Recibir telemetría MQTT desde la ESP32, registrar timestamps y publicar comandos hacia los actuadores como servidor de control.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, EPINOZA BRAVO LUDWING, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

import json
from datetime import datetime
import firebase_config
import os
from ai_processor import FatigueDetector

class DummyPahoClient:
    def subscribe(self, topic): print(f"[PYTHON-SERVER] Suscrito a: {topic}")
    def publish(self, topic, payload): print(f"[PYTHON-SERVER] CMD -> {topic}: {payload}")

BROKER = "192.168.0.100"
CLIENT_ID = "server_python_01"
TOPIC_BASE = "asistlab"
DEVICE_ID = "esp32_01"

def log_telemetria(topic, payload):
    ts = datetime.now().isoformat()
    print(f"[{ts}] {topic} -> {payload}")
    # Enviar a Firebase
    firebase_config.log_evento("Telemetria", {
        "topic": topic,
        "payload": payload,
        "device_id": DEVICE_ID
    })

def on_firebase_command(cmd_doc, client):
    """Callback para manejar comandos desde Firebase hacia MQTT"""
    actuador = cmd_doc.get('actuador')
    accion = cmd_doc.get('accion')
    payload = {}
    if actuador == 'solenoide':
        payload = {"abrir": accion == "abrir", "tiempo_ms": 2000}
    elif actuador == 'buzzer':
        payload = {"tipo": accion}
    
    if actuador and payload:
        topic = f"{TOPIC_BASE}/cmd/{actuador}/{DEVICE_ID}"
        client.publish(topic, json.dumps(payload))
        firebase_config.log_evento("Cambio_Actuador", {"actuador": actuador, "accion": accion, "topic": topic})

def simular_recepcion(client):
    msg_topic = f"{TOPIC_BASE}/sensor/resumen/{DEVICE_ID}"
    msg_payload = {"rfid_uid": "EMP001", "distancia_cm": 20, "pulso_hrv": {"pulso_bpm": 80}}
    log_telemetria(msg_topic, msg_payload)
    
    if msg_payload["rfid_uid"] and msg_payload["distancia_cm"] < 25:
        cmd_oled = {"linea1": "CHECK-IN OK", "linea2": f"Pulso: {msg_payload['pulso_hrv']['pulso_bpm']}bpm"}
        client.publish(f"{TOPIC_BASE}/cmd/oled/{DEVICE_ID}", json.dumps(cmd_oled))
        client.publish(f"{TOPIC_BASE}/cmd/buzzer/{DEVICE_ID}", json.dumps({"tipo": "ok"}))
        client.publish(f"{TOPIC_BASE}/cmd/solenoide/{DEVICE_ID}", json.dumps({"abrir": True, "tiempo_ms": 2000}))
        
        firebase_config.log_evento("Alerta_IA", {
            "mensaje": "Check-in exitoso",
            "nivel": "info",
            "rfid_uid": msg_payload["rfid_uid"]
        })

def simular_recepcion_camara(client, detector):
    """Simula la recepción de una imagen en Base64 desde la ESP32-CAM y su procesamiento por IA"""
    test_img_path = "data/test_face.jpg"
    if not os.path.exists(test_img_path):
        return
        
    print(f"\n[PYTHON-SERVER] Simulando recepción de imagen desde {TOPIC_BASE}/sensor/camara/cam_01")
    import base64
    with open(test_img_path, "rb") as image_file:
        b64_img = base64.b64encode(image_file.read()).decode('utf-8')
    
    # Procesar con IA
    print("[AI] Procesando imagen con modelo MediaPipe Face Mesh...")
    is_fatigued, ear_val, _ = detector.process_base64_image(b64_img)
    
    print(f"[AI] Resultado EAR: {ear_val:.3f} | Fatiga: {'SI' if is_fatigued else 'NO'}")
    
    # Lógica de decisión
    if is_fatigued:
        # 1. Enviar comando de actuador (Buzzer)
        client.publish(f"{TOPIC_BASE}/cmd/buzzer/{DEVICE_ID}", json.dumps({"tipo": "alerta_fatiga"}))
        
        # 2. Registrar en Firebase
        firebase_config.log_evento("Alerta_IA", {
            "mensaje": "Fatiga detectada (EAR bajo)",
            "nivel": "danger",
            "ear_value": ear_val,
            "dispositivo": "cam_01"
        })

def main():
    print("=== SERVIDOR PYTHON INICIADO ===")
    client = DummyPahoClient()
    
    # Inicializar Firebase pasando el callback con el cliente atado
    firebase_config.init_firebase(cmd_callback=lambda doc: on_firebase_command(doc, client))
    
    # Inicializar modelo de IA
    print("[AI] Inicializando modelo de Fatiga (MediaPipe)...")
    detector = FatigueDetector(ear_threshold=0.25)
    
    client.subscribe(f"{TOPIC_BASE}/sensor/+/+")
    
    # Simulación de una lectura entrante
    simular_recepcion(client)
    
    # Simulación de recepción de cámara y Pipeline IA -> Actuador
    simular_recepcion_camara(client, detector)

if __name__ == "__main__":
    main()
