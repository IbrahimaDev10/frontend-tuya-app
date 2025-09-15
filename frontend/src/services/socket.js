// src/services/socket.js
import { io } from "socket.io-client";

const API_BASE = (import.meta.env.VITE_API_URL?.replace("/api", "")) || "http://localhost:5000";

let socket = null;

export function connectSocket(token) {
  if (!socket) {
    socket = io(API_BASE, {
      transports: ["websocket"],
      auth: token ? { token } : undefined,
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000
    });
  }
  return socket;
}

export function getSocket() {
  return socket;
}

export function disconnectSocket() {
  if (socket) {
    socket.disconnect();
    socket = null;
  }
}