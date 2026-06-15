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
    from mfrc522 import MFRC522
    HAS_RFID = True
except ImportError:
    HAS_RFID = False

try:
    from max30102 import MAX30102
    HAS_MAX30102 = True
except ImportError:
    HAS_MAX30102 = False

class DetectorPulso:
    def __init__(self):
        self.ir_buffer = []
        self.last_bpm = 0
        
    def procesar_muestras(self, samples):
        for red, ir in samples:
            self.ir_buffer.append(ir)
        # Mantener historial de 150 muestras (3 segundos a 50Hz)
        if len(self.ir_buffer) > 150:
            self.ir_buffer = self.ir_buffer[-150:]
            
    def limpiar(self):
        self.ir_buffer = []
        self.last_bpm = 0
        
    def calcular_bpm(self):
        if len(self.ir_buffer) < 100:
            return self.last_bpm # Necesitamos al menos 2 segundos de datos
            
        # Filtro de media móvil para suavizar ruido
        smoothed = []
        for i in range(1, len(self.ir_buffer)-1):
            smoothed.append((self.ir_buffer[i-1] + self.ir_buffer[i] + self.ir_buffer[i+1]) / 3)
            
        min_val = min(smoothed)
        max_val = max(smoothed)
        
        # Si la amplitud es muy pequeña, es ruido o el dedo está inmóvil
        if max_val - min_val < 20:
            return 0
            
        # Umbral dinámico (mitad de la amplitud de la onda)
        threshold = min_val + (max_val - min_val) * 0.5
        
        peaks = []
        min_dist = 8 # A 25Hz, 8 samples = 0.32s (aprox 187 BPM max)
        last_peak_idx = -min_dist
        
        for i in range(1, len(smoothed) - 1):
            if smoothed[i] > smoothed[i-1] and smoothed[i] > smoothed[i+1]:
                if smoothed[i] > threshold:
                    if i - last_peak_idx >= min_dist:
                        peaks.append(i)
                        last_peak_idx = i
                        
        if len(peaks) >= 2:
            intervalos = []
            for i in range(1, len(peaks)):
                intervalos.append(peaks[i] - peaks[i-1])
            avg_interval = sum(intervalos) / len(intervalos)
            
            # 25 Hz = 25 muestras por segundo en el FIFO
            bpm = (25 / avg_interval) * 60
            
            # Limitar a rango humano
            if 40 <= bpm <= 180:
                self.last_bpm = int(bpm)
                
        return self.last_bpm

