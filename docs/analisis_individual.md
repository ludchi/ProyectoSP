# Análisis Individual y Conclusiones
**PROYECTO:** Sistema de registro de Asistencias y Desgaste Laboral

> **IMPORTANTE:** Este documento es OBLIGATORIO para evitar la penalización del 40% en la rúbrica de la materia.
> Cada integrante debe rellenar su respectiva sección explicando un problema técnico que enfrentó, cómo lo resolvió y su conclusión personal sobre la arquitectura implementada (HAL y MQTT).

---

## 1. Integrante: CASTRO LUNA CESAR ARMANDO

### Práctica: HAL y MQTT
*   **Problema encontrado:** Inestabilidad en la recepción de datos del sensor de pulso al publicarlos concurrentemente por MQTT, lo que causaba desconexiones del broker debido a la saturación de mensajes por segundo.
*   **Solución aplicada:** Se ajustó el código en la capa HAL para procesar las lecturas en la ESP32 de forma local y enviar únicamente un resumen estabilizado cada vez que se detecta un pulso válido, reduciendo drásticamente la carga de red.
*   **Conclusión personal:** El uso de la arquitectura HAL demostró ser esencial para aislar los problemas de hardware de la comunicación de red. MQTT resultó ser un protocolo muy ligero y apto, pero requiere un buen manejo del flujo de datos para no saturar los dispositivos.

### Práctica: Integración en la Nube y Dashboard (Firebase)
*   **Problema en la Nube:** Retrasos significativos y alto consumo de cuota al subir fotos contínuas de la ESP32-CAM al dashboard para monitoreo en vivo.
*   **Solución en la Nube:** Se modificó la lógica en el servidor Python para que guarde las imágenes en memoria RAM y **sólo las suba a Firebase** en el instante en que un empleado pasa su tarjeta RFID (registrando su asistencia), limitando el uso a dos fotos por empleado al día.
*   **Conclusión personal:** La integración con Firebase requiere un diseño cuidadoso de la base de datos para evitar altos costos por operaciones de escritura y almacenamiento de archivos excesivos.

### Práctica: Integración de Inteligencia Artificial (Detección de Fatiga)
*   **Problema encontrado:** El modelo de IA (MediaPipe Face Landmarker) ocasionalmente daba falsos positivos de "fatiga" bajo condiciones de iluminación muy baja, ya que no lograba localizar correctamente los puntos de los ojos.
*   **Solución aplicada:** Se ajustó el umbral del EAR (Eye Aspect Ratio) a 0.25 para ser menos estricto y se configuró un proceso que envía una alerta específica "Alerta_IA" a Firebase cuando se detecta el EAR por debajo de lo normal de forma prolongada.
*   **Conclusión personal:** La IA es muy potente, pero su precisión depende fuertemente de la calidad de los datos de entrada. En un ecosistema IoT, asegurar una buena captura desde la cámara es tan importante como el modelo mismo.

---

## 2. Integrante: ESPINOZA BRAVO LUDWIG

### Práctica: HAL y MQTT
*   **Problema encontrado:** Los conflictos de alimentación al tener el lector RFID MFRC522 (3.3V) y el MAX30102 (que necesita picos fuertes de corriente) en la misma placa ESP32, lo que provocaba que la pantalla OLED se apagara al poner el dedo en el sensor.
*   **Solución aplicada:** Se estructuró un flujo donde se simplificaron los componentes, retirando hardware innecesario (ultrasonido, relé) y alimentando el MAX30102 directamente del pin VIN (5V) mientras se mantenía el RFID rígidamente en 3.3V, aislando los picos de consumo.
*   **Conclusión personal:** Separar correctamente la alimentación de los sensores y entender los niveles lógicos es vital. La separación del hardware mediante clases en Python nos permitió enfocarnos en la lógica biométrica sin preocuparnos por detalles eléctricos al final.

