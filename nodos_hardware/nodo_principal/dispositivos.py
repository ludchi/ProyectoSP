"""
OBJETIVO: Biblioteca HAL que abstrae RFID, pulso HRV, ultrasonido, OLED, buzzer y solenoide para control de asistencias con medición de estrés laboral.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, EPINOZA BRAVO LUDWING, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

import time

class CajaSensores:
    def __init__(self):
        self.lecturas_ultrasonido = []
        self.contador_lecturas = 0
        self.uid_actual = ""
        self.pulsos_historial = [72, 74, 70, 75]
        
    def leer_rfid(self):
        if int(time.time() * 10) % 20 < 5:
            self.uid_actual = "EMP001-A1B2C3D4"
        else:
            self.uid_actual = ""
        return self.uid_actual
    
    def leer_ultrasonido_cm(self):
        lectura_cruda = 15 + (self.contador_lecturas % 10) * 3
        self.lecturas_ultrasonido.append(lectura_cruda)
        if len(self.lecturas_ultrasonido) > 5:
            self.lecturas_ultrasonido.pop(0)
        self.contador_lecturas += 1
        return sum(self.lecturas_ultrasonido) / len(self.lecturas_ultrasonido)
    
    def leer_pulso_hrv(self):
        pulso = 70 + (self.contador_lecturas % 30)
        hrv = 45 - (pulso - 75) * 0.3
        return {"pulso_bpm": pulso, "hrv_ms": max(20, hrv)}
    
    def obtener_resumen_sensores(self):
        return {
            "rfid_uid": self.leer_rfid(),
            "distancia_cm": self.leer_ultrasonido_cm(),
            "pulso_hrv": self.leer_pulso_hrv()
        }

class CajaActuadores:
    def __init__(self):
        self.mensajes_pantalla = []
        self.ultimo_tono = 0
        
    def mostrar_mensaje(self, linea1, linea2=""):
        mensaje = f"{linea1}\n{linea2}"
        self.mensajes_pantalla.append(mensaje)
        if len(self.mensajes_pantalla) > 3:
            self.mensajes_pantalla.pop(0)
        print(f"[OLED] {mensaje}")
    
    def tono_buzzer(self, tipo):
        self.ultimo_tono += 1
        tonos = {"ok": 500, "error": 200, "advertencia": 1000}
        duracion = 200 if tipo == "ok" else 800
        print(f"[BUZZER] Tono {tonos.get(tipo, 500)}Hz x {duracion}ms")
    
    def solenoide_abrir(self, abrir=True):
        estado = "ABIERTO" if abrir else "CERRADO"
        print(f"[SOLENOIDE] {estado}")
    
    def estado_seguro(self):
        print("[EMERGENCIA] ESTADO SEGURO ACTIVADO")
        self.solenoide_abrir(False)
        self.tono_buzzer("error")
        self.mostrar_mensaje("ESTADO SEGURO", "Sistema detenido")
