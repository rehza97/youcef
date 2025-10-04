import React, { useState, useEffect } from "react";
import { Bell } from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import {
  fetchNotifications as apiFetchNotifications,
  markNotificationAsRead,
  markAllNotificationsAsRead,
} from "../../services/api";
import { useNotificationsWebSocket } from "../../hooks/useNotificationsWebSocket";
import { useToast } from "../../hooks/use-toast";
import { handleApiError } from "../../lib/error-handler";

const NotificationBell = () => {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const { toast } = useToast();

  // Real-time notifications from WebSocket
  const { notifications: liveNotifications, isConnected: wsConnected } =
    useNotificationsWebSocket();

  useEffect(() => {
    fetchNotifications();
  }, []);

  // Merge live notifications with existing ones
  useEffect(() => {
    if (liveNotifications.length > 0) {
      const newNotifications = liveNotifications.filter(
        (liveNotif) =>
          !notifications.some((existing) => existing.id === liveNotif.id)
      );

      if (newNotifications.length > 0) {
        setNotifications((prev) => [...newNotifications, ...prev]);
        setUnreadCount((prev) => prev + newNotifications.length);

        // Show toast for new notifications
        newNotifications.forEach((notification) => {
          toast({
            title: notification.title,
            description: notification.message,
            variant: getNotificationVariant(notification.notification_type),
          });
        });
      }
    }
  }, [liveNotifications, notifications, toast]);

  const fetchNotifications = async () => {
    try {
      setIsLoading(true);
      const response = await apiFetchNotifications({
        limit: 20,
        unread_only: false,
      });
      setNotifications(response.data || []);
      updateUnreadCount();
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du chargement des notifications",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const updateUnreadCount = () => {
    const unread = notifications.filter((n) => !n.is_read).length;
    setUnreadCount(unread);
  };

  const markAsRead = async (notificationId) => {
    try {
      await markNotificationAsRead(notificationId);
      setNotifications((prev) =>
        prev.map((n) => (n.id === notificationId ? { ...n, is_read: true } : n))
      );
      updateUnreadCount();
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du marquage comme lu",
      });
    }
  };

  const markAllAsRead = async () => {
    try {
      await markAllNotificationsAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
      toast({
        title: "Notifications marquées comme lues",
        description: "Toutes les notifications ont été marquées comme lues",
      });
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du marquage comme lu",
      });
    }
  };

  const getNotificationVariant = (type) => {
    switch (type) {
      case "success":
        return "default";
      case "error":
        return "destructive";
      case "warning":
        return "destructive";
      case "message":
        return "default";
      case "file_share":
        return "default";
      case "conversation":
        return "default";
      default:
        return "default";
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case "success":
        return "✅";
      case "error":
        return "❌";
      case "warning":
        return "⚠️";
      case "message":
        return "💬";
      case "file_share":
        return "📁";
      case "conversation":
        return "👥";
      default:
        return "ℹ️";
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now - date) / (1000 * 60 * 60);

    if (diffInHours < 1) {
      return "À l'instant";
    } else if (diffInHours < 24) {
      return `Il y a ${Math.floor(diffInHours)}h`;
    } else {
      return date.toLocaleDateString("fr-FR");
    }
  };

  return (
    <div className="relative">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="relative"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <Badge
            variant="destructive"
            className="absolute -top-1 -right-1 h-5 w-5 rounded-full p-0 text-xs"
          >
            {unreadCount > 99 ? "99+" : unreadCount}
          </Badge>
        )}
        {wsConnected && (
          <div className="absolute -bottom-1 -right-1 h-2 w-2 bg-green-500 rounded-full"></div>
        )}
      </Button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border z-50 max-h-96 overflow-y-auto">
          <div className="p-4 border-b">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold">Notifications</h3>
              <div className="flex items-center gap-2">
                {wsConnected && (
                  <div className="flex items-center gap-1 text-xs text-green-600">
                    <div className="h-2 w-2 bg-green-500 rounded-full"></div>
                    En temps réel
                  </div>
                )}
                {unreadCount > 0 && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={markAllAsRead}
                    className="text-xs"
                  >
                    Tout marquer comme lu
                  </Button>
                )}
              </div>
            </div>
          </div>

          <div className="p-2">
            {isLoading ? (
              <div className="text-center py-4">
                <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 mx-auto"></div>
                <p className="text-sm text-gray-600 mt-2">Chargement...</p>
              </div>
            ) : notifications.length === 0 ? (
              <div className="text-center py-8">
                <Bell className="h-8 w-8 mx-auto text-gray-300 mb-2" />
                <p className="text-sm text-gray-500">Aucune notification</p>
              </div>
            ) : (
              <div className="space-y-2">
                {notifications.map((notification) => (
                  <div
                    key={notification.id}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      notification.is_read
                        ? "bg-gray-50 border-gray-200"
                        : "bg-blue-50 border-blue-200"
                    }`}
                    onClick={() => markAsRead(notification.id)}
                  >
                    <div className="flex items-start gap-3">
                      <div className="text-lg">
                        {getNotificationIcon(notification.notification_type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h4 className="font-medium text-sm">
                          {notification.title}
                        </h4>
                        <p className="text-xs text-gray-600 mt-1">
                          {notification.message}
                        </p>
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-xs text-gray-500">
                            {formatDate(notification.created_at)}
                          </span>
                          {!notification.is_read && (
                            <div className="h-2 w-2 bg-blue-500 rounded-full"></div>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
