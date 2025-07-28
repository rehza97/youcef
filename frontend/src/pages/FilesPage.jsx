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
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../components/ui/tabs";
import { Alert, AlertDescription } from "../components/ui/alert";
import { Progress } from "../components/ui/progress";
import {
  Upload,
  FileText,
  BarChart3,
  PieChart,
  TrendingUp,
  Filter,
  Search,
  Trash2,
  Download,
  Eye,
  Settings,
  Database,
  CheckCircle,
  XCircle,
  Clock,
} from "lucide-react";
import { toast } from "sonner";
import axios from "axios";

// Chart components
import { Bar, Line, Pie, Doughnut } from "react-chartjs-2";
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const FilesPage = () => {
  const [files, setFiles] = useState([]);
  const [fileStats, setFileStats] = useState({});
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [showFileDetails, setShowFileDetails] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // Data processing states
  const [processedData, setProcessedData] = useState({});
  const [processingStatus, setProcessingStatus] = useState({});
  const [overview, setOverview] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [filters, setFilters] = useState({
    organisation: "all",
    dateFact: "all",
    encaisseRate: "all",
  });
  const [searchTerm, setSearchTerm] = useState("");

  // Sample chart data for demonstration
  const sampleChartData = {
    histogram_combined: {
      labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
      datasets: [
        {
          label: "Encaissement",
          data: [200000, 240000, 180000, 220000, 260000, 300000],
          backgroundColor: "rgba(54, 162, 235, 0.5)",
          borderColor: "rgba(54, 162, 235, 1)",
          borderWidth: 1,
        },
        {
          label: "Montant TTC",
          data: [250000, 300000, 225000, 275000, 325000, 375000],
          backgroundColor: "rgba(255, 99, 132, 0.5)",
          borderColor: "rgba(255, 99, 132, 1)",
          borderWidth: 1,
        },
      ],
    },
    pie_3d: {
      labels: ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
      datasets: [
        {
          data: [200000, 240000, 180000, 220000, 260000, 300000],
          backgroundColor: [
            "#FF6384",
            "#36A2EB",
            "#FFCE56",
            "#4BC0C0",
            "#9966FF",
            "#FF9F40",
          ],
        },
      ],
    },
    histogram_dot_rate: {
      labels: ["DOT ALGER", "DOT ORAN", "DOT CONSTANTINE", "DOT ANNABA"],
      datasets: [
        {
          label: "Taux d'encaissement (%)",
          data: [80, 90, 75, 85],
          backgroundColor: "rgba(75, 192, 192, 0.5)",
          borderColor: "rgba(75, 192, 192, 1)",
          borderWidth: 1,
        },
      ],
    },
  };

  useEffect(() => {
    fetchFiles();
    fetchFileStats();
    // Load sample chart data
    setChartData(sampleChartData);
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
      toast.error("Erreur lors du chargement des fichiers");
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
      toast.error(
        "Seuls les fichiers Excel (.xlsx, .xls) et CSV (.csv) sont autorisés"
      );
      return;
    }

    try {
      setUploading(true);
      const response = await filesAPI.uploadFile(file);

      // Process the uploaded file for encaissement data
      await processFileData(response.data.file_id, file);

      fetchFiles();
      fetchFileStats();
      toast.success("Fichier téléchargé et traité avec succès");
    } catch (error) {
      console.error("Erreur lors du téléchargement:", error);
      toast.error("Erreur lors du téléchargement du fichier");
    } finally {
      setUploading(false);
    }
  };

  const processFileData = async (fileId, file) => {
    try {
      setProcessingStatus((prev) => ({ ...prev, [fileId]: "processing" }));

      const formData = new FormData();
      formData.append("file", file);

      const response = await axios.post(
        `/api/encaissement/upload-data`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      // Store processed data
      setProcessedData((prev) => ({
        ...prev,
        [fileId]: response.data,
      }));

      // Update overview with combined data
      updateCombinedOverview();

      setProcessingStatus((prev) => ({ ...prev, [fileId]: "completed" }));
      toast.success(`Données traitées pour ${file.name}`);
    } catch (error) {
      console.error("Erreur lors du traitement des données:", error);
      setProcessingStatus((prev) => ({ ...prev, [fileId]: "failed" }));
      toast.error("Erreur lors du traitement des données");
    }
  };

  const updateCombinedOverview = () => {
    // Combine data from all processed files
    const allData = Object.values(processedData);
    if (allData.length === 0) return;

    const combinedOverview = {
      total_organisations: 0,
      total_factures: 0,
      total_montant_ttc: 0,
      total_encaissement: 0,
      avg_encaisse_rate: 0,
    };

    allData.forEach((data) => {
      if (data.overview) {
        combinedOverview.total_organisations +=
          data.overview.total_organisations || 0;
        combinedOverview.total_factures += data.overview.total_factures || 0;
        combinedOverview.total_montant_ttc +=
          data.overview.total_montant_ttc || 0;
        combinedOverview.total_encaissement +=
          data.overview.total_encaissement || 0;
      }
    });

    if (allData.length > 0) {
      combinedOverview.avg_encaisse_rate =
        (combinedOverview.total_encaissement /
          combinedOverview.total_montant_ttc) *
        100;
    }

    setOverview(combinedOverview);
  };

  const handleFileClick = async (file) => {
    setSelectedFile(file);
    setShowFileDetails(true);
  };

  const handleDeleteFile = async (fileId) => {
    if (
      !confirm(
        "Êtes-vous sûr de vouloir supprimer ce fichier ? Toutes les données associées seront également supprimées."
      )
    )
      return;

    try {
      await filesAPI.deleteFile(fileId);

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

      // Update combined overview
      updateCombinedOverview();

      fetchFiles();
      fetchFileStats();
      toast.success("Fichier et données associées supprimés avec succès");
    } catch (error) {
      console.error("Erreur lors de la suppression:", error);
      toast.error("Erreur lors de la suppression du fichier");
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
      toast.success("Fichier téléchargé avec succès");
    } catch (error) {
      console.error("Erreur lors du téléchargement:", error);
      toast.error("Erreur lors du téléchargement du fichier");
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

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: "DZD",
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(amount);
  };

  const formatPercentage = (value) => {
    return `${value.toFixed(2)}%`;
  };

  // Chart rendering helper with null checks
  const renderChart = (chartType, customData) => {
    if (!chartData || !chartData[chartType]) {
      return (
        <div className="flex items-center justify-center h-64 text-gray-500">
          <div className="text-center">
            <BarChart3 className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>Données de graphique non disponibles</p>
          </div>
        </div>
      );
    }

    const chartDataToRender = customData || chartData[chartType];

    switch (chartType) {
      case "histogram_combined":
        return (
          <Bar
            data={chartDataToRender}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  position: "top",
                },
                title: {
                  display: true,
                  text: "Encaissement vs Montant TTC par mois",
                },
              },
            }}
          />
        );
      case "pie_3d":
        return (
          <Doughnut
            data={chartDataToRender}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  position: "top",
                },
                title: {
                  display: true,
                  text: "Répartition des encaissements par mois",
                },
              },
            }}
          />
        );
      case "histogram_dot_rate":
        return (
          <Bar
            data={chartDataToRender}
            options={{
              responsive: true,
              plugins: {
                legend: {
                  position: "top",
                },
                title: {
                  display: true,
                  text: "Taux d'encaissement par DOT",
                },
              },
            }}
          />
        );
      default:
        return (
          <div className="flex items-center justify-center h-64 text-gray-500">
            <p>Type de graphique non reconnu</p>
          </div>
        );
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Gestion des Fichiers et Données
        </h1>
        <p className="text-gray-600">
          Télécharger, traiter et analyser vos fichiers Excel et CSV
        </p>
      </div>

      <Tabs defaultValue="files" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="files">Fichiers</TabsTrigger>
          <TabsTrigger value="data">Données Traitées</TabsTrigger>
          <TabsTrigger value="analytics">Analyses</TabsTrigger>
        </TabsList>

        <TabsContent value="files" className="space-y-6">
          {/* Statistiques */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
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
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Télécharger un fichier
              </CardTitle>
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
                      ? "Téléchargement et traitement en cours..."
                      : "Cliquez pour sélectionner un fichier"}
                  </p>
                  <p className="text-gray-600">
                    Formats supportés: Excel (.xlsx, .xls) et CSV (.csv)
                  </p>
                  {uploading && <Progress value={50} className="mt-4" />}
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
                <Card
                  key={file.id}
                  className="hover:shadow-md transition-shadow"
                >
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
                            {processingStatus[file.id] && (
                              <Badge className="flex items-center gap-1">
                                {getProcessingStatusIcon(
                                  processingStatus[file.id]
                                )}
                                {processingStatus[file.id] === "completed"
                                  ? "Données traitées"
                                  : processingStatus[file.id] === "processing"
                                  ? "Traitement en cours"
                                  : "Échec du traitement"}
                              </Badge>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleFileClick(file)}
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          Détails
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleDownloadFile(file.id)}
                        >
                          <Download className="h-4 w-4 mr-1" />
                          Télécharger
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDeleteFile(file.id)}
                        >
                          <Trash2 className="h-4 w-4 mr-1" />
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
        </TabsContent>

        <TabsContent value="data" className="space-y-6">
          {/* Overview Cards */}
          {overview && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Organisations
                  </CardTitle>
                  <BarChart3 className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {overview.total_organisations}
                  </div>
                  <p className="text-xs text-muted-foreground">Total des DOT</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Factures
                  </CardTitle>
                  <FileText className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {overview.total_factures}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Total des factures
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Montant TTC
                  </CardTitle>
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {formatCurrency(overview.total_montant_ttc)}
                  </div>
                  <p className="text-xs text-muted-foreground">Montant total</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    Taux d'encaissement
                  </CardTitle>
                  <PieChart className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {formatPercentage(overview.avg_encaisse_rate)}
                  </div>
                  <Progress
                    value={overview.avg_encaisse_rate}
                    className="mt-2"
                  />
                  <p className="text-xs text-muted-foreground">
                    Moyenne générale
                  </p>
                </CardContent>
              </Card>
            </div>
          )}

          {/* Processed Data Summary */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="h-5 w-5" />
                Résumé des Données Traitées
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.keys(processedData).length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    <Database className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p>Aucune donnée traitée pour le moment</p>
                    <p className="text-sm">
                      Téléchargez des fichiers pour commencer le traitement
                    </p>
                  </div>
                ) : (
                  Object.entries(processedData).map(([fileId, data]) => {
                    const file = files.find((f) => f.id === parseInt(fileId));
                    return (
                      <div key={fileId} className="border rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <h4 className="font-semibold">
                            {file?.original_filename || `Fichier ${fileId}`}
                          </h4>
                          <Badge
                            className={getStatusColor(
                              processingStatus[fileId] || "completed"
                            )}
                          >
                            {processingStatus[fileId] === "completed"
                              ? "Traité"
                              : "En cours"}
                          </Badge>
                        </div>
                        {data.overview && (
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div>
                              <span className="text-gray-600">
                                Organisations:
                              </span>
                              <div className="font-semibold">
                                {data.overview.total_organisations}
                              </div>
                            </div>
                            <div>
                              <span className="text-gray-600">Factures:</span>
                              <div className="font-semibold">
                                {data.overview.total_factures}
                              </div>
                            </div>
                            <div>
                              <span className="text-gray-600">
                                Montant TTC:
                              </span>
                              <div className="font-semibold">
                                {formatCurrency(
                                  data.overview.total_montant_ttc
                                )}
                              </div>
                            </div>
                            <div>
                              <span className="text-gray-600">Taux:</span>
                              <div className="font-semibold">
                                {formatPercentage(
                                  data.overview.avg_encaisse_rate
                                )}
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-6">
          {/* Filters and Search */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Filter className="h-5 w-5" />
                Filtres et recherche
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <div>
                  <Label htmlFor="organisation">DOT (Organisation)</Label>
                  <Select
                    value={filters.organisation}
                    onValueChange={(value) =>
                      setFilters({ ...filters, organisation: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner une organisation" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Toutes</SelectItem>
                      <SelectItem value="DOT_ALGER">DOT ALGER</SelectItem>
                      <SelectItem value="DOT_ORAN">DOT ORAN</SelectItem>
                      <SelectItem value="DOT_CONSTANTINE">
                        DOT CONSTANTINE
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="dateFact">Mois (Date Fact)</Label>
                  <Select
                    value={filters.dateFact}
                    onValueChange={(value) =>
                      setFilters({ ...filters, dateFact: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner un mois" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Tous</SelectItem>
                      <SelectItem value="2024-01">Janvier 2024</SelectItem>
                      <SelectItem value="2024-02">Février 2024</SelectItem>
                      <SelectItem value="2024-03">Mars 2024</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="encaisseRate">Taux d'encaissement</Label>
                  <Select
                    value={filters.encaisseRate}
                    onValueChange={(value) =>
                      setFilters({ ...filters, encaisseRate: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Sélectionner un taux" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Tous</SelectItem>
                      <SelectItem value="0-25">0-25%</SelectItem>
                      <SelectItem value="25-50">25-50%</SelectItem>
                      <SelectItem value="50-75">50-75%</SelectItem>
                      <SelectItem value="75-100">75-100%</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="search">Recherche</Label>
                  <div className="relative">
                    <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      id="search"
                      placeholder="Rechercher..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-8"
                    />
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Charts Section */}
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Histogramme combiné */}
              <Card>
                <CardHeader>
                  <CardTitle>
                    Histogramme combiné (Encaissement et Montant TTC par mois)
                  </CardTitle>
                </CardHeader>
                <CardContent>{renderChart("histogram_combined")}</CardContent>
              </Card>

              {/* Secteur 3D */}
              <Card>
                <CardHeader>
                  <CardTitle>Secteur 3D (encaissement / mois)</CardTitle>
                </CardHeader>
                <CardContent>{renderChart("pie_3d")}</CardContent>
              </Card>
            </div>

            {/* Histogramme DOT et Taux */}
            <Card>
              <CardHeader>
                <CardTitle>Histogramme (DOT et Taux d'encaissement)</CardTitle>
              </CardHeader>
              <CardContent>{renderChart("histogram_dot_rate")}</CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

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

              {/* Data Processing Status */}
              {processingStatus[selectedFile.id] && (
                <div className="border border-blue-200 bg-blue-50 p-4 rounded">
                  <h3 className="font-semibold text-blue-800 mb-2">
                    Statut du traitement des données
                  </h3>
                  <div className="flex items-center gap-2">
                    {getProcessingStatusIcon(processingStatus[selectedFile.id])}
                    <span className="text-blue-700">
                      {processingStatus[selectedFile.id] === "completed"
                        ? "Données traitées avec succès"
                        : processingStatus[selectedFile.id] === "processing"
                        ? "Traitement en cours..."
                        : "Échec du traitement"}
                    </span>
                  </div>
                </div>
              )}

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
