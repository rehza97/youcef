import { useEffect, useRef, useState, useCallback } from "react";
import { useAuth } from "../contexts/AuthContext";

export function useChatWebSocket(conversationId) {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!user || !conversationId) return;
    const ws = new WebSocket(`ws://localhost:8000/ws/chat/${conversationId}/`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setMessages((prev) => [...prev, data]);
      } catch (e) {}
    };
    ws.onclose = () => {};
    return () => {
      ws.close();
    };
  }, [user, conversationId]);

  const sendMessage = useCallback((content) => {
    if (wsRef.current && wsRef.current.readyState === 1) {
      wsRef.current.send(JSON.stringify({ content }));
    }
  }, []);

  return { messages, sendMessage };
}
