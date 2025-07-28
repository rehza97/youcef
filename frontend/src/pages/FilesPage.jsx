import React, { useState, useEffect } from "react";
import { filesAPI } from "../services/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";

const FilesPage = () => {
  const [files, setFiles] = useState([]);
  const [fileStats, setFileStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [showFileDetails, setShowFileDetails] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  useEffect(() => {
    fetchFiles();
    fetchFileStats();
  }, [currentPage]);

  const fetchFiles = async () => {
    try {
      setLoading(true);
      const response = await filesAPI.getUserFiles({
        page: currentPage,
        per_page: 10,
      });
      setFiles(response.data.files || []);
      setTotalPages(Math.ceil(response.data.total / 10));
    } catch (error) {
      console.error("Erreur lors du chargement des fichiers:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchFileStats = async () => {
    try {
      const response = await filesAPI.getFileStats();
      setFileStats(response.data);
    } catch (error) {
      console.error("Erreur lors du chargement des statistiques:", error);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Vérifier le type de fichier
    const allowedTypes = [
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", // .xlsx
      "application/vnd.ms-excel", // .xls
      "text/csv", // .csv
      "application/csv",
    ];

    if (!allowedTypes.includes(file.type)) {
      alert(
        "Seuls les fichiers Excel (.xlsx, .xls) et CSV (.csv) sont autorisés"
      );
      return;
    }

    try {
      setUploading(true);
      await filesAPI.uploadFile(file);
      fetchFiles();
      fetchFileStats();
      alert("Fichier téléchargé avec succès");
    } catch (error) {
      console.error("Erreur lors du téléchargement:", error);
      alert("Erreur lors du téléchargement du fichier");
    } finally {
      setUploading(false);
    }
  };

  const handleFileClick = async (file) => {
    setSelectedFile(file);
    setShowFileDetails(true);
  };

  const handleDeleteFile = async (fileId) => {
    if (!confirm("Êtes-vous sûr de vouloir supprimer ce fichier ?")) return;

    try {
      await filesAPI.deleteFile(fileId);
      fetchFiles();
      fetchFileStats();
      alert("Fichier supprimé avec succès");
    } catch (error) {
      console.error("Erreur lors de la suppression:", error);
      alert("Erreur lors de la suppression du fichier");
    }
  };

  const handleDownloadFile = async (fileId) => {
    try {
      const response = await filesAPI.downloadFile(fileId);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = selectedFile.original_filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Erreur lors du téléchargement:", error);
      alert("Erreur lors du téléchargement du fichier");
    }
  };

  const getFileTypeIcon = (fileType) => {
    switch (fileType) {
      case "excel":
        return "📊";
      case "csv":
        return "📋";
      default:
        return "📄";
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "completed":
        return "bg-green-100 text-green-800";
      case "processing":
        return "bg-yellow-100 text-yellow-800";
      case "failed":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
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
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("fr-FR");
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Gestion des Fichiers
        </h1>
        <p className="text-gray-600">
          Télécharger et gérer vos fichiers Excel et CSV
        </p>
      </div>

      {/* Statistiques */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-blue-600">
              {fileStats.total_files || 0}
            </div>
            <div className="text-sm text-gray-600">Total des fichiers</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-green-600">
              {fileStats.excel_files || 0}
            </div>
            <div className="text-sm text-gray-600">Fichiers Excel</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-purple-600">
              {fileStats.csv_files || 0}
            </div>
            <div className="text-sm text-gray-600">Fichiers CSV</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-orange-600">
              {fileStats.total_size_mb || 0} MB
            </div>
            <div className="text-sm text-gray-600">Taille totale</div>
          </CardContent>
        </Card>
      </div>

      {/* Zone de téléchargement */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Télécharger un fichier</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
            <input
              type="file"
              accept=".xlsx,.xls,.csv"
              onChange={handleFileUpload}
              disabled={uploading}
              className="hidden"
              id="file-upload"
            />
            <label htmlFor="file-upload" className="cursor-pointer">
              <div className="text-4xl mb-4">📁</div>
              <p className="text-lg font-medium mb-2">
                {uploading
                  ? "Téléchargement en cours..."
                  : "Cliquez pour sélectionner un fichier"}
              </p>
              <p className="text-gray-600">
                Formats supportés: Excel (.xlsx, .xls) et CSV (.csv)
              </p>
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Liste des fichiers */}
      <div className="space-y-4">
        {loading ? (
          <Card>
            <CardContent className="p-6">
              <div className="text-center">Chargement des fichiers...</div>
            </CardContent>
          </Card>
        ) : files.length === 0 ? (
          <Card>
            <CardContent className="p-6">
              <div className="text-center text-gray-500">
                Aucun fichier téléchargé
              </div>
            </CardContent>
          </Card>
        ) : (
          files.map((file) => (
            <Card key={file.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="text-3xl">
                      {getFileTypeIcon(file.file_type)}
                    </div>
                    <div className="flex-1">
                      <h3 className="font-semibold text-lg">
                        {file.original_filename}
                      </h3>
                      <p className="text-gray-600">
                        {file.file_type.toUpperCase()} •{" "}
                        {formatFileSize(file.file_size)}
                      </p>
                      <div className="flex gap-2 mt-1">
                        <Badge
                          className={getStatusColor(file.processing_status)}
                        >
                          {file.processing_status === "completed"
                            ? "Terminé"
                            : file.processing_status === "processing"
                            ? "En cours"
                            : file.processing_status === "failed"
                            ? "Échec"
                            : "En attente"}
                        </Badge>
                        <Badge variant="outline">
                          {formatDate(file.uploaded_at)}
                        </Badge>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleFileClick(file)}
                    >
                      Détails
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDownloadFile(file.id)}
                    >
                      Télécharger
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDeleteFile(file.id)}
                    >
                      Supprimer
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center mt-6">
          <div className="flex gap-2">
            <Button
              variant="outline"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(currentPage - 1)}
            >
              Précédent
            </Button>
            <span className="flex items-center px-4">
              Page {currentPage} sur {totalPages}
            </span>
            <Button
              variant="outline"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(currentPage + 1)}
            >
              Suivant
            </Button>
          </div>
        </div>
      )}

      {/* Modal de détails du fichier */}
      {showFileDetails && selectedFile && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">Détails du fichier</h2>

            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-600">
                    Nom du fichier
                  </label>
                  <p className="text-gray-900">
                    {selectedFile.original_filename}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-600">
                    Type de fichier
                  </label>
                  <p className="text-gray-900">
                    {selectedFile.file_type.toUpperCase()}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-600">
                    Taille
                  </label>
                  <p className="text-gray-900">
                    {formatFileSize(selectedFile.file_size)}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-600">
                    Statut
                  </label>
                  <Badge
                    className={getStatusColor(selectedFile.processing_status)}
                  >
                    {selectedFile.processing_status === "completed"
                      ? "Terminé"
                      : selectedFile.processing_status === "processing"
                      ? "En cours"
                      : selectedFile.processing_status === "failed"
                      ? "Échec"
                      : "En attente"}
                  </Badge>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-600">
                    Date de téléchargement
                  </label>
                  <p className="text-gray-900">
                    {formatDate(selectedFile.uploaded_at)}
                  </p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-600">
                    ID du fichier
                  </label>
                  <p className="text-gray-900">{selectedFile.id}</p>
                </div>
              </div>

              {selectedFile.error_message && (
                <div className="border border-red-200 bg-red-50 p-4 rounded">
                  <h3 className="font-semibold text-red-800 mb-2">
                    Erreur de traitement
                  </h3>
                  <p className="text-red-700">{selectedFile.error_message}</p>
                </div>
              )}
            </div>

            <Separator className="my-4" />

            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => setShowFileDetails(false)}
              >
                Fermer
              </Button>
              <Button onClick={() => handleDownloadFile(selectedFile.id)}>
                Télécharger
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default FilesPage;
