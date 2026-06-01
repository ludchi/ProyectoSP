# Análisis Individual y Conclusiones
**PROYECTO:** Sistema de registro de Asistencias y Desgaste Laboral

> **IMPORTANTE:** Este documento es OBLIGATORIO para evitar la penalización del 40% en la rúbrica de la materia.
> Cada integrante debe rellenar su respectiva sección explicando un problema técnico que enfrentó, cómo lo resolvió y su conclusión personal sobre la arquitectura implementada (HAL y MQTT).

---

## 1. Integrante: CASTRO LUNA CESAR ARMANDO

### Práctica: HAL y MQTT
*   **Problema encontrado:** Inestabilidad en la recepción de datos del sensor de pulso al publicarlos concurrentemente por MQTT, lo que causaba desconexiones del broker debido a la saturación de mensajes por segundo.
*   **Solución aplicada:** Se ajustó el código en la capa HAL para procesar las lecturas en la ESP32 de forma local y enviar únicamente un resumen estabilizado cada 2 segundos, reduciendo drásticamente la carga de red.
*   **Conclusión personal:** El uso de la arquitectura HAL demostró ser esencial para aislar los problemas de hardware de la comunicación de red. MQTT resultó ser un protocolo muy ligero y apto, pero requiere un buen manejo del flujo de datos para no saturar los dispositivos.

### Práctica: Integración en la Nube y Dashboard (Firebase)
*   **Problema en la Nube:** Retrasos significativos (latencia) al subir cada evento de telemetría individual a Firestore, provocando cuellos de botella en el servidor Python.
*   **Solución en la Nube:** Se implementó una lógica asíncrona usando `firebase-admin` en el servidor, agrupando las actualizaciones de telemetría frecuentes en el documento `estado_actual` en lugar de crear un documento nuevo cada segundo, y reservando la creación de documentos nuevos únicamente para eventos críticos como `Alerta_IA`.
*   **Conclusión personal:** La integración con Firebase requiere un diseño cuidadoso de la base de datos (NoSQL) para evitar problemas de latencia y altos costos por operaciones de escritura excesivas.

### Práctica: Integración de Inteligencia Artificial (Detección de Fatiga)
*   **Problema encontrado:** El modelo de IA (MediaPipe Face Landmarker) ocasionalmente daba falsos positivos de "fatiga" bajo condiciones de iluminación muy baja, ya que no lograba localizar correctamente los puntos de los ojos (landmarks).
*   **Solución aplicada:** Se agregó un preprocesamiento básico en OpenCV para ecualizar el histograma de la imagen si está muy oscura antes de pasarla al modelo, y se ajustó el umbral del EAR (Eye Aspect Ratio) a 0.25 para ser menos estricto.
*   **Conclusión personal:** La IA es muy potente, pero su precisión depende fuertemente de la calidad de los datos de entrada. En un ecosistema IoT, asegurar una buena captura desde la cámara es tan importante como el modelo mismo.

---

## 2. Integrante: EPINOZA BRAVO LUDWING

### Práctica: HAL y MQTT
*   **Problema encontrado:** Interferencia de las peticiones de red (Wi-Fi/MQTT) de la ESP32 sobre los retardos críticos que necesitan el sensor HC-SR04 y el Buzzer, generando mediciones falsas de distancia.
*   **Solución aplicada:** Se estructuró un flujo no bloqueante (non-blocking) con la función `check_msg()` de MQTT para no bloquear el hilo principal, logrando mantener el control del relé y buzzer de forma estable.
*   **Conclusión personal:** Poder enviar comandos JSON a través de tópicos de forma asíncrona es una gran ventaja de MQTT. La separación del hardware mediante clases en Python nos permitió enfocarnos en la lógica de 'Check-In' sin preocuparnos por los detalles eléctricos.

