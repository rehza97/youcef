import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  Lock,
  Download,
  Eye,
  Loader2,
  Shield,
} from "lucide-react";
import { toast } from "sonner";
import {
  getAllAdminFiles,
  downloadAdminFile,
} from "../../services/api";
import { handleApiError } from "../../lib/error-handler";

const SecureFilesManager = () => {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);

  useEffect(() => {
    fetchFiles();
  }, []);

  const fetchFiles = async () => {
    try {
      setLoading(true);
      const response = await getAllAdminFiles();
      setFiles(response.data.files || []);
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du chargement des fichiers sécurisés",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async (fileId, fileName) => {
    try {
      const blob = await downloadAdminFile(fileId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      toast.success("Téléchargement commencé");
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du téléchargement",
      });
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString("fr-FR", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getSecurityLevel = (level) => {
    switch (level) {
      case "high":
        return <Badge className="bg-red-100 text-red-800">Élevée</Badge>;
      case "medium":
        return <Badge className="bg-yellow-100 text-yellow-800">Moyenne</Badge>;
      case "low":
        return <Badge className="bg-green-100 text-green-800">Basse</Badge>;
      default:
        return <Badge className="bg-gray-100 text-gray-800">Normale</Badge>;
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-purple-600" />
          Gestionnaire de Fichiers Sécurisés (Admin)
        </CardTitle>
      </CardHeader>

      <CardContent>
        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600 mx-auto mb-2"></div>
            <p className="text-sm text-gray-600">Chargement des fichiers...</p>
          </div>
        ) : files.length === 0 ? (
          <div className="text-center py-8">
            <Lock className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p className="text-gray-600">Aucun fichier sécurisé</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Nom du Fichier</TableHead>
                  <TableHead>Taille</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Niveau de Sécurité</TableHead>
                  <TableHead>Accès Restreint</TableHead>
                  <TableHead>Date de Création</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {files.map((file) => (
                  <TableRow key={file.id}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Lock className="h-4 w-4 text-purple-600" />
                        {file.name}
                      </div>
                    </TableCell>
                    <TableCell>{formatFileSize(file.size)}</TableCell>
                    <TableCell>
                      <span className="px-2 py-1 bg-gray-100 rounded text-sm">
                        {file.file_type || "Fichier"}
                      </span>
                    </TableCell>
                    <TableCell>{getSecurityLevel(file.security_level)}</TableCell>
                    <TableCell>
                      {file.is_restricted ? (
                        <Badge className="bg-red-100 text-red-800">Oui</Badge>
                      ) : (
                        <Badge className="bg-green-100 text-green-800">Non</Badge>
                      )}
                    </TableCell>
                    <TableCell>{formatDate(file.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-2 justify-end">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedFile(file)}
                          className="text-purple-600 border-purple-200"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDownload(file.id, file.name)}
                          className="text-blue-600 border-blue-200"
                        >
                          <Download className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {/* File Details Sidebar */}
        {selectedFile && (
          <div className="mt-8 p-6 bg-gray-50 rounded-lg border">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-semibold flex items-center gap-2">
                <Shield className="h-5 w-5 text-purple-600" />
                Détails du Fichier
              </h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedFile(null)}
              >
                ✕
              </Button>
            </div>

            <div className="space-y-3">
              <div>
                <p className="text-sm text-gray-600">Nom</p>
                <p className="font-medium">{selectedFile.name}</p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Taille</p>
                  <p className="font-medium">
                    {formatFileSize(selectedFile.size)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-gray-600">Type</p>
                  <p className="font-medium">{selectedFile.file_type}</p>
                </div>
              </div>
              <div>
                <p className="text-sm text-gray-600">Créé le</p>
                <p className="font-medium">{formatDate(selectedFile.created_at)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-600">Description</p>
                <p className="font-medium text-sm">
                  {selectedFile.description || "Aucune description"}
                </p>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-gray-600">Niveau de Sécurité</p>
                  {getSecurityLevel(selectedFile.security_level)}
                </div>
                <div>
                  <p className="text-sm text-gray-600">Accès Restreint</p>
                  {selectedFile.is_restricted ? (
                    <Badge className="bg-red-100 text-red-800">Oui</Badge>
                  ) : (
                    <Badge className="bg-green-100 text-green-800">Non</Badge>
                  )}
                </div>
              </div>

              {selectedFile.restricted_to?.length > 0 && (
                <div>
                  <p className="text-sm text-gray-600 mb-2">
                    Accès Restreint À ({selectedFile.restricted_to.length} utilisateur(s))
                  </p>
                  <div className="space-y-1">
                    {selectedFile.restricted_to.map((user) => (
                      <div
                        key={user.id}
                        className="text-sm px-2 py-1 bg-white rounded border"
                      >
                        {user.username} ({user.email})
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default SecureFilesManager;
