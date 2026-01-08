import { time } from "console";
import { io, Socket } from "socket.io-client";

let socket: Socket | null = null;
let isInitializing = false;
let isBound = false;
export function getSocket(): Socket {
  if (socket && socket.connected) {
    return socket;
  }
  if (isInitializing) {
    console.warn("⚠️ [SOCKET.IO] Already initializing, waiting...");
    // Return the socket even if not connected yet
    setTimeout(() => {}, 2000); // simple delay
    return socket!;
  }
  if (!socket) {
    isInitializing = true;
    socket = io("http://localhost:5001", {
      transports: ["websocket"],
      autoConnect: true,
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5,
    });
  }

  socket.on("connect", () => {
    console.log("Socket connected:", socket?.id);
    isInitializing = false;
  });
  socket.on("disconnect", (reason) => {
    console.log("Socket disconnected:", reason);
  });
  socket.on("error", (error) => {
    console.error("Socket error:", error);
  });
  return socket;
}

export function isSocketReady(): boolean {
  return socket !== null && socket !== undefined && socket.connected;
}
