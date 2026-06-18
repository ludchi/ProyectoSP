/*
OBJETIVO: Gestión de Firebase y Dashboard de usuario.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, ESPINOZA BRAVO LUDWIG, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
*/

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import { getFirestore, collection, doc, onSnapshot, query, orderBy, limit } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-firestore.js";

// Your web app's Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyB46ZDJBJjSCHolBhS8U4LdXpmm11dJG6s",
  authDomain: "sadl-a3713.firebaseapp.com",
  projectId: "sadl-a3713",
  storageBucket: "sadl-a3713.firebasestorage.app",
  messagingSenderId: "761607923575",
  appId: "1:761607923575:web:f2da8247b1f49d07a1a372",
  measurementId: "G-LX5M1W2G8Y"
};

// Elementos del DOM
const statusDot = document.getElementById('system-status-dot');
const statusText = document.getElementById('system-status-text');
const valRfid = document.getElementById('val-rfid');
const valPulso = document.getElementById('val-pulso');
const alertsList = document.getElementById('alerts-list');
const tablaAsistencias = document.getElementById('tabla-asistencias');
const cameraFeed = document.getElementById('camera-feed');
const cameraOverlay = document.getElementById('camera-overlay');
const cameraStatus = document.getElementById('camera-status');

const CAMERA_URL = "http://localhost:8089/camara";
let db;
let cameraInterval;

try {
    const app = initializeApp(firebaseConfig);
    db = getFirestore(app);
    setOnlineStatus(true);
    initListeners();
    iniciarCamara();
} catch (error) {
    console.error("Error inicializando Firebase:", error);
    setOnlineStatus(false);
    alertsList.innerHTML = `<li class="alert-empty" style="color: var(--accent-red)">Error de conexión Firebase</li>`;
}

function setOnlineStatus(online) {
    if (online) {
        statusDot.className = 'pulse-dot online';
        statusText.textContent = 'Conectado a Firebase';
    } else {
        statusDot.className = 'pulse-dot offline';
        statusText.textContent = 'Desconectado';
    }
}

