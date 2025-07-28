import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Upload,
  FileText,
  BarChart3,
  PieChart,
  TrendingUp,
  Filter,
  Search,
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

const EncaissementPage = () => {
  const [file, setFile] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [processedData, setProcessedData] = useState(null);
  const [overview, setOverview] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [filters, setFilters] = useState({
    organisation: "all",
    dateFact: "all",
    encaisseRate: "all",
  });
  const [searchTerm, setSearchTerm] = useState("");

  // Sample data for demonstration
  const sampleOverview = {
    total_organisations: 15,
    total_factures: 1250,
    total_montant_ttc: 1500000.0,
    total_encaissement: 1200000.0,
    avg_encaisse_rate: 80.5,
  };

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
    // Load sample data on component mount
    setOverview(sampleOverview);
    setChartData(sampleChartData);
  }, []);

  const handleFileUpload = async () => {
    if (!file) {
      toast.error("Please select a file first");
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(
        "/api/encaissement/upload-data",
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );

      setProcessedData(response.data);
      setOverview(response.data.overview);
      toast.success("Data uploaded and processed successfully!");
    } catch (error) {
      console.error("Upload error:", error);
      toast.error("Error uploading file. Please try again.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      if (
        selectedFile.type.includes("excel") ||
        selectedFile.type.includes("csv") ||
        selectedFile.name.endsWith(".xlsx") ||
        selectedFile.name.endsWith(".xls") ||
        selectedFile.name.endsWith(".csv")
      ) {
        setFile(selectedFile);
        toast.success("File selected successfully");
      } else {
        toast.error("Please select an Excel or CSV file");
      }
    }
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
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Encaissement AR DOT
          </h1>
          <p className="text-gray-600 mt-2">
            Module de traitement et d'analyse des encaissements
          </p>
        </div>
        <Badge variant="secondary" className="text-sm">
          Module 1-Parc Corporate NGBSS
        </Badge>
      </div>

      {/* File Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="h-5 w-5" />
            Upload des données
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="file">Sélectionner un fichier Excel ou CSV</Label>
              <Input
                id="file"
                type="file"
                accept=".xlsx,.xls,.csv"
                onChange={handleFileChange}
                className="mt-2"
              />
            </div>
            <div className="flex items-end">
              <Button
                onClick={handleFileUpload}
                disabled={!file || isUploading}
                className="w-full"
              >
                {isUploading ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Traitement...
                  </>
                ) : (
                  <>
                    <FileText className="h-4 w-4 mr-2" />
                    Traiter les données
                  </>
                )}
              </Button>
            </div>
          </div>

          {file && (
            <Alert>
              <FileText className="h-4 w-4" />
              <AlertDescription>
                Fichier sélectionné: {file.name} (
                {(file.size / 1024 / 1024).toFixed(2)} MB)
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

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
              <CardTitle className="text-sm font-medium">Factures</CardTitle>
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
              <CardTitle className="text-sm font-medium">Montant TTC</CardTitle>
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
              <Progress value={overview.avg_encaisse_rate} className="mt-2" />
              <p className="text-xs text-muted-foreground">Moyenne générale</p>
            </CardContent>
          </Card>
        </div>
      )}

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
      <Tabs defaultValue="overview" className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="overview">OVERVIEW</TabsTrigger>
          <TabsTrigger value="by-organisation">Par Organisation</TabsTrigger>
          <TabsTrigger value="by-date">Par Date</TabsTrigger>
          <TabsTrigger value="by-rate">Par Taux</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
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
        </TabsContent>

        <TabsContent value="by-organisation">
          <Card>
            <CardHeader>
              <CardTitle>Données par Organisation</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Sample data table */}
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse border border-gray-300">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border border-gray-300 px-4 py-2">
                          Organisation
                        </th>
                        <th className="border border-gray-300 px-4 py-2">
                          N FACT
                        </th>
                        <th className="border border-gray-300 px-4 py-2">
                          Montant TTC
                        </th>
                        <th className="border border-gray-300 px-4 py-2">
                          Encaissement
                        </th>
                        <th className="border border-gray-300 px-4 py-2">
                          Taux (%)
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="border border-gray-300 px-4 py-2">
                          DOT ALGER
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          150
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(250000)}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(200000)}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          80.0%
                        </td>
                      </tr>
                      <tr>
                        <td className="border border-gray-300 px-4 py-2">
                          DOT ORAN
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          120
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(180000)}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(162000)}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          90.0%
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="by-date">
          <Card>
            <CardHeader>
              <CardTitle>Données par Date</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Sample data table */}
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse border border-gray-300">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border border-gray-300 px-4 py-2">
                          Date Fact
                        </th>
                        <th className="border border-gray-300 px-4 py-2">
                          N FACT
                        </th>
                        <th className="border border-gray-300 px-4 py-2">
                          Montant TTC
                        </th>
                        <th className="border border-gray-300 px-4 py-2">
                          Encaissement
                        </th>
                        <th className="border border-gray-300 px-4 py-2">
                          Taux (%)
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="border border-gray-300 px-4 py-2">
                          2024-01
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          200
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(300000)}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(240000)}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          80.0%
                        </td>
                      </tr>
                      <tr>
                        <td className="border border-gray-300 px-4 py-2">
                          2024-02
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          180
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(270000)}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(243000)}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          90.0%
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="by-rate">
          <Card>
            <CardHeader>
              <CardTitle>Données par Taux d'encaissement</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Sample data table */}
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse border border-gray-300">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border border-gray-300 px-4 py-2">
                          Taux d'encaissement
                        </th>
                        <th className="border border-gray-300 px-4 py-2">
                          N FACT
                        </th>
                        <th className="border border-gray-300 px-4 py-2">
                          Montant TTC
                        </th>
                        <th className="border border-gray-300 px-4 py-2">
                          Encaissement
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td className="border border-gray-300 px-4 py-2">
                          0-25%
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          50
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(75000)}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(15000)}
                        </td>
                      </tr>
                      <tr>
                        <td className="border border-gray-300 px-4 py-2">
                          25-50%
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          100
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(150000)}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(60000)}
                        </td>
                      </tr>
                      <tr>
                        <td className="border border-gray-300 px-4 py-2">
                          50-75%
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          200
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(300000)}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(225000)}
                        </td>
                      </tr>
                      <tr>
                        <td className="border border-gray-300 px-4 py-2">
                          75-100%
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-center">
                          300
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(450000)}
                        </td>
                        <td className="border border-gray-300 px-4 py-2 text-right">
                          {formatCurrency(405000)}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default EncaissementPage;
