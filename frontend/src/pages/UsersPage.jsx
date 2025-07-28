import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";

const UsersPage = () => {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Utilisateurs</h1>
        <p className="text-gray-600 mt-2">
          Gérer les comptes utilisateurs et les permissions
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Gestion des Utilisateurs</CardTitle>
          <CardDescription>
            Voir et gérer tous les comptes utilisateurs dans le système
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            La fonctionnalité de gestion des utilisateurs sera implémentée ici.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default UsersPage;
