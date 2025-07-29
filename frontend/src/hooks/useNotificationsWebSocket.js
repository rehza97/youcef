import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../contexts/AuthContext";
import { debug } from "../lib/debug.js";

export const useNotificationsWebSocket = () => {
  const { user, token } = useAuth();
  const [notifications, setNotifications] = useState([]);
  const [liveNotifications, setLiveNotifications] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(() => {
    if (!user || !token) {
      debug.warn("useNotificationsWebSocket: User or token not available");
      return;
    }

    debug.websocket("useNotificationsWebSocket: Attempting to connect", {
      userId: user.id,
    });

    try {
      // Updated URL format with query parameters
      const wsUrl = `ws://localhost:8000/ws/notifications/?user_id=${user.id}&token=${token}`;
      console.log("🔍 DEBUG: WebSocket URL being used:", wsUrl);
      debug.websocket("useNotificationsWebSocket: Connecting to", wsUrl);

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        debug.websocket("useNotificationsWebSocket: Connection opened");
        setIsConnected(true);
        setConnectionStatus("connected");
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          debug.websocket("useNotificationsWebSocket: Message received", data);

          if (data.type === "connection") {
            debug.websocket(
              "useNotificationsWebSocket: Connection confirmed",
              data
            );
          } else if (data.type === "notification") {
            debug.websocket(
              "useNotificationsWebSocket: New notification",
              data
            );
            setLiveNotifications((prev) => [data, ...prev]);
          }
        } catch (error) {
          debug.error(
            "useNotificationsWebSocket: Error parsing message",
            error
          );
        }
      };

      ws.onclose = (event) => {
        debug.websocket("useNotificationsWebSocket: Connection closed", {
          code: event.code,
          reason: event.reason,
        });
        setIsConnected(false);
        setConnectionStatus("disconnected");
        wsRef.current = null;

        // Attempt to reconnect if not a clean close
        if (
          event.code !== 1000 &&
          reconnectAttempts.current < maxReconnectAttempts
        ) {
          const delay = Math.pow(2, reconnectAttempts.current) * 1000; // Exponential backoff
          debug.websocket(
            `useNotificationsWebSocket: Reconnecting in ${delay}ms (attempt ${
              reconnectAttempts.current + 1
            })`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        } else {
          debug.warn(
            "useNotificationsWebSocket: Max reconnection attempts reached or clean close"
          );
          setConnectionStatus("failed");
        }
      };

      ws.onerror = (error) => {
        debug.error("useNotificationsWebSocket: WebSocket error", error);
        setConnectionStatus("error");
      };
    } catch (error) {
      debug.error("useNotificationsWebSocket: Connection error", error);
      setConnectionStatus("error");
    }
  }, [user, token]);

  const disconnect = useCallback(() => {
    debug.websocket("useNotificationsWebSocket: Disconnecting");
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close(1000, "User disconnected");
      wsRef.current = null;
    }
    setIsConnected(false);
    setConnectionStatus("disconnected");
  }, []);

  const reconnect = useCallback(() => {
    debug.websocket("useNotificationsWebSocket: Manual reconnect");
    disconnect();
    reconnectAttempts.current = 0;
    setTimeout(connect, 1000);
  }, [disconnect, connect]);

  useEffect(() => {
    debug.websocket("useNotificationsWebSocket: Effect triggered", {
      user: !!user,
      token: !!token,
    });

    if (user && token) {
      connect();
    }

    return () => {
      debug.websocket("useNotificationsWebSocket: Cleanup");
      disconnect();
    };
  }, [user, token, connect, disconnect]);

  return {
    notifications: liveNotifications,
    isConnected,
    connectionStatus,
    reconnect,
  };
};
