import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";

const RolesPage = () => {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Rôles</h1>
        <p className="text-gray-600 mt-2">
          Gérer les rôles utilisateurs et les permissions
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Gestion des Rôles</CardTitle>
          <CardDescription>
            Configurer les rôles utilisateurs et leurs permissions associées
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            La fonctionnalité de gestion des rôles sera implémentée ici.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default RolesPage;
