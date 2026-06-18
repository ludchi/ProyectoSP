"""
OBJETIVO: Implementar la lógica MQTT en la ESP32 para publicar telemetría de sensores y suscribirse a comandos OLED.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, ESPINOZA BRAVO LUDWIG, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

import time
import json
from dispositivos import CajaSensores, CajaActuadores

try:
    from umqttsimple import MQTTClient
except ImportError:
    print("ERROR: Falta el archivo umqttsimple.py en la ESP32")


BROKER = "172.20.10.4"
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
    
    elif topic == f"{TOPIC_BASE}/cmd/actuadores/{CLIENT_ID}":
        accion = data.get("accion", "")
        if accion == "registro_ok":
            # LED Verde + Buzzer: Registro exitoso sin fatiga
            actuadores.confirmar_registro()
        elif accion == "registro_fatiga":
            # LED Rojo + Buzzer: Registro exitoso PERO con fatiga detectada
            actuadores.alerta_fatiga()
        elif accion == "apagar":
            actuadores.apagar_todo()

def main():
    print("=== SISTEMA ASISTENCIAS Y DESGASTE LABORAL (ESP32 MQTT) ===")
    client = MQTTClient(CLIENT_ID, BROKER)
    client.set_callback(on_message)
    client.connect()
    
    # Suscribirse a comandos OLED y nuevos actuadores (LEDs + Buzzer)
    client.subscribe(f"{TOPIC_BASE}/cmd/oled/{CLIENT_ID}")
    client.subscribe(f"{TOPIC_BASE}/cmd/actuadores/{CLIENT_ID}")
    
    print("Conectado a broker MQTT, esperando comandos...")
    
    try:
        while True:
            client.check_msg()
            
            # 1. Esperar tarjeta RFID
            uid = sensores.leer_rfid()
            
            if uid:
                print(f"[RFID] Tarjeta detectada: {uid}. Iniciando medición de pulso...")
                publicar_json(client, f"{TOPIC_BASE}/sensor/rfid/{CLIENT_ID}", {"uid": uid, "presente": True})
                
                # Indicar al usuario que coloque el dedo
                actuadores.mostrar_mensaje("Pon tu dedo", "Calculando...")
                
                lecturas_validas = []
                inicio = time.time()
                
                # 2. Bucle para obtener 10 lecturas válidas de BPM
                while len(lecturas_validas) < 10:
                    client.check_msg()
                    pulso_datos = sensores.leer_pulso_hrv()
                    bpm = pulso_datos.get("pulso_bpm", 0)
                    
                    if bpm > 40:
                        lecturas_validas.append(bpm)
                        # Mostrar progreso en la OLED
                        actuadores.mostrar_mensaje("Midiendo...", f"Progreso: {len(lecturas_validas)}/10")
                        
                    # Si pasan 30 segundos sin completar, abortar para no bloquear el sistema
                    if time.time() - inicio > 30:
                        print("[ALERTA] Timeout esperando lecturas de pulso.")
                        break
                        
                    time.sleep_ms(300)
                
                # 3. Si se consiguieron las lecturas, calcular promedio y enviar al servidor
                if len(lecturas_validas) >= 10:
                    promedio_bpm = sum(lecturas_validas) // len(lecturas_validas)
                    print(f"[INFO] Promedio calculado: {promedio_bpm} BPM. Enviando resumen...")
                    
                    datos = {
                        "rfid_uid": uid,
                        "pulso_hrv": {"pulso_bpm": promedio_bpm, "hrv_ms": 0}
                    }
                    publicar_json(client, f"{TOPIC_BASE}/sensor/resumen/{CLIENT_ID}", datos)
                    actuadores.mostrar_mensaje("Enviando...", f"{promedio_bpm} BPM")
                else:
                    actuadores.mostrar_mensaje("Error", "Pulso no detectado")
                
                # Pausa para evitar lecturas dobles instantáneas de la misma tarjeta
                time.sleep(2)
            else:
                time.sleep_ms(200) # Polling rápido para RFID
                
    except KeyboardInterrupt:
        print("\nDeteniendo MQTT en ESP32...")
        actuadores.estado_seguro()
        client.disconnect()

if __name__ == "__main__":
    main()

