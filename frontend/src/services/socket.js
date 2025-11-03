// src/services/socket.js
import { io } from "socket.io-client";

// Détection automatique de l'environnement
const isDevelopment = import.meta.env.MODE === 'development';
const API_BASE = (import.meta.env.VITE_API_URL?.replace("/api", "")) || 
  (isDevelopment ? 'http://localhost:5000' : 'https://sertecingenierie.onrender.com');

console.log('🔌 Socket.IO URL:', API_BASE);
console.log('🔧 Mode:', import.meta.env.MODE);

let socket = null;

/**
 * Connexion au serveur Socket.IO
 */
export function connectSocket(token) {
  if (socket?.connected) {
    console.log("✅ Socket déjà connecté");
    return socket;
  }

  // Déconnexion propre si socket existe déjà
  if (socket) {
    socket.disconnect();
    socket = null;
  }

  console.log(`🔌 Connexion à Socket.IO: ${API_BASE}`);

  socket = io(API_BASE, {
    transports: ["polling", "websocket"],
    auth: token ? { token } : undefined,
    reconnection: true,
    reconnectionAttempts: 5,
    reconnectionDelay: 1000,
    timeout: 10000,
    autoConnect: true,
  });

  // Événements de base
  socket.on("connect", () => {
    console.log("✅ Socket connecté:", socket.id);
    console.log("   Transport:", socket.io.engine.transport.name);
  });

  socket.on("connect_error", (error) => {
    console.error("❌ Erreur de connexion Socket:", error.message);
  });

  socket.on("disconnect", (reason) => {
    console.warn("🔌 Socket déconnecté:", reason);
  });

  socket.on("reconnect", (attemptNumber) => {
    console.log(`✅ Reconnecté après ${attemptNumber} tentative(s)`);
  });

  // Événement upgrade vers websocket
  socket.io.engine.on("upgrade", (transport) => {
    console.log("⬆️ Upgrade vers:", transport.name);
  });

  // Événements applicatifs
  socket.on("new_data", (data) => {
    console.log("📊 Nouvelles données reçues:", data);
  });

  socket.on("device_status", (data) => {
    console.log("📱 Changement de statut appareil:", data);
  });

  socket.on("alert", (data) => {
    console.log("🚨 Alerte reçue:", data);
  });

  return socket;
}

/**
 * Obtenir l'instance du socket
 */
export function getSocket() {
  return socket;
}

/**
 * Déconnexion
 */
export function disconnectSocket() {
  if (socket) {
    console.log("🔌 Déconnexion du socket");
    socket.disconnect();
    socket = null;
  }
}

/**
 * Vérifier si connecté
 */
export function isSocketConnected() {
  return socket?.connected || false;
}

/**
 * Rejoindre la room d'un appareil
 */
export function joinDevice(deviceId) {
  if (socket?.connected) {
    console.log(`📱 Rejoindre la room de l'appareil: ${deviceId}`);
    socket.emit('join_device', { device_id: deviceId });
  }
}

/**
 * S'abonner à tous les appareils
 */
export function subscribeAllDevices() {
  if (socket?.connected) {
    console.log('📡 Abonnement à tous les appareils');
    socket.emit('subscribe_all_devices');
  }
}

export { socket };