class CajaSensores:
    def __init__(self):
        self.uid_actual = ""
        self.pulsos_historial = [72, 74, 70, 75]
            
        # --- Configuración I2C (Compartido OLED y MAX30102) ---
        self.i2c = I2C(0, scl=Pin(22), sda=Pin(21), freq=400000)
        
        # --- Configuración MAX30102 ---
        if HAS_MAX30102:
            try:
                dispositivos_i2c = self.i2c.scan()
                print(f"[INFO] Dispositivos en bus I2C: {[hex(d) for d in dispositivos_i2c]}")
                
                if 0x57 not in dispositivos_i2c:
                    print("[ALERTA] MAX30102 (0x57) NO encontrado en bus I2C.")
                    self.sensor_pulso = None
                else:
                    self.detector_pulso = DetectorPulso()
                    self.sensor_pulso = MAX30102(self.i2c)
                    print("[INFO] MAX30102 inicializado correctamente.")
            except Exception as e:
                print(f"[ERROR] Falló inicialización MAX30102: {e}")
                self.sensor_pulso = None
        else:
            self.sensor_pulso = None
            print("[ADVERTENCIA] No se encontró max30102.py, sensor de pulso desactivado.")

        # --- Configuración SPI y RC522 (SEGUNDO, después de I2C) ---
        if HAS_RFID:
            try:
                sck_pin = Pin(18, Pin.OUT)
                mosi_pin = Pin(19, Pin.OUT)
                miso_pin = Pin(16, Pin.OUT)
                sda_pin = Pin(17, Pin.OUT)

                self.spi = SPI(2, baudrate=1000000, polarity=0, phase=0, sck=sck_pin, mosi=mosi_pin, miso=miso_pin)
                self.lector_rfid = MFRC522(self.spi, sda_pin)
                
                version = self.lector_rfid._rreg(0x37)
                print(f"[INFO] RFID RC522 inicializado. Versión: 0x{version:02x}")
                if version == 0x00 or version == 0xff:
                    print("[ALERTA CRÍTICA] Sin conexión SPI (versión 0x00). Revisa cables.")
            except Exception as e:
                print(f"[ERROR] Falló inicialización RC522: {e}")
                self.lector_rfid = None
        else:
            self.lector_rfid = None
            print("[ADVERTENCIA] No se encontró mfrc522.py, RFID desactivado.")


    def leer_rfid(self):
        if self.lector_rfid:
            try:
                # Re-inicializar antena antes de cada lectura (como hace el código de prueba exitoso)
                self.lector_rfid.init()
                import utime
                utime.sleep_ms(50)
                
                (stat, tag_type) = self.lector_rfid.request(self.lector_rfid.REQIDL)
                if stat == self.lector_rfid.OK:
                    (stat, raw_uid) = self.lector_rfid.anticoll()
                    if stat == self.lector_rfid.OK:
                        self.uid_actual = "-".join([hex(i)[2:].upper() for i in raw_uid])
                        print(f"[RFID] Tarjeta detectada: {self.uid_actual}")
                        return self.uid_actual
                    else:
                        print(f"[DEBUG RFID] Falló anticoll, stat: {stat}")
            except Exception as e:
                print(f"[DEBUG RFID] Excepción al leer: {e}")
            self.uid_actual = ""
            return self.uid_actual
        else:
            self.uid_actual = ""
            return self.uid_actual
    

    
    def leer_pulso_hrv(self):
        if self.sensor_pulso:
            try:
                # Extraer TODAS las muestras acumuladas en lugar de solo 1
                muestras = self.sensor_pulso.read_available_samples()
                if not muestras:
                    # Si no hay muestras nuevas, devolvemos el último estado conocido asumiendo que no hay dedo
                    return {"pulso_bpm": 0, "hrv_ms": 0, "red": 0, "ir": 0}
                
                # Tomar la muestra más reciente para revisar el umbral de presencia de dedo
                ultimo_red, ultimo_ir = muestras[-1]
                
                # Umbral de detección ajustado para LED a 7mA:
                if 400 < ultimo_ir < 120000:
                    # Hay dedo, agregamos las muestras al historial para análisis matemático
                    self.detector_pulso.procesar_muestras(muestras)
                    bpm_real = self.detector_pulso.calcular_bpm()
                    return {"pulso_bpm": bpm_real, "hrv_ms": 0, "red": ultimo_red, "ir": ultimo_ir}
                else:
                    # No hay dedo o hay luz ambiental bloqueando. Limpiamos historial.
                    self.detector_pulso.limpiar()
                    return {"pulso_bpm": 0, "hrv_ms": 0, "red": ultimo_red, "ir": ultimo_ir}
            except Exception as e:
                # Retornamos el error en el JSON para verlo en el servidor
                return {"pulso_bpm": 0, "hrv_ms": 0, "error_sensor": str(e)}
        else:
            return {"pulso_bpm": 0, "hrv_ms": 0}
    
    def obtener_resumen_sensores(self):
        return {
            "rfid_uid": self.leer_rfid(),
            "pulso_hrv": self.leer_pulso_hrv()
        }

class CajaActuadores:
    def __init__(self):
        self.mensajes_pantalla = []
        

        
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
    

    
    def estado_seguro(self):
        print("[EMERGENCIA] ESTADO SEGURO ACTIVADO")
        self.tono_buzzer("error")
        self.mostrar_mensaje("ESTADO SEGURO", "Sistema detenido")
