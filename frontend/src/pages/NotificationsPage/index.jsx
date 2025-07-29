import React, { useState, useEffect } from "react";
import { notificationsAPI } from "../../services/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Switch } from "../../components/ui/switch";
import { Label } from "../../components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  Bell,
  Check,
  X,
  Settings,
  Filter,
  Search,
  AlertCircle,
  Info,
  CheckCircle,
  Clock,
  Star,
  MessageSquare,
  User,
  Shield,
} from "lucide-react";
import { toast } from "sonner";

const NotificationsPage = () => {
  const [notifications, setNotifications] = useState([]);
  const [stats, setStats] = useState({});
  const [preferences, setPreferences] = useState({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    fetchNotifications();
    fetchStats();
    fetchPreferences();
  }, []);

  const fetchNotifications = async () => {
    try {
      setLoading(true);
      const response = await notificationsAPI.fetchNotifications();
      setNotifications(response.data.notifications || []);
    } catch (error) {
      console.error("Erreur lors du chargement des notifications:", error);
      toast.error("Erreur lors du chargement des notifications");
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await notificationsAPI.getStats();
      setStats(response.data.stats || {});
    } catch (error) {
      console.error("Erreur lors du chargement des statistiques:", error);
    }
  };

  const fetchPreferences = async () => {
    try {
      const response = await notificationsAPI.getPreferences();
      setPreferences(response.data.preferences || {});
    } catch (error) {
      console.error("Erreur lors du chargement des préférences:", error);
    }
  };

  const handleMarkAsRead = async (notificationId) => {
    try {
      await notificationsAPI.markAsRead(notificationId);
      setNotifications((prev) =>
        prev.map((notif) =>
          notif.id === notificationId ? { ...notif, read: true } : notif
        )
      );
      toast.success("Notification marquée comme lue");
    } catch (error) {
      console.error("Erreur lors du marquage comme lu:", error);
      toast.error("Erreur lors du marquage comme lu");
    }
  };

  const handleMarkAllAsRead = async () => {
    try {
      await notificationsAPI.markAllAsRead();
      setNotifications((prev) =>
        prev.map((notif) => ({ ...notif, read: true }))
      );
      toast.success("Toutes les notifications marquées comme lues");
    } catch (error) {
      console.error("Erreur lors du marquage de toutes comme lues:", error);
      toast.error("Erreur lors du marquage de toutes comme lues");
    }
  };

  const handleUpdatePreferences = async (newPreferences) => {
    try {
      await notificationsAPI.updatePreferences(newPreferences);
      setPreferences(newPreferences);
      toast.success("Préférences mises à jour");
    } catch (error) {
      console.error("Erreur lors de la mise à jour des préférences:", error);
      toast.error("Erreur lors de la mise à jour des préférences");
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case "info":
        return <Info className="h-4 w-4 text-blue-500" />;
      case "success":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "warning":
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case "error":
        return <X className="h-4 w-4 text-red-500" />;
      case "message":
        return <MessageSquare className="h-4 w-4 text-purple-500" />;
      case "user":
        return <User className="h-4 w-4 text-indigo-500" />;
      case "security":
        return <Shield className="h-4 w-4 text-orange-500" />;
      default:
        return <Bell className="h-4 w-4 text-gray-500" />;
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
      case "message":
        return "bg-purple-100 text-purple-800";
      case "user":
        return "bg-indigo-100 text-indigo-800";
      case "security":
        return "bg-orange-100 text-orange-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleString("fr-FR");
  };

  const filteredNotifications = notifications.filter((notification) => {
    if (filter === "all") return true;
    if (filter === "unread") return !notification.read;
    if (filter === "read") return notification.read;
    return notification.type === filter;
  });

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Notifications</h1>
        <p className="text-gray-600">Gérer vos notifications et préférences</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Statistiques */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bell className="h-5 w-5" />
                Statistiques
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Total</span>
                  <Badge variant="outline">{stats.total || 0}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Non lues</span>
                  <Badge className="bg-red-100 text-red-800">
                    {stats.unread || 0}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Lues</span>
                  <Badge className="bg-green-100 text-green-800">
                    {stats.read || 0}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Aujourd'hui</span>
                  <Badge variant="outline">{stats.today || 0}</Badge>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Préférences */}
          <Card className="mt-6">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Préférences
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label htmlFor="email-notifications">
                    Notifications email
                  </Label>
                  <Switch
                    id="email-notifications"
                    checked={preferences.email_notifications || false}
                    onCheckedChange={(checked) =>
                      handleUpdatePreferences({
                        ...preferences,
                        email_notifications: checked,
                      })
                    }
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="push-notifications">Notifications push</Label>
                  <Switch
                    id="push-notifications"
                    checked={preferences.push_notifications || false}
                    onCheckedChange={(checked) =>
                      handleUpdatePreferences({
                        ...preferences,
                        push_notifications: checked,
                      })
                    }
                  />
                </div>
                <div className="flex items-center justify-between">
                  <Label htmlFor="sms-notifications">Notifications SMS</Label>
                  <Switch
                    id="sms-notifications"
                    checked={preferences.sms_notifications || false}
                    onCheckedChange={(checked) =>
                      handleUpdatePreferences({
                        ...preferences,
                        sms_notifications: checked,
                      })
                    }
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Liste des notifications */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Bell className="h-5 w-5" />
                  Notifications
                </CardTitle>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleMarkAllAsRead}
                  >
                    <Check className="h-4 w-4 mr-2" />
                    Tout marquer comme lu
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {/* Filtres */}
              <div className="mb-4 flex gap-2">
                <Button
                  variant={filter === "all" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFilter("all")}
                >
                  Toutes
                </Button>
                <Button
                  variant={filter === "unread" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFilter("unread")}
                >
                  Non lues
                </Button>
                <Button
                  variant={filter === "read" ? "default" : "outline"}
                  size="sm"
                  onClick={() => setFilter("read")}
                >
                  Lues
                </Button>
              </div>

              {loading ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                  <p>Chargement des notifications...</p>
                </div>
              ) : filteredNotifications.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <Bell className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p>Aucune notification</p>
                  <p className="text-sm">
                    Vous n'avez aucune notification pour le moment
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {filteredNotifications.map((notification) => (
                    <div
                      key={notification.id}
                      className={`border rounded-lg p-4 ${
                        !notification.read ? "bg-blue-50" : ""
                      }`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3 flex-1">
                          <div className="mt-1">
                            {getNotificationIcon(notification.type)}
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              <h3 className="font-semibold">
                                {notification.title}
                              </h3>
                              <Badge
                                className={getNotificationColor(
                                  notification.type
                                )}
                              >
                                {notification.type}
                              </Badge>
                              {!notification.read && (
                                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                              )}
                            </div>
                            <p className="text-sm text-gray-600 mb-2">
                              {notification.message}
                            </p>
                            <p className="text-xs text-gray-500">
                              {formatDate(notification.created_at)}
                            </p>
                          </div>
                        </div>
                        <div className="flex gap-2">
                          {!notification.read && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleMarkAsRead(notification.id)}
                            >
                              <Check className="h-4 w-4" />
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default NotificationsPage;
