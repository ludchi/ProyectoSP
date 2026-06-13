"""
OBJETIVO: Biblioteca HAL que abstrae RFID, pulso HRV, ultrasonido, OLED, buzzer y solenoide para control de asistencias con medición de estrés laboral.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, EPINOZA BRAVO LUDWING, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

import time
from machine import Pin, I2C, SPI, PWM

# Intentar importar librerías. Si fallan, se usarán simulaciones como respaldo.
try:
    import ssd1306
    HAS_OLED = True
except ImportError:
    HAS_OLED = False

try:
    import hcsr04
    HAS_HCSR04 = True
except ImportError:
    HAS_HCSR04 = False

try:
    from mfrc522 import MFRC522
    HAS_RFID = True
except ImportError:
    HAS_RFID = False

try:
    from max30100 import MAX30100
    HAS_MAX30100 = True
except ImportError:
    HAS_MAX30100 = False


class CajaSensores:
    def __init__(self):
        self.lecturas_ultrasonido = []
        self.uid_actual = ""
        self.pulsos_historial = [72, 74, 70, 75]
        
        # --- Configuración HC-SR04 ---
        if HAS_HCSR04:
            self.sensor_distancia = hcsr04.HCSR04(trigger_pin=13, echo_pin=12, echo_timeout_us=10000)
        else:
            self.sensor_distancia = None
            print("[ADVERTENCIA] No se encontró hcsr04.py, usando simulación para ultrasonido.")
            
        # --- Configuración I2C (Compartido OLED y MAX30100) ---
        # Instanciamos aquí para el MAX30100.
        self.i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
        
        # --- Configuración MAX30100 ---
        if HAS_MAX30100:
            try:
                self.sensor_pulso = MAX30100(self.i2c)
                self.sensor_pulso.setup_sensor()
            except Exception as e:
                print(f"[ERROR] Falló inicialización MAX30100: {e}")
                self.sensor_pulso = None
        else:
            self.sensor_pulso = None
            print("[ADVERTENCIA] No se encontró max30100.py, usando simulación para pulso.")

        # --- Configuración SPI y RC522 ---
        if HAS_RFID:
            try:
                self.pin_rst = Pin(4, Pin.OUT)
                self.pin_rst.value(1) # Despertar al módulo
                self.spi = SPI(2, baudrate=2500000, polarity=0, phase=0, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
                
                # Instanciación con 2 argumentos (SPI, CS)
                self.lector_rfid = MFRC522(self.spi, Pin(5))
                self.lector_rfid.init() # Encender antena según la librería del usuario
            except Exception as e:
                print(f"[ERROR] Falló inicialización RC522: {e}")
                self.lector_rfid = None
        else:
            self.lector_rfid = None
            print("[ADVERTENCIA] No se encontró mfrc522.py, usando simulación para RFID.")


    def leer_rfid(self):
        if self.lector_rfid:
            try:
                (stat, tag_type) = self.lector_rfid.request(self.lector_rfid.REQIDL)
                if stat == self.lector_rfid.OK:
                    (stat, raw_uid) = self.lector_rfid.anticoll()
                    if stat == self.lector_rfid.OK:
                        self.uid_actual = "-".join([hex(i)[2:].upper() for i in raw_uid])
                        return self.uid_actual
            except Exception:
                pass
            self.uid_actual = ""
            return self.uid_actual
        else:
            # Simulación
            if int(time.time() * 10) % 20 < 5:
                self.uid_actual = "EMP001-A1B2C3D4"
            else:
                self.uid_actual = ""
            return self.uid_actual
    
    def leer_ultrasonido_cm(self):
        if self.sensor_distancia:
            try:
                dist = self.sensor_distancia.distance_cm()
                if dist < 0 or dist > 400:
                    dist = 400
                self.lecturas_ultrasonido.append(dist)
                if len(self.lecturas_ultrasonido) > 5:
                    self.lecturas_ultrasonido.pop(0)
                return sum(self.lecturas_ultrasonido) / len(self.lecturas_ultrasonido)
            except Exception:
                return 400
        else:
            # Simulación
            return 15 + (int(time.time()) % 10) * 3
    
    def leer_pulso_hrv(self):
        if self.sensor_pulso:
            self.sensor_pulso.check()
            if self.sensor_pulso.available():
                red = self.sensor_pulso.pop_red_from_storage()
                ir = self.sensor_pulso.pop_ir_from_storage()
                if ir > 50000: # Umbral muy básico para detectar dedo
                    # Simular datos médicos en base a la detección
                    return {"pulso_bpm": 75, "hrv_ms": 40} 
            return {"pulso_bpm": 0, "hrv_ms": 0}
        else:
            # Simulación
            pulso = 70 + (int(time.time()) % 30)
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
        
        # --- Configuración Relé (Solenoide) ---
        self.pin_solenoide = Pin(26, Pin.OUT)
        self.pin_solenoide.value(0) # Cerrado por defecto
        
        # --- Configuración Buzzer ---
        self.pin_buzzer = PWM(Pin(27), freq=500, duty=0)
        
        # --- Configuración OLED ---
        if HAS_OLED:
            try:
                self.i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
                self.oled = ssd1306.SSD1306_I2C(128, 64, self.i2c)
                self.oled.fill(0)
                self.oled.text("SISTEMA LISTO", 0, 0)
                self.oled.show()
            except Exception as e:
                print(f"[ERROR] Falló inicialización OLED: {e}")
                self.oled = None
        else:
            self.oled = None
            print("[ADVERTENCIA] No se encontró ssd1306.py, usando simulación para OLED.")

        
    def mostrar_mensaje(self, linea1, linea2=""):
        if self.oled:
            self.oled.fill(0)
            self.oled.text(linea1, 0, 10)
            self.oled.text(linea2, 0, 30)
            self.oled.show()
        else:
            mensaje = f"{linea1}\n{linea2}"
            self.mensajes_pantalla.append(mensaje)
            if len(self.mensajes_pantalla) > 3:
                self.mensajes_pantalla.pop(0)
            print(f"[OLED SIMULADO] {mensaje}")
    
    def tono_buzzer(self, tipo):
        tonos = {"ok": 500, "error": 200, "advertencia": 1000}
        duracion_ms = 200 if tipo == "ok" else 800
        freq = tonos.get(tipo, 500)
        
        self.pin_buzzer.freq(freq)
        self.pin_buzzer.duty(512) # 50% duty cycle
        time.sleep_ms(duracion_ms)
        self.pin_buzzer.duty(0) # Apagar
        
        print(f"[BUZZER] Tono {freq}Hz x {duracion_ms}ms")
    
    def solenoide_abrir(self, abrir=True):
        if abrir:
            self.pin_solenoide.value(1)
            print("[SOLENOIDE] ABIERTO")
        else:
            self.pin_solenoide.value(0)
            print("[SOLENOIDE] CERRADO")
    
    def estado_seguro(self):
        print("[EMERGENCIA] ESTADO SEGURO ACTIVADO")
        self.solenoide_abrir(False)
        self.tono_buzzer("error")
        self.mostrar_mensaje("ESTADO SEGURO", "Sistema detenido")
