import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../components/ui/card";

const ProtectedPage = () => {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Protected Page
        </h1>
        <p className="text-gray-600 dark:text-gray-400 mt-2">
          This is a protected page that requires authentication
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Access Granted</CardTitle>
          <CardDescription>
            You have successfully accessed this protected resource
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600 dark:text-gray-400">
            This page demonstrates that authentication is working correctly.
          </p>
        </CardContent>
      </Card>
    </div>
  );
};

export default ProtectedPage;
