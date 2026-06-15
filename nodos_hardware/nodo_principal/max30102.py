from machine import I2C
import time

class MAX30102:
    def __init__(self, i2c, address=0x57):
        self.i2c = i2c
        self.address = address
        self.setup()

    def setup(self):
        # Inicialización básica del sensor
        self.i2c.writeto_mem(self.address, 0x09, b'\x40') # Reset
        time.sleep(0.1)
        self.i2c.writeto_mem(self.address, 0x09, b'\x03') # Modo SpO2 y HR
        self.i2c.writeto_mem(self.address, 0x0A, b'\x23') # Configuración de LED (411us, 4096nA, 50Hz)
        
        # FIFO Config: Promediar 2 muestras (SMP_AVE=001) y activar Rollover (FIFO_ROL_LO_EN=1) -> 00110000 = 0x30
        self.i2c.writeto_mem(self.address, 0x08, b'\x30')
        
        self.i2c.writeto_mem(self.address, 0x0C, b'\x24') # Corriente LED1 (Rojo)
        self.i2c.writeto_mem(self.address, 0x0D, b'\x24') # Corriente LED2 (IR)

    def read_fifo(self):
        # Lee los datos crudos de una sola muestra
        data = self.i2c.readfrom_mem(self.address, 0x07, 6)
        red = (data[0] << 16 | data[1] << 8 | data[2]) & 0x03FFFF
        ir = (data[3] << 16 | data[4] << 8 | data[5]) & 0x03FFFF
        return red, ir

    def read_available_samples(self):
        # Lee todas las muestras acumuladas en el FIFO sin bloquear
        wr_ptr = self.i2c.readfrom_mem(self.address, 0x04, 1)[0]
        rd_ptr = self.i2c.readfrom_mem(self.address, 0x06, 1)[0]
        
        samples_available = wr_ptr - rd_ptr
        if samples_available < 0:
            samples_available += 32
            
        if samples_available == 0:
            return []
            
        # Leer todo de golpe (hasta 192 bytes)
        bytes_to_read = samples_available * 6
        data = self.i2c.readfrom_mem(self.address, 0x07, bytes_to_read)
        
        samples = []
        for i in range(samples_available):
            offset = i * 6
            red = (data[offset] << 16 | data[offset+1] << 8 | data[offset+2]) & 0x03FFFF
            ir = (data[offset+3] << 16 | data[offset+4] << 8 | data[offset+5]) & 0x03FFFF
            samples.append((red, ir))
            
        return samples