import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";

const ProfilePage = () => {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Profil</h1>
        <p className="text-gray-600 mt-2">
          Gérer votre profil utilisateur et les paramètres du compte
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profil Utilisateur</CardTitle>
          <CardDescription>
            Voir et modifier vos informations personnelles
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            La fonctionnalité de gestion du profil sera implémentée ici.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default ProfilePage;
