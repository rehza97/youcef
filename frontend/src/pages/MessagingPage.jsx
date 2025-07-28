import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";

const MessagingPage = () => {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Messagerie</h1>
        <p className="text-gray-600 mt-2">
          Discuter avec d'autres utilisateurs et gérer les conversations
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Centre de Messagerie</CardTitle>
          <CardDescription>
            Envoyer et recevoir des messages avec d'autres utilisateurs
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            La fonctionnalité de messagerie sera implémentée ici.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default MessagingPage;
