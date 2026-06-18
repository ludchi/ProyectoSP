"""
OBJETIVO: Servidor central Python que procesa asistencias (entrada/salida), IA de fatiga y sirve la cámara al Dashboard.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, ESPINOZA BRAVO LUDWIG, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

import json
from datetime import datetime
import firebase_config
import os
import time
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import paho.mqtt.client as mqtt
from ai_processor import FatigueDetector
import cv2

BROKER = "127.0.0.1"
CLIENT_ID = "server_python_01"
TOPIC_BASE = "asistlab"

detector = None

# === ESTADO DE ASISTENCIA (Entrada/Salida) ===
# Guardamos qué empleados ya registraron ENTRADA hoy.
# La segunda pasada de tarjeta se interpreta como SALIDA.
empleados_presentes = {}  # {uid: timestamp_entrada}
COOLDOWN_SECONDS = 60  # 1 minuto entre entrada y salida o viceversa
cooldowns = {}

# === MINI-SERVIDOR HTTP PARA CÁMARA ===
CAMERA_IMG_PATH = os.path.join(os.path.dirname(__file__), "ultima_captura.jpg")
CAMERA_HTTP_PORT = 8089

class CameraHTTPHandler(SimpleHTTPRequestHandler):
    """Sirve la última imagen procesada por la IA al Dashboard."""
    def do_GET(self):
        if self.path == "/camara" or self.path == "/camara.jpg":
            try:
                if os.path.exists(CAMERA_IMG_PATH):
                    self.send_response(200)
                    self.send_header("Content-type", "image/jpeg")
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                    self.end_headers()
                    with open(CAMERA_IMG_PATH, "rb") as f:
                        self.wfile.write(f.read())
                else:
                    self.send_response(204)  # No Content
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.end_headers()
            except Exception:
                self.send_response(500)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Silenciar logs HTTP para no ensuciar la consola

def iniciar_servidor_camara():
    """Inicia el mini-servidor HTTP en un thread aparte."""
    server = HTTPServer(("0.0.0.0", CAMERA_HTTP_PORT), CameraHTTPHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"[HTTP] 📷 Servidor de cámara en http://localhost:{CAMERA_HTTP_PORT}/camara")

# === PROCESAMIENTO DE CÁMARA (IA FATIGA) ===
ultima_foto_b64 = None
ultima_fatiga_detectada = False  # Guarda si la foto del registro tenía fatiga

asistencia_pendiente = None

def resetear_pantalla(client, dispositivo):
    try:
        client.publish(f"{TOPIC_BASE}/cmd/oled/{dispositivo}", json.dumps({
            "linea1": "Sistema Listo",
            "linea2": "Acerque tarjeta"
        }))
    except:
        pass

def ejecutar_registro(client, uid, bpm, dispositivo):
    global ultima_foto_b64, empleados_presentes, cooldowns, ultima_fatiga_detectada
    ahora = time.time()
    
    if uid not in empleados_presentes:
        # === ENTRADA ===
        print(f"🟢 ENTRADA: Tarjeta {uid} + Pulso {bpm} BPM")
        exito, nombre, _ = firebase_config.registrar_asistencia(uid, bpm, tipo="entrada")
        
        if exito:
            empleados_presentes[uid] = ahora
            cooldowns[uid] = ahora
            client.publish(f"{TOPIC_BASE}/cmd/oled/{dispositivo}", json.dumps({
                "linea1": "Bienvenido!",
                "linea2": nombre
            }))
            # Activar actuadores: LED Rojo si hay fatiga, LED Verde si registro normal
            if ultima_fatiga_detectada:
                client.publish(f"{TOPIC_BASE}/cmd/actuadores/{dispositivo}", json.dumps({"accion": "registro_fatiga"}))
                print("🚨 REGISTRO CON FATIGA → LED ROJO")
            else:
                client.publish(f"{TOPIC_BASE}/cmd/actuadores/{dispositivo}", json.dumps({"accion": "registro_ok"}))
            if ultima_foto_b64:
                firebase_config.actualizar_camara_dashboard(ultima_foto_b64)
            ultima_foto_b64 = None
            threading.Timer(4.0, resetear_pantalla, args=[client, dispositivo]).start()
    else:
        # === SALIDA ===
        print(f"🔴 SALIDA: Tarjeta {uid} + Pulso {bpm} BPM")
        exito, nombre, datos_extra = firebase_config.registrar_asistencia(uid, bpm, tipo="salida")
        
        if exito:
            del empleados_presentes[uid]
            cooldowns[uid] = ahora
            nivel = datos_extra.get('nivel', '')
            linea2 = f"Estres: {nivel}" if nivel else "Hasta pronto!"
            client.publish(f"{TOPIC_BASE}/cmd/oled/{dispositivo}", json.dumps({
                "linea1": f"Adios {nombre}",
                "linea2": linea2
            }))
            # Activar actuadores: LED Rojo si hay fatiga, LED Verde si registro normal
            if ultima_fatiga_detectada:
                client.publish(f"{TOPIC_BASE}/cmd/actuadores/{dispositivo}", json.dumps({"accion": "registro_fatiga"}))
                print("🚨 REGISTRO CON FATIGA → LED ROJO")
            else:
                client.publish(f"{TOPIC_BASE}/cmd/actuadores/{dispositivo}", json.dumps({"accion": "registro_ok"}))
            if ultima_foto_b64:
                firebase_config.actualizar_camara_dashboard(ultima_foto_b64)
            ultima_foto_b64 = None
            threading.Timer(4.0, resetear_pantalla, args=[client, dispositivo]).start()

def procesar_camara(client, base64_payload):
    global ultima_foto_b64, asistencia_pendiente, ultima_fatiga_detectada
    print(f"\n[PYTHON-SERVER] 📸 Recibida foto de la ESP32-CAM. Tamaño: {len(base64_payload)} bytes")
    
    try:
        is_fatigued, ear_val, img_procesada, face_detected = detector.process_base64_image(base64_payload)
        print(f"[AI] Resultado EAR: {ear_val:.3f} | Fatiga: {'SI' if is_fatigued else 'NO'}")
        
        # Guardar la imagen procesada como archivo para servir al Dashboard y mantenerla en RAM para Firebase
        if img_procesada is not None:
            cv2.imwrite(CAMERA_IMG_PATH, img_procesada)
            # Solo si hay un rostro detectado (ojos), actualizamos la caché que se subirá a Firebase
            if face_detected:
                print(f"[DEBUG] Rostro válido. Revisando pendientes... (Pendiente: {bool(asistencia_pendiente)})")
                _, buffer = cv2.imencode('.jpg', img_procesada, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
                import base64
                ultima_foto_b64 = base64.b64encode(buffer).decode('utf-8')
                # Guardar si esta foto tiene fatiga (se usará al momento del registro)
                ultima_fatiga_detectada = is_fatigued
                
                # Si había un registro esperando foto, completarlo ahora
                if asistencia_pendiente:
                    diferencia = time.time() - asistencia_pendiente['timestamp']
                    print(f"[DEBUG] Hay registro pendiente. Edad: {diferencia:.1f}s")
                    if diferencia <= 120: # Ampliado a 120 seg para no cortar nunca al usuario
                        print("✅ FOTO OBTENIDA. Completando registro pendiente...")
                        ejecutar_registro(client, asistencia_pendiente['uid'], asistencia_pendiente['bpm'], asistencia_pendiente['dispositivo'])
                    asistencia_pendiente = None
            
            # === MOSTRAR VENTANA LOCAL EN TIEMPO REAL ===
            cv2.imshow("Monitor IA - Asistencias y Fatiga", img_procesada)
            cv2.waitKey(1)
            
        if is_fatigued:
            print("🚨 ¡FATIGA DETECTADA!")
            firebase_config.log_evento("Alerta_IA", {
                "mensaje": "Fatiga detectada (EAR bajo)",
                "nivel": "danger",
                "ear_value": ear_val,
                "dispositivo": "cam_01"
            })
    except Exception as e:
        print(f"[ERROR AI] No se pudo procesar la imagen: {e}")

# === CALLBACKS MQTT ===
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Conectado al Broker MQTT en {BROKER}")
        client.subscribe(f"{TOPIC_BASE}/sensor/#")
        print(f"📡 Suscrito a todos los sensores: {TOPIC_BASE}/sensor/#")
    else:
        print(f"❌ Error al conectar MQTT, código: {rc}")

def on_message(client, userdata, msg):
    global ultima_foto_b64, asistencia_pendiente
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    if "camara" in topic:
        procesar_camara(client, payload)
    elif "/sensor/rfid/" in topic:
        try:
            datos = json.loads(payload)
            if datos.get("presente", False):
                ultima_foto_b64 = None
                asistencia_pendiente = None # Limpiar también cualquier registro colgado
                print("[PYTHON-SERVER] 🧹 Caché de foto y registros pendientes limpios por nuevo RFID")
        except:
            pass
            
    elif "/sensor/resumen/" in topic:
        try:
            datos = json.loads(payload)
            uid = datos.get("rfid_uid", "")
            bpm = datos.get("pulso_hrv", {}).get("pulso_bpm", 0)
            
            # --- LÓGICA DE ASISTENCIA ENTRADA/SALIDA ---
            if uid != "" and bpm > 40:
                ahora = time.time()
                dispositivo = topic.split('/')[-1]
                
                # Checar cooldown para evitar spam
                if uid in cooldowns and (ahora - cooldowns[uid]) < COOLDOWN_SECONDS:
                    tiempo_restante = int(COOLDOWN_SECONDS - (ahora - cooldowns[uid]))
                    minutos = tiempo_restante // 60
                    segundos = tiempo_restante % 60
                    print(f"⌛ Ignorando lectura. En cooldown: faltan {minutos}m {segundos}s")
                    client.publish(f"{TOPIC_BASE}/cmd/oled/{dispositivo}", json.dumps({
                        "linea1": "Espera por favor",
                        "linea2": f"{minutos}m {segundos}s rest"
                    }))
                    return  # Ignorar
                
                # BLOQUEO ESTRICTO ASÍNCRONO
                if not ultima_foto_b64:
                    print(f"⚠️ PENDIENTE: Se detectó pulso ({bpm} BPM) pero falta foto. Esperando a que mire a la cámara...")
                    client.publish(f"{TOPIC_BASE}/cmd/oled/{dispositivo}", json.dumps({
                        "linea1": "Mire a la",
                        "linea2": "camara..."
                    }))
                    asistencia_pendiente = {
                        "uid": uid,
                        "bpm": bpm,
                        "dispositivo": dispositivo,
                        "timestamp": time.time()
                    }
                    return
                
                # Si ya había foto, ejecuta directo
                ejecutar_registro(client, uid, bpm, dispositivo)
            
            elif uid != "" and bpm == 0:
                dispositivo = topic.split('/')[-1]
                client.publish(f"{TOPIC_BASE}/cmd/oled/{dispositivo}", json.dumps({
                    "linea1": "Pon tu dedo",
                    "linea2": "en el sensor"
                }))
                
        except Exception as e:
            print(f"Error procesando resumen: {e}")

def on_firebase_command(cmd_doc, client):
    """Procesa comandos remotos desde el Dashboard."""
    actuador = cmd_doc.get('actuador')
    accion = cmd_doc.get('accion')
    dispositivo = cmd_doc.get('dispositivo', 'esp32_01')
    
    if actuador == 'oled':
        payload = {"linea1": accion, "linea2": ""}
        topic = f"{TOPIC_BASE}/cmd/oled/{dispositivo}"
        client.publish(topic, json.dumps(payload))

def main():
    global detector
    print("=== SERVIDOR PYTHON - ASISTENCIAS Y DESGASTE LABORAL ===")
    
    # Inicializar modelo de IA
    print("[AI] Inicializando modelo de Fatiga (MediaPipe)...")
    detector = FatigueDetector(ear_threshold=0.25)
    
    # Iniciar mini-servidor HTTP para la cámara en el Dashboard
    iniciar_servidor_camara()
    
    # Crear cliente MQTT
    client = mqtt.Client(CLIENT_ID)
    client.on_connect = on_connect
    client.on_message = on_message
    
    # Inicializar Firebase
    firebase_config.init_firebase(cmd_callback=lambda doc: on_firebase_command(doc, client))
    
    print(f"Conectando a Mosquitto en {BROKER}...")
    try:
        client.connect(BROKER, 1883, 60)
        client.loop_forever()
    except Exception as e:
        print(f"No se pudo conectar al Broker {BROKER}. Asegúrate de que Mosquitto esté corriendo. Error: {e}")

if __name__ == "__main__":
    main()
