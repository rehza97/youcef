import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";

const SettingsPage = () => {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Paramètres</h1>
        <p className="text-gray-600 mt-2">
          Configurer les paramètres et préférences de l'application
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Paramètres de l'Application</CardTitle>
          <CardDescription>
            Gérer la configuration système et les préférences utilisateur
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            La fonctionnalité des paramètres sera implémentée ici.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default SettingsPage;
