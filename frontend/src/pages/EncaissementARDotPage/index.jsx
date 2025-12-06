import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MultiSelect } from "@/components/ui/multi-select";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  Cell,
  ResponsiveContainer,
} from "recharts";
import {
  Download,
  RefreshCw,
  AlertTriangle,
  TrendingUp,
  DollarSign,
  Percent,
  FileText,
} from "lucide-react";
import {
  getEncaissementDashboardOverview,
  getEncaissementMonthlyAggregates,
  getEncaissementMonthlyDistribution,
  getEncaissementDotAggregates,
  getEncaissementAnomalyStatistics,
  getEncaissementAvailableMonths,
  getEncaissementAvailableOrganisations,
  exportEncaissementRecords,
  getEncaissementRecords,
} from "../../services/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FileText } from "lucide-react";

// Number formatter for French locale
const numberFr = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

const formatCurrency = (value) => {
  return `${numberFr.format(value || 0)} DZD`;
};

const formatPercent = (value) => {
  return `${numberFr.format(value || 0)} %`;
};

// Color palette for charts
const COLORS = [
  "#0088FE",
  "#00C49F",
  "#FFBB28",
  "#FF8042",
  "#8884d8",
  "#82ca9d",
  "#ffc658",
  "#ff7c7c",
  "#8dd1e1",
  "#d084d0",
];

/**
 * Overview KPI Card Component
 */
const OverviewCard = ({
  title,
  value,
  subtitle,
  icon: Icon,
  color = "blue",
}) => (
  <Card className="hover:shadow-lg transition-shadow">
    <CardHeader className="flex flex-row items-center justify-between pb-2">
      <CardTitle className="text-sm font-medium text-muted-foreground">
        {title}
      </CardTitle>
      {Icon && <Icon className={`h-5 w-5 text-${color}-600`} />}
    </CardHeader>
    <CardContent>
      <div className={`text-2xl font-bold text-${color}-700`}>{value}</div>
      {subtitle && (
        <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
      )}
    </CardContent>
  </Card>
);

/**
 * Main Encaissement AR DOT Dashboard Page
 * Displays 4 visualizations as specified:
 * 1. OVERVIEW - KPI cards (Montant TTC, Encaissement, Taux)
 * 2. Combined Bar Chart - Montant TTC & Encaissement by month
 * 3. 3D Pie Chart - Encaissement by month
 * 4. Bar Chart - DOT and Taux d'encaissement
 */
