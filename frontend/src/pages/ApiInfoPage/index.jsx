import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";

const ApiInfoPage = () => {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Informations API</h1>
        <p className="text-gray-600 mt-2">
          Voir la documentation API et les informations des points de
          terminaison
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Documentation API</CardTitle>
          <CardDescription>
            Informations sur les points de terminaison API disponibles
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600">
            La documentation API et les informations seront affichées ici.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default ApiInfoPage;
