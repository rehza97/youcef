import { useState, useEffect, useRef } from "react";
import { useAuth } from "../contexts/AuthContext";
import { createChatWebSocket } from "../services/api";

export const useChatWebSocket = (conversationId) => {
  const { user, token } = useAuth();
  const [liveMessages, setLiveMessages] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const wsConnectionRef = useRef(null);

  useEffect(() => {
    if (!conversationId || !user || !token) return;

    // Use centralized WebSocket service from api.js
    const wsConnection = createChatWebSocket(
      conversationId,
      (data) => {
        if (data.type === "message") {
          setLiveMessages((prev) => [...prev, data]);
        }
      },
      () => {
        console.log("Chat WebSocket connected");
        setIsConnected(true);
      },
      () => {
        console.log("Chat WebSocket disconnected");
        setIsConnected(false);
      },
      (error) => {
        console.error("Chat WebSocket error:", error);
        setIsConnected(false);
      }
    );

    if (wsConnection) {
      wsConnectionRef.current = wsConnection;
    }

    return () => {
      if (wsConnectionRef.current) {
        wsConnectionRef.current.close();
        wsConnectionRef.current = null;
      }
    };
  }, [conversationId, user, token]);

  const sendMessage = (content) => {
    if (wsConnectionRef.current) {
      wsConnectionRef.current.send({
        type: "message",
        content: content,
        conversation_id: conversationId,
      });
    }
  };

  return {
    messages: liveMessages,
    liveMessages,
    isConnected,
    sendMessage,
  };
};
