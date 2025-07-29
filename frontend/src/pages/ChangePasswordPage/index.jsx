import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";

const ChangePasswordPage = () => {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">
          Changer le Mot de Passe
        </h1>
        <p className="text-gray-600 mt-2">
          Mettre à jour le mot de passe de votre compte
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Changement de Mot de Passe</CardTitle>
          <CardDescription>
            Mettre à jour le mot de passe de votre compte en toute sécurité
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            La fonctionnalité de changement de mot de passe sera implémentée
            ici.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default ChangePasswordPage;
