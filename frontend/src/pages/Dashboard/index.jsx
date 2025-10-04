import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { useAuth } from "../../contexts/AuthContext";
import {
  getUsers,
  fetchNotifications,
  getNotificationStats,
  fetchConversations,
  healthCheck,
  detailedHealthCheck,
} from "../../services/api";
import { handleApiError } from "../../lib/error-handler";
import { toast } from "sonner";
import {
  Activity,
  Users,
  Bell,
  MessageSquare,
  Shield,
  Settings,
  FileText,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Clock,
  RefreshCw,
} from "lucide-react";

const Dashboard = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalUsers: 0,
    totalNotifications: 0,
    unreadNotifications: 0,
    totalConversations: 0,
    systemStatus: "unknown",
  });
  const [recentActivity, setRecentActivity] = useState([]);
  const [systemHealth, setSystemHealth] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);

      // Fetch data in parallel
      const [
        usersResponse,
        notificationsResponse,
        conversationsResponse,
        healthResponse,
      ] = await Promise.allSettled([
        getUsers(),
        getNotificationStats(),
        fetchConversations(),
        detailedHealthCheck(),
      ]);

      // Process users data
      let totalUsers = 0;
      if (usersResponse.status === "fulfilled") {
        totalUsers = usersResponse.value.data?.length || 0;
      }

      // Process notifications data
      let totalNotifications = 0;
      let unreadNotifications = 0;
      if (notificationsResponse.status === "fulfilled") {
        const stats = notificationsResponse.value.data?.stats || {};
        totalNotifications = stats.total_notifications || 0;
        unreadNotifications = stats.unread_notifications || 0;
      }

      // Process conversations data
      let totalConversations = 0;
      if (conversationsResponse.status === "fulfilled") {
        totalConversations =
          conversationsResponse.value.data?.conversations?.length || 0;
      }

      // Process system health
      let systemStatus = "unknown";
      if (healthResponse.status === "fulfilled") {
        const health = healthResponse.value.data;
        systemStatus = health?.status === "healthy" ? "good" : "warning";
        setSystemHealth(health);
      }

      setStats({
        totalUsers,
        totalNotifications,
        unreadNotifications,
        totalConversations,
        systemStatus,
      });

      // Generate recent activity based on fetched data
      generateRecentActivity();
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage:
          "Erreur lors du chargement des données du tableau de bord",
      });
    } finally {
      setLoading(false);
    }
  };

  const generateRecentActivity = () => {
    const activities = [];

    if (stats.totalUsers > 0) {
      activities.push({
        id: 1,
        type: "success",
        title: `${stats.totalUsers} utilisateurs actifs`,
        description: "Utilisateurs connectés au système",
        time: "À l'instant",
        icon: Users,
      });
    }

    if (stats.unreadNotifications > 0) {
      activities.push({
        id: 2,
        type: "info",
        title: `${stats.unreadNotifications} notifications non lues`,
        description: "Nouvelles notifications disponibles",
        time: "Il y a 2 minutes",
        icon: Bell,
      });
    }

    if (stats.totalConversations > 0) {
      activities.push({
        id: 3,
        type: "info",
        title: `${stats.totalConversations} conversations actives`,
        description: "Conversations en cours",
        time: "Il y a 5 minutes",
        icon: MessageSquare,
      });
    }

    if (systemHealth?.status === "healthy") {
      activities.push({
        id: 4,
        type: "success",
        title: "Système opérationnel",
        description: "Tous les services fonctionnent correctement",
        time: "Il y a 10 minutes",
        icon: CheckCircle,
      });
    }

    setRecentActivity(activities);
  };

  const handleQuickAction = (href) => {
    navigate(href);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "good":
        return "text-green-600 bg-green-100";
      case "warning":
        return "text-yellow-600 bg-yellow-100";
      case "error":
        return "text-red-600 bg-red-100";
      default:
        return "text-gray-600 bg-gray-100";
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case "good":
        return "Bon";
      case "warning":
        return "Attention";
      case "error":
        return "Problème";
      default:
        return "Inconnu";
    }
  };

  const getActivityIcon = (type) => {
    switch (type) {
      case "success":
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "info":
        return <Activity className="h-4 w-4 text-blue-500" />;
      case "warning":
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case "error":
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const dashboardStats = [
    {
      title: "Total Utilisateurs",
      value: stats.totalUsers.toLocaleString(),
      icon: Users,
      description: "Utilisateurs actifs dans le système",
      color: "text-blue-600",
    },
    {
      title: "Notifications",
      value: stats.unreadNotifications,
      icon: Bell,
      description: "Notifications non lues",
      color: "text-orange-600",
      badge:
        stats.totalNotifications > stats.unreadNotifications
          ? `${stats.totalNotifications} total`
          : null,
    },
    {
      title: "Conversations",
      value: stats.totalConversations,
      icon: MessageSquare,
      description: "Conversations actives",
      color: "text-green-600",
    },
    {
      title: "État du Système",
      value: getStatusText(stats.systemStatus),
      icon: Activity,
      description: "Statut des services",
      color: getStatusColor(stats.systemStatus),
    },
  ];

  const quickActions = [
    {
      title: "Gérer les Utilisateurs",
      description: "Voir et gérer les comptes utilisateurs",
      icon: Users,
      href: "/users",
      color: "text-blue-600",
    },
    {
      title: "Gestion des Rôles",
      description: "Configurer les rôles et permissions",
      icon: Shield,
      href: "/roles",
      color: "text-purple-600",
    },
    {
      title: "Notifications",
      description: "Gérer les notifications et préférences",
      icon: Bell,
      href: "/notifications",
      color: "text-orange-600",
    },
    {
      title: "Messagerie",
      description: "Accéder aux conversations",
      icon: MessageSquare,
      href: "/messaging",
      color: "text-green-600",
    },
    {
      title: "Fichiers",
      description: "Gérer les fichiers uploadés",
      icon: FileText,
      href: "/files",
      color: "text-indigo-600",
    },
    {
      title: "Encaissement",
      description: "Module de traitement financier",
      icon: TrendingUp,
      href: "/encaissement",
      color: "text-emerald-600",
    },
  ];

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center space-y-4">
            <RefreshCw className="h-8 w-8 animate-spin text-blue-600" />
            <p className="text-gray-600">Chargement du tableau de bord...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Bon retour, {user?.username || "Utilisateur"} !
          </h1>
          <p className="text-gray-600 mt-2">
            Voici ce qui se passe avec votre application aujourd'hui.
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchDashboardData}
          className="flex items-center space-x-2"
        >
          <RefreshCw className="h-4 w-4" />
          Actualiser
        </Button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {dashboardStats.map((stat, index) => (
          <Card key={index} className="hover:shadow-md transition-shadow">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.title}
              </CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="flex items-center space-x-2">
                <div className="text-2xl font-bold">{stat.value}</div>
                {stat.badge && (
                  <Badge variant="secondary" className="text-xs">
                    {stat.badge}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {stat.description}
              </p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Actions Rapides
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {quickActions.map((action, index) => (
            <Card
              key={index}
              className="hover:shadow-lg transition-shadow cursor-pointer"
              onClick={() => handleQuickAction(action.href)}
            >
              <CardHeader>
                <div className="flex items-center space-x-2">
                  <action.icon className={`h-5 w-5 ${action.color}`} />
                  <CardTitle className="text-lg">{action.title}</CardTitle>
                </div>
                <CardDescription>{action.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleQuickAction(action.href);
                  }}
                >
                  Ouvrir {action.title}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Recent Activity */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">
          Activité Récente
        </h2>
        <Card>
          <CardHeader>
            <CardTitle>Activité Système</CardTitle>
            <CardDescription>
              Dernières activités et événements système
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {recentActivity.length > 0 ? (
                recentActivity.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-center space-x-4"
                  >
                    {getActivityIcon(activity.type)}
                    <div className="flex-1">
                      <p className="text-sm font-medium">{activity.title}</p>
                      <p className="text-xs text-gray-500">
                        {activity.description}
                      </p>
                      <p className="text-xs text-gray-400">{activity.time}</p>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <Clock className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                  <p>Aucune activité récente</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Health Details */}
      {systemHealth && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Détails du Système
          </h2>
          <Card>
            <CardHeader>
              <CardTitle>État des Services</CardTitle>
              <CardDescription>
                Informations détaillées sur l'état du système
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <p className="text-sm font-medium">Statut Général</p>
                  <Badge
                    variant={
                      systemHealth.status === "healthy"
                        ? "default"
                        : "destructive"
                    }
                    className="mt-1"
                  >
                    {systemHealth.status === "healthy"
                      ? "Opérationnel"
                      : "Problème"}
                  </Badge>
                </div>
                <div>
                  <p className="text-sm font-medium">Version</p>
                  <p className="text-sm text-gray-600">
                    {systemHealth.version || "N/A"}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium">Dernière Vérification</p>
                  <p className="text-sm text-gray-600">
                    {systemHealth.timestamp
                      ? new Date(systemHealth.timestamp).toLocaleString()
                      : "N/A"}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default Dashboard;
