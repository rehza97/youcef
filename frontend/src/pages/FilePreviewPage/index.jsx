import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { filesAPI } from "../../services/api";
import api from "../../services/api";
import { useAuth } from "../../contexts/AuthContext";
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
import { Skeleton } from "../../components/ui/skeleton";
import { Alert, AlertDescription } from "../../components/ui/alert";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../../components/ui/tabs";
import {
  ArrowLeft,
  Download,
  FileText,
  Search,
  Filter,
  ChevronLeft,
  ChevronRight,
  Eye,
  EyeOff,
  Settings,
  Info,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { toast } from "sonner";

const FilePreviewPage = () => {
  const { fileId } = useParams();
  const navigate = useNavigate();
  const { user, token } = useAuth();

  // State for preview data
  const [previewData, setPreviewData] = useState([]);
  const [filteredData, setFilteredData] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedColumns, setSelectedColumns] = useState([]);
  const [showColumnSelector, setShowColumnSelector] = useState(false);
  const [sortColumn, setSortColumn] = useState("");
  const [sortDirection, setSortDirection] = useState("asc");

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingTask, setProcessingTask] = useState(null);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState("");
  const [processingStats, setProcessingStats] = useState({});
  const [processingErrors, setProcessingErrors] = useState([]);
  const [processingAnomalies, setProcessingAnomalies] = useState([]);

  // WebSocket connection
  const wsRef = useRef(null);
  const [wsConnected, setWsConnected] = useState(false);

  // Saved data state
  const [savedDataPage, setSavedDataPage] = useState(1);
  const [savedDataPageSize] = useState(50);
  const [savedDataSearch, setSavedDataSearch] = useState("");
  const [savedDataFilters, setSavedDataFilters] = useState({
    subscriberStatus: "all",
    telecomType: "all",
    offerType: "all",
  });

  // Fetch file details and previews
  const {
    data: fileData,
    isLoading: fileLoading,
    error: fileError,
  } = useQuery({
    queryKey: ["file", fileId],
    queryFn: () => filesAPI.getFile(fileId),
    enabled: !!fileId,
  });

  // Extract previews from fileData (since the API returns both file data and previews)
  const previews = fileData?.data?.file_previews || [];

  // Fetch saved park data
  const {
    data: savedData,
    isLoading: savedDataLoading,
    error: savedDataError,
    refetch: refetchSavedData,
  } = useQuery({
    queryKey: [
      "savedParkData",
      savedDataPage,
      savedDataPageSize,
      savedDataSearch,
      savedDataFilters,
    ],
    queryFn: () =>
      api.etl.parkData.getSavedData({
        page: savedDataPage,
        pageSize: savedDataPageSize,
        search: savedDataSearch || undefined,
        subscriberStatus:
          savedDataFilters.subscriberStatus === "all"
            ? undefined
            : savedDataFilters.subscriberStatus,
        telecomType:
          savedDataFilters.telecomType === "all"
            ? undefined
            : savedDataFilters.telecomType,
        offerType:
          savedDataFilters.offerType === "all"
            ? undefined
            : savedDataFilters.offerType,
      }),
    enabled: true,
  });

  // Fetch park data statistics
  const { data: parkStats } = useQuery({
    queryKey: ["parkStats"],
    queryFn: () => api.etl.parkData.getStats(),
    enabled: true,
  });

  // Process preview data when it loads
  useEffect(() => {
    if (previews && previews.length > 0) {
      try {
        console.log("🔍 [DEBUG] Processing preview data:", previews[0]);
        const parsedData = JSON.parse(previews[0].preview_data);
        console.log("🔍 [DEBUG] Parsed data:", parsedData);
        setPreviewData(parsedData);
        setFilteredData(parsedData);

        // Initialize with all columns visible
        if (parsedData.length > 0) {
          setSelectedColumns(Object.keys(parsedData[0]));
        }
      } catch (error) {
        console.error("Error parsing preview data:", error);
        console.error("Raw preview_data:", previews[0].preview_data);
        toast.error(
          "Erreur lors du chargement des données de prévisualisation"
        );
      }
    }
  }, [previews]);

  // Filter and search functionality
  useEffect(() => {
    let filtered = [...previewData];

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter((row) =>
        Object.values(row).some((value) =>
          String(value).toLowerCase().includes(searchTerm.toLowerCase())
        )
      );
    }

    // Apply sorting
    if (sortColumn) {
      filtered.sort((a, b) => {
        const aVal = a[sortColumn];
        const bVal = b[sortColumn];

        if (sortDirection === "asc") {
          return aVal > bVal ? 1 : -1;
        } else {
          return aVal < bVal ? 1 : -1;
        }
      });
    }

    setFilteredData(filtered);
    setCurrentPage(1); // Reset to first page when filtering
  }, [previewData, searchTerm, sortColumn, sortDirection]);

  // Pagination
  const totalPages = Math.ceil(filteredData.length / rowsPerPage);
  const startIndex = (currentPage - 1) * rowsPerPage;
  const endIndex = startIndex + rowsPerPage;
  const currentData = filteredData.slice(startIndex, endIndex);

  // Column management
  const allColumns = previewData.length > 0 ? Object.keys(previewData[0]) : [];
  const visibleColumns = selectedColumns.filter((col) =>
    allColumns.includes(col)
  );

  const toggleColumn = (column) => {
    setSelectedColumns((prev) =>
      prev.includes(column)
        ? prev.filter((col) => col !== column)
        : [...prev, column]
    );
  };

  const handleSort = (column) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const formatValue = (value) => {
    if (value === null || value === undefined) return "N/A";
    if (typeof value === "string" && value.length > 100) {
      return value.substring(0, 100) + "...";
    }
    return String(value);
  };

  // Helper function to check if we should show saved data
  const shouldShowSavedData = () => {
    if (savedDataLoading) return false;
    if (savedDataError) return false;
    if (!savedData) return false;
    if (!savedData.data) return false;
    if (!savedData.data.data) return false;
    if (!Array.isArray(savedData.data.data)) return false;
    if (savedData.data.data.length === 0) return false;
    return true;
  };

  // Get all available columns from the first record
  const getAvailableColumns = () => {
    if (!savedData?.data?.data || savedData.data.data.length === 0) return [];
    return Object.keys(savedData.data.data[0]);
  };

  const handleDownload = async () => {
    try {
      const response = await filesAPI.downloadFile(fileId);
      const blob = new Blob([response.data]);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = fileData?.data?.original_filename || "unknown_file";
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      toast.success("Fichier téléchargé avec succès");
    } catch (error) {
      console.error("Download error:", error);
      toast.error("Erreur lors du téléchargement");
    }
  };

  // Processing functions
  const startProcessing = async () => {
    try {
      setIsProcessing(true);
      setProcessingStatus("Starting processing...");

      // Use the proper file processing endpoint via API service
      const result = await filesAPI.processFile(fileId);

      if (result.data && result.data.message) {
        const taskId = result.data.task_id || fileId; // Use task_id if available, fallback to fileId
        setProcessingTask(taskId);
        setProcessingStatus("Processing started");
        toast.success("Traitement démarré en arrière-plan");

        console.log(
          `🆔 Processing started with task_id: ${taskId} for file_id: ${fileId}`
        );

        // Connect to WebSocket for real-time updates using the correct task_id
        connectToProcessingUpdates(taskId);
      } else {
        throw new Error(result.data?.message || "Failed to start processing");
      }
    } catch (error) {
      console.error("Processing error:", error);
      toast.error("Erreur lors du démarrage du traitement");
      setIsProcessing(false);
      setProcessingStatus("Failed to start");
    }
  };

  const connectToProcessingUpdates = (taskId) => {
    try {
      // Use token from AuthContext
      const authToken = token;
      const userId = user?.id || "1";

      if (!authToken) {
        console.error(
          "❌ No authentication token available for WebSocket connection"
        );
        toast.error(
          "Token d'authentification manquant. Veuillez vous reconnecter."
        );
        return;
      }

      // Check if token might be expired (basic check)
      try {
        const tokenPayload = JSON.parse(atob(authToken.split(".")[1]));
        const currentTime = Math.floor(Date.now() / 1000);
        if (tokenPayload.exp && tokenPayload.exp < currentTime) {
          console.error("❌ Token appears to be expired");
          toast.error("Session expirée. Veuillez vous reconnecter.");
          return;
        }
      } catch (e) {
        console.warn("⚠️ Could not parse token for expiration check:", e);
      }

      console.log(
        `🔌 Connecting to WebSocket for task: ${taskId}, user: ${userId}`
      );
      const wsUrl = `ws://localhost:8000/ws/processing/?user_id=${userId}&token=${authToken}`;
      console.log(`🔗 WebSocket URL: ${wsUrl}`);

      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log("✅ Connected to processing WebSocket");
        setWsConnected(true);

        // Subscribe to task updates
        const subscribeMessage = {
          type: "subscribe_task",
          task_id: taskId,
        };
        console.log("📤 Sending subscription message:", subscribeMessage);
        wsRef.current.send(JSON.stringify(subscribeMessage));
      };

      wsRef.current.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          console.log("📨 Processing update received:", message);

          if (message.type === "processing_update") {
            const data = message.data;
            console.log("📊 Processing data:", data);

            setProcessingProgress(data.progress || 0);
            setProcessingStatus(data.message || data.status || "");
            setProcessingStats(data.statistics || {});
            setProcessingErrors(data.errors || []);
            setProcessingAnomalies(data.anomalies || []);

            if (data.status === "completed") {
              setIsProcessing(false);
              toast.success("Traitement terminé avec succès");
            } else if (data.status === "failed") {
              setIsProcessing(false);
              toast.error("Traitement échoué");
            }
          } else if (message.type === "connection") {
            console.log("🔗 WebSocket connection confirmed:", message);
          }
        } catch (error) {
          console.error("❌ Error parsing WebSocket message:", error);
          console.error("Raw message:", event.data);
        }
      };

      wsRef.current.onclose = (event) => {
        console.log(
          "🔌 Disconnected from processing WebSocket",
          event.code,
          event.reason
        );
        setWsConnected(false);
      };

      wsRef.current.onerror = (error) => {
        console.error("❌ Processing WebSocket error:", error);
        setWsConnected(false);
      };
    } catch (error) {
      console.error("Error connecting to WebSocket:", error);
    }
  };

  const cancelProcessing = async () => {
    if (processingTask) {
      try {
        const result = await filesAPI.cancelProcessing(processingTask);

        if (result.data && result.data.message) {
          setIsProcessing(false);
          setProcessingStatus("Cancelled");
          toast.info("Traitement annulé");
        }
      } catch (error) {
        console.error("Error cancelling processing:", error);
        toast.error("Erreur lors de l'annulation");
      }
    }
  };

  // Cleanup WebSocket on unmount
  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  if (fileLoading) {
    return (
      <div className="container mx-auto p-6">
        <div className="space-y-6">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  if (fileError) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Erreur lors du chargement des données: {fileError?.message}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  if (!fileData) {
    return (
      <div className="container mx-auto p-6">
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            Aucune donnée de prévisualisation disponible pour ce fichier.
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  const preview = previews && previews.length > 0 ? previews[0] : null;

  // Debug logging to help identify the issue
  console.log("🔍 [DEBUG] FilePreviewPage - fileData:", fileData);
  console.log("🔍 [DEBUG] FilePreviewPage - previews:", previews);
  console.log("🔍 [DEBUG] FilePreviewPage - preview:", preview);

  // Get total rows and columns with fallback
  const totalRows =
    preview?.total_rows ||
    (previews && previews.length > 0 ? previews[0]?.total_rows : 0);
  const totalColumns =
    preview?.total_columns ||
    (previews && previews.length > 0 ? previews[0]?.total_columns : 0);

  return (
    <TooltipProvider>
      <div className="container mx-auto p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Button
              variant="outline"
              size="sm"
              onClick={() => navigate("/files")}
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Retour
            </Button>
            <div>
              <h1 className="text-2xl font-bold">Aperçu du fichier</h1>
              <p className="text-gray-600">
                {fileData?.data?.original_filename || "Unknown file"}
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="outline">
              <FileText className="h-3 w-3 mr-1" />
              {fileData?.data?.file_type?.toUpperCase() || "UNKNOWN"}
            </Badge>
            <Button onClick={handleDownload} disabled={isProcessing}>
              <Download className="h-4 w-4 mr-2" />
              Télécharger
            </Button>
            {!isProcessing ? (
              <Button onClick={startProcessing} variant="default">
                <Settings className="h-4 w-4 mr-2" />
                Traiter le fichier
              </Button>
            ) : (
              <Button onClick={cancelProcessing} variant="destructive">
                <AlertCircle className="h-4 w-4 mr-2" />
                Annuler
              </Button>
            )}
          </div>
        </div>

        {/* File Info */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Info className="h-5 w-5 mr-2" />
              Informations du fichier
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <Label className="text-sm font-medium text-gray-600">
                  Taille
                </Label>
                <p className="text-lg font-semibold">
                  {fileData?.data?.file_size
                    ? (fileData.data.file_size / 1024 / 1024).toFixed(2)
                    : "0.00"}{" "}
                  MB
                </p>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-600">
                  Lignes totales
                </Label>
                <p className="text-lg font-semibold">
                  {totalRows?.toLocaleString() || "0"}
                </p>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-600">
                  Colonnes
                </Label>
                <p className="text-lg font-semibold">{totalColumns || "0"}</p>
              </div>
              <div>
                <Label className="text-sm font-medium text-gray-600">
                  Statut
                </Label>
                <Badge
                  className={
                    fileData?.data?.processing_status === "completed"
                      ? "bg-green-100 text-green-800"
                      : fileData?.data?.processing_status === "processing"
                      ? "bg-yellow-100 text-yellow-800"
                      : "bg-gray-100 text-gray-800"
                  }
                >
                  {fileData?.data?.processing_status === "completed"
                    ? "Terminé"
                    : fileData?.data?.processing_status === "processing"
                    ? "En cours"
                    : fileData?.data?.processing_status || "En attente"}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Processing Status */}
        {isProcessing && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Settings className="h-5 w-5 mr-2" />
                Traitement en cours
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Progress Bar */}
                <div>
                  <div className="flex justify-between text-sm mb-2">
                    <span>Progression</span>
                    <span>{processingProgress.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${processingProgress}%` }}
                    ></div>
                  </div>
                </div>

                {/* Status */}
                <div className="flex items-center space-x-2">
                  <Badge variant={wsConnected ? "default" : "secondary"}>
                    {wsConnected ? "Connecté" : "Déconnecté"}
                  </Badge>
                  <span className="text-sm text-gray-600">
                    {processingStatus}
                  </span>
                </div>

                {/* Statistics */}
                {Object.keys(processingStats).length > 0 && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <Label className="text-sm font-medium text-gray-600">
                        Lignes traitées
                      </Label>
                      <p className="text-lg font-semibold">
                        {processingStats.total_records || 0}
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-600">
                        Lignes filtrées
                      </Label>
                      <p className="text-lg font-semibold text-orange-600">
                        {processingStats.filtered_rows || 0}
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-600">
                        Anomalies
                      </Label>
                      <p className="text-lg font-semibold text-red-600">
                        {processingAnomalies.length}
                      </p>
                    </div>
                    <div>
                      <Label className="text-sm font-medium text-gray-600">
                        Erreurs
                      </Label>
                      <p className="text-lg font-semibold text-red-600">
                        {processingErrors.length}
                      </p>
                    </div>
                  </div>
                )}

                {/* Anomalies */}
                {processingAnomalies.length > 0 && (
                  <div>
                    <Label className="text-sm font-medium text-gray-600 mb-2 block">
                      Anomalies détectées
                    </Label>
                    <div className="max-h-32 overflow-y-auto space-y-1">
                      {processingAnomalies.slice(0, 5).map((anomaly, index) => (
                        <div
                          key={index}
                          className="text-xs bg-yellow-50 p-2 rounded border"
                        >
                          <strong>{anomaly.type}:</strong> {anomaly.description}
                        </div>
                      ))}
                      {processingAnomalies.length > 5 && (
                        <div className="text-xs text-gray-500">
                          ... et {processingAnomalies.length - 5} autres
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Controls */}
        <Card>
          <CardContent className="pt-6">
            <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between">
              <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
                {/* Search */}
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <Input
                    placeholder="Rechercher dans les données..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="pl-10 w-64"
                  />
                </div>

                {/* Rows per page */}
                <div className="flex items-center space-x-2">
                  <Label className="text-sm">Lignes par page:</Label>
                  <Select
                    value={rowsPerPage.toString()}
                    onValueChange={(value) => setRowsPerPage(parseInt(value))}
                  >
                    <SelectTrigger className="w-20">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="25">25</SelectItem>
                      <SelectItem value="50">50</SelectItem>
                      <SelectItem value="100">100</SelectItem>
                      <SelectItem value="200">200</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Column selector */}
              <Button
                variant="outline"
                onClick={() => setShowColumnSelector(true)}
              >
                <Settings className="h-4 w-4 mr-2" />
                Colonnes ({visibleColumns.length}/{allColumns.length})
              </Button>
            </div>

            {/* Results info */}
            <div className="mt-4 text-sm text-gray-600">
              Affichage de {startIndex + 1} à{" "}
              {Math.min(endIndex, filteredData.length)} sur{" "}
              {filteredData.length.toLocaleString()} lignes
              {searchTerm &&
                ` (filtrées sur ${previewData.length.toLocaleString()} total)`}
            </div>
          </CardContent>
        </Card>

        {/* Data Tabs */}
        <Tabs defaultValue="preview" className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="preview">Aperçu du fichier</TabsTrigger>
            <TabsTrigger value="saved">Données sauvegardées</TabsTrigger>
          </TabsList>

          <TabsContent value="preview" className="space-y-4">
            <Card>
              <CardContent className="p-0">
                {previewData.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p>Aucune donnée de prévisualisation disponible</p>
                    <p className="text-sm mt-2">
                      Le fichier est en cours de traitement ou n'a pas encore
                      été analysé.
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          {visibleColumns.map((column) => (
                            <TableHead
                              key={column}
                              className="cursor-pointer hover:bg-gray-50 select-none"
                              onClick={() => handleSort(column)}
                            >
                              <div className="flex items-center space-x-1">
                                <span>{column}</span>
                                {sortColumn === column && (
                                  <span className="text-blue-600">
                                    {sortDirection === "asc" ? "↑" : "↓"}
                                  </span>
                                )}
                              </div>
                            </TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {currentData.map((row, rowIndex) => (
                          <TableRow key={startIndex + rowIndex}>
                            {visibleColumns.map((column, colIndex) => (
                              <TableCell key={colIndex} className="max-w-xs">
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    <div className="truncate">
                                      {formatValue(row[column])}
                                    </div>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    <p className="max-w-xs break-words">
                                      {String(row[column])}
                                    </p>
                                  </TooltipContent>
                                </Tooltip>
                              </TableCell>
                            ))}
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="saved" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center justify-between">
                  <span>Données sauvegardées</span>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => refetchSavedData()}
                      disabled={savedDataLoading}
                    >
                      <RefreshCw className="h-4 w-4 mr-2" />
                      Actualiser
                    </Button>
                  </div>
                </CardTitle>
              </CardHeader>
              <CardContent>
                {/* Statistics */}
                {parkStats && (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {parkStats.total_records?.toLocaleString() || 0}
                      </div>
                      <div className="text-sm text-gray-600">
                        Total enregistrements
                      </div>
                    </div>
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {parkStats.recent_records?.toLocaleString() || 0}
                      </div>
                      <div className="text-sm text-gray-600">Récents (24h)</div>
                    </div>
                    <div className="text-center p-4 bg-purple-50 rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">
                        {parkStats.subscriber_statuses?.length || 0}
                      </div>
                      <div className="text-sm text-gray-600">
                        Statuts uniques
                      </div>
                    </div>
                    <div className="text-center p-4 bg-orange-50 rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">
                        {parkStats.telecom_types?.length || 0}
                      </div>
                      <div className="text-sm text-gray-600">Types télécom</div>
                    </div>
                  </div>
                )}

                {/* Filters */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                  <div>
                    <Label htmlFor="search">Rechercher</Label>
                    <Input
                      id="search"
                      placeholder="Code client, numéro service..."
                      value={savedDataSearch}
                      onChange={(e) => setSavedDataSearch(e.target.value)}
                    />
                  </div>
                  <div>
                    <Label htmlFor="status">Statut abonné</Label>
                    <Select
                      value={savedDataFilters.subscriberStatus}
                      onValueChange={(value) =>
                        setSavedDataFilters((prev) => ({
                          ...prev,
                          subscriberStatus: value,
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Tous les statuts" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Tous les statuts</SelectItem>
                        {parkStats?.subscriber_statuses?.map((status) => (
                          <SelectItem key={status} value={status}>
                            {status}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="telecom">Type télécom</Label>
                    <Select
                      value={savedDataFilters.telecomType}
                      onValueChange={(value) =>
                        setSavedDataFilters((prev) => ({
                          ...prev,
                          telecomType: value,
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Tous les types" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Tous les types</SelectItem>
                        {parkStats?.telecom_types?.map((type) => (
                          <SelectItem key={type} value={type}>
                            {type}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label htmlFor="offer">Type d'offre</Label>
                    <Select
                      value={savedDataFilters.offerType}
                      onValueChange={(value) =>
                        setSavedDataFilters((prev) => ({
                          ...prev,
                          offerType: value,
                        }))
                      }
                    >
                      <SelectTrigger>
                        <SelectValue placeholder="Tous les types" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">Tous les types</SelectItem>
                        {parkStats?.offer_types?.map((type) => (
                          <SelectItem key={type} value={type}>
                            {type}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* Data Table */}
                {savedDataLoading ? (
                  <div className="space-y-4">
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-64 w-full" />
                  </div>
                ) : savedDataError ? (
                  <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                      Erreur lors du chargement des données:{" "}
                      {savedDataError.message}
                    </AlertDescription>
                  </Alert>
                ) : !shouldShowSavedData() ? (
                  <div className="p-8 text-center text-gray-500">
                    <FileText className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p>Aucune donnée sauvegardée trouvée</p>
                    <p className="text-sm mt-2">
                      Traitez un fichier pour voir les données sauvegardées ici.
                    </p>
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          {getAvailableColumns().map((column) => (
                            <TableHead key={column} className="min-w-[120px]">
                              {column}
                            </TableHead>
                          ))}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {Array.isArray(savedData?.data?.data) &&
                          savedData.data.data.map((record, index) => (
                            <TableRow key={record.id || index}>
                              {getAvailableColumns().map((column) => (
                                <TableCell
                                  key={column}
                                  className="max-w-xs truncate text-sm"
                                >
                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <div className="truncate">
                                        {formatValue(record[column])}
                                      </div>
                                    </TooltipTrigger>
                                    <TooltipContent>
                                      <p className="max-w-xs break-words">
                                        {String(record[column] || "N/A")}
                                      </p>
                                    </TooltipContent>
                                  </Tooltip>
                                </TableCell>
                              ))}
                            </TableRow>
                          ))}
                      </TableBody>
                    </Table>
                  </div>
                )}

                {/* Pagination */}
                {savedData?.data && savedData.data.total_pages > 1 && (
                  <div className="flex items-center justify-between mt-6">
                    <div className="text-sm text-gray-600">
                      Page {savedData.data.page} sur{" "}
                      {savedData.data.total_pages}(
                      {savedData.data.total.toLocaleString()} enregistrements)
                    </div>
                    <div className="flex items-center space-x-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setSavedDataPage(Math.max(1, savedDataPage - 1))
                        }
                        disabled={savedDataPage === 1}
                      >
                        <ChevronLeft className="h-4 w-4" />
                        Précédent
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setSavedDataPage(
                            Math.min(
                              savedData.data.total_pages,
                              savedDataPage + 1
                            )
                          )
                        }
                        disabled={savedDataPage === savedData.data.total_pages}
                      >
                        Suivant
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Pagination */}
        {totalPages > 1 && (
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  Page {currentPage} sur {totalPages}
                </div>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Précédent
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setCurrentPage(Math.min(totalPages, currentPage + 1))
                    }
                    disabled={currentPage === totalPages}
                  >
                    Suivant
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Column Selector Dialog */}
        <Dialog open={showColumnSelector} onOpenChange={setShowColumnSelector}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Sélectionner les colonnes à afficher</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedColumns(allColumns)}
                >
                  Tout sélectionner
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedColumns([])}
                >
                  Tout désélectionner
                </Button>
              </div>
              <div className="grid grid-cols-2 gap-2 max-h-96 overflow-y-auto">
                {allColumns.map((column) => (
                  <div
                    key={column}
                    className="flex items-center space-x-2 p-2 rounded border"
                  >
                    <input
                      type="checkbox"
                      id={column}
                      checked={selectedColumns.includes(column)}
                      onChange={() => toggleColumn(column)}
                      className="rounded"
                    />
                    <label
                      htmlFor={column}
                      className="text-sm cursor-pointer flex-1 truncate"
                    >
                      {column}
                    </label>
                  </div>
                ))}
              </div>
              <div className="flex justify-end space-x-2">
                <Button
                  variant="outline"
                  onClick={() => setShowColumnSelector(false)}
                >
                  Fermer
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </TooltipProvider>
  );
};

export default FilePreviewPage;
