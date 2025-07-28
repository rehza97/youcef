import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { useAuth } from "../contexts/AuthContext";
import { useToast } from "../hooks/use-toast";
import {
  Activity,
  Users,
  Bell,
  MessageSquare,
  Shield,
  Settings,
} from "lucide-react";

const Dashboard = () => {
  const { user } = useAuth();
  const { toast } = useToast();

  const stats = [
    {
      title: "Total Utilisateurs",
      value: "1,234",
      icon: Users,
      description: "Utilisateurs actifs dans le système",
    },
    {
      title: "Notifications",
      value: "56",
      icon: Bell,
      description: "Notifications non lues",
    },
    {
      title: "Messages",
      value: "89",
      icon: MessageSquare,
      description: "Nouveaux messages",
    },
    {
      title: "État du Système",
      value: "Bon",
      icon: Activity,
      description: "Tous les systèmes opérationnels",
    },
  ];

  const quickActions = [
    {
      title: "Gérer les Utilisateurs",
      description: "Voir et gérer les comptes utilisateurs",
      icon: Users,
      href: "/users",
    },
    {
      title: "Gestion des Rôles",
      description: "Configurer les rôles et permissions",
      icon: Shield,
      href: "/roles",
    },
    {
      title: "Paramètres Système",
      description: "Configurer les préférences système",
      icon: Settings,
      href: "/settings",
    },
  ];

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">
          Bon retour, {user?.username || "Utilisateur"} !
        </h1>
        <p className="text-gray-600 mt-2">
          Voici ce qui se passe avec votre application aujourd'hui.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">
                {stat.title}
              </CardTitle>
              <stat.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {quickActions.map((action, index) => (
            <Card key={index} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-center space-x-2">
                  <action.icon className="h-5 w-5 text-blue-600" />
                  <CardTitle className="text-lg">{action.title}</CardTitle>
                </div>
                <CardDescription>{action.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => {
                    // Navigate to the action
                    window.location.href = action.href;
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
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">
                    Vérification système terminée
                  </p>
                  <p className="text-xs text-gray-500">Il y a 2 minutes</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">
                    Nouvel utilisateur enregistré
                  </p>
                  <p className="text-xs text-gray-500">Il y a 5 minutes</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="w-2 h-2 bg-yellow-500 rounded-full"></div>
                <div className="flex-1">
                  <p className="text-sm font-medium">Sauvegarde terminée</p>
                  <p className="text-xs text-gray-500">Il y a 10 minutes</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Dashboard;
