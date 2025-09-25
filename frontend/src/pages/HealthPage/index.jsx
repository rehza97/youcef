import React, { useState, useEffect } from "react";
import { generalAPI } from "../../services/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Separator } from "../../components/ui/separator";

const HealthPage = () => {
  const [healthStatus, setHealthStatus] = useState(null);
  const [detailedHealth, setDetailedHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastChecked, setLastChecked] = useState(null);

  useEffect(() => {
    checkHealth();
  }, []);

  const checkHealth = async () => {
    try {
      setLoading(true);

      // Vérification de santé basique
      const basicResponse = await generalAPI.healthCheck();
      setHealthStatus(basicResponse.data);

      // Vérification de santé détaillée
      const detailedResponse = await generalAPI.detailedHealthCheck();
      setDetailedHealth(detailedResponse.data);

      setLastChecked(new Date());
    } catch (error) {
      console.error("Erreur lors de la vérification de santé:", error);
      setHealthStatus({ status: "error", message: "Erreur de connexion" });
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "healthy":
        return "bg-green-100 text-green-800";
      case "warning":
        return "bg-yellow-100 text-yellow-800";
      case "error":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case "healthy":
        return "✅";
      case "warning":
        return "⚠️";
      case "error":
        return "❌";
      default:
        return "❓";
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return "N/A";
    return new Date(timestamp).toLocaleString("fr-FR");
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          État du Système
        </h1>
        <p className="text-gray-600">
          Surveiller l'état et les performances du système
        </p>
      </div>

      {/* Contrôles */}
      <div className="mb-6">
        <Button onClick={checkHealth} disabled={loading}>
          {loading ? "Vérification..." : "Vérifier l'état du système"}
        </Button>
        {lastChecked && (
          <span className="ml-4 text-sm text-gray-500">
            Dernière vérification: {lastChecked.toLocaleString("fr-FR")}
          </span>
        )}
      </div>

      {/* État général */}
      {healthStatus && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {getStatusIcon(healthStatus.status)} État Général du Système
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h3 className="font-semibold mb-2">Statut</h3>
                <Badge className={getStatusColor(healthStatus.status)}>
                  {healthStatus.status === "healthy"
                    ? "Opérationnel"
                    : healthStatus.status === "warning"
                    ? "Attention"
                    : healthStatus.status === "error"
                    ? "Erreur"
                    : "Inconnu"}
                </Badge>
              </div>
              <div>
                <h3 className="font-semibold mb-2">Version</h3>
                <p className="text-gray-600">{healthStatus.version || "N/A"}</p>
              </div>
              <div>
                <h3 className="font-semibold mb-2">Service</h3>
                <p className="text-gray-600">{healthStatus.service || "N/A"}</p>
              </div>
              <div>
                <h3 className="font-semibold mb-2">Horodatage</h3>
                <p className="text-gray-600">
                  {formatTimestamp(healthStatus.timestamp)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* État détaillé */}
      {detailedHealth && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>État Détaillé du Système</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Base de données */}
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  🗄️ Base de Données
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm text-gray-600">Statut:</span>
                    <Badge
                      className={
                        detailedHealth.database?.includes("connected")
                          ? "bg-green-100 text-green-800"
                          : "bg-red-100 text-red-800"
                      }
                    >
                      {detailedHealth.database?.includes("connected")
                        ? "Connecté"
                        : "Erreur"}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Détails:</span>
                    <p className="text-sm">
                      {detailedHealth.database || "N/A"}
                    </p>
                  </div>
                </div>
              </div>

              {/* Environnement */}
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  🌍 Environnement
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm text-gray-600">Mode:</span>
                    <Badge
                      className={
                        detailedHealth.environment === "development"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-orange-100 text-orange-800"
                      }
                    >
                      {detailedHealth.environment === "development"
                        ? "Développement"
                        : "Production"}
                    </Badge>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Version:</span>
                    <p className="text-sm">{detailedHealth.version || "N/A"}</p>
                  </div>
                </div>
              </div>

              {/* Service */}
              <div className="border rounded-lg p-4">
                <h3 className="font-semibold mb-2 flex items-center gap-2">
                  ⚙️ Service
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <span className="text-sm text-gray-600">Nom:</span>
                    <p className="text-sm">{detailedHealth.service || "N/A"}</p>
                  </div>
                  <div>
                    <span className="text-sm text-gray-600">Statut:</span>
                    <Badge className={getStatusColor(detailedHealth.status)}>
                      {detailedHealth.status === "healthy"
                        ? "Opérationnel"
                        : "Problème"}
                    </Badge>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Informations système */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Fonctionnalités Disponibles</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-green-500">✅</span>
                <span>Authentification & Autorisation</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✅</span>
                <span>Contrôle d'Accès Basé sur les Rôles (RBAC)</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✅</span>
                <span>Messagerie en Temps Réel</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✅</span>
                <span>Système de Notifications</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✅</span>
                <span>Support WebSocket</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✅</span>
                <span>Limitation de Débit</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-green-500">✅</span>
                <span>Support CORS</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Points de Terminaison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div>
                <span className="font-medium">Authentification:</span>
                <span className="text-gray-600 ml-2">/api/auth</span>
              </div>
              <div>
                <span className="font-medium">Utilisateurs:</span>
                <span className="text-gray-600 ml-2">/api/users</span>
              </div>
              <div>
                <span className="font-medium">Notifications:</span>
                <span className="text-gray-600 ml-2">/api/notifications</span>
              </div>
              <div>
                <span className="font-medium">Messagerie:</span>
                <span className="text-gray-600 ml-2">/api/conversations</span>
              </div>
              <div>
                <span className="font-medium">Fichiers:</span>
                <span className="text-gray-600 ml-2">/api/files</span>
              </div>
              <div>
                <span className="font-medium">Santé:</span>
                <span className="text-gray-600 ml-2">/api/health</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* État de chargement */}
      {loading && (
        <Card>
          <CardContent className="p-6">
            <div className="text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
              <p>Vérification de l'état du système...</p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default HealthPage;
