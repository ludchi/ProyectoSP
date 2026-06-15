"""
OBJETIVO: Gestión de Firebase y Dashboard de usuario.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, EPINOZA BRAVO LUDWING, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

# pyrefly: ignore [missing-import]
import firebase_admin
# pyrefly: ignore [missing-import]
from firebase_admin import credentials
# pyrefly: ignore [missing-import]
from firebase_admin import firestore
import datetime
import threading
import os

# Variable global para mantener vivo el listener de Firebase
cmd_watch = None

# Placeholder for credentials, ideally this should be set via env var or actual file
CREDENTIALS_PATH = "serviceAccountKey.json"

db = None
on_command_callback = None

def init_firebase(cmd_callback=None):
    global db, on_command_callback
    on_command_callback = cmd_callback
    try:
        if os.path.exists(CREDENTIALS_PATH):
            cred = credentials.Certificate(CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)
            db = firestore.client()
            print("[FIREBASE] Inicializado correctamente con credenciales.")
            _start_command_listener()
        else:
            print(f"[FIREBASE] ADVERTENCIA: Archivo de credenciales '{CREDENTIALS_PATH}' no encontrado. Usando modo simulado.")
    except Exception as e:
        print(f"[FIREBASE] ERROR al inicializar Firebase: {e}")

def log_evento(tipo, datos):
    """
    Registra un evento en Firestore (ej: Telemetria, Alertas, Actuadores)
    Privacidad: Se asume que 'datos' no contiene imágenes ni datos identificables sensibles directos no anonimizados.
    """
    if not db:
        return # Modo simulado
    
    try:
        # Aseguramos que haya un timestamp generado por el servidor
        datos['timestamp'] = firestore.SERVER_TIMESTAMP
        datos['tipo_evento'] = tipo

        # Guardar en la colección de eventos generales
        db.collection('eventos').add(datos)
        print(f"[FIREBASE] Evento registrado en la nube: {tipo}")
        
        # Si es telemetría, actualizamos el estado actual
        if tipo == "Telemetria":
            db.collection('estado_actual').document('sensores').set(datos)
        
        # Si es alerta, se guarda en su colección específica para el dashboard
        if tipo == "Alerta_IA":
            db.collection('alertas').add(datos)
            
    except Exception as e:
        print(f"[FIREBASE] ERROR al registrar evento: {e}")

def obtener_empleado(uid):
    """
    Busca un empleado en la colección 'empleados' mediante su UID de tarjeta RFID.
    Retorna un diccionario con los datos del empleado si existe, o None si no.
    """
    if not db:
        return {"nombre": "Simulado"} # Modo simulado
    try:
        doc_ref = db.collection('empleados').document(uid)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"[FIREBASE] ERROR al buscar empleado: {e}")
        return None

def registrar_asistencia(uid, empleado_data, bpm):
    """
    Guarda el registro de entrada/salida en la colección 'asistencias'.
    Calcula si hay estrés laboral basado en los BPM.
    """
    if not db:
        print(f"[FIREBASE-SIMULADO] Asistencia registrada para {empleado_data.get('nombre', 'Desconocido')} con {bpm} BPM.")
        return

    try:
        # Lógica básica de estrés: Si BPM es mayor a 100 en reposo, o menor a 50
        estado_estres = "NORMAL"
        if bpm > 100 or bpm < 50:
            estado_estres = "ALERTA_ESTRES"

        registro = {
            "uid": uid,
            "nombre": empleado_data.get('nombre', 'Desconocido'),
            "puesto": empleado_data.get('puesto', 'Sin Asignar'),
            "timestamp": firestore.SERVER_TIMESTAMP,
            "bpm_registrado": bpm,
            "estado_estres": estado_estres
        }
        
        db.collection('asistencias').add(registro)
        print(f"[FIREBASE] ✅ Asistencia guardada: {registro['nombre']} ({bpm} BPM) -> {estado_estres}")
        
    except Exception as e:
        print(f"[FIREBASE] ERROR al registrar asistencia: {e}")

def _start_command_listener():
    """
    Escucha cambios en la colección de comandos enviados desde el Dashboard.
    Usa 'stream' (non-polling) para evitar latencia de la nube.
    """
    if not db:
        return
        
    try:
        # Escuchamos los comandos remotos pendientes usando FieldFilter (sintaxis nueva)
        # pyrefly: ignore [missing-import]
        from google.cloud.firestore_v1.base_query import FieldFilter
        col_query = db.collection('comandos_remotos').where(filter=FieldFilter('procesado', '==', False))
        
        def on_snapshot(col_snapshot, changes, read_time):
            for change in changes:
                if change.type.name == 'ADDED':
                    cmd_doc = change.document.to_dict()
                    cmd_id = change.document.id
                    
                    if on_command_callback:
                        # Mandar el comando a mqtt_server.py
                        on_command_callback(cmd_doc)
                    
                    # Marcar como procesado
                    db.collection('comandos_remotos').document(cmd_id).update({'procesado': True})
                    print(f"[FIREBASE] Comando remoto {cmd_id} procesado.")

        # Suscripción stream en tiempo real (guardamos la referencia global para evitar que se cierre)
        global cmd_watch
        cmd_watch = col_query.on_snapshot(on_snapshot)
        print("[FIREBASE] Listener de comandos remotos iniciado.")
        
    except Exception as e:
        print(f"[FIREBASE] ERROR al iniciar listener de comandos: {e}")
