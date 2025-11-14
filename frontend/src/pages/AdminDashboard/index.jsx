import React, { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { BarChart3, FileUp, Send, Shield } from "lucide-react";
import BroadcastAnalytics from "../../components/admin/BroadcastAnalytics";
import BroadcastFileManager from "../../components/admin/BroadcastFileManager";
import FileDistribution from "../../components/admin/FileDistribution";
import SecureFilesManager from "../../components/admin/SecureFilesManager";

const AdminDashboard = () => {
  const [activeTab, setActiveTab] = useState("analytics");

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-2">
          <Shield className="h-8 w-8 text-purple-600" />
          Tableau de Bord Administrateur
        </h1>
        <p className="text-gray-600">
          Gérez les diffusions, les fichiers et visualisez les analyses
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4 mb-6">
          <TabsTrigger value="analytics" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            <span className="hidden sm:inline">Analyses</span>
          </TabsTrigger>
          <TabsTrigger value="broadcast-files" className="flex items-center gap-2">
            <FileUp className="h-4 w-4" />
            <span className="hidden sm:inline">Fichiers</span>
          </TabsTrigger>
          <TabsTrigger value="distribution" className="flex items-center gap-2">
            <Send className="h-4 w-4" />
            <span className="hidden sm:inline">Distribution</span>
          </TabsTrigger>
          <TabsTrigger value="secure-files" className="flex items-center gap-2">
            <Shield className="h-4 w-4" />
            <span className="hidden sm:inline">Sécurisés</span>
          </TabsTrigger>
        </TabsList>

        {/* Analytics Tab */}
        <TabsContent value="analytics">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="h-5 w-5" />
                  Analyses de Diffusion
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-600 mb-4">
                  Consultez les statistiques détaillées sur les diffusions, l'engagement et la lecture.
                </p>
              </CardContent>
            </Card>
            <BroadcastAnalytics />
          </div>
        </TabsContent>

        {/* Broadcast Files Tab */}
        <TabsContent value="broadcast-files">
          <div className="space-y-6">
            <BroadcastFileManager />
          </div>
        </TabsContent>

        {/* File Distribution Tab */}
        <TabsContent value="distribution">
          <div className="space-y-6">
            <FileDistribution />
          </div>
        </TabsContent>

        {/* Secure Files Tab */}
        <TabsContent value="secure-files">
          <div className="space-y-6">
            <SecureFilesManager />
          </div>
        </TabsContent>
      </Tabs>

      {/* Admin Guidelines */}
      <Card className="mt-8 border-purple-200 bg-purple-50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-purple-600" />
            Directives Administrateur
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2 text-sm text-purple-900">
            <li>
              ✓ <strong>Analyses:</strong> Surveillez l'engagement des diffusions et le taux de lecture
            </li>
            <li>
              ✓ <strong>Fichiers de Diffusion:</strong> Téléchargez et gérez les fichiers à diffuser
            </li>
            <li>
              ✓ <strong>Distribution:</strong> Distribuez les fichiers à tous les utilisateurs, à des DOTs ou à des utilisateurs spécifiques
            </li>
            <li>
              ✓ <strong>Fichiers Sécurisés:</strong> Consultez et gérez les fichiers administrateur sécurisés
            </li>
            <li>
              ⚠️ <strong>Permissions:</strong> Seuls les administrateurs peuvent accéder à ce tableau de bord
            </li>
            <li>
              ⚠️ <strong>Taille Maximum:</strong> Les fichiers de diffusion sont limités à 50 MB
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminDashboard;
