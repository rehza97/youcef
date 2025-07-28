import React, { useState, useEffect } from "react";
import { notificationsAPI } from "../services/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { useAuth } from "../contexts/AuthContext";

const NotificationsPage = () => {
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState({});
  const [preferences, setPreferences] = useState({});
  const [loading, setLoading] = useState(true);
  const [showUnreadOnly, setShowUnreadOnly] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);
  const { user: currentUser } = useAuth();

  useEffect(() => {
    fetchNotifications();
    fetchStats();
    fetchPreferences();
  }, [showUnreadOnly]);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const response = await notificationsAPI.fetchNotifications({
        unread_only: showUnreadOnly,
      });
      setNotifications(response.data);
    } catch (error) {
      console.error("Erreur lors du chargement des notifications:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await notificationsAPI.getStats();
      setStats(response.data);
    } catch (error) {
      console.error("Erreur lors du chargement des statistiques:", error);
    }
  };

  const fetchPreferences = async () => {
    try {
      const response = await notificationsAPI.getPreferences();
      setPreferences(response.data);
    } catch (error) {
      console.error("Erreur lors du chargement des préférences:", error);
    }
  };

  const handleMarkAsRead = async (notificationId) => {
    try {
      await notificationsAPI.markAsRead(notificationId);
      fetchNotifications();
      fetchStats();
    } catch (error) {
      console.error("Erreur lors du marquage comme lu:", error);
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await notificationsAPI.markAllAsRead();
      fetchNotifications();
      fetchStats();
    } catch (error) {
      console.error("Erreur lors du marquage de tous comme lu:", error);
    }
  };

  const handleUpdatePreferences = async (newPreferences) => {
    try {
      await notificationsAPI.updatePreferences(newPreferences);
      setShowPreferences(false);
      fetchPreferences();
    } catch (error) {
      console.error("Erreur lors de la mise à jour des préférences:", error);
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case "info":
        return "ℹ️";
      case "success":
        return "✅";
      case "warning":
        return "⚠️";
      case "error":
        return "❌";
      default:
        return "📢";
    }
  };

  const getNotificationColor = (type) => {
    switch (type) {
      case "info":
        return "bg-blue-100 text-blue-800";
      case "success":
        return "bg-green-100 text-green-800";
      case "warning":
        return "bg-yellow-100 text-yellow-800";
      case "error":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Notifications</h1>
        <p className="text-gray-600">Voir et gérer vos notifications</p>
      </div>

      {/* Statistiques */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-blue-600">
              {stats.total_notifications || 0}
            </div>
            <div className="text-sm text-gray-600">Total des notifications</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-red-600">
              {stats.unread_notifications || 0}
            </div>
            <div className="text-sm text-gray-600">Non lues</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-green-600">
              {stats.read_notifications || 0}
            </div>
            <div className="text-sm text-gray-600">Lues</div>
          </CardContent>
        </Card>
      </div>

      {/* Contrôles */}
      <div className="flex gap-4 mb-6">
        <Button
          variant={showUnreadOnly ? "default" : "outline"}
          onClick={() => setShowUnreadOnly(!showUnreadOnly)}
        >
          {showUnreadOnly ? "Toutes les notifications" : "Non lues seulement"}
        </Button>
        <Button variant="outline" onClick={handleMarkAllAsRead}>
          Marquer tout comme lu
        </Button>
        <Button variant="outline" onClick={() => setShowPreferences(true)}>
          Préférences
        </Button>
      </div>

      {/* Liste des notifications */}
      <div className="space-y-4">
        {loading ? (
          <Card>
            <CardContent className="p-6">
              <div className="text-center">Chargement des notifications...</div>
            </CardContent>
          </Card>
        ) : notifications.length === 0 ? (
          <Card>
            <CardContent className="p-6">
              <div className="text-center text-gray-500">
                {showUnreadOnly
                  ? "Aucune notification non lue"
                  : "Aucune notification"}
              </div>
            </CardContent>
          </Card>
        ) : (
          notifications.map((notification) => (
            <Card
              key={notification.id}
              className={`${
                !notification.is_read ? "border-blue-200 bg-blue-50" : ""
              }`}
            >
              <CardContent className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3 flex-1">
                    <div className="text-2xl">
                      {getNotificationIcon(notification.notification_type)}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold">{notification.title}</h3>
                        <Badge
                          className={getNotificationColor(
                            notification.notification_type
                          )}
                        >
                          {notification.notification_type}
                        </Badge>
                        {!notification.is_read && (
                          <Badge variant="default">Nouveau</Badge>
                        )}
                      </div>
                      <p className="text-gray-600 mb-2">
                        {notification.message}
                      </p>
                      <div className="text-sm text-gray-500">
                        {new Date(notification.created_at).toLocaleString(
                          "fr-FR"
                        )}
                      </div>
                    </div>
                  </div>
                  {!notification.is_read && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleMarkAsRead(notification.id)}
                    >
                      Marquer comme lu
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Modal des préférences */}
      {showPreferences && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">
              Préférences de notifications
            </h2>

            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">
                  Notifications par email
                </label>
                <input
                  type="checkbox"
                  checked={preferences.email_notifications || false}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      email_notifications: e.target.checked,
                    })
                  }
                  className="rounded"
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">
                  Notifications push
                </label>
                <input
                  type="checkbox"
                  checked={preferences.push_notifications || false}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      push_notifications: e.target.checked,
                    })
                  }
                  className="rounded"
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">
                  Notifications de messagerie
                </label>
                <input
                  type="checkbox"
                  checked={preferences.messaging_notifications || false}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      messaging_notifications: e.target.checked,
                    })
                  }
                  className="rounded"
                />
              </div>

              <div className="flex items-center justify-between">
                <label className="text-sm font-medium">
                  Notifications système
                </label>
                <input
                  type="checkbox"
                  checked={preferences.system_notifications || false}
                  onChange={(e) =>
                    setPreferences({
                      ...preferences,
                      system_notifications: e.target.checked,
                    })
                  }
                  className="rounded"
                />
              </div>
            </div>

            <Separator className="my-4" />

            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => setShowPreferences(false)}
              >
                Annuler
              </Button>
              <Button onClick={() => handleUpdatePreferences(preferences)}>
                Sauvegarder
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationsPage;
