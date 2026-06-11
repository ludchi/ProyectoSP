"""
OBJETIVO: Implementar la lógica MQTT en la ESP32 para publicar telemetría de TODOS los sensores y suscribirse a comandos de TODOS los actuadores usando la HAL.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, EPINOZA BRAVO LUDWING, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

import time
import json
from dispositivos import CajaSensores, CajaActuadores

try:
    from umqttsimple import MQTTClient
except ImportError:
    print("ERROR: Falta el archivo umqttsimple.py en la ESP32")


BROKER = "192.168.1.168"
CLIENT_ID = "esp32_01"
TOPIC_BASE = "asistlab"

sensores = CajaSensores()
actuadores = CajaActuadores()

def publicar_json(client, topic, data):
    payload = json.dumps(data)
    client.publish(topic, payload)

def on_message(topic, msg):
    try:
        topic = topic.decode() if isinstance(topic, bytes) else topic
        data = json.loads(msg)
    except Exception as e:
        print("Error parseando mensaje MQTT:", e)
        return
    
    print("MQTT RX:", topic, data)
    
    if topic == f"{TOPIC_BASE}/cmd/oled/{CLIENT_ID}":
        actuadores.mostrar_mensaje(data.get("linea1", ""), data.get("linea2", ""))
    elif topic == f"{TOPIC_BASE}/cmd/buzzer/{CLIENT_ID}":
        actuadores.tono_buzzer(data.get("tipo", "ok"))
    elif topic == f"{TOPIC_BASE}/cmd/solenoide/{CLIENT_ID}":
        abrir = data.get("abrir", False)
        tiempo_ms = data.get("tiempo_ms", 1000)
        actuadores.solenoide_abrir(abrir)
        if abrir:
            time.sleep(tiempo_ms / 1000.0)
            actuadores.solenoide_abrir(False)
    elif topic == f"{TOPIC_BASE}/cmd/safe/{CLIENT_ID}":
        if data.get("activar", False):
            actuadores.estado_seguro()

def main():
    print("=== SISTEMA ASISTENCIAS Y DESGASTE LABORAL (ESP32 MQTT) ===")
    client = MQTTClient(CLIENT_ID, BROKER)
    client.set_callback(on_message)
    client.connect()
    
    for topic in ["oled", "buzzer", "solenoide", "safe"]:
        client.subscribe(f"{TOPIC_BASE}/cmd/{topic}/{CLIENT_ID}")
    
    print("Conectado a broker MQTT, esperando comandos...")
    
    try:
        while True:
            datos = sensores.obtener_resumen_sensores()
            
            publicar_json(client, f"{TOPIC_BASE}/sensor/resumen/{CLIENT_ID}", datos)
            publicar_json(client, f"{TOPIC_BASE}/sensor/rfid/{CLIENT_ID}", {"uid": datos["rfid_uid"], "presente": bool(datos["rfid_uid"])})
            publicar_json(client, f"{TOPIC_BASE}/sensor/ultrasonido/{CLIENT_ID}", {"distancia_cm": datos["distancia_cm"]})
            publicar_json(client, f"{TOPIC_BASE}/sensor/pulso/{CLIENT_ID}", datos["pulso_hrv"])
            
            ultimo_msg = actuadores.mensajes_pantalla[-1] if actuadores.mensajes_pantalla else ""
            publicar_json(client, f"{TOPIC_BASE}/actuador/oled/{CLIENT_ID}", {"ultimo_mensaje": ultimo_msg})
            
            client.check_msg()
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nDeteniendo MQTT en ESP32...")
        actuadores.estado_seguro()
        client.disconnect()

if __name__ == "__main__":
    main()