### Práctica: Integración en la Nube y Dashboard (Firebase)
*   **Problema en el Dashboard:** Desincronización de la interfaz web, donde el usuario debía refrescar manualmente la página para ver si un comando remoto había sido ejecutado.
*   **Solución en el Dashboard:** Se cambió el enfoque de consulta tradicional (polling) por una suscripción `onSnapshot` del SDK modular de Firebase. Esto permitió que la interfaz web reaccione en tiempo real a los cambios de estado en la nube, mostrando retroalimentación visual inmediata.
*   **Conclusión personal:** La adición de Firebase a la arquitectura simplifica la creación de interfaces responsivas y en tiempo real, conectando el mundo del hardware con el de los usuarios finales de manera transparente.

### Práctica: Integración de Inteligencia Artificial (Detección de Fatiga)
*   **Problema encontrado:** La latencia al enviar imágenes desde la ESP32-CAM por MQTT causaba que el modelo de Python procesara cuadros desactualizados, perdiendo la sincronía con el estado real del usuario.
*   **Solución aplicada:** Se redujo la resolución de la captura en la ESP32 a QVGA y se implementó un sistema de "skip-frames" en el servidor Python, procesando solo el fotograma más reciente y descartando los encolados.
*   **Conclusión personal:** La integración de IA en un servidor externo (Python) permite usar modelos pesados (como Face Mesh) que no cabrían en la memoria de la ESP32, siempre que la red sea rápida y estable.

---

## 3. Integrante: LOZANO CARDONA ANGEL JOSUE

### Práctica: HAL y MQTT
*   **Problema encontrado:** Conflictos de concurrencia y sobrecarga de memoria al intentar enviar frames pesados de cámara y recibir instrucciones simultáneamente en la misma placa.
*   **Solución aplicada:** Se optó por diseñar la arquitectura separando la ESP32-CAM como un nodo de hardware totalmente independiente (`nodo_camara`), dejando a la ESP32 principal libre para manejar los demás sensores y actuadores.
*   **Conclusión personal:** La implementación del estándar jerárquico de tópicos (`proyecto/tipo_nodo/nombre_modulo/id`) fue un acierto total para el diseño del sistema. Facilita enormemente depurar los mensajes y permite que el ecosistema escale fácilmente.

### Práctica: Integración en la Nube y Dashboard (Firebase)
*   **Problema de Seguridad (Nube):** Riesgo de exposición de datos sensibles (imágenes no anonimizadas) y acceso no autorizado a los comandos de actuadores expuestos públicamente en Firestore.
*   **Solución de Seguridad:** Se implementó una estricta política de privacidad en el servidor Python, asegurando que ningún dato visual identificable se suba a Firebase. Además, se configuraron colecciones separadas (`comandos_remotos` vs `alertas`) preparadas para ser protegidas mediante reglas de seguridad de Firestore (Security Rules) que restrinjan el control de actuadores solo a usuarios autenticados.
*   **Conclusión personal:** Integrar Firebase demostró que la seguridad debe ser prioridad desde el diseño inicial, asegurando que la anonimización ocurra en el servidor perimetral (Python) antes de llegar a la nube pública.

### Práctica: Integración de Inteligencia Artificial (Detección de Fatiga)
*   **Problema encontrado:** Riesgo de saturar el broker MQTT al transmitir cadenas gigantescas de Base64 correspondientes a las imágenes de la cámara, afectando a la telemetría de otros sensores (como pulso y RFID).
*   **Solución aplicada:** Se configuró a la ESP32-CAM para usar un tópico MQTT completamente dedicado (`asistlab/sensor/camara/cam_01`) con QoS 0, asegurando que su gran ancho de banda no bloquee los mensajes críticos del sistema de control de acceso.
*   **Conclusión personal:** El ecosistema IoT es muy flexible; usar Python como "cerebro central" de IA escuchando tópicos MQTT resulta en una arquitectura robusta, modular y fácil de escalar a múltiples cámaras en el futuro sin modificar el hardware.
