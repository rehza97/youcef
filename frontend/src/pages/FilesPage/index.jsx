import React, { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import {
  uploadFile,
  uploadBatchFiles,
  getUserFiles,
  deleteFile,
  processFile,
  getFileStats,
  downloadFile,
  getAvailableFileTypes,
  updateFileClassification,
} from "../../services/api";
import { useNotificationsWebSocket } from "../../hooks/useNotificationsWebSocket";
import { useAuth } from "../../contexts/AuthContext";
import { useProcessing } from "../../contexts/ProcessingContext";
import { debugComponent } from "../../lib/debug.js";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Alert, AlertDescription } from "../../components/ui/alert";
import { Progress } from "../../components/ui/progress";
import { Skeleton } from "../../components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../../components/ui/tooltip";
import {
  Upload,
  FileText,
  Trash2,
  Download,
  Eye,
  CheckCircle,
  XCircle,
  Clock,
  Info,
  AlertCircle,
  RefreshCw,
  Wifi,
  WifiOff,
  Play,
} from "lucide-react";
import { toast } from "sonner";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";


const FilesPage = () => {
  const debug = debugComponent("FilesPage");
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { user, token } = useAuth();
  const [selectedFile, setSelectedFile] = useState(null);
  const [showFileDetails, setShowFileDetails] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [availableFileTypes, setAvailableFileTypes] = useState([]);
  const [selectedFileType, setSelectedFileType] = useState("");

  // Real-time notifications from WebSocket
  const { notifications: liveNotifications, isConnected: wsConnected } =
    useNotificationsWebSocket();

  // Processing WebSocket connection
  const [processingWs, setProcessingWs] = useState(null);
  const [processingTasks, setProcessingTasks] = useState({});

  // Count file-related notifications
  const fileNotificationCount = liveNotifications.filter(
    (notification) =>
      notification.data?.action?.includes("upload") ||
      notification.data?.action?.includes("processing")
  ).length;

  debug.log("Component rendered", {
    wsConnected,
    notificationCount: liveNotifications.length,
    fileNotificationCount,
  });

  // Data processing states
  const [processedData, setProcessedData] = useState({});
  const [processingStatus, setProcessingStatus] = useState({});
  const [liveProcessingData, setLiveProcessingData] = useState({}); // Real-time processing stats
  const [processedRecordsCount, setProcessedRecordsCount] = useState({}); // Progressive record count
  const [uploadProgress, setUploadProgress] = useState(0);

  // Fetch available file types on mount
  useEffect(() => {
    const fetchFileTypes = async () => {
      try {
        const response = await getAvailableFileTypes();
        setAvailableFileTypes(response.data.file_types || []);
      } catch (error) {
        console.error("Error fetching file types:", error);
      }
    };
    fetchFileTypes();
  }, []);

  // Handle real-time notifications
  useEffect(() => {
    if (liveNotifications.length > 0) {
      const fileNotifications = liveNotifications.filter(
        (notification) =>
          notification.notification_type === "success" ||
          notification.notification_type === "info" ||
          notification.notification_type === "error"
      );

      fileNotifications.forEach((notification) => {
        if (notification.data?.action === "upload") {
          toast.success(`Fichier téléchargé: ${notification.data.filename}`);
        } else if (notification.data?.action === "processing_started") {
          toast.info(`Traitement commencé: ${notification.data.filename}`);
        } else if (notification.data?.action === "processing_progress") {
          toast.info(
            `Progression: ${notification.data.filename} - ${notification.data.progress}%`
          );
        } else if (notification.data?.action === "processing_completed") {
          toast.success(`Traitement terminé: ${notification.data.filename}`);
          // Refresh files list
          queryClient.invalidateQueries({ queryKey: ["files"] });
          queryClient.invalidateQueries({ queryKey: ["fileStats"] });
        } else if (notification.data?.action === "processing_failed") {
          toast.error(`Erreur de traitement: ${notification.data.filename}`);
        }
      });
    }
  }, [liveNotifications, queryClient]);


  // React Query hooks
  const {
    data: filesData,
    isLoading: filesLoading,
    error: filesError,
    refetch: refetchFiles,
  } = useQuery({
    queryKey: ["files", currentPage],
    queryFn: () => getUserFiles({ page: currentPage, per_page: 10 }),
  });

  const { data: fileStats, isLoading: statsLoading } = useQuery({
    queryKey: ["fileStats"],
    queryFn: () => getFileStats(),
  });

  const uploadFileMutation = useMutation({
    mutationFn: (file) => {
      debug.log("Upload mutation started", {
        fileName: file.name,
        fileSize: file.size,
      });
      setUploadProgress(0); // Reset progress
      return uploadFile(file, (progress) => {
        setUploadProgress(progress);
      });
    },
    onSuccess: (response) => {
      debug.success("File upload successful", response.data);
      setUploadProgress(100);

      // Store the uploaded file info for optional processing (no auto-start)
      const uploadedFile = response.data;
      if (uploadedFile && uploadedFile.id) {
        debug.log("File uploaded; waiting for user to start processing", {
          fileId: uploadedFile.id,
        });
      } else {
        console.error("Invalid file upload response:", response.data);
        toast.error("Réponse de téléchargement invalide");
      }

      toast.success("Fichier téléchargé avec succès");

      // Invalidate queries and reset progress
      queryClient.invalidateQueries({ queryKey: ["files"] });
      queryClient.invalidateQueries({ queryKey: ["fileStats"] });

      // Reset progress immediately after showing success
      setTimeout(() => {
        setUploadProgress(0);
        debug.log("Upload progress reset");
      }, 1500);
    },
    onError: (error) => {
      debug.error("File upload failed", error);
      setUploadProgress(0);
      toast.error("Erreur lors du téléchargement du fichier");
    },
  });

  const deleteFileMutation = useMutation({
    mutationFn: (fileId) => {
      debug.log("Delete mutation started", { fileId });
      return deleteFile(fileId);
    },
    onSuccess: () => {
      debug.success("File deleted successfully");
      queryClient.invalidateQueries({ queryKey: ["files"] });
      queryClient.invalidateQueries({ queryKey: ["fileStats"] });
      toast.success("Fichier supprimé avec succès");
    },
    onError: (error) => {
      debug.error("File deletion failed", error);
      toast.error("Erreur lors de la suppression du fichier");
    },
  });

  // Handle file upload
  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files);
    if (files.length === 0) return;

    console.log(`📁 Selected ${files.length} file(s) for upload`);

    if (files.length === 1) {
      // Single file upload
      console.log(`🚀 Starting single file upload: ${files[0].name}`);
      uploadFileMutation.mutate(files[0]);
    } else {
      // Multiple files - use batch upload for better performance
      console.log(`🚀 Starting batch upload for ${files.length} files`);
      const uploadBatch = async () => {
        try {
          setUploadProgress(0);
          const response = await uploadBatchFiles(files, (progress) => {
            setUploadProgress(progress);
          });

          console.log(`✅ Batch upload successful:`, response.data);
          setUploadProgress(100);
          toast.success(`${files.length} fichiers téléchargés avec succès`);

          queryClient.invalidateQueries({ queryKey: ["files"] });
          queryClient.invalidateQueries({ queryKey: ["fileStats"] });

          // Reset progress after delay
          setTimeout(() => {
            setUploadProgress(0);
            console.log("Batch upload progress reset");
          }, 1500);
        } catch (error) {
          console.error(`❌ Batch upload failed:`, error);
          toast.error("Erreur lors du téléchargement des fichiers");
          setUploadProgress(0);
        }
      };

      uploadBatch();
    }

    // Reset the input
    event.target.value = "";
  };

  const processingContext = useProcessing();
  const { subscribeTask, isConnected, connectionStatus, reconnect } =
    processingContext || {};

  const processFileData = async (fileId, file) => {
    try {
      console.log(`🚀 Starting file processing for fileId: ${fileId}`);
      setProcessingStatus((prev) => ({ ...prev, [fileId]: "processing" }));

      console.log(`📡 Calling processFile(${fileId})`);
      const response = await processFile(fileId);
      const taskId = response.data.task_id || String(fileId);

      setProcessedData((prev) => ({
        ...prev,
        [fileId]: {
          status: "processing",
          message: response.data.message,
          task_id: taskId,
        },
      }));

      // subscribe globally for updates with progressive data loading
      const unsubscribe = subscribeTask(taskId, (message) => {
        try {
          if (message?.task_id !== taskId) return;

          if (message.type === "processing_update") {
            const stats = message.data?.statistics || {};

            // Update live processing data for progressive display
            setLiveProcessingData((prev) => ({
              ...prev,
              [fileId]: {
                progress: message.data?.progress ?? 0,
                status: message.data?.status || "processing",
                message: message.data?.message || "Traitement en cours...",
                total_rows: stats.total_rows || stats.total_records || 0,
                processed_rows: stats.processed_rows || 0,
                saved_rows: stats.saved_rows || 0,
                filtered_rows: stats.filtered_rows || 0,
                errors: stats.errors || 0,
                timestamp: new Date().toISOString(),
              },
            }));

            // Update progressive record count
            if (stats.saved_rows > 0) {
              setProcessedRecordsCount((prev) => ({
                ...prev,
                [fileId]: stats.saved_rows,
              }));
            }

            // Update main processed data
            setProcessedData((prev) => ({
              ...prev,
              [fileId]: {
                ...(prev[fileId] || {}),
                status: message.data?.status || "processing",
                progress: message.data?.progress ?? prev[fileId]?.progress,
                message: message.data?.message ?? prev[fileId]?.message,
                statistics: stats,
              },
            }));
          } else if (message.type === "completed") {
            setProcessingStatus((prev) => ({ ...prev, [fileId]: "completed" }));
            setLiveProcessingData((prev) => ({
              ...prev,
              [fileId]: {
                ...prev[fileId],
                status: "completed",
                progress: 100,
              },
            }));
            toast.success("Traitement terminé avec succès!");
            queryClient.invalidateQueries({ queryKey: ["files"] });
            queryClient.invalidateQueries({ queryKey: ["fileStats"] });
            unsubscribe && unsubscribe();
          } else if (message.type === "failed") {
            setProcessingStatus((prev) => ({ ...prev, [fileId]: "failed" }));
            setLiveProcessingData((prev) => ({
              ...prev,
              [fileId]: {
                ...prev[fileId],
                status: "failed",
                message: message.data?.message || "Échec du traitement",
              },
            }));
            toast.error("Traitement échoué");
            unsubscribe && unsubscribe();
          }
        } catch (error) {
          console.error("Error handling processing update:", error);
        }
      });

    } catch (error) {
      console.error("❌ Error processing file:", error);
      setProcessingStatus((prev) => ({ ...prev, [fileId]: "failed" }));
      toast.error("Erreur lors du traitement du fichier");
    }
  };

  const handleFileClick = async (file) => {
    setSelectedFile(file);
    setShowFileDetails(true);
  };

  const handlePreviewFile = (fileId) => {
    navigate(`/files/${fileId}/preview`);
  };

  const handleDeleteFile = async (fileId) => {
    if (
      !confirm(
        "Êtes-vous sûr de vouloir supprimer ce fichier ? Toutes les données associées seront également supprimées."
      )
    )
      return;

    deleteFileMutation.mutate(fileId);

    // Remove associated processed data
    setProcessedData((prev) => {
      const newData = { ...prev };
      delete newData[fileId];
      return newData;
    });

    // Remove processing status
    setProcessingStatus((prev) => {
      const newStatus = { ...prev };
      delete newStatus[fileId];
      return newStatus;
    });
  };

  const handleDownloadFile = async (fileId) => {
    try {
      const response = await downloadFile(fileId);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const file = files.find(f => f.id === fileId);
      a.download = file?.original_filename || "file";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success("Fichier téléchargé avec succès");
    } catch (error) {
      console.error("Erreur lors du téléchargement:", error);
      toast.error("Erreur lors du téléchargement du fichier");
    }
  };

  const handleStartTreatment = async (file) => {
    await processFileData(file.id, file);
  };

  const isFileProcessing = (file) => {
    return (
      file.processing_status === "processing" ||
      processingStatus[file.id] === "processing" ||
      liveProcessingData[file.id]?.status === "processing"
    );
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

  const getProcessingStatusIcon = (status) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case "processing":
        return <Clock className="h-4 w-4 text-yellow-600" />;
      case "failed":
        return <XCircle className="h-4 w-4 text-red-600" />;
      default:
        return <Clock className="h-4 w-4 text-gray-600" />;
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

  const truncateFileName = (filename, maxLength = 20) => {
    if (!filename) return "";
    if (filename.length <= maxLength) return filename;
    return filename.substring(0, maxLength) + "...";
  };

  const files = filesData?.data?.files || [];
  const totalPages = Math.ceil((filesData?.data?.total || 0) / 10);

  return (
    <TooltipProvider>
      <div className="container mx-auto p-6">
        <div className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Gestion des Fichiers et Données
              </h1>
              <p className="text-gray-600">
                Télécharger, traiter et analyser vos fichiers Excel et CSV
              </p>
              {/* WebSocket Connection Status */}
              <div className="flex items-center mt-2">
                <div
                  className={`flex items-center text-sm ${
                    isConnected ? "text-green-600" : "text-red-600"
                  }`}
                >
                  {isConnected ? (
                    <Wifi className="h-4 w-4 mr-1" />
                  ) : (
                    <WifiOff className="h-4 w-4 mr-1" />
                  )}
                  {isConnected
                    ? "Notifications en temps réel activées"
                    : "Notifications en temps réel désactivées"}
                </div>
                {isConnected && fileNotificationCount > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {fileNotificationCount} notification
                    {fileNotificationCount > 1 ? "s" : ""}
                  </Badge>
                )}
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Button
                onClick={() => refetchFiles()}
                variant="outline"
                size="sm"
                disabled={filesLoading}
              >
                <RefreshCw
                  className={`h-4 w-4 mr-2 ${
                    filesLoading ? "animate-spin" : ""
                  }`}
                />
                Actualiser
              </Button>
            </div>
          </div>
        </div>

        {filesError && (
          <Alert className="mb-6">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>
              Erreur lors du chargement des fichiers. Veuillez réessayer.
            </AlertDescription>
          </Alert>
        )}

        <div className="space-y-6">
            {/* Enhanced Statistics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              {statsLoading ? (
                Array.from({ length: 4 }).map((_, i) => (
                  <Card key={i}>
                    <CardContent className="p-4">
                      <Skeleton className="h-8 w-16 mb-2" />
                      <Skeleton className="h-4 w-24" />
                    </CardContent>
                  </Card>
                ))
              ) : (
                <>

                </>
              )}
            </div>

            {/* Enhanced Upload Zone */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Upload className="h-5 w-5" />
                  Télécharger un fichier
                  <Badge
                    variant={isConnected ? "default" : "secondary"}
                    className="ml-2"
                  >
                    {isConnected ? (
                      <>
                        <Wifi className="h-3 w-3 mr-1" />
                        Temps réel
                      </>
                    ) : (
                      <>
                        <WifiOff className="h-3 w-3 mr-1" />
                        {connectionStatus === "error" ? "Erreur" : "Déconnecté"}
                      </>
                    )}
                  </Badge>
                  {!isConnected && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={reconnect}
                      className="ml-2"
                    >
                      <RefreshCw className="h-3 w-3 mr-1" />
                      Reconnecter
                    </Button>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {/* Optional File Type Selector */}
                <div className="mb-4">
                  <Label htmlFor="file-type-select" className="text-sm font-medium text-gray-700">
                    Type de fichier (optionnel)
                  </Label>
                  <Select
                    value={selectedFileType}
                    onValueChange={setSelectedFileType}
                  >
                    <SelectTrigger id="file-type-select" className="w-full mt-1">
                      <SelectValue placeholder="Détection automatique (recommandé)" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="auto">Détection automatique</SelectItem>
                      {availableFileTypes.map((type) => (
                        <SelectItem key={type.value} value={type.value}>
                          {type.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {selectedFileType && selectedFileType !== "auto" && (
                    <p className="text-xs text-gray-500 mt-1">
                      {availableFileTypes.find(t => t.value === selectedFileType)?.description}
                    </p>
                  )}
                </div>

                <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center">
                  <input
                    type="file"
                    accept=".xlsx,.xls,.csv"
                    multiple
                    onChange={handleFileUpload}
                    disabled={uploadFileMutation.isPending}
                    className="hidden"
                    id="file-upload"
                  />
                  <label htmlFor="file-upload" className="cursor-pointer">
                    <div className="text-4xl mb-4">📁</div>
                    <p className="text-lg font-medium mb-2">
                      {uploadFileMutation.isPending || uploadProgress > 0
                        ? "Téléchargement en cours..."
                        : "Cliquez pour sélectionner un ou plusieurs fichiers"}
                    </p>
                    <p className="text-gray-600">
                      Formats supportés: Excel (.xlsx, .xls) et CSV (.csv)
                    </p>
                    {(uploadFileMutation.isPending || uploadProgress > 0) && (
                      <div className="mt-4 space-y-2">
                        <Progress value={uploadProgress} className="w-full" />
                        <p className="text-sm text-blue-600">
                          ⏳ Téléchargement en cours... {uploadProgress}%
                        </p>
                        {uploadProgress === 100 && (
                          <p className="text-sm text-green-600">
                            ✓ Upload terminé avec succès
                          </p>
                        )}
                      </div>
                    )}
                    {!isConnected && (
                      <div
                        className={`mt-4 p-3 border rounded ${
                          connectionStatus === "auth_failed"
                            ? "bg-red-50 border-red-300"
                            : "bg-yellow-50 border-yellow-200"
                        }`}
                      >
                        {connectionStatus === "auth_failed" ? (
                          <>
                            <p className="text-sm font-semibold text-red-700 mb-2">
                              🔐 Échec d'authentification
                            </p>
                            <p className="text-sm text-red-600 mb-2">
                              Votre token de session est invalide. Cela se
                              produit généralement après un redémarrage du
                              serveur.
                            </p>
                            <p className="text-sm text-red-600 font-medium">
                              ⚠️ Sans connexion temps réel, vous ne verrez pas
                              la progression du traitement !
                            </p>
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={() => (window.location.href = "/login")}
                              className="mt-3"
                            >
                              Se reconnecter
                            </Button>
                          </>
                        ) : (
                          <>
                            <p className="text-sm text-yellow-700">
                              ⚠️ Connexion temps réel perdue.
                              {connectionStatus === "error"
                                ? " Erreur de connexion."
                                : " Tentative de reconnexion automatique..."}
                            </p>
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={reconnect}
                              className="mt-2"
                            >
                              <RefreshCw className="h-3 w-3 mr-1" />
                              Reconnecter maintenant
                            </Button>
                          </>
                        )}
                      </div>
                    )}
                  </label>
                </div>
              </CardContent>
            </Card>

            {/* Enhanced File List with Table */}
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>Fichiers téléchargés</CardTitle>
                  {!filesLoading && files.length > 0 && (
                    <div className="text-sm text-gray-600">
                      {files.length} fichier{files.length > 1 ? "s" : ""}
                      {filesData?.data?.total && filesData.data.total > files.length && (
                        <span className="text-gray-500"> sur {filesData.data.total}</span>
                      )}
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {filesLoading ? (
                  <div className="space-y-4">
                    {Array.from({ length: 3 }).map((_, i) => (
                      <div key={i} className="flex items-center space-x-4">
                        <Skeleton className="h-12 w-12 rounded" />
                        <div className="space-y-2 flex-1">
                          <Skeleton className="h-4 w-3/4" />
                          <Skeleton className="h-4 w-1/2" />
                        </div>
                        <Skeleton className="h-8 w-20" />
                      </div>
                    ))}
                  </div>
                ) : files.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p>Aucun fichier téléchargé</p>
                    <p className="text-sm">
                      Commencez par télécharger un fichier
                    </p>
                  </div>
                ) : (
                  <div className="max-h-[600px] overflow-y-auto rounded-md border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Fichier</TableHead>
                          <TableHead>Type</TableHead>
                          <TableHead>Classification</TableHead>
                          <TableHead>Taille</TableHead>
                          <TableHead>Statut</TableHead>
                          <TableHead>Traitement</TableHead>
                          <TableHead>Actions</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {files.map((file) => (
                          <TableRow key={file.id}>
                            <TableCell>
                              <div className="flex items-center space-x-3">
                                <div className="text-2xl">
                                  {getFileTypeIcon(file.file_type)}
                                </div>
                                <div className="min-w-0 flex-1">
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <div className="font-medium truncate">
                                        {truncateFileName(file.original_filename, 20)}
                                      </div>
                                    </TooltipTrigger>
                                    {file.original_filename.length > 20 && (
                                      <TooltipContent>
                                        <p>{file.original_filename}</p>
                                      </TooltipContent>
                                    )}
                                  </Tooltip>
                                  <div className="text-sm text-gray-500">
                                    {formatDate(file.uploaded_at)}
                                  </div>
                                </div>
                              </div>
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline">
                                {file.file_type.toUpperCase()}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <div className="flex flex-col space-y-1 min-w-0">
                                {file.is_manual_classification && file.manual_kpi_type ? (
                                  <>
                                    <div className="flex items-center space-x-1 min-w-0">
                                      <span className="text-xs flex-shrink-0">✋</span>
                                      <Tooltip>
                                        <TooltipTrigger asChild>
                                          <Badge variant="secondary" className="text-xs truncate max-w-full">
                                            {truncateFileName(availableFileTypes.find(t => t.value === file.manual_kpi_type)?.label || file.manual_kpi_type, 20)}
                                          </Badge>
                                        </TooltipTrigger>
                                        {(availableFileTypes.find(t => t.value === file.manual_kpi_type)?.label || file.manual_kpi_type).length > 20 && (
                                          <TooltipContent>
                                            <p>{availableFileTypes.find(t => t.value === file.manual_kpi_type)?.label || file.manual_kpi_type}</p>
                                          </TooltipContent>
                                        )}
                                      </Tooltip>
                                    </div>
                                    <span className="text-[10px] text-gray-500">Manuel</span>
                                  </>
                                ) : file.detected_kpi_type && file.detected_kpi_type !== 'unknown' ? (
                                  <>
                                    <div className="flex items-center space-x-1 min-w-0">
                                      <span className="text-xs flex-shrink-0">🤖</span>
                                      <Tooltip>
                                        <TooltipTrigger asChild>
                                          <Badge
                                            variant="outline"
                                            className={`text-xs truncate max-w-full ${
                                              file.detection_confidence >= 80
                                                ? 'border-green-500 text-green-700'
                                                : file.detection_confidence >= 50
                                                ? 'border-yellow-500 text-yellow-700'
                                                : 'border-red-500 text-red-700'
                                            }`}
                                          >
                                            {truncateFileName(availableFileTypes.find(t => t.value === file.detected_kpi_type)?.label || file.detected_kpi_type, 20)}
                                          </Badge>
                                        </TooltipTrigger>
                                        {(availableFileTypes.find(t => t.value === file.detected_kpi_type)?.label || file.detected_kpi_type).length > 20 && (
                                          <TooltipContent>
                                            <p>{availableFileTypes.find(t => t.value === file.detected_kpi_type)?.label || file.detected_kpi_type}</p>
                                          </TooltipContent>
                                        )}
                                      </Tooltip>
                                    </div>
                                    <span className="text-[10px] text-gray-500">
                                      Auto ({file.detection_confidence || 0}%)
                                    </span>
                                  </>
                                ) : (
                                  <Badge variant="outline" className="text-xs border-gray-300 text-gray-500">
                                    Non classifié
                                  </Badge>
                                )}
                              </div>
                            </TableCell>
                            <TableCell>
                              {formatFileSize(file.file_size)}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center space-x-2">
                                <Badge
                                  className={getStatusColor(
                                    file.processing_status
                                  )}
                                >
                                  {file.processing_status === "completed"
                                    ? "Terminé"
                                    : file.processing_status === "processing"
                                    ? "En cours"
                                    : file.processing_status === "failed"
                                    ? "Échec"
                                    : "En attente"}
                                </Badge>
                                {file.processing_status === "processing" && (
                                  <div className="flex items-center space-x-1">
                                    <div className="animate-spin h-3 w-3 border-2 border-blue-600 border-t-transparent rounded-full"></div>
                                    <span className="text-xs text-blue-600">
                                      Temps réel
                                    </span>
                                  </div>
                                )}
                              </div>
                            </TableCell>
                            <TableCell>
                              {liveProcessingData[file.id] ? (
                                <div className="space-y-2 min-w-[200px]">
                                  <div className="flex items-center justify-between text-xs">
                                    <span className="font-medium">
                                      {liveProcessingData[file.id].status ===
                                      "completed"
                                        ? "✅ Terminé"
                                        : liveProcessingData[file.id].status ===
                                          "failed"
                                        ? "❌ Échec"
                                        : "🔄 En cours..."}
                                    </span>
                                    <span className="font-semibold text-blue-600">
                                      {Math.round(
                                        liveProcessingData[file.id].progress || 0
                                      )}
                                      %
                                    </span>
                                  </div>
                                  <Progress
                                    value={
                                      liveProcessingData[file.id].progress || 0
                                    }
                                    className="h-2"
                                  />
                                  <div className="flex items-center justify-between text-[10px] text-gray-600">
                                    <span>
                                      {liveProcessingData[
                                        file.id
                                      ].saved_rows?.toLocaleString() || 0}{" "}
                                      /{" "}
                                      {liveProcessingData[
                                        file.id
                                      ].total_rows?.toLocaleString() || 0}{" "}
                                      lignes
                                    </span>
                                    {liveProcessingData[file.id].errors > 0 && (
                                      <span className="text-red-600">
                                        {liveProcessingData[file.id].errors}{" "}
                                        erreurs
                                      </span>
                                    )}
                                  </div>
                                </div>
                              ) : processingStatus[file.id] ? (
                                <div className="flex items-center space-x-2">
                                  <Badge className="flex items-center gap-1">
                                    {getProcessingStatusIcon(
                                      processingStatus[file.id]
                                    )}
                                    {processingStatus[file.id] === "completed"
                                      ? "Traité"
                                      : processingStatus[file.id] === "processing"
                                      ? "En cours"
                                      : "Échec"}
                                  </Badge>
                                </div>
                              ) : null}
                            </TableCell>
                            <TableCell>
                              <div className="flex items-center space-x-2">
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      onClick={() => handleStartTreatment(file)}
                                      disabled={isFileProcessing(file) || file.processing_status === "completed"}
                                    >
                                      <Play className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>
                                      {file.processing_status === "completed"
                                        ? "Déjà traité"
                                        : isFileProcessing(file)
                                        ? "Traitement en cours"
                                        : "Démarrer le traitement"}
                                    </p>
                                  </TooltipContent>
                                </Tooltip>

                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      onClick={() => handleFileClick(file)}
                                      disabled={isFileProcessing(file)}
                                    >
                                      <Eye className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Voir les détails</p>
                                  </TooltipContent>
                                </Tooltip>

                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      onClick={() => handlePreviewFile(file.id)}
                                      disabled={isFileProcessing(file)}
                                    >
                                      <FileText className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Aperçu du contenu</p>
                                  </TooltipContent>
                                </Tooltip>

                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="outline"
                                      size="sm"
                                      onClick={() => handleDownloadFile(file.id)}
                                      disabled={isFileProcessing(file)}
                                    >
                                      <Download className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Télécharger</p>
                                  </TooltipContent>
                                </Tooltip>

                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <Button
                                      variant="destructive"
                                      size="sm"
                                      onClick={() => handleDeleteFile(file.id)}
                                      disabled={deleteFileMutation.isPending || isFileProcessing(file)}
                                    >
                                      <Trash2 className="h-4 w-4" />
                                    </Button>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p>Supprimer</p>
                                  </TooltipContent>
                                </Tooltip>
                              </div>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Enhanced Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center">
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
        </div>

        {/* Enhanced File Details Dialog */}
        <Dialog open={showFileDetails} onOpenChange={setShowFileDetails}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Détails du fichier</DialogTitle>
            </DialogHeader>
            {selectedFile && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="block text-sm font-medium text-gray-600">
                      Nom du fichier
                    </Label>
                    <p className="text-gray-900">
                      {selectedFile.original_filename}
                    </p>
                  </div>
                  <div>
                    <Label className="block text-sm font-medium text-gray-600">
                      Type de fichier
                    </Label>
                    <p className="text-gray-900">
                      {selectedFile.file_type.toUpperCase()}
                    </p>
                  </div>
                  <div>
                    <Label className="block text-sm font-medium text-gray-600">
                      Taille
                    </Label>
                    <p className="text-gray-900">
                      {formatFileSize(selectedFile.file_size)}
                    </p>
                  </div>
                  <div>
                    <Label className="block text-sm font-medium text-gray-600">
                      Statut
                    </Label>
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
                    <Label className="block text-sm font-medium text-gray-600">
                      Date de téléchargement
                    </Label>
                    <p className="text-gray-900">
                      {formatDate(selectedFile.uploaded_at)}
                    </p>
                  </div>
                  <div>
                    <Label className="block text-sm font-medium text-gray-600">
                      ID du fichier
                    </Label>
                    <p className="text-gray-900">{selectedFile.id}</p>
                  </div>
                  <div className="col-span-2">
                    <Label className="block text-sm font-medium text-gray-600 mb-2">
                      Classification
                    </Label>
                    {selectedFile.is_manual_classification && selectedFile.manual_kpi_type ? (
                      <div className="flex items-center space-x-2">
                        <span>✋</span>
                        <Badge variant="secondary">
                          {availableFileTypes.find(t => t.value === selectedFile.manual_kpi_type)?.label || selectedFile.manual_kpi_type}
                        </Badge>
                        <span className="text-xs text-gray-500">(Classification manuelle)</span>
                      </div>
                    ) : selectedFile.detected_kpi_type && selectedFile.detected_kpi_type !== 'unknown' ? (
                      <div className="space-y-2">
                        <div className="flex items-center space-x-2">
                          <span>🤖</span>
                          <Badge
                            variant="outline"
                            className={
                              selectedFile.detection_confidence >= 80
                                ? 'border-green-500 text-green-700'
                                : selectedFile.detection_confidence >= 50
                                ? 'border-yellow-500 text-yellow-700'
                                : 'border-red-500 text-red-700'
                            }
                          >
                            {availableFileTypes.find(t => t.value === selectedFile.detected_kpi_type)?.label || selectedFile.detected_kpi_type}
                          </Badge>
                          <span className="text-xs text-gray-500">
                            (Détection automatique - {selectedFile.detection_confidence || 0}% de confiance)
                          </span>
                        </div>
                        {selectedFile.detection_confidence < 80 && (
                          <Alert className="bg-yellow-50 border-yellow-200">
                            <AlertCircle className="h-4 w-4 text-yellow-600" />
                            <AlertDescription className="text-sm text-yellow-700">
                              Confiance faible. Vous pouvez définir manuellement le type de fichier ci-dessous.
                            </AlertDescription>
                          </Alert>
                        )}
                      </div>
                    ) : (
                      <Badge variant="outline" className="border-gray-300 text-gray-500">
                        Non classifié
                      </Badge>
                    )}
                  </div>
                </div>

                {/* Data Processing Status */}
                {processingStatus[selectedFile.id] && (
                  <Alert>
                    <Info className="h-4 w-4" />
                    <AlertDescription>
                      <div className="flex items-center gap-2">
                        {getProcessingStatusIcon(
                          processingStatus[selectedFile.id]
                        )}
                        <span>
                          {processingStatus[selectedFile.id] === "completed"
                            ? "Données traitées avec succès"
                            : processingStatus[selectedFile.id] === "processing"
                            ? "Traitement en cours..."
                            : "Échec du traitement"}
                        </span>
                      </div>
                    </AlertDescription>
                  </Alert>
                )}

                {/* Manual Classification Section */}
                <div className="border-t pt-4">
                  <Label className="block text-sm font-medium text-gray-700 mb-2">
                    Modifier la classification
                  </Label>
                  <div className="flex items-center space-x-2">
                    <Select
                      value={selectedFile.manual_kpi_type || selectedFile.detected_kpi_type || ""}
                      onValueChange={async (value) => {
                        try {
                          await updateFileClassification(selectedFile.id, value);
                          toast.success("Classification mise à jour avec succès");
                          queryClient.invalidateQueries({ queryKey: ["files"] });
                          setShowFileDetails(false);
                        } catch (error) {
                          console.error("Error updating classification:", error);
                          toast.error("Erreur lors de la mise à jour de la classification");
                        }
                      }}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder="Sélectionner un type de fichier" />
                      </SelectTrigger>
                      <SelectContent>
                        {availableFileTypes.map((type) => (
                          <SelectItem key={type.value} value={type.value}>
                            {type.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Sélectionnez un type pour remplacer la classification automatique
                  </p>
                </div>

                {selectedFile.error_message && (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      {selectedFile.error_message}
                    </AlertDescription>
                  </Alert>
                )}

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
            )}
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  );
};

export default FilesPage;
