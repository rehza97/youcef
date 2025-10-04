import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  useCallback,
} from "react";
import { useAuth } from "./AuthContext";
import { createProcessingWebSocket } from "../services/api";

const ProcessingContext = createContext(null);

export const ProcessingProvider = ({ children }) => {
  const { user, token } = useAuth();

  // All hooks must be called unconditionally before any early returns
  const wsConnectionRef = useRef(null);
  const subscribersRef = useRef(new Map());
  const lastByTaskRef = useRef(new Map());
  const [isConnected, setIsConnected] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("disconnected");

  const notifySubscribers = useCallback((taskId, message) => {
    const set = subscribersRef.current.get(taskId);
    if (set && set.size) {
      set.forEach((handler) => {
        try {
          handler(message);
        } catch {}
      });
    }
  }, []);

  const sendMessage = useCallback((payload) => {
    if (wsConnectionRef.current) {
      return wsConnectionRef.current.send(payload);
    }
    return false;
  }, []);

  const subscribeTask = useCallback(
    (taskId, handler) => {
      if (!taskId || typeof handler !== "function") return () => {};

      if (!subscribersRef.current.has(taskId)) {
        subscribersRef.current.set(taskId, new Set());
      }
      subscribersRef.current.get(taskId).add(handler);

      // send subscribe over WS
      sendMessage({ type: "subscribe_task", task_id: taskId });

      // deliver last cached message if exists
      const last = lastByTaskRef.current.get(taskId);
      if (last) {
        try {
          handler(last);
        } catch {}
      }

      // unsubscribe
      return () => {
        const set = subscribersRef.current.get(taskId);
        if (set) {
          set.delete(handler);
          if (set.size === 0) {
            subscribersRef.current.delete(taskId);
            sendMessage({ type: "unsubscribe_task", task_id: taskId });
          }
        }
      };
    },
    [sendMessage]
  );

  const connect = useCallback(() => {
    if (!user || !token) return;

    // Use centralized WebSocket service from api.js
    const wsConnection = createProcessingWebSocket(
      (message) => {
        const { type, task_id } = message;
        if (task_id) {
          lastByTaskRef.current.set(task_id, message);
          notifySubscribers(task_id, message);
        }
      },
      () => {
        console.log("✅ Processing WebSocket connected successfully");
        setIsConnected(true);
        setConnectionStatus("connected");
      },
      (event) => {
        console.log(
          `🔌 Processing WebSocket closed: ${event.code} - ${event.reason}`
        );
        setIsConnected(false);

        // Check if this is an authentication error
        if (event.code === 4001 || event.code === 4003 || event.code === 403) {
          console.error("❌ Authentication failed for Processing WebSocket");
          console.error(
            "💡 Please log out and log back in to refresh your token"
          );
          setConnectionStatus("auth_failed");
        } else {
          setConnectionStatus("disconnected");
        }
        // Auto-reconnection is now handled by the WebSocketService
      },
      (error) => {
        console.error("❌ Processing WebSocket error:", error);
        setConnectionStatus("error");
        // Auto-reconnection is now handled by the WebSocketService
      }
    );

    if (wsConnection) {
      wsConnectionRef.current = wsConnection;
    }
  }, [user, token, notifySubscribers]);

  useEffect(() => {
    connect();
    return () => {
      if (wsConnectionRef.current) {
        wsConnectionRef.current.close();
        wsConnectionRef.current = null;
      }
    };
  }, [connect]);

  const value = useMemo(
    () => ({
      isConnected: user && token ? isConnected : false,
      connectionStatus: user && token ? connectionStatus : "disconnected",
      subscribeTask,
      lastByTask: lastByTaskRef.current,
      sendMessage,
      reconnect: () => {
        if (wsConnectionRef.current) {
          wsConnectionRef.current.reconnect();
        } else if (user && token) {
          // Try to reconnect if we have auth
          connect();
        }
      },
    }),
    [
      isConnected,
      connectionStatus,
      subscribeTask,
      sendMessage,
      user,
      token,
      connect,
    ]
  );

  return (
    <ProcessingContext.Provider value={value}>
      {children}
    </ProcessingContext.Provider>
  );
};

export const useProcessing = () => {
  const context = useContext(ProcessingContext);
  if (!context) {
    console.warn("useProcessing must be used within a ProcessingProvider");
    // Return default values to prevent crashes
    return {
      isConnected: false,
      connectionStatus: "disconnected",
      subscribeTask: () => () => {},
      lastByTask: {},
      sendMessage: () => false,
      reconnect: () => {},
    };
  }
  return context;
};
