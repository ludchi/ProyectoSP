# Análisis Individual Final: Fabricación y Ensamble Físico

> **IMPORTANTE:** Llenar este documento es un requisito CRÍTICO para evitar una penalización del 40% en la nota final. Cada integrante debe describir sus propios retos, soluciones y conclusiones respecto a la etapa de ensamblaje físico del dispositivo.

---

## 1. Integrante: CASTRO LUNA CESAR ARMANDO

### Problema (Retos de la fabricación física)
Al intentar montar todos los componentes en una sola placa, enfrentamos caídas de tensión severas y reinicios aleatorios en la ESP32. El sensor de ritmo cardíaco (MAX30102) exigía picos de corriente fuertes a 5V que afectaban la lectura del lector RFID (MFRC522) que operaba a 3.3V. Además, intentar que la misma ESP32 procesara la cámara y los biométricos sobrecargaba la memoria RAM del microcontrolador.

### Solución de ingeniería aplicada
Rediseñé completamente el circuito físico aislando los buses de voltaje. Creé líneas independientes para los 5V (OLED y MAX30102) y 3.3V (RFID). Para solucionar la memoria, tomé la decisión de retirar la cámara del circuito principal y separar la ESP32-CAM como un nodo de red completamente independiente. A nivel de firmware, programé una capa HAL para testear cada hardware por separado, asegurando una integración final libre de cortocircuitos.

### Conclusión de cierre del proyecto
El ensamble físico me enseñó que la electrónica no perdona errores de diseño. Comprendí que el hardware debe modularizarse igual que el software; separar la carga eléctrica y el procesamiento en múltiples nodos fue la clave para que nuestro sistema fuera verdaderamente estable en producción.

---

## 2. Integrante: ESPINOZA BRAVO LUDWIG

### Problema (Retos de la fabricación física y conectividad)
La transición a la conectividad real generó dos grandes problemas lógicos: primero, enviar pesadas cadenas en Base64 desde la cámara saturaba el broker MQTT y bloqueaba las lecturas de los sensores biométricos. Segundo, los usuarios al registrarse pasaban la tarjeta múltiples veces por error, creando spam masivo en Firebase y generando cálculos corruptos de estrés laboral.

### Solución de ingeniería aplicada
Implementé una arquitectura de Servidor Perimetral (Edge Computing) en Python. Creé una estructura de subprocesamiento asíncrono donde MQTT maneja los fotogramas en paralelo. Para el spam, desarrollé una lógica de bloqueo ("cooldown") de 5 minutos en el servidor: si se detecta un doble escaneo, Python bloquea el envío a la nube y manda un comando MQTT al OLED físico indicando "Espera 5 mins". Además, moví todo el análisis pesado de MediaPipe a este servidor para proteger los recursos de los microcontroladores.

### Conclusión de cierre del proyecto
Concluyo que la nube no debe ser un vertedero de datos en bruto. Procesar la Inteligencia Artificial de forma perimetral en una computadora y aplicar filtros lógicos antes de tocar Firebase, es el factor que separa a un simple prototipo de un sistema IoT escalable y profesional.

---

## 3. Integrante: LOZANO CARDONA ANGEL JOSUE

### Problema (Retos de Diseño Web y Chasis)
Por el lado de software, el Dashboard web sufría problemas de actualización: si hacíamos *polling* continuo, agotábamos la cuota gratuita de lectura en Firebase; si no lo hacíamos, la página mostraba datos viejos. Por el lado de hardware, encapsular el prototipo en un chasis genérico forzaba los cables Dupont y ocultaba la visibilidad de la OLED y los LEDs de alerta, arruinando la interacción física.

### Solución de ingeniería aplicada
Programé el Frontend en JavaScript puro utilizando el listener `onSnapshot` de Firebase, logrando que el Dashboard fuera 100% reactivo (cero polling) y agrupando dinámicamente el estrés de los empleados en tarjetas con timers visuales. Físicamente, diseñé la distribución estructural del chasis priorizando la ergonomía: coloqué la lente de la ESP32-CAM y la OLED a la altura visual, e integré aberturas específicas para la tarjeta y el dedo, gestionando el espacio para que los cables no sufrieran dobleces térmicos.

### Conclusión de cierre del proyecto
Aprendí que la Experiencia de Usuario (UX) conecta todo el esfuerzo de ingeniería. Un backend potente y un circuito complejo no sirven de nada si el chasis físico es incómodo de usar o si la plataforma web no despliega la información vital (como alertas de fatiga) de forma instantánea y legible para el cliente final.
