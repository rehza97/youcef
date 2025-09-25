import React, { useState, useEffect } from "react";
import { encaissementAPI } from "../../services/api";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  Upload,
  Download,
  BarChart3,
  PieChart,
  TrendingUp,
  FileText,
  AlertCircle,
  CheckCircle,
  Clock,
  DollarSign,
  Percent,
  Building,
  Calendar,
} from "lucide-react";
import { toast } from "sonner";
import { handleApiError } from "../../lib/error-handler";

const EncaissementPage = () => {
  const [overview, setOverview] = useState({});
  const [byOrganisation, setByOrganisation] = useState([]);
  const [byDate, setByDate] = useState([]);
  const [byEncaisseRate, setByEncaisseRate] = useState([]);
  const [chartData, setChartData] = useState({});
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [overviewRes, orgRes, dateRes, rateRes] = await Promise.all([
        encaissementAPI.getOverview(),
        encaissementAPI.getByOrganisation(),
        encaissementAPI.getByDate(),
        encaissementAPI.getByEncaisseRate(),
      ]);

      setOverview(overviewRes.data || {});
      setByOrganisation(orgRes.data?.organisations || []);
      setByDate(dateRes.data?.data || []);
      setByEncaisseRate(rateRes.data?.rate_buckets || []);
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du chargement des données",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleFileUpload = async () => {
    if (!selectedFile) {
      toast.error("Veuillez sélectionner un fichier");
      return;
    }

    try {
      setUploading(true);
      await encaissementAPI.uploadData(selectedFile);
      toast.success("Fichier uploadé avec succès");
      setSelectedFile(null);
      fetchData(); // Refresh data after upload
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors de l'upload du fichier",
      });
    } finally {
      setUploading(false);
    }
  };

  const fetchChartData = async (chartType) => {
    try {
      const response = await encaissementAPI.getChartData(chartType);
      setChartData((prev) => ({ ...prev, [chartType]: response.data }));
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du chargement des données du graphique",
      });
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat("fr-DZ", {
      style: "currency",
      currency: "DZD",
    }).format(amount || 0);
  };

  const formatPercentage = (value) => {
    return `${(value || 0).toFixed(2)}%`;
  };

  const renderChart = (chartType, customData) => {
    const data = customData || chartData[chartType];
    if (!data) {
      return (
        <div className="flex items-center justify-center h-64 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <div className="text-center">
            <BarChart3 className="h-12 w-12 text-gray-400 mx-auto mb-2" />
            <p className="text-gray-500">Aucune donnée disponible</p>
          </div>
        </div>
      );
    }

    return (
      <div className="h-64 bg-gray-50 dark:bg-gray-800 rounded-lg p-4">
        <div className="text-center">
          <BarChart3 className="h-8 w-8 text-blue-600 mx-auto mb-2" />
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Graphique {chartType}
          </p>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Encaissement AR DOT</h1>
        <div className="flex items-center space-x-4">
          <Input
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileChange}
            className="max-w-xs"
          />
          <Button
            onClick={handleFileUpload}
            disabled={!selectedFile || uploading}
            className="flex items-center space-x-2"
          >
            <Upload className="h-4 w-4" />
            {uploading ? "Upload en cours..." : "Upload"}
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Organisations</CardTitle>
            <Building className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview.total_organisations || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Factures
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview.total_factures || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Montant TTC</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(overview.total_montant_ttc)}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Taux d'Encaissement
            </CardTitle>
            <Percent className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatPercentage(overview.avg_encaisse_rate)}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex space-x-2 border-b">
        {[
          { id: "overview", label: "Aperçu", icon: BarChart3 },
          { id: "organisation", label: "Par Organisation", icon: Building },
          { id: "date", label: "Par Date", icon: Calendar },
          { id: "rate", label: "Par Taux", icon: TrendingUp },
        ].map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? "default" : "ghost"}
            onClick={() => setActiveTab(tab.id)}
            className="flex items-center space-x-2"
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </Button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Graphique Histogramme Combiné</CardTitle>
              </CardHeader>
              <CardContent>{renderChart("histogram_combined")}</CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Graphique Pie 3D</CardTitle>
              </CardHeader>
              <CardContent>{renderChart("pie_3d")}</CardContent>
            </Card>
          </div>
        )}

        {activeTab === "organisation" && (
          <Card>
            <CardHeader>
              <CardTitle>Données par Organisation</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Organisation</TableHead>
                    <TableHead>Nombre de Factures</TableHead>
                    <TableHead>Montant TTC</TableHead>
                    <TableHead>Encaissement</TableHead>
                    <TableHead>Taux</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {byOrganisation.map((org, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">
                        {org["Org Name"]}
                      </TableCell>
                      <TableCell>{org["N FACT"]}</TableCell>
                      <TableCell>
                        {formatCurrency(org["Montant Ttc"])}
                      </TableCell>
                      <TableCell>
                        {formatCurrency(org["Encaissement"])}
                      </TableCell>
                      <TableCell>
                        {formatPercentage(org["Taux d'encaissement"])}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {activeTab === "date" && (
          <Card>
            <CardHeader>
              <CardTitle>Données par Date</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Nombre de Factures</TableHead>
                    <TableHead>Montant TTC</TableHead>
                    <TableHead>Encaissement</TableHead>
                    <TableHead>Taux</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {byDate.map((date, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">
                        {date.period}
                      </TableCell>
                      <TableCell>{date.organisations_count}</TableCell>
                      <TableCell>
                        {formatCurrency(date.total_montant_ttc)}
                      </TableCell>
                      <TableCell>
                        {formatCurrency(date.total_encaissement)}
                      </TableCell>
                      <TableCell>
                        {formatPercentage(date.encaisse_rate)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        {activeTab === "rate" && (
          <Card>
            <CardHeader>
              <CardTitle>Données par Taux d'Encaissement</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Plage de Taux</TableHead>
                    <TableHead>Nombre de Factures</TableHead>
                    <TableHead>Montant TTC</TableHead>
                    <TableHead>Encaissement</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {byEncaisseRate.map((rate, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">
                        {rate["Rate Bucket"]}
                      </TableCell>
                      <TableCell>{rate["N FACT"]}</TableCell>
                      <TableCell>
                        {formatCurrency(rate["Montant Ttc"])}
                      </TableCell>
                      <TableCell>
                        {formatCurrency(rate["Encaissement"])}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default EncaissementPage;