### Práctica: Integración en la Nube y Dashboard (Firebase)
*   **Problema en el Dashboard:** La tabla de asistencias mostraba un registro largo y confuso, sin agrupar por empleado y saturando la vista.
*   **Solución en el Dashboard:** Se reescribió la lógica en Javascript (`app.js`) para descargar hasta 50 registros recientes y agruparlos dinámicamente por empleado, mostrando solo la hora de Entrada, la de Salida y calculando el nivel de estrés visualmente en una sola fila compacta.
*   **Conclusión personal:** La adición de Firebase al ecosistema no es suficiente si el Frontend no procesa los datos; agrupar información en el cliente web permite construir interfaces altamente legibles y amigables.

### Práctica: Integración de Inteligencia Artificial (Detección de Fatiga)
*   **Problema encontrado:** La cámara mostraba la misma foto para todos si alguien se quedaba parado mucho tiempo, o la imagen parpadeaba feo en el dashboard web.
*   **Solución aplicada:** Se integró un temporizador de 10 segundos en JavaScript que elimina la imagen del dashboard automáticamente luego de cada escaneo, regresando al estado "Esperando..." para asegurar que el sistema se vea limpio para el próximo empleado.
*   **Conclusión personal:** La IA que detecta rostros debe ir acompañada de una muy buena experiencia de usuario (UX). Un diseño web ordenado ayuda a que los resultados del modelo de Machine Learning brillen.

---

## 3. Integrante: LOZANO CARDONA ANGEL JOSUE

### Práctica: HAL y MQTT
*   **Problema encontrado:** Conflictos de concurrencia y sobrecarga de memoria al intentar enviar frames pesados de cámara y recibir instrucciones simultáneamente en la misma placa.
*   **Solución aplicada:** Se optó por diseñar la arquitectura separando la ESP32-CAM como un nodo de hardware totalmente independiente (`nodo_camara`), dejando a la ESP32 principal libre para manejar los sensores biométricos (pulso y tarjeta).
*   **Conclusión personal:** La implementación del estándar jerárquico de tópicos MQTT fue un acierto total para el diseño del sistema. Facilita enormemente depurar los mensajes y permite que el ecosistema escale fácilmente con más cámaras o lectores.

### Práctica: Integración en la Nube y Dashboard (Firebase)
*   **Problema de Integridad (Nube):** Los usuarios pasaban su tarjeta varias veces accidentalmente (o por jugar), creando spam en la base de datos y calculando falsas "Salidas" con estrés corrupto un par de segundos después de su entrada.
*   **Solución en la Nube:** Se implementó una lógica de "Cooldown" de 5 minutos directamente en el script central de Python. Si la persona intenta escanear dos veces en ese lapso, la lectura se ignora para Firebase, pero se envía un comando remoto por MQTT a la pantalla OLED para advertirle "Espera 5m rest" al usuario.
*   **Conclusión personal:** Validar la lógica de negocio (como bloquear el spam) en el servidor perimetral (Python) en lugar del hardware o la nube protege la cuota de Firebase y mantiene la estabilidad del sistema.

### Práctica: Integración de Inteligencia Artificial (Detección de Fatiga)
*   **Problema encontrado:** Riesgo de saturar el broker MQTT al transmitir cadenas gigantescas de Base64 correspondientes a las imágenes de la cámara, afectando a la telemetría de otros sensores (como pulso y RFID).
*   **Solución aplicada:** Se configuró a la ESP32-CAM para usar un tópico MQTT completamente dedicado (`asistlab/sensor/camara/cam_01`), asegurando que el servidor reciba la imagen, decodifique, analice la fatiga con OpenCV, y envíe el "visto bueno" a la OLED sin afectar los tiempos del hardware.
*   **Conclusión personal:** El ecosistema IoT es muy flexible; usar Python como "cerebro central" de IA escuchando tópicos MQTT resulta en una arquitectura robusta, modular y fácil de escalar a múltiples nodos de IA en el futuro sin forzar el hardware empotrado.
