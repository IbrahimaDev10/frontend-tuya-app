// src/store/realtimeContext.jsx
import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { connectSocket, disconnectSocket } from "../services/socket";

const RealtimeContext = createContext(null);

export function RealtimeProvider({ children }) {
  const [latestByDevice, setLatestByDevice] = useState(new Map());

  useEffect(() => {
    const token = localStorage.getItem("token");
    const s = connectSocket(token);

    const onNewData = (payload) => {
      if (payload?.device_id) {
        setLatestByDevice(prev => {
          const next = new Map(prev);
          next.set(payload.device_id, payload);
          return next;
        });
      }
    };

    s.on("connect", () => console.log("[socket] connected"));
    s.on("disconnect", () => console.log("[socket] disconnected"));
    s.on("new_data", onNewData);

    return () => {
      try { s.off("new_data", onNewData); } catch {}
      disconnectSocket();
    };
  }, []);

  const value = useMemo(() => ({
    getLatestFor: (deviceId) => latestByDevice.get(deviceId) || null,
    latestByDevice
  }), [latestByDevice]);

  return (
    <RealtimeContext.Provider value={value}>
      {children}
    </RealtimeContext.Provider>
  );
}

export function useDeviceRealtime(deviceId) {
  const ctx = useContext(RealtimeContext);
  if (!ctx) throw new Error("useDeviceRealtime must be used within RealtimeProvider");
  return ctx.getLatestFor(deviceId);
}