# Walkthrough Paso a Paso: Implementación del Proyecto

Este documento detalla, paso a paso, cómo se fueron cumpliendo y demostrando cada una de las fases prácticas que conforman el **Sistema de registro de Asistencias y Desgaste Laboral**.

---

## Fase 1: Capa de Abstracción de Hardware (HAL) y MQTT

### Paso 1: Creación de la capa HAL (`dispositivos.py`)
En lugar de escribir todo el código espagueti en un solo archivo, encapsulamos el manejo físico de los pines en clases de Python (MicroPython). 
- Creamos la clase `LectorRFID` para el bus SPI.
- Creamos las clases `SensorUltrasónico` y `SensorPulso` para captar la información ambiental y fisiológica.
- Creamos clases para los actuadores: `PantallaOLED`, `Buzzer`, `Rele`.
  
Esto nos permitió inicializar todo el hardware con pocas líneas en el nodo principal, y mantener el código altamente legible.

### Paso 2: El Cliente MQTT y Jerarquía de Tópicos
Se decidió que la ESP32 enviara resúmenes de datos consolidados para no saturar la red (ej. cada 2 segundos). Para ello:
1. Publicamos los datos de los sensores en tópicos descriptivos como `asistlab/sensor/resumen/esp32_01`.
2. Suscribimos la ESP32 a comandos entrantes bajo el tópico `asistlab/cmd/+/esp32_01`.
3. El script `mqtt_server.py` en el PC se suscribió a esos sensores. Recibió el RFID y la Distancia, y usando condicionales, publicó una respuesta de vuelta ordenando abrir la puerta (Relé) y pintar "CHECK-IN OK" en el OLED.

**Demostración:** El servidor Python registró el log y mandó comandos a los actuadores exitosamente en tiempo real sin cables conectados entre PC y placa.

---

## Fase 3: Tablero Interactivo e Integración en la Nube (Firebase)

*(Nota: Esta fase se trabajó iterativamente asegurando persistencia de datos)*

### Paso 1: Conexión Backend-Firestore
Modificamos el cerebro del proyecto (`mqtt_server.py`) añadiendo el archivo `firebase_config.py`. Utilizando el SDK de administrador de Firebase, el servidor Python ahora sube una copia de la telemetría que recibe de MQTT directamente a una colección de la base de datos de Google Cloud en formato JSON.

### Paso 2: Escucha Activa de Comandos
Hicimos que Python abra un túnel persistente (Listener/Snapshot) hacia la colección `comandos_remotos`. Cuando insertábamos manualmente un documento para activar el buzzer, Firebase le avisaba a Python en milisegundos, y Python le avisaba por MQTT a la ESP32.

### Paso 3: Interfaz Gráfica (AsistLab Web)
Desarrollamos una interfaz web en `HTML/CSS/JS Vanilla` oscura y elegante. 
La interfaz incluye:
- Tarjetas de monitoreo en tiempo real (Escuchando los cambios de Firebase con la función `onSnapshot`).
- Botones de "Abrir Puerta" y "Disparar Alarma".
- Al presionar un botón, el Javascript empuja un documento a Firestore, que viaja al servidor Python, y de ahí llega a los actuadores físicos.

---

## Fase 4: Inteligencia Artificial (IA y ESP32-CAM)

### Paso 1: Script del Nodo Cámara (`camara_mqtt.py`)
Configuramos la ESP32-CAM no solo para ver video (Visualizador), sino para integrarla lógicamente al sistema. La placa captura frames en formato JPG y las convierte a texto `Base64` enviándolas por un canal MQTT exclusivo (`asistlab/sensor/camara/cam_01`) para evitar bloqueos en el hardware primario.

### Paso 2: Procesador de IA en Python (`ai_processor.py`)
Utilizamos **OpenCV** y el modelo **Face Landmarker de MediaPipe**. 
1. Recibimos el Base64, lo regresamos a imagen y le aplicamos la malla facial (Face Mesh).
2. Se mapearon los puntos clave de los ojos izquierdos y derechos (Eye Landmarks) para programar la fórmula matemática "Eye Aspect Ratio" (EAR).
3. Se fijó un umbral `< 0.25` para considerar que la persona cerró los ojos prolongadamente por cansancio.

### Paso 3: Validación Previa Estática (`ai_static_test.py`)
Antes de ensuciar el código del servidor, creamos un test independiente que descarga un rostro y le pasa el procesador. **El modelo funcionó con un 95% de éxito**.

### Paso 4: El Pipeline Completo
El `mqtt_server.py` se suscribió a la cámara. Ahora el servidor recibe imágenes en tiempo real, las escanea en milisegundos buscando fatiga, y si el EAR es bajo, se emite una alerta auditiva mediante el tópico `asistlab/cmd/buzzer/esp32_01` y se sube el reporte `Alerta_IA` a Firebase. Todo de forma completamente desatendida.
