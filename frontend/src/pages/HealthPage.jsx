import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";

const HealthPage = () => {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">État du Système</h1>
        <p className="text-gray-600 mt-2">
          Surveiller l'état et les performances du système
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Vérification de l'État</CardTitle>
          <CardDescription>
            Voir les informations sur l'état et le statut du système
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            La fonctionnalité de surveillance de l'état du système sera
            implémentée ici.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default HealthPage;
