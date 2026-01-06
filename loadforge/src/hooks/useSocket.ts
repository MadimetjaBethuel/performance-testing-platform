import { useEffect } from "react";
import socket from "~/utils/socket";

export function useSocket() {
  useEffect(() => {
    socket.on("connected", (data) => {
      console.log("Connected:", data);
    });

    socket.on("test_started", (data) => {
      console.log("Test started:", data);
    });

    socket.on("phase_complete", (data) => {
      console.log("Phase complete:", data);
    });

    socket.on("test_completed", (data) => {
      console.log("Test completed:", data);
    });

    socket.on("error", (err) => {
      console.error("Socket error:", err);
    });

    return () => {
      socket.off();
    };
  }, []);

  const startTest = (payload: any) => {
    socket.emit("start_test", payload);
  };

  return { startTest };
}
