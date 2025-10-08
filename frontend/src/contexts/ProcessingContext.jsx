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

  // Global processing state
  const [activeTasks, setActiveTasks] = useState(new Map());
  const [globalProcessingCount, setGlobalProcessingCount] = useState(0);

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
      try {
        const result = wsConnectionRef.current.send(payload);
        console.log("📤 Message sent via WebSocket:", payload);
        return result;
      } catch (error) {
        console.error("❌ Error sending WebSocket message:", error);
        return false;
      }
    }
    console.warn("⚠️ No WebSocket connection available for sending message");
    return false;
  }, []);

  const subscribeTask = useCallback(
    (taskId, handler) => {
      if (!taskId || typeof handler !== "function") {
        console.warn("⚠️ Invalid taskId or handler for subscribeTask");
        return () => {};
      }

      console.log(`🔔 Subscribing to task: ${taskId}`);

      if (!subscribersRef.current.has(taskId)) {
        subscribersRef.current.set(taskId, new Set());
      }
      subscribersRef.current.get(taskId).add(handler);

      // send subscribe over WS
      const subscribeMessage = { type: "subscribe_task", task_id: taskId };
      console.log("📤 Sending subscription message:", subscribeMessage);
      const sent = sendMessage(subscribeMessage);

      if (!sent) {
        console.warn(
          "⚠️ Failed to send subscription message - WebSocket not connected"
        );
      }

      // deliver last cached message if exists
      const last = lastByTaskRef.current.get(taskId);
      if (last) {
        try {
          console.log(`📨 Delivering cached message for task ${taskId}:`, last);
          handler(last);
        } catch (e) {
          console.error("Error delivering cached message:", e);
        }
      }

      // unsubscribe
      return () => {
        console.log(`🔕 Unsubscribing from task: ${taskId}`);
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
    if (!user || !token) {
      console.log("⚠️ No user or token available for Processing WebSocket");
      return;
    }

    console.log("🔄 Connecting to Processing WebSocket...");

    // Use centralized WebSocket service from api.js
    const wsConnection = createProcessingWebSocket(
      (message) => {
        console.log("📨 Processing WebSocket message received:", message);
        const { type, task_id, data } = message;
        if (task_id) {
          lastByTaskRef.current.set(task_id, message);
          notifySubscribers(task_id, message);

          // Update global active tasks tracking
          setActiveTasks((prev) => {
            const newTasks = new Map(prev);
            if (
              data?.status === "completed" ||
              data?.status === "failed" ||
              data?.status === "cancelled"
            ) {
              // Remove completed/failed tasks
              newTasks.delete(task_id);
            } else if (
              data?.status === "processing" ||
              data?.status === "started"
            ) {
              // Add/update active tasks
              newTasks.set(task_id, {
                task_id,
                status: data.status,
                progress: data.progress || 0,
                message: data.message || "",
                file_id: data.file_id,
                filename: data.filename || "Unknown file",
                timestamp: Date.now(),
              });
            }
            return newTasks;
          });
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
      console.log("🔗 Processing WebSocket connection established");
    } else {
      console.error("❌ Failed to create Processing WebSocket connection");
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
        console.log("🔄 Manual reconnection requested");
        if (wsConnectionRef.current) {
          wsConnectionRef.current.reconnect();
        } else if (user && token) {
          // Try to reconnect if we have auth
          connect();
        }
      },
      getConnectionInfo: () => ({
        isConnected: user && token ? isConnected : false,
        connectionStatus: user && token ? connectionStatus : "disconnected",
        hasUser: !!user,
        hasToken: !!token,
        activeSubscriptions: Array.from(subscribersRef.current.keys()),
      }),
      // Global processing state
      activeTasks: Array.from(activeTasks.values()),
      globalProcessingCount: activeTasks.size,
      getActiveTask: (taskId) => activeTasks.get(taskId),
      hasActiveProcessing: activeTasks.size > 0,
    }),
    [
      isConnected,
      connectionStatus,
      subscribeTask,
      sendMessage,
      user,
      token,
      connect,
      activeTasks,
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
