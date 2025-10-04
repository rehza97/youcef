import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "../contexts/AuthContext";
import { debug } from "../lib/debug.js";
import { createNotificationsWebSocket } from "../services/api";

export const useNotificationsWebSocket = () => {
  const { user, token } = useAuth();
  const [liveNotifications, setLiveNotifications] = useState([]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const wsConnectionRef = useRef(null);

  const connect = useCallback(() => {
    if (!user || !token) {
      debug.warn("useNotificationsWebSocket: User or token not available");
      return;
    }

    debug.websocket("useNotificationsWebSocket: Attempting to connect", {
      userId: user.id,
    });

    try {
      // Use centralized WebSocket service from api.js
      const wsConnection = createNotificationsWebSocket(
        (data) => {
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
        },
        () => {
          debug.websocket("useNotificationsWebSocket: Connection opened");
          setIsConnected(true);
          setConnectionStatus("connected");
        },
        (event) => {
          debug.websocket("useNotificationsWebSocket: Connection closed", {
            code: event.code,
            reason: event.reason,
          });
          setIsConnected(false);
          setConnectionStatus("disconnected");
        },
        (error) => {
          debug.error("useNotificationsWebSocket: WebSocket error", error);
          setConnectionStatus("error");
        }
      );

      if (wsConnection) {
        wsConnectionRef.current = wsConnection;
      }
    } catch (error) {
      debug.error("useNotificationsWebSocket: Connection error", error);
      setConnectionStatus("error");
    }
  }, [user, token]);

  const disconnect = useCallback(() => {
    debug.websocket("useNotificationsWebSocket: Disconnecting");
    if (wsConnectionRef.current) {
      wsConnectionRef.current.close();
      wsConnectionRef.current = null;
    }
    setIsConnected(false);
    setConnectionStatus("disconnected");
  }, []);

  const reconnect = useCallback(() => {
    debug.websocket("useNotificationsWebSocket: Manual reconnect");
    disconnect();
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
