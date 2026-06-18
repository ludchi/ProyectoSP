"""
OBJETIVO: Gestión de Firebase y Dashboard de usuario.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, ESPINOZA BRAVO LUDWIG, LOZANO CARDONA ANGEL JOSUE
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
    Registra un evento en Firestore (ej: Alertas IA)
    """
    if not db:
        return # Modo simulado
    
    try:
        datos['timestamp'] = firestore.SERVER_TIMESTAMP
        datos['tipo_evento'] = tipo

        db.collection('eventos').add(datos)
        print(f"[FIREBASE] Evento registrado en la nube: {tipo}")
        
        # Si es alerta, se guarda en su colección específica para el dashboard
        if tipo == "Alerta_IA":
            db.collection('alertas').add(datos)
            
    except Exception as e:
        print(f"[FIREBASE] ERROR al registrar evento: {e}")

def actualizar_camara_dashboard(base64_img):
    """Sube la última foto al dashboard solo cuando hay una asistencia para ahorrar cuota."""
    if not db:
        return
    try:
        db.collection('estado_actual').document('camara').set({
            "imagen_b64": base64_img,
            "timestamp": firestore.SERVER_TIMESTAMP
        })
    except Exception as e:
        print(f"[FIREBASE] Error subiendo imagen: {e}")

def registrar_asistencia(uid, bpm, tipo="entrada"):
    """
    Registra la asistencia de un empleado (entrada o salida).
    En la salida calcula la diferencia de estrés comparando BPM entrada vs salida.
    Retorna (éxito, nombre, datos_extra).
    """
    if not db:
        # Modo simulado si no hay credenciales
        return True, f"Empleado {uid}", {}
        
    try:
        # 1. Buscar al empleado en la colección
        doc_ref = db.collection('empleados').document(uid)
        doc = doc_ref.get()
        
        if doc.exists:
            data = doc.to_dict() or {}
            print(f"[DEBUG FIREBASE] Documento {uid} encontrado. Datos: {data}")
            
            # Limpiar llaves por si en Firebase las escribiste con mayúsculas o espacios extra
            data_limpia = {str(k).strip().lower(): v for k, v in data.items()}
            
            nombre = data_limpia.get('nombre') or data_limpia.get('empleados') or data_limpia.get('empleado') or f"Emp {uid}"
            
            if nombre == f"Emp {uid}":
                print(f"[DEBUG FIREBASE] No se encontró el campo 'nombre' en el documento.")
        else:
            # Si no existe, crear un perfil temporal
            nombre = f"Nuevo {uid[-4:]}"
            doc_ref.set({
                "nombre": nombre,
                "rol": "Desconocido",
                "creado_en": firestore.SERVER_TIMESTAMP
            })
            
        # 2. Registrar la asistencia
        asistencia_data = {
            "uid": uid,
            "nombre": nombre,
            "pulso_bpm": bpm,
            "tipo": tipo,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "tipo_evento": "Asistencia"
        }
        
        # Si es salida, buscar la entrada más reciente para calcular estrés
        datos_extra = {}
        if tipo == "salida":
            try:
                # pyrefly: ignore [missing-import]
                from google.cloud.firestore_v1.base_query import FieldFilter
                
                # Solución sin Índice Compuesto: Pedimos las entradas del usuario y ordenamos en Python
                entradas_ref = db.collection('asistencias')\
                    .where(filter=FieldFilter('uid', '==', uid))\
                    .where(filter=FieldFilter('tipo', '==', 'entrada'))\
                    .get()
                
                # Filtrar aquellas que tengan timestamp y ordenarlas de más reciente a más antigua
                entradas_validas = [doc for doc in entradas_ref if doc.to_dict().get('timestamp') is not None]
                entradas_ordenadas = sorted(entradas_validas, key=lambda x: x.to_dict().get('timestamp'), reverse=True)
                
                # Tomar la más reciente
                entradas = entradas_ordenadas[:1]
                
                for entrada_doc in entradas:
                    bpm_entrada = entrada_doc.to_dict().get('pulso_bpm', 0)
                    if bpm_entrada > 0:
                        diferencia = bpm - bpm_entrada
                        porcentaje = round((diferencia / bpm_entrada) * 100, 1)
                        
                        asistencia_data['bpm_entrada'] = bpm_entrada
                        asistencia_data['bpm_salida'] = bpm
                        asistencia_data['diferencia_bpm'] = diferencia
                        asistencia_data['porcentaje_estres'] = porcentaje
                        
                        # Clasificar nivel de estrés
                        if porcentaje > 15:
                            nivel = "alto"
                        elif porcentaje > 5:
                            nivel = "medio"
                        else:
                            nivel = "bajo"
                        asistencia_data['nivel_estres'] = nivel
                        
                        datos_extra = {
                            'bpm_entrada': bpm_entrada,
                            'diferencia': diferencia,
                            'nivel': nivel
                        }
            except Exception as e:
                print(f"[FIREBASE] No se pudo calcular estrés: {e}")
        
        db.collection('asistencias').add(asistencia_data)
        emoji = "🟢" if tipo == "entrada" else "🔴"
        print(f"[FIREBASE] {emoji} {tipo.upper()} registrada para {nombre} ({bpm} BPM)")
        
        return True, nombre, datos_extra
        
    except Exception as e:
        print(f"[FIREBASE] ERROR al registrar asistencia: {e}")
        return False, "Error DB", {}

def _start_command_listener():
    """
    Escucha cambios en la colección de comandos enviados desde el Dashboard.
    """
    if not db:
        return
        
    try:
        # pyrefly: ignore [missing-import]
        from google.cloud.firestore_v1.base_query import FieldFilter
        col_query = db.collection('comandos_remotos').where(filter=FieldFilter('procesado', '==', False))
        
        def on_snapshot(col_snapshot, changes, read_time):
            for change in changes:
                if change.type.name == 'ADDED':
                    cmd_doc = change.document.to_dict()
                    cmd_id = change.document.id
                    
                    if on_command_callback:
                        on_command_callback(cmd_doc)
                    
                    # Marcar como procesado
                    db.collection('comandos_remotos').document(cmd_id).update({'procesado': True})
                    print(f"[FIREBASE] Comando remoto {cmd_id} procesado.")

        global cmd_watch
        cmd_watch = col_query.on_snapshot(on_snapshot)
        print("[FIREBASE] Listener de comandos remotos iniciado.")
        
    except Exception as e:
        print(f"[FIREBASE] ERROR al iniciar listener de comandos: {e}")
