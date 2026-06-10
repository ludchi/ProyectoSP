import network
import time

# Configuración de tu red Wi-Fi
SSID = 'TU_RED_WIFI'
PASSWORD = 'TU_CONTRASEÑA_WIFI'

def connect_wifi():
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        print('Conectando a la red Wi-Fi...')
        sta_if.active(True)
        sta_if.connect(SSID, PASSWORD)
        
        # Esperar hasta que se conecte
        timeout = 10
        while not sta_if.isconnected() and timeout > 0:
            time.sleep(1)
            print('.', end='')
            timeout -= 1
            
    if sta_if.isconnected():
        print('\nConexión exitosa!')
        print('Configuración de red (IP, Máscara, Puerta de enlace, DNS):', sta_if.ifconfig())
    else:
        print('\nError: No se pudo conectar a la red Wi-Fi. Revisa el SSID y la contraseña.')

connect_wifi()
