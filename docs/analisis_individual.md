# Análisis Individual y Conclusiones
**PROYECTO:** Sistema de registro de Asistencias y Desgaste Laboral

> **IMPORTANTE:** Este documento es OBLIGATORIO para evitar la penalización del 40% en la rúbrica de la materia.
> Cada integrante debe rellenar su respectiva sección explicando un problema técnico que enfrentó, cómo lo resolvió y su conclusión personal sobre la arquitectura implementada (HAL y MQTT).

---

## 1. Integrante: CASTRO LUNA CESAR ARMANDO
*   **Problema encontrado:** Inestabilidad en la recepción de datos del sensor de pulso al publicarlos concurrentemente por MQTT, lo que causaba desconexiones del broker debido a la saturación de mensajes por segundo.
*   **Solución aplicada:** Se ajustó el código en la capa HAL para procesar las lecturas en la ESP32 de forma local y enviar únicamente un resumen estabilizado cada 2 segundos, reduciendo drásticamente la carga de red.
*   **Conclusión personal:** El uso de la arquitectura HAL demostró ser esencial para aislar los problemas de hardware de la comunicación de red. MQTT resultó ser un protocolo muy ligero y apto, pero requiere un buen manejo del flujo de datos para no saturar los dispositivos.

---

## 2. Integrante: EPINOZA BRAVO LUDWING
*   **Problema encontrado:** Interferencia de las peticiones de red (Wi-Fi/MQTT) de la ESP32 sobre los retardos críticos que necesitan el sensor HC-SR04 y el Buzzer, generando mediciones falsas de distancia.
*   **Solución aplicada:** Se estructuró un flujo no bloqueante (non-blocking) con la función `check_msg()` de MQTT para no bloquear el hilo principal, logrando mantener el control del relé y buzzer de forma estable.
*   **Conclusión personal:** Poder enviar comandos JSON a través de tópicos de forma asíncrona es una gran ventaja de MQTT. La separación del hardware mediante clases en Python nos permitió enfocarnos en la lógica de 'Check-In' sin preocuparnos por los detalles eléctricos.

---

## 3. Integrante: LOZANO CARDONA ANGEL JOSUE
*   **Problema encontrado:** Conflictos de concurrencia y sobrecarga de memoria al intentar enviar frames pesados de cámara y recibir instrucciones simultáneamente en la misma placa.
*   **Solución aplicada:** Se optó por diseñar la arquitectura separando la ESP32-CAM como un nodo de hardware totalmente independiente (`nodo_camara`), dejando a la ESP32 principal libre para manejar los demás sensores y actuadores.
*   **Conclusión personal:** La implementación del estándar jerárquico de tópicos (`proyecto/tipo_nodo/nombre_modulo/id`) fue un acierto total para el diseño del sistema. Facilita enormemente depurar los mensajes y permite que el ecosistema escale fácilmente.
