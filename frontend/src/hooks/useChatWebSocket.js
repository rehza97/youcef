import { useState, useEffect, useRef } from "react";
import { useAuth } from "../contexts/AuthContext";

export const useChatWebSocket = (conversationId) => {
  const { user, token } = useAuth();
  const [messages, setMessages] = useState([]);
  const [liveMessages, setLiveMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef(null);

  useEffect(() => {
    if (!conversationId || !user || !token) return;

    // Updated URL format with query parameters
    const wsUrl = `ws://localhost:8000/ws/chat/?conversation_id=${conversationId}&token=${token}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log("Chat WebSocket connected");
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "message") {
        setLiveMessages((prev) => [...prev, data]);
      }
    };

    ws.onclose = () => {
      console.log("Chat WebSocket disconnected");
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error("Chat WebSocket error:", error);
      setIsConnected(false);
    };

    return () => {
      ws.close();
    };
  }, [conversationId, user, token]);

  const sendMessage = (content) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "message",
          content: content,
          conversation_id: conversationId,
        })
      );
    }
  };

  return {
    messages: [...messages, ...liveMessages],
    liveMessages,
    isConnected,
    sendMessage,
  };
};
