"""
OBJETIVO: Biblioteca HAL que abstrae RFID, pulso HRV y OLED para control de asistencias con medición de estrés laboral.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, ESPINOZA BRAVO LUDWIG, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
"""

import time
from machine import Pin, I2C, SPI

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

        # --- Configuración SPI y RC522 ---
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
                print(f"[DEBUG MAX30102] RAW_RED: {ultimo_red} | RAW_IR: {ultimo_ir}")
                
                # Umbral de detección ajustado para LED a 7mA:
                if 100 < ultimo_ir < 250000:
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
            # SIMULACIÓN (Ya que no hay sensor físico conectado)
            # Si hay una tarjeta presente, simulamos un pulso aleatorio
            if self.uid_actual != "":
                import random
                bpm_simulado = random.randint(65, 95)
                return {"pulso_bpm": bpm_simulado, "hrv_ms": 0, "simulado": True}
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

        # --- Configuración LEDs ---
        try:
            self.led_rojo = Pin(2, Pin.OUT)   # GPIO 2 - LED Rojo (Fatiga/Alerta)
            self.led_verde = Pin(4, Pin.OUT)  # GPIO 4 - LED Verde (Registro OK)
            self.led_rojo.off()
            self.led_verde.off()
            print("[INFO] LEDs inicializados: Rojo (GPIO 2), Verde (GPIO 4)")
        except Exception as e:
            print(f"[ERROR] Falló inicialización LEDs: {e}")
            self.led_rojo = None
            self.led_verde = None

        # --- Configuración Buzzer ---
        try:
            self.buzzer = Pin(15, Pin.OUT)    # GPIO 15 - Buzzer Pasivo
            self.buzzer.off()
            print("[INFO] Buzzer inicializado (GPIO 15)")
        except Exception as e:
            print(f"[ERROR] Falló inicialización Buzzer: {e}")
            self.buzzer = None

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
    
    def alerta_fatiga(self):
        """Actuador: LED Rojo + Buzzer largo indican fatiga en el momento del registro."""
        if self.led_rojo:
            print("[ACTUADOR] 🔴 LED ROJO: Registro con fatiga")
            self.led_rojo.on()
        if self.buzzer:
            print("[ACTUADOR] 🔊 BUZZER: Alerta de fatiga (tono largo)")
            # 3 beeps largos de alerta (tono más grave ~500 Hz)
            for _ in range(3):
                for _ in range(50):
                    self.buzzer.on()
                    time.sleep_us(1000)  # ~500 Hz (más grave que el normal)
                    self.buzzer.off()
                    time.sleep_us(1000)
                time.sleep_ms(200)
        # Mantener LED rojo 3 segundos y luego apagar
        time.sleep(3)
        if self.led_rojo:
            self.led_rojo.off()
    
    def confirmar_registro(self):
        """Actuador: LED Verde + Buzzer confirman un registro exitoso (entrada o salida)."""
        if self.led_verde:
            print("[ACTUADOR] 🟢 LED VERDE: Registro confirmado")
            self.led_verde.on()
        if self.buzzer:
            print("[ACTUADOR] 🔊 BUZZER: Beep de confirmación")
            # Generar un tono corto con el buzzer pasivo
            for _ in range(80):
                self.buzzer.on()
                time.sleep_us(500)  # ~1000 Hz
                self.buzzer.off()
                time.sleep_us(500)
        # Mantener LED verde 2 segundos y luego apagar
        time.sleep(2)
        if self.led_verde:
            self.led_verde.off()
    
    def apagar_todo(self):
        """Apaga todos los actuadores de señalización."""
        if self.led_rojo:
            self.led_rojo.off()
        if self.led_verde:
            self.led_verde.off()
        if self.buzzer:
            self.buzzer.off()

    def estado_seguro(self):
        print("[EMERGENCIA] ESTADO SEGURO ACTIVADO")
        self.apagar_todo()
        self.mostrar_mensaje("ESTADO SEGURO", "Sistema detenido")

