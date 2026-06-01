/*
OBJETIVO: Gestión de Firebase y Dashboard de usuario.
INTEGRANTES: CASTRO LUNA CESAR ARMANDO, EPINOZA BRAVO LUDWING, LOZANO CARDONA ANGEL JOSUE
PROYECTO: Sistema de registro de Asistencias y Desgaste Laboral
*/

import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-app.js";
import { getFirestore, collection, doc, onSnapshot, query, orderBy, limit, addDoc, serverTimestamp } from "https://www.gstatic.com/firebasejs/10.8.1/firebase-firestore.js";

// TODO: Reemplaza esta configuración con la de tu proyecto de Firebase
const firebaseConfig = {
    apiKey: "AIzaSy_PLACEHOLDER_API_KEY",
    authDomain: "tu-proyecto.firebaseapp.com",
    projectId: "tu-proyecto",
    storageBucket: "tu-proyecto.appspot.com",
    messagingSenderId: "1234567890",
    appId: "1:1234567890:web:abcdef123456"
};

// Elementos del DOM
const statusDot = document.getElementById('system-status-dot');
const statusText = document.getElementById('system-status-text');
const valRfid = document.getElementById('val-rfid');
const valDistancia = document.getElementById('val-distancia');
const valPulso = document.getElementById('val-pulso');
const alertsList = document.getElementById('alerts-list');
const btnAbrirPuerta = document.getElementById('btn-abrir-puerta');
const btnActivarBuzzer = document.getElementById('btn-activar-buzzer');

let db;

try {
    const app = initializeApp(firebaseConfig);
    db = getFirestore(app);
    setOnlineStatus(true);
    initListeners();
} catch (error) {
    console.error("Error inicializando Firebase:", error);
    setOnlineStatus(false);
    alertsList.innerHTML = `<li class="alert-empty" style="color: var(--accent-red)">Error de conexión: Revisa tus credenciales de Firebase en app.js</li>`;
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
    // 1. Escuchar última telemetría
    const sensorDocRef = doc(db, 'estado_actual', 'sensores');
    onSnapshot(sensorDocRef, (docSnap) => {
        if (docSnap.exists()) {
            const data = docSnap.data();
            if (data.payload) {
                valRfid.textContent = data.payload.rfid_uid || '---';
                valDistancia.textContent = data.payload.distancia_cm || '0';
                if (data.payload.pulso_hrv) {
                    valPulso.textContent = data.payload.pulso_hrv.pulso_bpm || '0';
                }
            }
        }
    }, (error) => {
        console.error("Error escuchando sensores:", error);
    });

    // 2. Escuchar últimas 5 alertas
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
            
            const li = document.createElement('li');
            li.className = `alert-item ${alert.nivel || 'info'}`;
            li.innerHTML = `
                <div class="alert-content">
                    <strong>${alert.mensaje || 'Alerta'}</strong>
                    <span>RFID: ${alert.rfid_uid || 'N/A'}</span>
                </div>
                <div class="alert-time">${timeStr}</div>
            `;
            alertsList.appendChild(li);
        });
    }, (error) => {
        console.error("Error escuchando alertas:", error);
    });
}

// 3. Enviar comandos remotos
async function sendCommand(actuador, accion) {
    if (!db) return alert("Firebase no está conectado.");
    
    try {
        await addDoc(collection(db, 'comandos_remotos'), {
            actuador: actuador,
            accion: accion,
            procesado: false,
            timestamp: serverTimestamp()
        });
        console.log(`Comando enviado: ${actuador} -> ${accion}`);
    } catch (error) {
        console.error("Error enviando comando:", error);
        alert("Error al enviar el comando.");
    }
}

btnAbrirPuerta.addEventListener('click', () => {
    btnAbrirPuerta.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Abriendo...';
    btnAbrirPuerta.disabled = true;
    
    sendCommand('solenoide', 'abrir').finally(() => {
        setTimeout(() => {
            btnAbrirPuerta.innerHTML = '<i class="fa-solid fa-door-open"></i> Abrir';
            btnAbrirPuerta.disabled = false;
        }, 1000);
    });
});

btnActivarBuzzer.addEventListener('click', () => {
    btnActivarBuzzer.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Activando...';
    btnActivarBuzzer.disabled = true;
    
    sendCommand('buzzer', 'ok').finally(() => {
        setTimeout(() => {
            btnActivarBuzzer.innerHTML = '<i class="fa-solid fa-bell"></i> Activar';
            btnActivarBuzzer.disabled = false;
        }, 1000);
    });
});
