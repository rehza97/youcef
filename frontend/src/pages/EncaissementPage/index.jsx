import React, { useState, useEffect, useCallback } from "react";
import {
  getParkAnalyticsOverview,
  getParkAnalyticsByTelecomType,
  getParkAnalyticsBySubscriberStatus,
  getParkAnalyticsByDOT,
  getParkAnalyticsByCustomerL2,
  getParkAnalyticsByCustomerL3,
  getParkAnalyticsAvailableFilters,
  exportParkAnalyticsData,
  getParkAnalyticsPreviewData,
} from "../../services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MultiSelect } from "@/components/ui/multi-select";
import {
  EnhancedBarChart,
  EnhancedPieChart,
  EnhancedMultiSeriesBarChart,
} from "@/components/ui/charts";
import {
  Download,
  BarChart3,
  Building,
  FileText,
  Filter,
  X,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";
import { handleApiError } from "../../lib/error-handler";

// Utility functions
const formatNumber = (num) => {
  if (!num) return "0";
  return new Intl.NumberFormat("fr-FR").format(num);
};

const formatRelativeTime = (dateString) => {
  if (!dateString) return "N/A";
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 60) return `Il y a ${diffMins} min`;
  if (diffHours < 24) return `Il y a ${diffHours}h`;
  if (diffDays < 7) return `Il y a ${diffDays}j`;
  return date.toLocaleDateString("fr-FR");
};

const useDebounce = (value, delay = 500) => {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);

  return debouncedValue;
};

// Sub-components
// eslint-disable-next-line no-unused-vars
const OverviewCard = ({ title, value, icon: Icon, subtitle }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
      <Icon className="h-4 w-4 text-muted-foreground" />
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold">{value}</div>
      {subtitle && (
        <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
      )}
    </CardContent>
  </Card>
);

const EmptyState = ({ message = "Aucune donnée disponible" }) => (
  <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
    <AlertCircle className="h-12 w-12 mb-4" />
    <p>{message}</p>
  </div>
);

const LoadingSpinner = () => (
  <div className="flex items-center justify-center h-64">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
  </div>
);

