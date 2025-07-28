import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";

const NotificationsPage = () => {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Notifications</h1>
        <p className="text-gray-600 mt-2">Voir et gérer vos notifications</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Centre de Notifications</CardTitle>
          <CardDescription>
            Voir et gérer toutes vos notifications
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            La fonctionnalité de gestion des notifications sera implémentée ici.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default NotificationsPage;
