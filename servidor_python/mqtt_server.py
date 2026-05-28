"""
OBJETIVO: Recibir telemetría MQTT desde la ESP32, registrar timestamps y publicar comandos hacia los actuadores como servidor de control.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, EPINOZA BRAVO LUDWING, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

import json
from datetime import datetime

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

def simular_recepcion(client):
    msg_topic = f"{TOPIC_BASE}/sensor/resumen/{DEVICE_ID}"
    msg_payload = {"rfid_uid": "EMP001", "distancia_cm": 20, "pulso_hrv": {"pulso_bpm": 80}}
    log_telemetria(msg_topic, msg_payload)
    
    if msg_payload["rfid_uid"] and msg_payload["distancia_cm"] < 25:
        cmd_oled = {"linea1": "CHECK-IN OK", "linea2": f"Pulso: {msg_payload['pulso_hrv']['pulso_bpm']}bpm"}
        client.publish(f"{TOPIC_BASE}/cmd/oled/{DEVICE_ID}", json.dumps(cmd_oled))
        client.publish(f"{TOPIC_BASE}/cmd/buzzer/{DEVICE_ID}", json.dumps({"tipo": "ok"}))
        client.publish(f"{TOPIC_BASE}/cmd/solenoide/{DEVICE_ID}", json.dumps({"abrir": True, "tiempo_ms": 2000}))

def main():
    print("=== SERVIDOR PYTHON INICIADO ===")
    client = DummyPahoClient()
    client.subscribe(f"{TOPIC_BASE}/sensor/+/+")
    
    # Simulación de una lectura entrante
    simular_recepcion(client)

if __name__ == "__main__":
    main()
