import json
from datetime import datetime
import firebase_config
import os
import paho.mqtt.client as mqtt
from ai_processor import FatigueDetector
import cv2

BROKER = "127.0.0.1"
CLIENT_ID = "server_python_01"
TOPIC_BASE = "asistlab"

detector = None

def log_telemetria(topic, payload_str):
    ts = datetime.now().isoformat()
    try:
        payload = json.loads(payload_str)
    except Exception:
        payload = {"raw": payload_str}
    
    print(f"[{ts}] {topic} -> {payload}")
    device_id = topic.split('/')[-1]
    
    firebase_config.log_evento("Telemetria", {
        "topic": topic,
        "payload": payload,
        "device_id": device_id
    })

def on_firebase_command(cmd_doc, client):
    actuador = cmd_doc.get('actuador')
    accion = cmd_doc.get('accion')
    dispositivo = cmd_doc.get('dispositivo', 'esp32_01')
    
    payload = {}
    if actuador == 'solenoide':
        payload = {"abrir": accion == "abrir", "tiempo_ms": 2000}
    elif actuador == 'buzzer':
        payload = {"tipo": accion}
    
    if actuador and payload:
        topic = f"{TOPIC_BASE}/cmd/{actuador}/{dispositivo}"
        client.publish(topic, json.dumps(payload))
        firebase_config.log_evento("Cambio_Actuador", {"actuador": actuador, "accion": accion, "topic": topic})

def procesar_camara(client, base64_payload):
    print(f"\n[PYTHON-SERVER] 📸 Recibida foto de la ESP32-CAM. Tamaño: {len(base64_payload)} bytes")
    
    try:
        is_fatigued, ear_val, img_procesada = detector.process_base64_image(base64_payload)
        print(f"[AI] Resultado EAR: {ear_val:.3f} | Fatiga: {'SI' if is_fatigued else 'NO'}")
        
        # --- NUEVO: MOSTRAR VIDEO EN VIVO ---
        if img_procesada is not None:
            cv2.imshow("Monitor de Fatiga en Vivo (ESP32-CAM)", img_procesada)
            cv2.waitKey(1)  # Obligatorio para que la ventana se actualice
        # ------------------------------------
        
        if is_fatigued:
            print("🚨 ¡FATIGA DETECTADA! Activando buzzer en la ESP32 principal...")
            # Enviar comando de actuador (Buzzer) al ESP32_01
            client.publish(f"{TOPIC_BASE}/cmd/buzzer/esp32_01", json.dumps({"tipo": "alerta_fatiga"}))
            
            # Registrar en Firebase
            firebase_config.log_evento("Alerta_IA", {
                "mensaje": "Fatiga detectada (EAR bajo)",
                "nivel": "danger",
                "ear_value": ear_val,
                "dispositivo": "cam_01"
            })
    except Exception as e:
        print(f"[ERROR AI] No se pudo procesar la imagen: {e}")

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Conectado al Broker MQTT en {BROKER}")
        client.subscribe(f"{TOPIC_BASE}/sensor/#")
        print(f"📡 Suscrito a todos los sensores: {TOPIC_BASE}/sensor/#")
    else:
        print(f"❌ Error al conectar MQTT, código: {rc}")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    if "camara" in topic:
        procesar_camara(client, payload)
    else:
        log_telemetria(topic, payload)

def main():
    global detector
    print("=== SERVIDOR PYTHON INICIADO ===")
    
    # Inicializar modelo de IA
    print("[AI] Inicializando modelo de Fatiga (MediaPipe)...")
    detector = FatigueDetector(ear_threshold=0.25)
    
    # Crear cliente MQTT Real
    client = mqtt.Client(CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Inicializar Firebase pasando el callback con el cliente atado
    firebase_config.init_firebase(cmd_callback=lambda doc: on_firebase_command(doc, client))
    
    print(f"Conectando a Mosquitto en {BROKER}...")
    try:
        client.connect(BROKER, 1883, 60)
        # Bucle infinito escuchando a la cámara y sensores
        client.loop_forever()
    except Exception as e:
        print(f"No se pudo conectar al Broker {BROKER}. Asegúrate de que Mosquitto esté corriendo. Error: {e}")

if __name__ == "__main__":
    main()