const EncaissementARDotPage = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Overview statistics
  const [overview, setOverview] = useState({
    total_montant_ttc: 0,
    total_encaissement: 0,
    total_montant_restant: 0,
    taux_encaissement: 0,
    nombre_factures: 0,
  });

  // Monthly aggregates for combined bar chart
  const [monthlyAggregates, setMonthlyAggregates] = useState([]);

  // Monthly distribution for pie chart
  const [monthlyDistribution, setMonthlyDistribution] = useState([]);

  // DOT aggregates for DOT bar chart
  const [dotAggregates, setDotAggregates] = useState([]);

  // Anomaly statistics
  const [anomalyStats, setAnomalyStats] = useState({
    total_anomalies: 0,
    by_type: {},
  });

  // Filters
  const [filters, setFilters] = useState({
    year: new Date().getFullYear(),
    organisations: [],
  });

  // Available metadata
  const [availableMonths, setAvailableMonths] = useState([]);
  const [availableOrganisations, setAvailableOrganisations] = useState([]);

  // Preview data state
  const [activeTab, setActiveTab] = useState("overview");
  const [previewData, setPreviewData] = useState([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewTotal, setPreviewTotal] = useState(0);
  const [previewPage, setPreviewPage] = useState(1);
  const [previewPageSize, setPreviewPageSize] = useState(10);

  /**
   * Fetch all dashboard data
   */
  const fetchData = async (showRefreshing = false) => {
    if (showRefreshing) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      // Fetch all data in parallel using centralized API methods
      const [
        overviewRes,
        monthlyAggregatesRes,
        monthlyDistributionRes,
        dotAggregatesRes,
        anomalyStatsRes,
        availableMonthsRes,
        availableOrgsRes,
      ] = await Promise.all([
        getEncaissementDashboardOverview(),
        getEncaissementMonthlyAggregates(filters.year),
        getEncaissementMonthlyDistribution(filters.year),
        getEncaissementDotAggregates(),
        getEncaissementAnomalyStatistics(),
        getEncaissementAvailableMonths(),
        getEncaissementAvailableOrganisations(),
      ]);

      // Update state with response data
      setOverview(overviewRes.data);
      setMonthlyAggregates(monthlyAggregatesRes.data);
      setMonthlyDistribution(monthlyDistributionRes.data);
      setDotAggregates(dotAggregatesRes.data);
      setAnomalyStats(anomalyStatsRes.data);
      setAvailableMonths(availableMonthsRes.data);
      setAvailableOrganisations(availableOrgsRes.data);
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * Fetch preview data
   */
  const fetchPreviewData = async () => {
    if (activeTab !== "preview") return;

    try {
      setPreviewLoading(true);

      const params = {
        page: previewPage,
        page_size: previewPageSize,
      };

      // Add filters if needed
      if (filters.year) {
        // Filter by year if needed
      }
      if (filters.organisations && filters.organisations.length > 0) {
        params.organisation = filters.organisations.join(",");
      }

      const response = await getEncaissementRecords(params);

      setPreviewData(response.data?.items || []);
      setPreviewTotal(response.data?.total || 0);
    } catch (error) {
      console.error("Error fetching preview data:", error);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Fetch preview data when tab changes or filters/page changes
  useEffect(() => {
    if (activeTab === "preview") {
      fetchPreviewData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, previewPage, previewPageSize, filters]);

  /**
   * Format monthly data for combined bar chart
   */
  const monthlyChartData = useMemo(() => {
    return monthlyAggregates.map((item) => ({
      mois: new Date(item.mois + "-01").toLocaleString("fr-FR", {
        month: "short",
        year: "2-digit",
      }),
      "Montant TTC": item.total_montant_ttc,
      Encaissement: item.total_encaissement,
      "Montant Restant": item.total_montant_restant,
    }));
  }, [monthlyAggregates]);

  /**
   * Format monthly distribution for pie chart
   */
  const pieChartData = useMemo(() => {
    return monthlyDistribution.map((item, index) => ({
      name: new Date(item.mois + "-01").toLocaleString("fr-FR", {
        month: "long",
        year: "numeric",
      }),
      value: item.total_encaissement,
      percentage: item.percentage,
      fill: COLORS[index % COLORS.length],
    }));
  }, [monthlyDistribution]);

  /**
   * Format DOT data for bar chart
   */
  const dotChartData = useMemo(() => {
    return dotAggregates.map((item) => ({
      organisation: item.organisation,
      taux: item.taux_encaissement,
      montant_ttc: item.total_montant_ttc,
      encaissement: item.total_encaissement,
    }));
  }, [dotAggregates]);

  /**
   * Export data to CSV or Excel
   */
  const exportData = async (format = "csv") => {
    try {
      const exportParams = {
        format: format,
        year: filters.year,
      };
      // Add organisations filter if selected
      if (filters.organisations && filters.organisations.length > 0) {
        exportParams.organisations = filters.organisations.join(",");
      }

      const response = await exportEncaissementRecords(exportParams);
      const mimeType =
        format === "xlsx"
          ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          : "text/csv";
      const blob = new Blob([response.data], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `encaissement_ar_dot_export_${filters.year}_${new Date()
        .toISOString()
        .slice(0, 10)}.${format === "xlsx" ? "xlsx" : "csv"}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error exporting data:", error);
    }
  };

  /**
   * Custom tooltip for pie chart
   */
  const renderPieTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
          <p className="font-semibold">{payload[0].name}</p>
          <p className="text-sm text-blue-600">
            Encaissement: {formatCurrency(payload[0].value)}
          </p>
          <p className="text-sm text-gray-600">
            {formatPercent(payload[0].payload.percentage)}
          </p>
        </div>
      );
    }
    return null;
  };

  /**
   * Custom tooltip for bar charts
   */
  const renderBarTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
          <p className="font-semibold mb-2">{label}</p>
          {payload.map((entry, index) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {formatCurrency(entry.value)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <RefreshCw className="h-12 w-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-lg text-gray-600">Chargement des données...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6 bg-gray-50 min-h-screen">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Encaissement AR DOT
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Tableau de bord - Factures AR et Encaissements par période
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => fetchData(true)}
            disabled={refreshing}
          >
            <RefreshCw
              className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`}
            />
            Actualiser
          </Button>
          <Button
            onClick={() => exportData("csv")}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            <Download className="h-4 w-4 mr-2" />
            CSV
          </Button>
          <Button
            onClick={() => exportData("xlsx")}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            <Download className="h-4 w-4 mr-2" />
            Excel
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 sm:grid-cols-5 gap-4">
            <div>
              <Label>Année</Label>
              <Select
                value={filters.year.toString()}
                onValueChange={(value) =>
                  setFilters((f) => ({ ...f, year: parseInt(value) }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="2024">2024</SelectItem>
                  <SelectItem value="2025">2025</SelectItem>
                  <SelectItem value="2026">2026</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="sm:col-span-3">
              <Label>Organisation (DOT)</Label>
              <MultiSelect
                options={
                  availableOrganisations.map((org) => ({
                    label: org,
                    value: org,
                  })) || []
                }
                selected={filters.organisations}
                onChange={(values) =>
                  setFilters((f) => ({ ...f, organisations: values }))
                }
                placeholder="Toutes les organisations"
              />
            </div>
            <div className="flex items-end">
              <Button onClick={() => fetchData()} className="w-full sm:w-auto">
                Appliquer les filtres
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="overview">Vue d'ensemble</TabsTrigger>
          <TabsTrigger value="preview">Aperçu des données</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-6">
          {/* VISUALIZATION 1: OVERVIEW - KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <OverviewCard
              title="Montant TTC Total"
              value={formatCurrency(overview.total_montant_ttc)}
              subtitle={`${overview.nombre_factures} factures`}
              icon={DollarSign}
              color="blue"
            />
            <OverviewCard
              title="Encaissement Total"
              value={formatCurrency(overview.total_encaissement)}
              subtitle="Montant encaissé"
              icon={TrendingUp}
              color="green"
            />
            <OverviewCard
              title="Taux d'Encaissement"
              value={formatPercent(overview.taux_encaissement)}
              subtitle={`${formatPercent(
                (overview.taux_encaissement / 100) * 100
              )} du montant TTC`}
              icon={Percent}
              color="purple"
            />
            <OverviewCard
              title="Montant Restant"
              value={formatCurrency(overview.total_montant_restant)}
              subtitle={`${anomalyStats.total_anomalies} anomalies`}
              icon={AlertTriangle}
              color="orange"
            />
          </div>

          {/* VISUALIZATION 2: Combined Bar Chart - Montant TTC & Encaissement by Month */}
          <Card>
            <CardHeader>
              <CardTitle>Montant TTC et Encaissement par Mois</CardTitle>
              <p className="text-sm text-muted-foreground">
                Comparaison mensuelle des montants facturés et encaissés
              </p>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={monthlyChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="mois" />
                  <YAxis />
                  <Tooltip content={renderBarTooltip} />
                  <Legend />
                  <Bar dataKey="Montant TTC" fill="#0088FE" />
                  <Bar dataKey="Encaissement" fill="#00C49F" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* VISUALIZATION 3: 3D Pie Chart - Encaissement by Month */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Distribution Mensuelle des Encaissements</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Répartition des encaissements par mois (%)
                </p>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <PieChart>
                    <Pie
                      data={pieChartData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry) =>
                        `${
                          entry.name.split(" ")[0]
                        }: ${entry.percentage.toFixed(1)}%`
                      }
                      outerRadius={120}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {pieChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.fill} />
                      ))}
                    </Pie>
                    <Tooltip content={renderPieTooltip} />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            {/* VISUALIZATION 4: Bar Chart - DOT and Taux d'Encaissement */}
            <Card>
              <CardHeader>
                <CardTitle>Taux d'Encaissement par DOT</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Performance d'encaissement par organisation
                </p>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={dotChartData} layout="horizontal">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" unit="%" />
                    <YAxis dataKey="organisation" type="category" width={100} />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          return (
                            <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
                              <p className="font-semibold mb-2">
                                {payload[0].payload.organisation}
                              </p>
                              <p className="text-sm text-blue-600">
                                Taux: {formatPercent(payload[0].value)}
                              </p>
                              <p className="text-sm text-gray-600">
                                Montant TTC:{" "}
                                {formatCurrency(payload[0].payload.montant_ttc)}
                              </p>
                              <p className="text-sm text-green-600">
                                Encaissement:{" "}
                                {formatCurrency(
                                  payload[0].payload.encaissement
                                )}
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Legend />
                    <Bar
                      dataKey="taux"
                      fill="#8884d8"
                      name="Taux d'Encaissement (%)"
                    />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>

          {/* Anomalies Summary */}
          {anomalyStats.total_anomalies > 0 && (
            <Card className="border-orange-200 bg-orange-50">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-orange-700">
                  <AlertTriangle className="h-5 w-5" />
                  Anomalies Détectées
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm mb-3">
                  {anomalyStats.total_anomalies} anomalies ont été détectées
                  dans les données
                </p>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                  {Object.entries(anomalyStats.by_type).map(([type, count]) => (
                    <div
                      key={type}
                      className="bg-white p-3 rounded border border-orange-200"
                    >
                      <p className="text-xs text-gray-600">{type}</p>
                      <p className="text-lg font-bold text-orange-600">
                        {count}
                      </p>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="preview" className="space-y-6">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Aperçu des Données</CardTitle>
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <Label htmlFor="page-size" className="text-sm">
                      Par page:
                    </Label>
                    <Select
                      value={previewPageSize.toString()}
                      onValueChange={(value) => {
                        setPreviewPageSize(parseInt(value));
                        setPreviewPage(1);
                      }}
                    >
                      <SelectTrigger id="page-size" className="w-20">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="10">10</SelectItem>
                        <SelectItem value="15">15</SelectItem>
                        <SelectItem value="20">20</SelectItem>
                        <SelectItem value="50">50</SelectItem>
                        <SelectItem value="100">100</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {numberFr.format(previewTotal)} enregistrement(s) total
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {previewLoading ? (
                <div className="flex items-center justify-center py-12">
                  <RefreshCw className="h-8 w-8 animate-spin text-blue-600 mr-2" />
                  <div className="text-muted-foreground">Chargement...</div>
                </div>
              ) : previewData.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                  <FileText className="h-12 w-12 mb-4" />
                  <p>Aucune donnée disponible</p>
                </div>
              ) : (
                <>
                  <div className="rounded-md border overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="sticky left-0 bg-background z-10">
                            ID
                          </TableHead>
                          <TableHead>Organisation</TableHead>
                          <TableHead>Source</TableHead>
                          <TableHead>N. Fact</TableHead>
                          <TableHead>Typ Fact</TableHead>
                          <TableHead>Date Fact</TableHead>
                          <TableHead>Client</TableHead>
                          <TableHead>N Client</TableHead>
                          <TableHead>Montant HT</TableHead>
                          <TableHead>Montant Taxe</TableHead>
                          <TableHead>Montant TTC</TableHead>
                          <TableHead>Chiffre Aff Exe</TableHead>
                          <TableHead>Encaissement</TableHead>
                          <TableHead>N Rglt</TableHead>
                          <TableHead>Date Rglt</TableHead>
                          <TableHead>Taux Encaissement</TableHead>
                          <TableHead>Montant Restant</TableHead>
                          <TableHead>Facture Avoir/Annulation</TableHead>
                          <TableHead>Obj Fact</TableHead>
                          <TableHead>Période</TableHead>
                          <TableHead>Ref</TableHead>
                          <TableHead>Terminé Flag</TableHead>
                          <TableHead>Créé Par</TableHead>
                          <TableHead>Mois</TableHead>
                          <TableHead>Dupliqué</TableHead>
                          <TableHead>Anomalie</TableHead>
                          <TableHead>Raison Anomalie</TableHead>
                          <TableHead>Créé le</TableHead>
                          <TableHead>Modifié le</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {previewData.map((record) => (
                          <TableRow key={record.id}>
                            <TableCell className="font-mono text-xs sticky left-0 bg-background z-10">
                              {record.id || "-"}
                            </TableCell>
                            <TableCell>{record.organisation || "-"}</TableCell>
                            <TableCell>{record.source || "-"}</TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.n_fact || "-"}
                            </TableCell>
                            <TableCell>{record.typ_fact || "-"}</TableCell>
                            <TableCell className="text-xs">
                              {record.date_fact
                                ? new Date(record.date_fact).toLocaleDateString(
                                    "fr-FR"
                                  )
                                : "-"}
                            </TableCell>
                            <TableCell className="max-w-[200px] truncate">
                              {record.client || "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.n_client || "-"}
                            </TableCell>
                            <TableCell className="text-right">
                              {record.montant_ht
                                ? formatCurrency(record.montant_ht)
                                : "-"}
                            </TableCell>
                            <TableCell className="text-right">
                              {record.montant_taxe
                                ? formatCurrency(record.montant_taxe)
                                : "-"}
                            </TableCell>
                            <TableCell className="text-right font-semibold">
                              {record.montant_ttc
                                ? formatCurrency(record.montant_ttc)
                                : "-"}
                            </TableCell>
                            <TableCell className="text-right">
                              {record.chiffre_aff_exe
                                ? formatCurrency(record.chiffre_aff_exe)
                                : "-"}
                            </TableCell>
                            <TableCell className="text-right font-semibold text-green-600">
                              {record.encaissement
                                ? formatCurrency(record.encaissement)
                                : "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.n_rglt || "-"}
                            </TableCell>
                            <TableCell className="text-xs">
                              {record.date_rglt
                                ? new Date(record.date_rglt).toLocaleDateString(
                                    "fr-FR"
                                  )
                                : "-"}
                            </TableCell>
                            <TableCell className="text-right">
                              {record.taux_encaissement !== null &&
                              record.taux_encaissement !== undefined
                                ? formatPercent(record.taux_encaissement)
                                : "-"}
                            </TableCell>
                            <TableCell className="text-right">
                              {record.montant_restant
                                ? formatCurrency(record.montant_restant)
                                : "-"}
                            </TableCell>
                            <TableCell className="max-w-[200px] truncate">
                              {record.facture_avoir_annulation || "-"}
                            </TableCell>
                            <TableCell className="max-w-[200px] truncate">
                              {record.obj_fact || "-"}
                            </TableCell>
                            <TableCell>{record.periode || "-"}</TableCell>
                            <TableCell>{record.ref || "-"}</TableCell>
                            <TableCell>{record.termine_flag || "-"}</TableCell>
                            <TableCell>{record.creer_par || "-"}</TableCell>
                            <TableCell>{record.mois || "-"}</TableCell>
                            <TableCell>
                              {record.is_duplicate ? (
                                <span className="text-orange-600 font-semibold">
                                  Oui
                                </span>
                              ) : (
                                "Non"
                              )}
                            </TableCell>
                            <TableCell>
                              {record.is_anomaly ? (
                                <span className="text-red-600 font-semibold">
                                  Oui
                                </span>
                              ) : (
                                "Non"
                              )}
                            </TableCell>
                            <TableCell className="max-w-[200px] truncate text-xs">
                              {record.anomaly_reason || "-"}
                            </TableCell>
                            <TableCell className="text-xs">
                              {record.created_at
                                ? new Date(record.created_at).toLocaleString(
                                    "fr-FR"
                                  )
                                : "-"}
                            </TableCell>
                            <TableCell className="text-xs">
                              {record.updated_at
                                ? new Date(record.updated_at).toLocaleString(
                                    "fr-FR"
                                  )
                                : "-"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                  {/* Pagination */}
                  <div className="flex items-center justify-between mt-4">
                    <div className="text-sm text-muted-foreground">
                      Page {previewPage} sur{" "}
                      {Math.ceil(previewTotal / previewPageSize) || 1} (
                      {numberFr.format(
                        Math.min(
                          (previewPage - 1) * previewPageSize + 1,
                          previewTotal
                        )
                      )}{" "}
                      -{" "}
                      {numberFr.format(
                        Math.min(previewPage * previewPageSize, previewTotal)
                      )}{" "}
                      sur {numberFr.format(previewTotal)})
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPreviewPage(1)}
                        disabled={previewPage === 1 || previewLoading}
                      >
                        Première
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setPreviewPage((p) => Math.max(1, p - 1))
                        }
                        disabled={previewPage === 1 || previewLoading}
                      >
                        Précédent
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setPreviewPage((p) =>
                            Math.min(
                              Math.ceil(previewTotal / previewPageSize) || 1,
                              p + 1
                            )
                          )
                        }
                        disabled={
                          previewPage >=
                            Math.ceil(previewTotal / previewPageSize) ||
                          previewLoading
                        }
                      >
                        Suivant
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() =>
                          setPreviewPage(
                            Math.ceil(previewTotal / previewPageSize) || 1
                          )
                        }
                        disabled={
                          previewPage >=
                            Math.ceil(previewTotal / previewPageSize) ||
                          previewLoading
                        }
                      >
                        Dernière
                      </Button>
                    </div>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default EncaissementARDotPage;
