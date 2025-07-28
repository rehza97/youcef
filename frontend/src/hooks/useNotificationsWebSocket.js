import { useEffect, useRef, useState } from "react";
import { useAuth } from "../contexts/AuthContext";

export function useNotificationsWebSocket() {
  const { user } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!user) return;
    const ws = new WebSocket(
      `ws://localhost:8000/ws/notifications/${user.id}/`
    );
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setNotifications((prev) => [data, ...prev]);
      } catch (e) {
        // Ignore parse errors
      }
    };
    ws.onclose = () => {
      // Optionally: try to reconnect after a delay
    };
    return () => {
      ws.close();
    };
  }, [user]);

  return { notifications };
}
