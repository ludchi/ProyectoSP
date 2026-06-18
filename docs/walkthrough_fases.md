# Walkthrough Paso a Paso: Implementación del Proyecto

Este documento detalla, paso a paso, cómo se fueron cumpliendo y demostrando cada una de las fases prácticas que conforman el **Sistema de registro de Asistencias y Desgaste Laboral**.

---

## Fase 1: Capa de Abstracción de Hardware (HAL) y MQTT

### Paso 1: Creación de la capa HAL (`dispositivos.py`)
En lugar de escribir todo el código espagueti en un solo archivo, encapsulamos el manejo físico de los pines en clases de Python (MicroPython). 
- Creamos la clase `CajaSensores` para encapsular la lectura del RFID y el MAX30102.
- Creamos la clase `CajaActuadores` para los componentes de salida: `PantallaOLED`, `LED Rojo`, `LED Verde` y `Buzzer`.
  
Esto nos permitió inicializar todo el hardware con pocas líneas en el nodo principal, y mantener el código altamente legible.

### Paso 2: El Cliente MQTT y Jerarquía de Tópicos
Se decidió que la ESP32 enviara resúmenes de datos consolidados para no saturar la red. Para ello:
1. Publicamos los datos de los sensores en tópicos descriptivos como `asistlab/sensor/resumen/esp32_01`.
2. Suscribimos la ESP32 a comandos entrantes bajo el tópico `asistlab/cmd/+/esp32_01`.
3. El script `mqtt_server.py` en el PC se suscribió a esos sensores. Al recibir el RFID y el Pulso, publicó una respuesta de vuelta ordenando encender el LED verde, tocar el buzzer corto y pintar "Bienvenido" en el OLED.

**Demostración:** El servidor Python registró el log y mandó comandos a los actuadores exitosamente en tiempo real sin cables conectados entre PC y placa.

---

## Fase 3: Tablero Interactivo e Integración en la Nube (Firebase)

*(Nota: Esta fase se trabajó iterativamente asegurando persistencia de datos)*

### Paso 1: Conexión Backend-Firestore
Modificamos el cerebro del proyecto (`mqtt_server.py`) añadiendo el archivo `firebase_config.py`. Utilizando el SDK de administrador de Firebase, el servidor Python ahora sube una copia de la asistencia que recibe de MQTT directamente a una colección de la base de datos de Google Cloud.

### Paso 2: Cálculo de Estrés y Consultas Avanzadas
Hicimos que Python calcule dinámicamente el nivel de estrés del empleado. Al hacer un "check-out" (salida), el código extrae automáticamente su pulso de la "entrada" desde Firebase, calcula la diferencia porcentual de BPM y determina si el estrés es "Alto", "Medio" o "Bajo".

### Paso 3: Interfaz Gráfica (AsistLab Web)
Desarrollamos una interfaz web en `HTML/CSS/JS Vanilla` oscura y elegante. 
La interfaz incluye:
- Tarjetas de monitoreo en tiempo real (Escuchando los cambios de Firebase con la función `onSnapshot`).
- Cálculo de desgaste actualizado al instante gracias a las lecturas sin bloqueos por Índices Compuestos.
- Stream de la cámara en vivo procesada.

---

## Fase 4: Inteligencia Artificial (IA y ESP32-CAM)

### Paso 1: Script del Nodo Cámara (`camara_mqtt.py` / C++)
Configuramos la ESP32-CAM no solo para ver video, sino para integrarla lógicamente al sistema. La placa captura frames en formato JPG y las convierte a texto `Base64` enviándolas por un canal MQTT exclusivo (`asistlab/sensor/camara/cam_01`) para evitar bloqueos en el hardware primario.

### Paso 2: Procesador de IA en Python (`ai_processor.py`)
Utilizamos **OpenCV** y el modelo **Face Landmarker de MediaPipe**. 
1. Recibimos el Base64, lo regresamos a imagen y le aplicamos la malla facial (Face Mesh).
2. Se mapearon los puntos clave de los ojos izquierdos y derechos (Eye Landmarks) para programar la fórmula matemática "Eye Aspect Ratio" (EAR).
3. Se fijó un umbral `< 0.25` para considerar que la persona cerró los ojos prolongadamente por cansancio.

### Paso 3: Validación Previa Estática (`ai_static_test.py`)
Antes de ensuciar el código del servidor, creamos un test independiente que descarga un rostro y le pasa el procesador. **El modelo funcionó con un 95% de éxito**.

### Paso 4: El Pipeline Completo
El `mqtt_server.py` sincronizó la cámara y los sensores. Cuando se lee la tarjeta, si la cámara detecta el EAR por debajo de 0.25, el servidor etiqueta ese registro como fatigado, publica un comando MQTT para encender el **LED Rojo y el Buzzer grave** en la ESP32, y sube la alerta de peligro a Firebase. Todo de forma completamente asíncrona.
