import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";

const PermissionsPage = () => {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Permissions</h1>
        <p className="text-gray-600 mt-2">
          Gérer les permissions et les droits d'accès
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Gestion des Permissions</CardTitle>
          <CardDescription>
            Configurez les permissions et les droits d'accès des utilisateurs
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            La gestion des permissions sera implémentée ici.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default PermissionsPage;