function initListeners() {
    // 1. Escuchar última telemetría RFID / Pulso (Si envías esto desde ESP32 a la DB, asegúrate que se actualice "estado_actual/sensores")
    // (Si usaste el nuevo mqtt_server.py esto ya no actualiza 'estado_actual'. Usaremos la info de "asistencias" y "alertas")
    
    // 2. Escuchar Tabla de Asistencias
    // Aumentamos el límite para poder agrupar a todos los empleados
    const asistenciasQuery = query(collection(db, "asistencias"), orderBy("timestamp", "desc"), limit(50));
    onSnapshot(asistenciasQuery, (snapshot) => {
        tablaAsistencias.innerHTML = '';
        
        if (snapshot.empty) {
            tablaAsistencias.innerHTML = '<tr><td colspan="4" class="text-center">No hay asistencias registradas</td></tr>';
            return;
        }

        // Agrupar por empleado
        const empleados = {};

        snapshot.forEach((doc) => {
            const data = doc.data();
            const uid = data.uid;
            
            if (!empleados[uid]) {
                empleados[uid] = {
                    nombre: data.nombre || 'Desconocido',
                    entrada: null,
                    salida: null,
                    estres: null
                };
            }
            
            // Como viene ordenado descendente, el primero que encontramos es el más reciente
            if (data.tipo === "entrada" && !empleados[uid].entrada) {
                empleados[uid].entrada = {
                    hora: data.timestamp ? data.timestamp.toDate().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '...',
                    bpm: data.pulso_bpm || 0
                };
            } else if (data.tipo === "salida" && !empleados[uid].salida) {
                empleados[uid].salida = {
                    hora: data.timestamp ? data.timestamp.toDate().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : '...',
                    bpm: data.pulso_bpm || 0
                };
                // Si tiene datos de estrés en la salida, los guardamos
                if (data.nivel_estres) {
                    empleados[uid].estres = {
                        nivel: data.nivel_estres,
                        diff: data.diferencia_bpm || 0
                    };
                }
            }
        });

        // Actualizar tarjetas de sensores con el documento más reciente (sin importar de quién sea)
        if (!snapshot.empty) {
            const data = snapshot.docs[0].data();
            if(data.uid) valRfid.textContent = data.uid;
            if(data.pulso_bpm) valPulso.textContent = data.pulso_bpm;
        }

        // Renderizar la tabla con los empleados agrupados
        Object.values(empleados).forEach(emp => {
            const fila = document.createElement('tr');
            
            const entradaHTML = emp.entrada 
                ? `<span class="tipo-entrada"><i class="fa-solid fa-arrow-right-to-bracket"></i> ${emp.entrada.hora} (${emp.entrada.bpm} ❤)</span>` 
                : `<span style="color: var(--text-secondary)">---</span>`;
                
            const salidaHTML = emp.salida
                ? `<span class="tipo-salida"><i class="fa-solid fa-arrow-right-from-bracket"></i> ${emp.salida.hora} (${emp.salida.bpm} ❤)</span>`
                : `<span style="color: var(--text-secondary)">---</span>`;
                
            let estresHTML = '<span style="color: var(--text-secondary)">—</span>';
            if (emp.estres) {
                const nivelClass = `estres-${emp.estres.nivel}`;
                const signo = emp.estres.diff > 0 ? '+' : '';
                estresHTML = `<span class="${nivelClass}">${emp.estres.nivel.toUpperCase()} (${signo}${emp.estres.diff} BPM)</span>`;
            }
            
            fila.innerHTML = `
                <td><strong>${emp.nombre}</strong></td>
                <td>${entradaHTML}</td>
                <td>${salidaHTML}</td>
                <td>${estresHTML}</td>
            `;
            tablaAsistencias.appendChild(fila);
        });
    }, (error) => {
        console.error("Error escuchando asistencias:", error);
    });

    // 3. Escuchar Alertas IA
    const alertsQuery = query(collection(db, 'alertas'), orderBy('timestamp', 'desc'), limit(5));
    onSnapshot(alertsQuery, (querySnapshot) => {
        alertsList.innerHTML = '';
        if (querySnapshot.empty) {
            alertsList.innerHTML = '<li class="alert-empty">No hay alertas recientes</li>';
            return;
        }

        querySnapshot.forEach((docSnap) => {
            const alert = docSnap.data();
            const date = alert.timestamp ? alert.timestamp.toDate() : new Date();
            const timeStr = date.toLocaleTimeString();

            // Usamos 'danger' para IA de fatiga
            const levelClass = alert.nivel || 'danger';

            const li = document.createElement('li');
            li.className = `alert-item ${levelClass}`;
            li.innerHTML = `
                <div class="alert-content">
                    <strong><i class="fa-solid fa-triangle-exclamation"></i> ${alert.mensaje || 'Alerta'}</strong>
                    <span>EAR: ${alert.ear_value ? alert.ear_value.toFixed(3) : 'N/A'} - ${alert.dispositivo || 'Camara'}</span>
                </div>
                <div class="alert-time">${timeStr}</div>
            `;
            alertsList.appendChild(li);
        });
    }, (error) => {
        console.error("Error escuchando alertas:", error);
    });
}

// 4. Refrescar Cámara desde Firebase (Solo cuando alguien se registra)
function iniciarCamara() {
    if (cameraInterval) clearInterval(cameraInterval);
    
    const camaraDoc = doc(db, "estado_actual", "camara");
    onSnapshot(camaraDoc, (docSnap) => {
        if (docSnap.exists()) {
            const data = docSnap.data();
            if (data.imagen_b64) {
                // Actualizar la imagen con la cadena Base64
                cameraFeed.src = "data:image/jpeg;base64," + data.imagen_b64;
                cameraOverlay.classList.add('hidden');
                
                // Formatear hora de la foto
                let horaStr = "Reciente";
                if (data.timestamp) {
                    horaStr = data.timestamp.toDate().toLocaleTimeString();
                }
                
                cameraStatus.innerHTML = `<i class="fa-solid fa-camera"></i> Último Registro: ${horaStr}`;
                cameraStatus.className = 'camera-status online';
                
                // La foto se quedará permanentemente hasta que alguien más se registre
            }
        } else {
            cameraOverlay.classList.remove('hidden');
            cameraStatus.innerHTML = 'Sin señal';
            cameraStatus.className = 'camera-status offline';
        }
    }, (error) => {
        console.error("Error escuchando camara:", error);
    });
}