const EncaissementPage = () => {
  // State management
  const [overview, setOverview] = useState({});
  const [telecomTypeData, setTelecomTypeData] = useState([]);
  const [subscriberStatusData, setSubscriberStatusData] = useState([]);
  const [dotData, setDotData] = useState([]);
  const [customerL2Data, setCustomerL2Data] = useState([]);
  const [customerL3Data, setCustomerL3Data] = useState([]);
  const [availableFilters, setAvailableFilters] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [exportStatus, setExportStatus] = useState("");
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [showFilters, setShowFilters] = useState(false);
  
  // Preview data state
  const [previewData, setPreviewData] = useState([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewTotal, setPreviewTotal] = useState(0);
  const [previewPage, setPreviewPage] = useState(1);
  const [previewPageSize, setPreviewPageSize] = useState(10);

  const [filters, setFilters] = useState({
    dot_ids: [], // Changed to array for multi-select
    actel_codes: [], // Changed to array for multi-select
    subscriber_statuses: [], // Changed to array for multi-select
    telecom_types: [], // Changed to array for multi-select
    offer_names: [], // Changed to array for multi-select
    offer_types: [], // Changed to array for multi-select
    customer_l2_codes: [], // Changed to array for multi-select
    customer_l3_codes: [], // Changed to array for multi-select
    search: "",
    date_from: "",
    date_to: "",
  });

  const debouncedSearch = useDebounce(filters.search, 500);

  // Fetch data with filters
  const fetchData = useCallback(
    async (isRefresh = false) => {
      try {
        if (isRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }
        setError(null);

        // Build filter params - convert arrays to comma-separated strings
        const filterParams = {};
        Object.entries(filters).forEach(([key, value]) => {
          if (Array.isArray(value) && value.length > 0) {
            // Convert array to comma-separated string for API
            filterParams[key] = value.join(",");
          } else if (typeof value === "string" && value.trim() !== "") {
            filterParams[key] = value;
          }
        });

        const [
          overviewRes,
          telecomRes,
          statusRes,
          dotRes,
          l2Res,
          l3Res,
          filtersRes,
        ] = await Promise.all([
          getParkAnalyticsOverview(filterParams),
          getParkAnalyticsByTelecomType(filterParams),
          getParkAnalyticsBySubscriberStatus(filterParams),
          getParkAnalyticsByDOT(filterParams),
          getParkAnalyticsByCustomerL2(filterParams),
          getParkAnalyticsByCustomerL3(filterParams),
          getParkAnalyticsAvailableFilters(),
        ]);

        setOverview(overviewRes.data || {});
        setTelecomTypeData(telecomRes.data?.distribution || []);
        setSubscriberStatusData(statusRes.data?.distribution || []);
        setDotData(dotRes.data?.distribution || []);
        setCustomerL2Data(l2Res.data?.distribution || []);
        setCustomerL3Data(l3Res.data?.distribution || []);
        setAvailableFilters(filtersRes.data || {});

        if (isRefresh) {
          toast.success("Données actualisées");
        }
      } catch (err) {
        const errorMsg = "Erreur lors du chargement des données";
        setError(errorMsg);
        handleApiError(err, {
          showToast: true,
          fallbackMessage: errorMsg,
        });
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [filters]
  );

  // Initial load
  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Apply filters effect
  useEffect(() => {
    if (!loading) {
      fetchData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedSearch, filters.date_from, filters.date_to]);

  // Fetch preview data
  const fetchPreviewData = useCallback(async () => {
    if (activeTab !== "preview") return;

    try {
      setPreviewLoading(true);
      
      // Build filter params - convert arrays to comma-separated strings
      const filterParams = {};
      Object.entries(filters).forEach(([key, value]) => {
        if (Array.isArray(value) && value.length > 0) {
          filterParams[key] = value.join(",");
        } else if (typeof value === "string" && value.trim() !== "") {
          filterParams[key] = value;
        }
      });

      const offset = (previewPage - 1) * previewPageSize;
      const response = await getParkAnalyticsPreviewData(
        filterParams,
        previewPageSize,
        offset
      );

      setPreviewData(response.data?.records || []);
      setPreviewTotal(response.data?.total_available || 0);
    } catch (err) {
      console.error("Error fetching preview data:", err);
      handleApiError(err, {
        showToast: true,
        fallbackMessage: "Erreur lors du chargement des données de prévisualisation",
      });
    } finally {
      setPreviewLoading(false);
    }
  }, [activeTab, filters, previewPage, previewPageSize]);

  // Fetch preview data when tab changes or filters/page changes
  useEffect(() => {
    if (activeTab === "preview") {
      fetchPreviewData();
    }
  }, [activeTab, fetchPreviewData]);

  const handleFilterChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  const applyFilters = () => {
    fetchData();
    toast.success("Filtres appliqués");
  };

  const resetFilters = () => {
    setFilters({
      dot_ids: [],
      actel_codes: [],
      subscriber_statuses: [],
      telecom_types: [],
      offer_names: [],
      offer_types: [],
      customer_l2_codes: [],
      customer_l3_codes: [],
      search: "",
      date_from: "",
      date_to: "",
    });
    toast.success("Filtres réinitialisés");
  };

  const validateDateRange = () => {
    if (filters.date_from && filters.date_to) {
      if (new Date(filters.date_from) > new Date(filters.date_to)) {
        toast.error("La date de début doit être antérieure à la date de fin");
        return false;
      }
    }
    return true;
  };

  const exportData = async (format = "csv") => {
    if (!validateDateRange()) return;

    try {
      setExporting(true);
      setExportProgress(0);
      setExportStatus("Préparation de l'export...");

      const exportFilters = {};
      Object.entries(filters).forEach(([key, value]) => {
        if (Array.isArray(value) && value.length > 0) {
          // Convert array to comma-separated string for API
          exportFilters[key] = value.join(",");
        } else if (typeof value === "string" && value.trim() !== "") {
          exportFilters[key] = value;
        }
      });
      exportFilters.format = format;

      console.log("🚀 Exporting with filters:", exportFilters);

      // Simulate initial progress
      setExportProgress(10);
      setExportStatus("Récupération des données...");

      // Track download progress
      const progressCallback = (progressEvent) => {
        if (progressEvent.total) {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 90) / progressEvent.total
          );
          setExportProgress(Math.min(90, 10 + percentCompleted));
        } else {
          // If total is unknown, simulate progress
          setExportProgress((prev) => Math.min(90, prev + 5));
        }
      };

      const response = await exportParkAnalyticsData(
        exportFilters,
        progressCallback
      );

      setExportProgress(95);
      setExportStatus("Génération du fichier...");

      const { data, total_records, message } = response.data;

      if (!data || data.length === 0) {
        setExportProgress(0);
        setExportStatus("");
        toast.info(
          message || "Aucune donnée disponible à exporter avec les filtres appliqués"
        );
        return;
      }

      setExportProgress(100);
      setExportStatus("Téléchargement...");

      // Small delay to show 100% before download
      await new Promise((resolve) => setTimeout(resolve, 300));

      downloadExportFile(data, format);

      // Simple success message - no limits!
      toast.success(
        `Export réussi: ${formatNumber(total_records)} enregistrements exportés`
      );
    } catch (err) {
      console.error("❌ Export failed:", err);
      setExportProgress(0);
      setExportStatus("");
      handleApiError(err, {
        showToast: true,
        fallbackMessage: "Erreur lors de l'export",
      });
    } finally {
      setExporting(false);
      // Reset progress after a short delay
      setTimeout(() => {
        setExportProgress(0);
        setExportStatus("");
      }, 1000);
    }
  };

  const downloadExportFile = (data, format) => {
    if (!data || data.length === 0) {
      toast.error("Aucune donnée à télécharger");
      return;
    }

    const headers = Object.keys(data[0] || {});
    let content = headers.join(",") + "\n";
    content += data
      .map((row) => headers.map((h) => `"${row[h] || ""}"`).join(","))
      .join("\n");

    const blob = new Blob([content], {
      type: format === "excel" ? "application/vnd.ms-excel" : "text/csv",
    });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `encaissement_parc_${
      new Date().toISOString().split("T")[0]
    }.${format}`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const getActiveFilterCount = () => {
    return Object.values(filters).filter((v) => {
      if (Array.isArray(v)) return v.length > 0;
      return v && typeof v === "string" && v.trim() !== "";
    }).length;
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <AlertCircle className="h-16 w-16 text-red-500" />
        <p className="text-lg font-medium">{error}</p>
        <Button onClick={() => fetchData()}>Réessayer</Button>
      </div>
    );
  }

  const activeFilterCount = getActiveFilterCount();

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-3xl font-bold">Parc Corporate NGBSS</h1>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setShowFilters((s) => !s)}
            className="relative"
          >
            <Filter className="h-4 w-4 mr-2" />
            Filtres
            {activeFilterCount > 0 && (
              <Badge
                variant="destructive"
                className="ml-2 h-5 w-5 p-0 flex items-center justify-center"
              >
                {activeFilterCount}
              </Badge>
            )}
          </Button>
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
            disabled={exporting}
            className="bg-green-600 hover:bg-green-700"
          >
            <Download className="h-4 w-4 mr-2" />
            CSV
          </Button>
          <Button
            onClick={() => exportData("excel")}
            disabled={exporting}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Download className="h-4 w-4 mr-2" />
            Excel
          </Button>
        </div>
      </div>

      {/* Export Progress Bar */}
      {exporting && (
        <Card className="border-blue-200 bg-blue-50/50">
          <CardContent className="pt-6">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium text-blue-900">
                  {exportStatus || "Export en cours..."}
                </span>
                <span className="text-blue-700 font-semibold">
                  {Math.round(exportProgress)}%
                </span>
              </div>
              <Progress value={exportProgress} className="h-2" />
            </div>
          </CardContent>
        </Card>
      )}

      {/* Total Active Subscribers - Hero Card */}
      <Card className="bg-gradient-to-r from-blue-500 to-blue-600 text-white">
        <CardContent className="pt-6">
          <div className="text-center">
            <div className="text-6xl font-bold mb-2">
              {formatNumber(overview.total_active_subscribers || 0)}
            </div>
            <div className="text-xl font-medium opacity-90">
              Total Active Subscribers
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Secondary Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <OverviewCard
          title="DOTs Accessibles"
          value={formatNumber(overview.total_dots)}
          icon={FileText}
        />
        <OverviewCard
          title="Activité 7 Jours"
          value={formatNumber(overview.recent_activity)}
          icon={BarChart3}
        />
        <OverviewCard
          title="Dernière MAJ"
          value={formatRelativeTime(overview.last_updated)}
          icon={RefreshCw}
          subtitle={
            overview.last_updated
              ? new Date(overview.last_updated).toLocaleString("fr-FR")
              : ""
          }
        />
      </div>

      {/* Enhanced Filters */}
      {showFilters && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>Filtres Avancés</CardTitle>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={resetFilters}>
                  <X className="h-4 w-4 mr-2" />
                  Réinitialiser
                </Button>
                <Button size="sm" onClick={applyFilters}>
                  Appliquer
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Primary Filters */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <Label>DOT</Label>
                  <MultiSelect
                    options={
                      availableFilters.dots?.map((d) => ({
                        label: d.name,
                        value: d.id.toString(),
                      })) || []
                    }
                    selected={filters.dot_ids}
                    onChange={(values) => handleFilterChange("dot_ids", values)}
                    placeholder="Tous les DOTs"
                  />
                </div>

                <div>
                  <Label>Statut Abonné</Label>
                  <MultiSelect
                    options={
                      availableFilters.subscriber_statuses?.map((s) => ({
                        label: s,
                        value: s,
                      })) || []
                    }
                    selected={filters.subscriber_statuses}
                    onChange={(values) =>
                      handleFilterChange("subscriber_statuses", values)
                    }
                    placeholder="Tous les statuts"
                  />
                </div>

                <div>
                  <Label>Type Télécom</Label>
                  <MultiSelect
                    options={
                      availableFilters.telecom_types?.map((t) => ({
                        label: t,
                        value: t,
                      })) || []
                    }
                    selected={filters.telecom_types}
                    onChange={(values) =>
                      handleFilterChange("telecom_types", values)
                    }
                    placeholder="Tous les types"
                  />
                </div>

                <div>
                  <Label>Code Actel</Label>
                  <MultiSelect
                    options={
                      availableFilters.actel_codes?.map((code) => ({
                        label: code,
                        value: code,
                      })) || []
                    }
                    selected={filters.actel_codes}
                    onChange={(values) =>
                      handleFilterChange("actel_codes", values)
                    }
                    placeholder="Tous les codes"
                  />
                </div>
              </div>

              {/* Secondary Filters */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <Label>Nom d'Offre</Label>
                  <MultiSelect
                    options={
                      availableFilters.offer_names?.map((offer) => ({
                        label: offer,
                        value: offer,
                      })) || []
                    }
                    selected={filters.offer_names}
                    onChange={(values) =>
                      handleFilterChange("offer_names", values)
                    }
                    placeholder="Toutes les offres"
                  />
                </div>

                <div>
                  <Label>Type d'Offre</Label>
                  <MultiSelect
                    options={
                      availableFilters.offer_types?.map((type) => ({
                        label: type,
                        value: type,
                      })) || []
                    }
                    selected={filters.offer_types}
                    onChange={(values) =>
                      handleFilterChange("offer_types", values)
                    }
                    placeholder="Tous les types"
                  />
                </div>

                <div>
                  <Label>Client L2</Label>
                  <MultiSelect
                    options={
                      availableFilters.customer_l2_codes?.map((l2) => ({
                        label: `${l2.code} - ${l2.description}`,
                        value: l2.code,
                      })) || []
                    }
                    selected={filters.customer_l2_codes}
                    onChange={(values) =>
                      handleFilterChange("customer_l2_codes", values)
                    }
                    placeholder="Tous L2"
                  />
                </div>

                <div>
                  <Label>Client L3</Label>
                  <MultiSelect
                    options={
                      availableFilters.customer_l3_codes?.map((l3) => ({
                        label: `${l3.code} - ${l3.description}`,
                        value: l3.code,
                      })) || []
                    }
                    selected={filters.customer_l3_codes}
                    onChange={(values) =>
                      handleFilterChange("customer_l3_codes", values)
                    }
                    placeholder="Tous L3"
                  />
                </div>
              </div>

              {/* Search and Date Range */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <Label>Recherche Globale</Label>
                  <Input
                    placeholder="Code client, nom, numéro..."
                    value={filters.search}
                    onChange={(e) =>
                      handleFilterChange("search", e.target.value)
                    }
                  />
                </div>

                <div>
                  <Label>Date de Début</Label>
                  <Input
                    type="date"
                    value={filters.date_from}
                    onChange={(e) =>
                      handleFilterChange("date_from", e.target.value)
                    }
                  />
                </div>

                <div>
                  <Label>Date de Fin</Label>
                  <Input
                    type="date"
                    value={filters.date_to}
                    onChange={(e) =>
                      handleFilterChange("date_to", e.target.value)
                    }
                  />
                </div>
              </div>

              {/* Active Filters Summary */}
              {activeFilterCount > 0 && (
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="font-medium text-sm">
                      Filtres actifs ({activeFilterCount})
                    </h4>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(filters).map(([key, value]) => {
                      const isActive = Array.isArray(value)
                        ? value.length > 0
                        : value && value.trim() !== "";

                      if (isActive) {
                        const labels = {
                          dot_ids: "DOT",
                          actel_codes: "Code Actel",
                          subscriber_statuses: "Statut",
                          telecom_types: "Type Télécom",
                          offer_names: "Offre",
                          offer_types: "Type Offre",
                          customer_l2_codes: "L2",
                          customer_l3_codes: "L3",
                          search: "Recherche",
                          date_from: "Depuis",
                          date_to: "Jusqu'à",
                        };

                        const displayValue = Array.isArray(value)
                          ? `${value.length} sélectionné(s)`
                          : value;

                        return (
                          <Badge
                            key={key}
                            variant="secondary"
                            className="text-xs"
                          >
                            {labels[key]}: {displayValue}
                            <X
                              className="h-3 w-3 ml-1 cursor-pointer"
                              onClick={() =>
                                handleFilterChange(
                                  key,
                                  Array.isArray(value) ? [] : ""
                                )
                              }
                            />
                          </Badge>
                        );
                      }
                      return null;
                    })}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <div className="flex flex-wrap gap-2 border-b pb-2">
        {[
          { id: "overview", label: "OVERVIEW", icon: BarChart3 },
          { id: "dot", label: "BY DOT", icon: Building },
          { id: "telecom", label: "BY Telecom Type", icon: BarChart3 },
          { id: "l2", label: "BY Code Customer L2", icon: FileText },
          { id: "l3", label: "BY Code Customer L3", icon: FileText },
          { id: "preview", label: "PREVIEW DATA", icon: FileText },
        ].map((tab) => (
          <Button
            key={tab.id}
            variant={activeTab === tab.id ? "default" : "ghost"}
            onClick={() => setActiveTab(tab.id)}
            className="flex items-center gap-2"
            size="sm"
          >
            <tab.icon className="h-4 w-4" />
            {tab.label}
          </Button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="space-y-6">
        {activeTab === "overview" && (
          <>
            {/* First Row: Telecom Type and Subscriber Status */}
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <Card className="overflow-hidden">
                <CardHeader>
                  <CardTitle>Distribution by Telecom Type</CardTitle>
                </CardHeader>
                <CardContent className="p-2">
                  {telecomTypeData.length > 0 ? (
                    <div className="w-full overflow-hidden">
                      <EnhancedPieChart
                        data={telecomTypeData.map((d) => ({
                          label: d.type,
                          value: d.count,
                        }))}
                        height={350}
                        showLabels={true}
                        labelPosition="outside"
                        showPercentages={true}
                        showValues={true}
                        minLabelPercentage={1}
                        showLegendBelow={true}
                        className="w-full"
                      />
                    </div>
                  ) : (
                    <EmptyState message="Aucune donnée de type télécom disponible" />
                  )}
                </CardContent>
              </Card>

              <Card className="overflow-hidden">
                <CardHeader>
                  <CardTitle>Distribution by Subscriber Status</CardTitle>
                </CardHeader>
                <CardContent className="p-2">
                  {subscriberStatusData.length > 0 ? (
                    <div className="w-full overflow-hidden">
                      <EnhancedPieChart
                        data={subscriberStatusData.map((d) => ({
                          label: d.status,
                          value: d.count,
                        }))}
                        height={350}
                        showLabels={true}
                        labelPosition="outside"
                        showPercentages={true}
                        showValues={true}
                        minLabelPercentage={0.5}
                        showLegendBelow={true}
                        className="w-full"
                      />
                    </div>
                  ) : (
                    <EmptyState message="Aucune donnée de statut disponible" />
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Second Row: Customer L2 Distribution */}
            <Card className="overflow-hidden">
              <CardHeader>
                <CardTitle>Distribution by Code Customer L2</CardTitle>
              </CardHeader>
              <CardContent className="p-2">
                {customerL2Data.length > 0 ? (
                  <div className="w-full overflow-hidden">
                    <EnhancedPieChart
                      data={customerL2Data.map((d) => ({
                        label: d.description,
                        value: d.count,
                      }))}
                      height={450}
                      showLabels={true}
                      labelPosition="outside"
                      showPercentages={true}
                      showValues={true}
                      minLabelPercentage={1}
                      showLegendBelow={true}
                      className="w-full"
                    />
                  </div>
                ) : (
                  <EmptyState message="Aucune donnée Client L2 disponible" />
                )}
              </CardContent>
            </Card>
          </>
        )}

        {activeTab === "telecom" && (
          <Card>
            <CardHeader>
              <CardTitle>Subscribers by Telecom Type</CardTitle>
            </CardHeader>
            <CardContent>
              {telecomTypeData.length > 0 ? (
                <EnhancedBarChart
                  data={telecomTypeData.map((d) => ({
                    label: d.type,
                    value: d.count,
                  }))}
                  height={450}
                  showValues={true}
                  showLegendBelow={true}
                  showPercentages={true}
                />
              ) : (
                <EmptyState message="Aucune donnée de type télécom disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "dot" && (
          <Card>
            <CardHeader>
              <CardTitle>Abonnés par DOT</CardTitle>
            </CardHeader>
            <CardContent>
              {dotData.length > 0 ? (
                <EnhancedMultiSeriesBarChart
                  data={dotData.map((d) => ({
                    label: d.dot_name,
                    value: d.count,
                  }))}
                  height={550}
                  showLegendBelow={true}
                  showPercentages={true}
                />
              ) : (
                <EmptyState message="Aucune donnée DOT disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "l2" && (
          <Card>
            <CardHeader>
              <CardTitle>Distribution par Client L2</CardTitle>
            </CardHeader>
            <CardContent>
              {customerL2Data.length > 0 ? (
                <EnhancedMultiSeriesBarChart
                  data={customerL2Data.map((d) => ({
                    label: d.description,
                    value: d.count,
                  }))}
                  height={550}
                  showLegendBelow={true}
                  showPercentages={true}
                />
              ) : (
                <EmptyState message="Aucune donnée Client L2 disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "l3" && (
          <Card width="100%">
            <CardHeader>
              <CardTitle>Distribution par Client L3</CardTitle>
            </CardHeader>
            <CardContent>
              {customerL3Data.length > 0 ? (
                <EnhancedMultiSeriesBarChart
                  data={customerL3Data.map((d) => ({
                    label: d.description,
                    value: d.count,
                  }))}
                  height={550}
                  showLegendBelow={true}
                  showPercentages={true}
                />
              ) : (
                <EmptyState message="Aucune donnée Client L3 disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "preview" && (
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Preview Data</CardTitle>
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
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {formatNumber(previewTotal)} enregistrement(s) total
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {previewLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-muted-foreground">Chargement...</div>
                </div>
              ) : previewData.length === 0 ? (
                <EmptyState message="Aucune donnée disponible" />
              ) : (
                <>
                  <div className="rounded-md border overflow-x-auto">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead className="sticky left-0 bg-background z-10">ID</TableHead>
                          <TableHead>Date Extraction</TableHead>
                          <TableHead>DOT</TableHead>
                          <TableHead>Code Actel</TableHead>
                          <TableHead>Code Client</TableHead>
                          <TableHead>Numéro Service</TableHead>
                          <TableHead>Service Relié</TableHead>
                          <TableHead>Nom Client</TableHead>
                          <TableHead>Username</TableHead>
                          <TableHead>L1 Code</TableHead>
                          <TableHead>L1 Description</TableHead>
                          <TableHead>L2 Code</TableHead>
                          <TableHead>L2 Description</TableHead>
                          <TableHead>L3 Code</TableHead>
                          <TableHead>L3 Description</TableHead>
                          <TableHead>Type Télécom</TableHead>
                          <TableHead>Type Offre</TableHead>
                          <TableHead>Nom Offre</TableHead>
                          <TableHead>Frais Location</TableHead>
                          <TableHead>Statut Abonné</TableHead>
                          <TableHead>Date Statut</TableHead>
                          <TableHead>Date Création</TableHead>
                          <TableHead>Date Activation</TableHead>
                          <TableHead>Date Expiration</TableHead>
                          <TableHead>CSR</TableHead>
                          <TableHead>Département</TableHead>
                          <TableHead>État</TableHead>
                          <TableHead>Zone</TableHead>
                          <TableHead>Ville</TableHead>
                          <TableHead>Grille</TableHead>
                          <TableHead>Rue</TableHead>
                          <TableHead>Numéro Rue</TableHead>
                          <TableHead>Bâtiment</TableHead>
                          <TableHead>Unité</TableHead>
                          <TableHead>Étage</TableHead>
                          <TableHead>Numéro Maison</TableHead>
                          <TableHead>Info Adresse</TableHead>
                          <TableHead>Province</TableHead>
                          <TableHead>District</TableHead>
                          <TableHead>Code Postal</TableHead>
                          <TableHead>ICCID</TableHead>
                          <TableHead>IMSI</TableHead>
                          <TableHead>Contact</TableHead>
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
                            <TableCell className="text-xs">
                              {record.extraction_date
                                ? new Date(record.extraction_date).toLocaleDateString("fr-FR")
                                : "-"}
                            </TableCell>
                            <TableCell>{record.dot_name || "-"}</TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.actel_code || "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.customer_code || "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.service_number || "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.related_service_number || "-"}
                            </TableCell>
                            <TableCell className="max-w-[200px] truncate">
                              {record.customer_full_name || "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.username || "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.customer_l1_code || "-"}
                            </TableCell>
                            <TableCell className="max-w-[150px] truncate">
                              {record.customer_l1_description || "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.customer_l2_code || "-"}
                            </TableCell>
                            <TableCell className="max-w-[150px] truncate">
                              {record.customer_l2_description || "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.customer_l3_code || "-"}
                            </TableCell>
                            <TableCell className="max-w-[150px] truncate">
                              {record.customer_l3_description || "-"}
                            </TableCell>
                            <TableCell>{record.telecom_type || "-"}</TableCell>
                            <TableCell>{record.offer_type || "-"}</TableCell>
                            <TableCell className="max-w-[200px] truncate">
                              {record.offer_name || "-"}
                            </TableCell>
                            <TableCell className="text-right">
                              {record.rental_fees
                                ? formatNumber(record.rental_fees)
                                : "-"}
                            </TableCell>
                            <TableCell>
                              <Badge variant="secondary">
                                {record.subscriber_status || "-"}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-xs">
                              {record.status_date
                                ? new Date(record.status_date).toLocaleDateString("fr-FR")
                                : "-"}
                            </TableCell>
                            <TableCell className="text-xs">
                              {record.creation_date
                                ? new Date(record.creation_date).toLocaleDateString("fr-FR")
                                : "-"}
                            </TableCell>
                            <TableCell className="text-xs">
                              {record.active_date
                                ? new Date(record.active_date).toLocaleDateString("fr-FR")
                                : "-"}
                            </TableCell>
                            <TableCell className="text-xs">
                              {record.expiry_date
                                ? new Date(record.expiry_date).toLocaleDateString("fr-FR")
                                : "-"}
                            </TableCell>
                            <TableCell>{record.csr_name || "-"}</TableCell>
                            <TableCell>{record.department_name || "-"}</TableCell>
                            <TableCell>{record.state || "-"}</TableCell>
                            <TableCell>{record.area || "-"}</TableCell>
                            <TableCell>{record.town || "-"}</TableCell>
                            <TableCell>{record.grid || "-"}</TableCell>
                            <TableCell className="max-w-[200px] truncate">
                              {record.street || "-"}
                            </TableCell>
                            <TableCell>{record.street_number || "-"}</TableCell>
                            <TableCell>{record.building_no || "-"}</TableCell>
                            <TableCell>{record.unit || "-"}</TableCell>
                            <TableCell>{record.floor || "-"}</TableCell>
                            <TableCell>{record.house_no || "-"}</TableCell>
                            <TableCell className="max-w-[200px] truncate">
                              {record.additional_address_info || "-"}
                            </TableCell>
                            <TableCell>{record.province || "-"}</TableCell>
                            <TableCell>{record.district || "-"}</TableCell>
                            <TableCell>{record.postal_code || "-"}</TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.iccid || "-"}
                            </TableCell>
                            <TableCell className="font-mono text-xs">
                              {record.imsi || "-"}
                            </TableCell>
                            <TableCell>{record.contact_number || "-"}</TableCell>
                            <TableCell className="text-xs">
                              {record.created_at
                                ? new Date(record.created_at).toLocaleString("fr-FR")
                                : "-"}
                            </TableCell>
                            <TableCell className="text-xs">
                              {record.updated_at
                                ? new Date(record.updated_at).toLocaleString("fr-FR")
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
                      {formatNumber(
                        Math.min(
                          (previewPage - 1) * previewPageSize + 1,
                          previewTotal
                        )
                      )}{" "}
                      -{" "}
                      {formatNumber(
                        Math.min(previewPage * previewPageSize, previewTotal)
                      )}{" "}
                      sur {formatNumber(previewTotal)})
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
                        onClick={() => setPreviewPage((p) => Math.max(1, p - 1))}
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
        )}
      </div>
    </div>
  );
};

export default EncaissementPage;
