import React, { useState, useEffect, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  getFile,
  processFile,
  downloadFile,
  getParkDataSavedData,
  getParkDataStats,
  getOrGenerateFilePreview,
  getRevenueObjectives,
  getAccountDescriptions,
  getRevenueJournals,
  getEncaissementRecords,
  getCreanceRecords,
} from "../../services/api";
import { useProcessing } from "../../contexts/ProcessingContext";
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
  const { subscribeTask, isConnected, activeTasks } = useProcessing();

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
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState("");

  // WebSocket connection info
  const connectionInfo = useProcessing().getConnectionInfo?.() || {};

  // Saved data state
  const [savedDataPage, setSavedDataPage] = useState(1);
  const [savedDataPageSize, setSavedDataPageSize] = useState(50);
  const [savedDataSearch, setSavedDataSearch] = useState("");
  const [savedDataFilters, setSavedDataFilters] = useState({
    subscriberStatus: "all",
    telecomType: "all",
    offerType: "all",
  });

  // Fetch file details
  const {
    data: fileData,
    isLoading: fileLoading,
    error: fileError,
    refetch: refetchFile,
  } = useQuery({
    queryKey: ["file", fileId],
    queryFn: () => getFile(fileId),
    enabled: !!fileId,
  });

  // Fetch/generate previews separately
  const {
    data: previewResponse,
    isLoading: previewLoading,
    error: previewError,
  } = useQuery({
    queryKey: ["filePreview", fileId],
    queryFn: () => getOrGenerateFilePreview(fileId, 50),
    enabled: !!fileId,
  });

  // Extract previews from previewResponse
  const previews = useMemo(
    () => previewResponse?.data?.data || [],
    [previewResponse?.data?.data]
  );

  // Detect file type using useMemo to avoid issues with undefined fileData
  const fileType = useMemo(() => {
    return fileData?.data?.detected_kpi_type || fileData?.data?.file_type || "";
  }, [fileData?.data?.detected_kpi_type, fileData?.data?.file_type]);
  
  const isRevenueObjectiveFile = useMemo(() => {
    return fileType === "chiffre_affaires_objective" || fileType === "revenue_objectives";
  }, [fileType]);
  
  const isAccountDescriptionFile = useMemo(() => {
    return fileType === "chiffre_affaires_account_desc" || fileType === "account_descriptions";
  }, [fileType]);
  
  const isRevenueJournalFile = useMemo(() => {
    return fileType === "chiffre_affaires" || fileType === "revenue_journal";
  }, [fileType]);
  
  const isEncaissementArDotFile = useMemo(() => {
    return fileType === "encaissement_ar_dot" || fileType === "encaissement";
  }, [fileType]);
  
  const isCreancePeriodiqueDotFile = useMemo(() => {
    return fileType === "creance_periodique_dot" || fileType === "creance_periodique";
  }, [fileType]);
  
  const isParkFile = useMemo(() => {
    return fileType === "parc_corporate_ngbss" || fileType === "park";
  }, [fileType]);

  // Fetch saved data based on file type
  const {
    data: savedData,
    isLoading: savedDataLoading,
    error: savedDataError,
    refetch: refetchSavedData,
  } = useQuery({
    queryKey: [
      isRevenueObjectiveFile ? "revenueObjectives" : isAccountDescriptionFile ? "accountDescriptions" : isRevenueJournalFile ? "revenueJournals" : isEncaissementArDotFile ? "encaissementRecords" : isCreancePeriodiqueDotFile ? "creanceRecords" : "savedParkData",
      savedDataPage,
      savedDataPageSize,
      savedDataSearch,
      savedDataFilters,
      fileId,
      fileType,
    ],
    queryFn: () => {
      if (isRevenueObjectiveFile) {
        // Fetch revenue objectives filtered by file_upload_id
        return getRevenueObjectives({
          dot_name: savedDataSearch || undefined,
          file_upload_id: fileId ? parseInt(fileId) : undefined,
        }).then((response) => {
          // Transform to match expected format
          const objectives = response.data || [];
          return {
            data: {
              data: objectives,
              total: objectives.length,
              page: 1,
              page_size: objectives.length,
              total_pages: 1,
            },
          };
        });
      } else if (isAccountDescriptionFile) {
        // Fetch account descriptions filtered by file_upload_id
        return getAccountDescriptions({
          cpt_comptable: savedDataSearch || undefined,
          file_upload_id: fileId ? parseInt(fileId) : undefined,
        }).then((response) => {
          // Transform to match expected format
          const accounts = response.data || [];
          return {
            data: {
              data: accounts,
              total: accounts.length,
              page: 1,
              page_size: accounts.length,
              total_pages: 1,
            },
          };
        });
      } else if (isRevenueJournalFile) {
        // Fetch revenue journals filtered by file_upload_id
        return getRevenueJournals({
          org_name: savedDataSearch || undefined,
          file_upload_id: fileId ? parseInt(fileId) : undefined,
          page: savedDataPage,
          page_size: savedDataPageSize,
        }).then((response) => {
          // Transform to match expected format
          const journals = response.data?.data || response.data || [];
          const total = response.data?.total || journals.length;
          const page = response.data?.page || savedDataPage;
          const page_size = response.data?.page_size || savedDataPageSize;
          const total_pages = response.data?.total_pages || Math.ceil(total / page_size);
          return {
            data: {
              data: journals,
              total: total,
              page: page,
              page_size: page_size,
              total_pages: total_pages,
            },
          };
        });
      } else if (isEncaissementArDotFile) {
        // Fetch encaissement AR DOT records filtered by file_upload_id
        return getEncaissementRecords({
          organisation: savedDataSearch || undefined,
          file_upload_id: fileId ? parseInt(fileId) : undefined,
          page: savedDataPage,
          page_size: savedDataPageSize,
        }).then((response) => {
          // Transform to match expected format
          const records = response.data?.items || response.data || [];
          const total = response.data?.total || records.length;
          const page = response.data?.page || savedDataPage;
          const page_size = response.data?.page_size || savedDataPageSize;
          const total_pages = response.data?.total_pages || Math.ceil(total / page_size);
          return {
            data: {
              data: records,
              total: total,
              page: page,
              page_size: page_size,
              total_pages: total_pages,
            },
          };
        });
      } else if (isCreancePeriodiqueDotFile) {
        // Fetch créance périodique DOT records filtered by file_upload_id
        return getCreanceRecords({
          dot: savedDataSearch || undefined,
          file_upload_id: fileId ? parseInt(fileId) : undefined,
          page: savedDataPage,
          page_size: savedDataPageSize,
        }).then((response) => {
          // Transform to match expected format
          const records = response.data?.items || response.data || [];
          const total = response.data?.total || records.length;
          const page = response.data?.page || savedDataPage;
          const page_size = response.data?.page_size || savedDataPageSize;
          const total_pages = response.data?.total_pages || Math.ceil(total / page_size);
          return {
            data: {
              data: records,
              total: total,
              page: page,
              page_size: page_size,
              total_pages: total_pages,
            },
          };
        });
      } else {
        // Fetch park data (default)
        return getParkDataSavedData({
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
        });
      }
    },
    enabled: !!fileId && !!fileData?.data,
  });

  // Fetch park data statistics (only for park files)
  const { data: parkStats, refetch: refetchStats } = useQuery({
    queryKey: ["parkStats"],
    queryFn: () => getParkDataStats(),
    enabled: isParkFile && !!fileData?.data,
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

  // Auto-subscribe to any existing active task for this file
  useEffect(() => {
    if (!fileId || !isConnected) return;

    // Check if there's an active task for this file
    const activeTask = activeTasks.find(
      (task) => task.file_id === parseInt(fileId)
    );

    if (activeTask && !isProcessing) {
      console.log(
        `🔄 Auto-subscribing to existing active task: ${activeTask.task_id} for file ${fileId}`
      );
      setIsProcessing(true);
      setProcessingStatus(activeTask.message || "Traitement en cours...");
      setProcessingProgress(activeTask.progress || 0);

      const unsubscribe = subscribeTask(activeTask.task_id, (message) => {
        try {
          if (message?.task_id !== activeTask.task_id) return;
          if (message.type === "processing_update") {
            const { data } = message;
            if (data) {
              setProcessingProgress(data.progress || 0);
              setProcessingStatus(data.message || "Traitement en cours...");

              if (data.status === "completed") {
                setIsProcessing(false);
                setProcessingProgress(100);
                setProcessingStatus("Traitement terminé");
                toast.success("Fichier traité avec succès!");
                refetchSavedData();
                unsubscribe();
              } else if (data.status === "failed") {
                setIsProcessing(false);
                setProcessingStatus("Échec du traitement");
                toast.error(`Erreur: ${data.message || "Traitement échoué"}`);
                unsubscribe();
              } else if (data.status === "cancelled") {
                setIsProcessing(false);
                setProcessingStatus("Traitement annulé");
                toast.info("Traitement annulé");
                unsubscribe();
              }
            }
          }
        } catch (error) {
          console.error("Error handling processing update:", error);
        }
      });

      return unsubscribe;
    }
  }, [
    fileId,
    isConnected,
    activeTasks,
    isProcessing,
    subscribeTask,
    refetchSavedData,
  ]);

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
    
    if (isRevenueObjectiveFile) {
      // For revenue objectives, show specific columns
      return ["dot_name", "objectif_ca"];
    } else if (isAccountDescriptionFile) {
      // For account descriptions, show all columns
      return ["cpt_comptable", "description_cpt_comptable", "type_cpte", "aut_bdg", "aut_imp", "auxil", "let"];
    } else if (isRevenueJournalFile) {
      // For revenue journals, show key columns
      return [
        "org_name", 
        "n_fact", 
        "typ_fact", 
        "date_fact", 
        "client", 
        "cpt_comptable", 
        "date_gl", 
        "mnt_ht", 
        "mnt_ttc", 
        "chiffre_aff_exe_dzd",
        "tva",
        "taux_realisation_ca"
      ];
    } else if (isEncaissementArDotFile) {
      // For encaissement AR DOT, show key columns
      return [
        "organisation",
        "source",
        "n_fact",
        "typ_fact",
        "date_fact",
        "client",
        "montant_ht",
        "montant_ttc",
        "encaissement",
        "taux_encaissement",
        "montant_restant",
        "date_rglt",
        "n_rglt"
      ];
    } else if (isCreancePeriodiqueDotFile) {
      // For créance périodique DOT, show key columns
      return [
        "dot",
        "actel",
        "mois",
        "annee",
        "period_key",
        "subs_status",
        "produit",
        "cust_lev1",
        "cust_lev2",
        "cust_lev3",
        "invoice_amt",
        "open_amt",
        "creance_brut",
        "creance_net",
        "creance_ht"
      ];
    }
    
    // For park data, show all columns
    return Object.keys(savedData.data.data[0]);
  };

  const handleDownload = async () => {
    try {
      const response = await downloadFile(fileId);
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
      const result = await processFile(fileId);
      const taskId = result?.data?.task_id || String(fileId);

      const unsubscribe = subscribeTask(taskId, (message) => {
        try {
          if (message?.task_id !== taskId) return;
          if (message.type === "processing_update") {
            setProcessingProgress(message.data?.progress ?? 0);
            setProcessingStatus(message.data?.status || "processing");
          } else if (message.type === "completed") {
            setProcessingStatus("completed");
            setIsProcessing(false);
            refetchFile();
            refetchStats();
            unsubscribe && unsubscribe();
          } else if (message.type === "failed") {
            setProcessingStatus("failed");
            setIsProcessing(false);
            unsubscribe && unsubscribe();
          }
        } catch (e) {
          console.error("Error handling processing message:", e);
        }
      });
    } catch (e) {
      console.error("Error starting processing:", e);
      setIsProcessing(false);
    }
  };

  const cancelProcessing = async () => {
    toast.info("Annulation du traitement non disponible pour le moment");
  };

  // Removed local WebSocket cleanup; global provider manages lifecycle

  if (fileLoading || previewLoading) {
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

  if (fileError || previewError) {
    return (
      <div className="container mx-auto p-6">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>
            Erreur lors du chargement des données:{" "}
            {fileError?.message || previewError?.message}
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
            {/* WebSocket Connection Status */}
            <Badge
              variant={connectionInfo.isConnected ? "default" : "destructive"}
              className="flex items-center"
            >
              <div
                className={`w-2 h-2 rounded-full mr-1 ${
                  connectionInfo.isConnected ? "bg-green-400" : "bg-red-400"
                }`}
              />
              {connectionInfo.isConnected ? "Connecté" : "Déconnecté"}
            </Badge>

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
                  <Badge variant={isConnected ? "default" : "secondary"}>
                    {isConnected ? "Connecté" : "Déconnecté"}
                  </Badge>
                  <span className="text-sm text-gray-600">
                    {processingStatus}
                  </span>
                </div>

                {/* Statistics placeholder (can be re-enabled when server provides them routinely) */}
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
                {isRevenueObjectiveFile && savedData?.data?.data ? (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {savedData.data.data.length || 0}
                      </div>
                      <div className="text-sm text-gray-600">
                        Total objectifs
                      </div>
                    </div>
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {savedData.data.data.reduce((sum, obj) => sum + (parseFloat(obj.objectif_ca) || 0), 0).toLocaleString('fr-FR') || 0}
                      </div>
                      <div className="text-sm text-gray-600">Objectif total (DZD)</div>
                    </div>
                    <div className="text-center p-4 bg-purple-50 rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">
                        {savedData.data.data.filter(obj => obj.dot_id).length || 0}
                      </div>
                      <div className="text-sm text-gray-600">
                        DOTs associés
                      </div>
                    </div>
                    <div className="text-center p-4 bg-orange-50 rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">
                        {savedData.data.data.length > 0 
                          ? Math.round(savedData.data.data.reduce((sum, obj) => sum + (parseFloat(obj.objectif_ca) || 0), 0) / savedData.data.data.length).toLocaleString('fr-FR')
                          : 0}
                      </div>
                      <div className="text-sm text-gray-600">Moyenne (DZD)</div>
                    </div>
                  </div>
                ) : isAccountDescriptionFile && savedData?.data?.data ? (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {savedData.data.data.length || 0}
                      </div>
                      <div className="text-sm text-gray-600">
                        Total comptes
                      </div>
                    </div>
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {new Set(savedData.data.data.map(acc => acc.type_cpte).filter(Boolean)).size || 0}
                      </div>
                      <div className="text-sm text-gray-600">Types de comptes</div>
                    </div>
                    <div className="text-center p-4 bg-purple-50 rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">
                        {savedData.data.data.filter(acc => acc.description_cpt_comptable).length || 0}
                      </div>
                      <div className="text-sm text-gray-600">
                        Comptes avec description
                      </div>
                    </div>
                    <div className="text-center p-4 bg-orange-50 rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">
                        {new Set(savedData.data.data.map(acc => acc.aut_bdg).filter(Boolean)).size || 0}
                      </div>
                      <div className="text-sm text-gray-600">Autorités budget</div>
                    </div>
                  </div>
                ) : isRevenueJournalFile && savedData?.data?.data ? (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {savedData.data.total || 0}
                      </div>
                      <div className="text-sm text-gray-600">Total enregistrements</div>
                    </div>
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {new Intl.NumberFormat('fr-FR', {
                          style: 'decimal',
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2
                        }).format(
                          savedData.data.data.reduce((sum, record) => 
                            sum + (parseFloat(record.chiffre_aff_exe_dzd) || 0), 0
                          )
                        )}
                      </div>
                      <div className="text-sm text-gray-600">Chiffre d'affaires total (DZD)</div>
                    </div>
                    <div className="text-center p-4 bg-purple-50 rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">
                        {new Set(savedData.data.data.map(record => record.org_name).filter(Boolean)).size || 0}
                      </div>
                      <div className="text-sm text-gray-600">Organisations</div>
                    </div>
                    <div className="text-center p-4 bg-orange-50 rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">
                        {new Set(savedData.data.data.map(record => record.n_fact).filter(Boolean)).size || 0}
                      </div>
                      <div className="text-sm text-gray-600">Factures uniques</div>
                    </div>
                  </div>
                ) : isEncaissementArDotFile && savedData?.data?.data ? (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {savedData.data.total || 0}
                      </div>
                      <div className="text-sm text-gray-600">Total enregistrements</div>
                    </div>
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {new Intl.NumberFormat('fr-FR', {
                          style: 'decimal',
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2
                        }).format(
                          savedData.data.data.reduce((sum, record) => 
                            sum + (parseFloat(record.montant_ttc) || 0), 0
                          )
                        )}
                      </div>
                      <div className="text-sm text-gray-600">Montant TTC total (DZD)</div>
                    </div>
                    <div className="text-center p-4 bg-purple-50 rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">
                        {new Intl.NumberFormat('fr-FR', {
                          style: 'decimal',
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2
                        }).format(
                          savedData.data.data.reduce((sum, record) => 
                            sum + (parseFloat(record.encaissement) || 0), 0
                          )
                        )}
                      </div>
                      <div className="text-sm text-gray-600">Encaissement total (DZD)</div>
                    </div>
                    <div className="text-center p-4 bg-orange-50 rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">
                        {new Set(savedData.data.data.map(record => record.organisation).filter(Boolean)).size || 0}
                      </div>
                      <div className="text-sm text-gray-600">Organisations</div>
                    </div>
                  </div>
                ) : isCreancePeriodiqueDotFile && savedData?.data?.data ? (
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                    <div className="text-center p-4 bg-blue-50 rounded-lg">
                      <div className="text-2xl font-bold text-blue-600">
                        {savedData.data.total || 0}
                      </div>
                      <div className="text-sm text-gray-600">Total enregistrements</div>
                    </div>
                    <div className="text-center p-4 bg-green-50 rounded-lg">
                      <div className="text-2xl font-bold text-green-600">
                        {new Intl.NumberFormat('fr-FR', {
                          style: 'decimal',
                          minimumFractionDigits: 2,
                          maximumFractionDigits: 2
                        }).format(
                          savedData.data.data.reduce((sum, record) => 
                            sum + (parseFloat(record.creance_net) || 0), 0
                          )
                        )}
                      </div>
                      <div className="text-sm text-gray-600">Créance Net total (DZD)</div>
                    </div>
                    <div className="text-center p-4 bg-purple-50 rounded-lg">
                      <div className="text-2xl font-bold text-purple-600">
                        {new Set(savedData.data.data.map(record => record.dot).filter(Boolean)).size || 0}
                      </div>
                      <div className="text-sm text-gray-600">DOTs</div>
                    </div>
                    <div className="text-center p-4 bg-orange-50 rounded-lg">
                      <div className="text-2xl font-bold text-orange-600">
                        {new Set(savedData.data.data.map(record => record.produit).filter(Boolean)).size || 0}
                      </div>
                      <div className="text-sm text-gray-600">Produits</div>
                    </div>
                  </div>
                ) : parkStats ? (
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
                ) : null}

                {/* Filters */}
                {isRevenueObjectiveFile ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    <div>
                      <Label htmlFor="search">Rechercher par DOT</Label>
                      <Input
                        id="search"
                        placeholder="Nom du DOT..."
                        value={savedDataSearch}
                        onChange={(e) => setSavedDataSearch(e.target.value)}
                      />
                    </div>
                  </div>
                ) : isAccountDescriptionFile ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    <div>
                      <Label htmlFor="search">Rechercher par code comptable</Label>
                      <Input
                        id="search"
                        placeholder="Code comptable..."
                        value={savedDataSearch}
                        onChange={(e) => setSavedDataSearch(e.target.value)}
                      />
                    </div>
                  </div>
                ) : isRevenueJournalFile ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    <div>
                      <Label htmlFor="search">Rechercher par organisation</Label>
                      <Input
                        id="search"
                        placeholder="Nom de l'organisation..."
                        value={savedDataSearch}
                        onChange={(e) => setSavedDataSearch(e.target.value)}
                      />
                    </div>
                  </div>
                ) : isEncaissementArDotFile ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    <div>
                      <Label htmlFor="search">Rechercher par organisation</Label>
                      <Input
                        id="search"
                        placeholder="Nom de l'organisation..."
                        value={savedDataSearch}
                        onChange={(e) => setSavedDataSearch(e.target.value)}
                      />
                    </div>
                  </div>
                ) : isCreancePeriodiqueDotFile ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    <div>
                      <Label htmlFor="search">Rechercher par DOT</Label>
                      <Input
                        id="search"
                        placeholder="Nom du DOT..."
                        value={savedDataSearch}
                        onChange={(e) => setSavedDataSearch(e.target.value)}
                      />
                    </div>
                  </div>
                ) : (
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
                )}

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
                              {column === "dot_name" ? "DOT" :
                               column === "objectif_ca" ? "Objectif C.A (DZD)" :
                               column === "cpt_comptable" ? "Code Comptable" :
                               column === "description_cpt_comptable" ? "Description Cpt Comptable" :
                               column === "type_cpte" ? "TYPE_CPTE" :
                               column === "aut_bdg" ? "AUT_BDG" :
                               column === "aut_imp" ? "AUT_IMP" :
                               column === "auxil" ? "AUXIL" :
                               column === "let" ? "LET" :
                               column === "org_name" ? "Organisation" :
                               column === "n_fact" ? "N° Facture" :
                               column === "typ_fact" ? "Type Facture" :
                               column === "date_fact" ? "Date Facture" :
                               column === "client" ? "Client" :
                               column === "date_gl" ? "Date GL" :
                               column === "mnt_ht" ? "Montant HT (DZD)" :
                               column === "mnt_ttc" ? "Montant TTC (DZD)" :
                               column === "chiffre_aff_exe_dzd" ? "Chiffre d'Affaires (DZD)" :
                               column === "tva" ? "TVA" :
                               column === "taux_realisation_ca" ? "Taux Réalisation C.A (%)" :
                               // Encaissement AR DOT columns
                               column === "organisation" ? "Organisation" :
                               column === "source" ? "Source" :
                               column === "encaissement" ? "Encaissement (DZD)" :
                               column === "taux_encaissement" ? "Taux Encaissement (%)" :
                               column === "montant_restant" ? "Montant Restant (DZD)" :
                               column === "date_rglt" ? "Date Règlement" :
                               column === "n_rglt" ? "N° Règlement" :
                               // Créance Périodique DOT columns
                               column === "dot" ? "DOT" :
                               column === "actel" ? "ACTEL" :
                               column === "mois" ? "Mois" :
                               column === "annee" ? "Année" :
                               column === "period_key" ? "Période" :
                               column === "subs_status" ? "Statut Abonné" :
                               column === "produit" ? "Produit" :
                               column === "cust_lev1" ? "Niveau Client 1" :
                               column === "cust_lev2" ? "Niveau Client 2" :
                               column === "cust_lev3" ? "Niveau Client 3" :
                               column === "invoice_amt" ? "Montant Facture (DZD)" :
                               column === "open_amt" ? "Montant Ouvert (DZD)" :
                               column === "creance_brut" ? "Créance Brut (DZD)" :
                               column === "creance_net" ? "Créance Net (DZD)" :
                               column === "creance_ht" ? "Créance HT (DZD)" :
                               column}
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
                                        {column === "objectif_ca" && isRevenueObjectiveFile
                                          ? new Intl.NumberFormat('fr-FR', {
                                              style: 'decimal',
                                              minimumFractionDigits: 2,
                                              maximumFractionDigits: 2
                                            }).format(parseFloat(record[column]) || 0)
                                          : (isRevenueJournalFile && (column === "mnt_ht" || column === "mnt_ttc" || column === "chiffre_aff_exe_dzd"))
                                          ? new Intl.NumberFormat('fr-FR', {
                                              style: 'decimal',
                                              minimumFractionDigits: 2,
                                              maximumFractionDigits: 2
                                            }).format(parseFloat(record[column]) || 0)
                                          : (isRevenueJournalFile && column === "tva")
                                          ? record[column] !== null && record[column] !== undefined
                                            ? new Intl.NumberFormat('fr-FR', {
                                                style: 'decimal',
                                                minimumFractionDigits: 4,
                                                maximumFractionDigits: 4
                                              }).format(parseFloat(record[column]) || 0)
                                            : "N/A"
                                          : (isRevenueJournalFile && column === "taux_realisation_ca")
                                          ? record[column] !== null && record[column] !== undefined
                                            ? new Intl.NumberFormat('fr-FR', {
                                                style: 'decimal',
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 2
                                              }).format(parseFloat(record[column]) || 0) + "%"
                                            : "N/A"
                                          : (isRevenueJournalFile && (column === "date_fact" || column === "date_gl"))
                                          ? record[column] 
                                            ? new Date(record[column]).toLocaleDateString('fr-FR')
                                            : "N/A"
                                          : (isEncaissementArDotFile && (column === "montant_ht" || column === "montant_ttc" || column === "encaissement" || column === "montant_restant"))
                                          ? new Intl.NumberFormat('fr-FR', {
                                              style: 'decimal',
                                              minimumFractionDigits: 2,
                                              maximumFractionDigits: 2
                                            }).format(parseFloat(record[column]) || 0)
                                          : (isEncaissementArDotFile && column === "taux_encaissement")
                                          ? record[column] !== null && record[column] !== undefined
                                            ? new Intl.NumberFormat('fr-FR', {
                                                style: 'decimal',
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 2
                                              }).format(parseFloat(record[column]) || 0) + "%"
                                            : "N/A"
                                          : (isEncaissementArDotFile && (column === "date_fact" || column === "date_rglt"))
                                          ? record[column] 
                                            ? new Date(record[column]).toLocaleDateString('fr-FR')
                                            : "N/A"
                                          : (isCreancePeriodiqueDotFile && (column === "invoice_amt" || column === "open_amt" || column === "creance_brut" || column === "creance_net" || column === "creance_ht"))
                                          ? new Intl.NumberFormat('fr-FR', {
                                              style: 'decimal',
                                              minimumFractionDigits: 2,
                                              maximumFractionDigits: 2
                                            }).format(parseFloat(record[column]) || 0)
                                          : formatValue(record[column])}
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
