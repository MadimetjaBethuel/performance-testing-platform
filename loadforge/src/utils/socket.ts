// utils/socket.ts
import { io, Socket } from "socket.io-client";

const socket: Socket = io("http://localhost:5001", {
  transports: ["websocket"],
  autoConnect: true,
});

export default socket;
