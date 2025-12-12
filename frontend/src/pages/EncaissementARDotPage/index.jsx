import React, { useEffect, useMemo, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MultiSelect } from "@/components/ui/multi-select";
import { Badge } from "@/components/ui/badge";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ComposedChart,
  Line,
  LineChart,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import {
  Download,
  RefreshCw,
  Filter,
  X,
  BarChart3,
  Building,
  FileText,
  AlertCircle,
  Calendar,
  Percent,
} from "lucide-react";
import { toast } from "sonner";
import {
  getEncaissementOverview,
  getEncaissementByOrganisation,
  getEncaissementByDate,
  getEncaissementByEncaisseRate,
  getEncaissementFilters,
  getEncaissementRecords,
  exportEncaissementRecords,
} from "../../services/api";
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

// Formatage français avec séparateur de milliers et 2 décimales
const formatNumber = (value) => {
  if (value === null || value === undefined || isNaN(value)) return "0,00";
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

const formatCurrency = (value) => {
  return `${formatNumber(value)} DZD`;
};

const formatPercent = (value) => {
  if (value === null || value === undefined || isNaN(value)) return "0,00%";
  return `${formatNumber(value)}%`;
};

// Couleurs matching les images
const COLORS = {
  primary: "#4A90E2", // Bleu
  secondary: "#E2734A", // Orange
  success: "#5CB85C", // Vert
  danger: "#D9534F", // Rouge
};

// Sub-components
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

/**
 * Custom Tooltip pour les graphiques
 */
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-4 border-2 border-gray-300 rounded-lg shadow-xl">
        <p className="font-bold text-gray-900 mb-2">{label}</p>
        {payload.map((entry, index) => (
          <p
            key={index}
            style={{ color: entry.color }}
            className="text-sm font-semibold"
          >
            {entry.name}:{" "}
            {entry.name.includes("Taux")
              ? formatPercent(entry.value)
              : formatCurrency(entry.value)}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

/**
 * Main Encaissement AR DOT Page Component
 */
const EncaissementARDotPage = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [showFilters, setShowFilters] = useState(false);

  // Filter state
  const [filters, setFilters] = useState({
    organisation: [], // DOT names (multi-select)
    date_fact_start: "", // Date Fact start (month)
    date_fact_end: "", // Date Fact end (month)
    taux_encaissement_min: "", // Taux encaissement minimum
    taux_encaissement_max: "", // Taux encaissement maximum
    search: "", // Global search
    year: "", // Year filter
  });

  // Available filter options
  const [filterOptions, setFilterOptions] = useState({
    organisations: [],
    months: [],
    taux_ranges: [],
  });

  // Data state
  const [overview, setOverview] = useState({
    yearly_data: [],
    users: [],
    total_montant_ttc: 0,
    total_encaissement: 0,
    total_montant_restant: 0,
    taux_encaissement: 0,
    nombre_factures: 0,
  });

  // Computed overview based on selected year
  const displayOverview = useMemo(() => {
    if (
      !filters.year ||
      filters.year === "all" ||
      !overview.yearly_data ||
      overview.yearly_data.length === 0
    ) {
      // Return totals if no year selected
      return {
        total_montant_ttc: overview.total_montant_ttc || 0,
        total_encaissement: overview.total_encaissement || 0,
        total_montant_restant: overview.total_montant_restant || 0,
        taux_encaissement: overview.taux_encaissement || 0,
        nombre_factures: overview.nombre_factures || 0,
      };
    }

    // Find selected year data
    const yearData = overview.yearly_data.find((y) => y.year === filters.year);
    if (!yearData) {
      return {
        total_montant_ttc: 0,
        total_encaissement: 0,
        total_montant_restant: 0,
        taux_encaissement: 0,
        nombre_factures: 0,
      };
    }

    return {
      total_montant_ttc: yearData.total_montant_ttc || 0,
      total_encaissement: yearData.total_encaissement || 0,
      total_montant_restant: yearData.total_montant_restant || 0,
      taux_encaissement: yearData.taux_encaissement || 0,
      nombre_factures: yearData.nombre_factures || 0,
    };
  }, [filters.year, overview]);
  const [byOrganisation, setByOrganisation] = useState([]);
  const [byDateFact, setByDateFact] = useState([]);
  const [byTauxEncaissement, setByTauxEncaissement] = useState([]);

  // Preview data state
  const [previewData, setPreviewData] = useState([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewTotal, setPreviewTotal] = useState(0);
  const [previewPage, setPreviewPage] = useState(1);
  const [previewPageSize, setPreviewPageSize] = useState(10);

  /**
   * Fetch data
   */
  const fetchData = async (showRefreshing = false, overrideYear = null) => {
    if (showRefreshing) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      // Use overrideYear if provided (for immediate updates), otherwise use filters.year
      const yearToUse = overrideYear !== null ? overrideYear : filters.year;
      // Build filter params for API calls
      const filterParams = {
        organisation:
          filters.organisation.length > 0 ? filters.organisation : undefined,
        date_fact_start: filters.date_fact_start || undefined,
        date_fact_end: filters.date_fact_end || undefined,
        taux_encaissement_min: filters.taux_encaissement_min || undefined,
        taux_encaissement_max: filters.taux_encaissement_max || undefined,
        search: filters.search || undefined,
        year: yearToUse || undefined,
      };

      // Remove undefined values
      Object.keys(filterParams).forEach(
        (key) => filterParams[key] === undefined && delete filterParams[key]
      );

      // Load all data simultaneously
      // Fetch overview without year filter to get all available years for dropdown
      // This ensures the year dropdown always shows all years regardless of current filters
      const overviewParamsForYears = { ...filterParams };
      delete overviewParamsForYears.year; // Remove year to get all available years

      // Fetch both overviews: one without year (for dropdown) and one with year (for display)
      const [ovResForYears, ovResFiltered, orgRes, dateRes, tauxRes] =
        await Promise.all([
          getEncaissementOverview(overviewParamsForYears), // Get all years for dropdown
          getEncaissementOverview(filterParams), // Get filtered overview for display
          getEncaissementByOrganisation(filterParams),
          getEncaissementByDate(filterParams),
          getEncaissementByEncaisseRate(filterParams),
        ]);

      // Use the overview with all years for the dropdown
      if (ovResForYears.data && ovResForYears.data.yearly_data) {
        setOverview((prev) => ({
          ...prev,
          yearly_data: ovResForYears.data.yearly_data, // Always show all years in dropdown
          users: ovResForYears.data.users || prev.users,
        }));
      }

      // Use the filtered overview for display (totals, by_month, by_organisation)
      if (ovResFiltered.data) {
        setOverview((prev) => ({
          ...prev,
          total_montant_ttc: ovResFiltered.data.total_montant_ttc || 0,
          total_encaissement: ovResFiltered.data.total_encaissement || 0,
          total_montant_restant: ovResFiltered.data.total_montant_restant || 0,
          taux_encaissement: ovResFiltered.data.taux_encaissement || 0,
          nombre_factures: ovResFiltered.data.nombre_factures || 0,
        }));
      }

      // Update other data with filtered results
      setByOrganisation(orgRes.data || []);
      setByDateFact(dateRes.data || []);
      setByTauxEncaissement(tauxRes.data || []);

      if (showRefreshing) {
        toast.success("Données actualisées");
      }
    } catch (error) {
      console.error("Error fetching data:", error);
      toast.error("Erreur lors du chargement des données");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  /**
   * Fetch filters
   */
  const fetchFilters = async () => {
    try {
      const res = await getEncaissementFilters();

      setFilterOptions({
        organisations: res.data.organisations || [],
        months: res.data.months || [],
        taux_ranges: res.data.taux_ranges || [
          { label: "0-25%", min: 0, max: 25 },
          { label: "25-50%", min: 25, max: 50 },
          { label: "50-75%", min: 50, max: 75 },
          { label: "75-100%", min: 75, max: 100 },
          { label: "100%+", min: 100, max: 999999 },
        ],
      });
    } catch (error) {
      console.error("Error fetching filters:", error);
    }
  };

  useEffect(() => {
    fetchFilters();
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Note: Year filter change now triggers fetchData directly in onValueChange
  // This ensures immediate update without waiting for useEffect

  /**
   * CHART 1: Montant TTC & Encaissement par Organisation
   */
  const organisationChartData = useMemo(() => {
    return byOrganisation
      .map((item) => ({
        organisation: item.organisation || "Inconnu",
        "Montant TTC": item.total_montant_ttc || 0,
        Encaissement: item.total_encaissement || 0,
        "Taux (%)": item.taux_encaissement_moyen || 0,
      }))
      .sort((a, b) => b["Taux (%)"] - a["Taux (%)"])
      .slice(0, 30);
  }, [byOrganisation]);

  /**
   * CHART 2: Encaissement par Date Fact (Mois)
   */
  const dateFactChartData = useMemo(() => {
    // Backend already filters by year, so we just process the data
    if (!byDateFact || !Array.isArray(byDateFact) || byDateFact.length === 0) {
      return [];
    }

    return byDateFact
      .filter((item) => item != null) // Filter out null/undefined items
      .map((item) => ({
        mois: item.mois || item.date_fact || "Inconnu",
        "Montant TTC": item.total_montant_ttc || 0,
        Encaissement: item.total_encaissement || 0,
        "Taux (%)": item.taux_encaissement_moyen || 0,
      }))
      .sort((a, b) => a.mois.localeCompare(b.mois));
  }, [byDateFact]);

  /**
   * CHART 3: DOT et Taux d'encaissement
   */
  const tauxEncaissementChartData = useMemo(() => {
    return byTauxEncaissement
      .map((item) => ({
        range: item.taux_range || item.range || "Inconnu",
        count: item.count || 0,
        "Montant TTC": item.total_montant_ttc || 0,
        Encaissement: item.total_encaissement || 0,
      }))
      .sort((a, b) => {
        // Sort by taux range (0-25%, 25-50%, etc.)
        const aMin = parseInt(a.range.split("-")[0] || "0");
        const bMin = parseInt(b.range.split("-")[0] || "0");
        return aMin - bMin;
      });
  }, [byTauxEncaissement]);

  /**
   * CHART 4: Pie Chart - Encaissement par Mois (3D style)
   */
  const pieChartData = useMemo(() => {
    // Backend already filters by year, so we just process the data
    if (!byDateFact || !Array.isArray(byDateFact) || byDateFact.length === 0) {
      return [];
    }

    const validItems = byDateFact.filter((item) => item != null);
    const total = validItems.reduce(
      (sum, item) => sum + (item.total_encaissement || 0),
      0
    );

    return validItems
      .map((item) => {
        const value = item.total_encaissement || 0;
        const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
        return {
          name: item.mois || item.date_fact || "Inconnu",
          value: value,
          percentage: parseFloat(percentage),
        };
      })
      .filter((item) => item.value > 0) // Only show months with encaissement
      .sort((a, b) => b.value - a.value); // Sort by value descending
  }, [byDateFact]);

  // Extended color palette for pie chart
  const PIE_COLORS = [
    "#4A90E2", // Blue
    "#E2734A", // Orange
    "#5CB85C", // Green
    "#D9534F", // Red
    "#9B59B6", // Purple
    "#F39C12", // Yellow
    "#1ABC9C", // Turquoise
    "#E74C3C", // Crimson
    "#3498DB", // Light Blue
    "#2ECC71", // Emerald
    "#E67E22", // Carrot
    "#95A5A6", // Gray
  ];

  /**
   * Export handler
   */
  const handleExport = async (format = "xlsx") => {
    try {
      setExporting(true);

      const exportParams = { ...filters, format };

      // Keep organisation as array if it's an array (backend can handle it)
      // Remove empty arrays
      if (
        Array.isArray(exportParams.organisation) &&
        exportParams.organisation.length === 0
      ) {
        delete exportParams.organisation;
      }

      // Remove empty strings and undefined values, but keep year if it's "all"
      Object.keys(exportParams).forEach((key) => {
        if (
          exportParams[key] === undefined ||
          exportParams[key] === "" ||
          exportParams[key] === null ||
          exportParams[key] === "all"
        ) {
          delete exportParams[key];
        }
      });

      console.log(
        "🚀 Starting encaissement export with filters:",
        exportParams
      );

      const response = await exportEncaissementRecords(exportParams);
      const mimeType =
        format === "xlsx"
          ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          : "text/csv";
      const blob = new Blob([response.data], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `encaissement_export_${
        new Date().toISOString().split("T")[0]
      }.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success("Export réussi");
    } catch (err) {
      console.error("❌ Export failed:", err);
      toast.error("Erreur lors de l'export");
    } finally {
      setExporting(false);
    }
  };

  const applyFilters = () => {
    fetchData();
    toast.success("Filtres appliqués");
  };

  const resetFilters = () => {
    setFilters({
      organisation: [],
      date_fact_start: "",
      date_fact_end: "",
      taux_encaissement_min: "",
      taux_encaissement_max: "",
      search: "",
      year: "",
    });
    toast.success("Filtres réinitialisés");
  };

  // Fetch preview data
  const fetchPreviewData = useCallback(async () => {
    if (activeTab !== "preview") return;

    try {
      setPreviewLoading(true);

      const params = {
        page: previewPage,
        page_size: previewPageSize,
      };

      // Add filters if needed
      if (filters.organisation && filters.organisation.length > 0) {
        params.organisation = filters.organisation.join(",");
      }

      // Add year filter
      if (filters.year) {
        params.year = filters.year;
      }

      const response = await getEncaissementRecords(params);

      setPreviewData(response.data?.items || []);
      setPreviewTotal(response.data?.total || 0);
    } catch (err) {
      console.error("Error fetching preview data:", err);
      toast.error("Erreur lors du chargement des données de prévisualisation");
    } finally {
      setPreviewLoading(false);
    }
  }, [activeTab, previewPage, previewPageSize, filters]);

  // Fetch preview data when tab changes or filters/page changes
  useEffect(() => {
    if (activeTab === "preview") {
      fetchPreviewData();
    }
  }, [activeTab, previewPage, previewPageSize, filters, fetchPreviewData]);

  const getActiveFilterCount = () => {
    return Object.values(filters).filter((v) => {
      if (Array.isArray(v)) return v.length > 0;
      return v && typeof v === "string" && v.trim() !== "";
    }).length;
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  const activeFilterCount = getActiveFilterCount();

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-3xl font-bold">Encaissement AR DOT</h1>
        <div className="flex flex-wrap items-center gap-2">
          {/* Year Filter Dropdown */}
          {overview.yearly_data && overview.yearly_data.length > 0 && (
            <div className="flex items-center gap-2">
              <Label
                htmlFor="year-filter"
                className="text-sm font-medium whitespace-nowrap"
              >
                Année:
              </Label>
              <Select
                value={filters.year || "all"}
                onValueChange={(value) => {
                  const yearValue = value === "all" ? "" : value;
                  setFilters((f) => ({
                    ...f,
                    year: yearValue,
                  }));
                  // IMPORTANT: pass year as 2nd arg (overrideYear) to avoid race with state update
                  fetchData(false, yearValue);
                }}
              >
                <SelectTrigger id="year-filter" className="w-40">
                  <SelectValue placeholder="Toutes" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Toutes les années</SelectItem>
                  {overview.yearly_data && overview.yearly_data.length > 0
                    ? overview.yearly_data
                        .sort((a, b) => b.year.localeCompare(a.year))
                        .map((yearData) => (
                          <SelectItem key={yearData.year} value={yearData.year}>
                            {yearData.year}
                          </SelectItem>
                        ))
                    : null}
                </SelectContent>
              </Select>
            </div>
          )}
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
            onClick={() => handleExport("csv")}
            disabled={exporting}
            className="bg-green-600 hover:bg-green-700"
          >
            <Download className="h-4 w-4 mr-2" />
            CSV
          </Button>
          <Button
            onClick={() => handleExport("xlsx")}
            disabled={exporting}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Download className="h-4 w-4 mr-2" />
            Excel
          </Button>
        </div>
      </div>

      {/* Hero Card - Total Encaissement */}
      <Card className="bg-gradient-to-r from-blue-500 to-blue-600 text-white">
        <CardContent className="pt-6">
          <div className="text-center">
            <div className="text-6xl font-bold mb-2">
              {formatCurrency(displayOverview.total_encaissement || 0)}
            </div>
            <div className="text-xl font-medium opacity-90">
              Encaissement Total{filters.year ? ` (${filters.year})` : ""}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Secondary Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-2">
          <CardContent className="pt-6 pb-6">
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-600">
                Montant TTC
              </div>
              <div className="text-3xl font-bold text-gray-900">
                {formatCurrency(displayOverview.total_montant_ttc || 0)}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-2">
          <CardContent className="pt-6 pb-6">
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-600">
                Encaissement
              </div>
              <div className="text-3xl font-bold text-gray-900">
                {formatCurrency(displayOverview.total_encaissement || 0)}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-2">
          <CardContent className="pt-6 pb-6">
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-600">
                Taux d'encaissement
              </div>
              <div className="text-3xl font-bold text-gray-900">
                {formatPercent(displayOverview.taux_encaissement || 0)}
              </div>
            </div>
          </CardContent>
        </Card>
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
                  <Label>Année</Label>
                  <Select
                    value={filters.year || "all"}
                    onValueChange={(value) => {
                      const yearValue = value === "all" ? "" : value;
                      setFilters((f) => ({
                        ...f,
                        year: yearValue,
                      }));
                      // IMPORTANT: pass year as 2nd arg (overrideYear) to avoid race with state update
                      fetchData(false, yearValue);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Toutes les années" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Toutes les années</SelectItem>
                      {overview.yearly_data && overview.yearly_data.length > 0
                        ? overview.yearly_data
                            .sort((a, b) => b.year.localeCompare(a.year))
                            .map((yearData) => (
                              <SelectItem
                                key={yearData.year}
                                value={yearData.year}
                              >
                                {yearData.year}
                              </SelectItem>
                            ))
                        : null}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label>DOT (Organisation)</Label>
                  <MultiSelect
                    options={filterOptions.organisations.map((name) => ({
                      label: name,
                      value: name,
                    }))}
                    selected={filters.organisation}
                    onChange={(values) =>
                      setFilters((f) => ({ ...f, organisation: values }))
                    }
                    placeholder="Tous les DOTs"
                  />
                </div>

                <div>
                  <Label>Mois (Date Fact) - Début</Label>
                  <Input
                    type="month"
                    value={filters.date_fact_start}
                    onChange={(e) =>
                      setFilters((f) => ({
                        ...f,
                        date_fact_start: e.target.value,
                      }))
                    }
                  />
                </div>

                <div>
                  <Label>Mois (Date Fact) - Fin</Label>
                  <Input
                    type="month"
                    value={filters.date_fact_end}
                    onChange={(e) =>
                      setFilters((f) => ({
                        ...f,
                        date_fact_end: e.target.value,
                      }))
                    }
                  />
                </div>

                <div>
                  <Label>Taux d'encaissement (%)</Label>
                  <div className="flex gap-2">
                    <Input
                      type="number"
                      placeholder="Min"
                      value={filters.taux_encaissement_min}
                      onChange={(e) =>
                        setFilters((f) => ({
                          ...f,
                          taux_encaissement_min: e.target.value,
                        }))
                      }
                    />
                    <Input
                      type="number"
                      placeholder="Max"
                      value={filters.taux_encaissement_max}
                      onChange={(e) =>
                        setFilters((f) => ({
                          ...f,
                          taux_encaissement_max: e.target.value,
                        }))
                      }
                    />
                  </div>
                </div>
              </div>

              {/* Search */}
              <div>
                <Label>Recherche Globale</Label>
                <Input
                  placeholder="Recherche dans tous les champs..."
                  value={filters.search}
                  onChange={(e) =>
                    setFilters((f) => ({ ...f, search: e.target.value }))
                  }
                />
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
                          year: "Année",
                          organisation: "DOT",
                          date_fact_start: "Date Fact Début",
                          date_fact_end: "Date Fact Fin",
                          taux_encaissement_min: "Taux Min",
                          taux_encaissement_max: "Taux Max",
                          search: "Recherche",
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
                                setFilters((f) => ({
                                  ...f,
                                  [key]: Array.isArray(value) ? [] : "",
                                }))
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
          { id: "organisation", label: "BY Organisation", icon: Building },
          { id: "date-fact", label: "BY Date Fact", icon: Calendar },
          {
            id: "taux-encaissement",
            label: "BY Taux d'encaissement",
            icon: Percent,
          },
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
            <Card>
              <CardHeader>
                <CardTitle>
                  Histogramme combiné (Encaissement et Montant TTC par mois de
                  Date Fact)
                </CardTitle>
              </CardHeader>
              <CardContent>
                {dateFactChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={450}>
                    <LineChart
                      data={dateFactChartData}
                      margin={{ bottom: 20, top: 20 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                      <XAxis
                        dataKey="mois"
                        angle={0}
                        textAnchor="middle"
                        style={{ fontSize: "12px" }}
                      />
                      <YAxis
                        tickFormatter={(value) =>
                          new Intl.NumberFormat("fr-FR", {
                            notation: "compact",
                          }).format(value)
                        }
                        style={{ fontSize: "12px" }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend
                        wrapperStyle={{ fontSize: "14px", paddingTop: "20px" }}
                      />
                      <Line
                        type="monotone"
                        dataKey="Montant TTC"
                        stroke={COLORS.primary}
                        strokeWidth={3}
                        dot={{ r: 5, fill: COLORS.primary }}
                        activeDot={{ r: 7 }}
                        name="Somme de Montant TTC"
                      />
                      <Line
                        type="monotone"
                        dataKey="Encaissement"
                        stroke={COLORS.secondary}
                        strokeWidth={3}
                        dot={{ r: 5, fill: COLORS.secondary }}
                        activeDot={{ r: 7 }}
                        name="Somme de Encaissement"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                ) : (
                  <EmptyState message="Aucune donnée disponible" />
                )}
              </CardContent>
            </Card>

            {/* Pie Chart - Secteur 3D (encaissement / mois) */}
            <Card>
              <CardHeader>
                <CardTitle>Secteur 3D (Encaissement / Mois)</CardTitle>
              </CardHeader>
              <CardContent>
                {pieChartData.length > 0 ? (
                  <div className="flex flex-col items-center">
                    <ResponsiveContainer width="100%" height={500}>
                      <PieChart>
                        <Pie
                          data={pieChartData}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, percentage }) =>
                            `${name}: ${percentage}%`
                          }
                          outerRadius={180}
                          fill="#8884d8"
                          dataKey="value"
                        >
                          {pieChartData.map((entry, index) => (
                            <Cell
                              key={`cell-${index}`}
                              fill={PIE_COLORS[index % PIE_COLORS.length]}
                            />
                          ))}
                        </Pie>
                        <Tooltip
                          formatter={(value, name, props) => [
                            `${formatCurrency(value)} (${
                              props.payload.percentage
                            }%)`,
                            "Encaissement",
                          ]}
                        />
                        <Legend
                          wrapperStyle={{
                            fontSize: "14px",
                            paddingTop: "20px",
                          }}
                          formatter={(value, entry) =>
                            `${entry.payload.name} (${entry.payload.percentage}%)`
                          }
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <EmptyState message="Aucune donnée disponible pour le graphique en secteurs" />
                )}
              </CardContent>
            </Card>
          </>
        )}

        {activeTab === "organisation" && (
          <Card>
            <CardHeader>
              <CardTitle>
                Encaissement par Organisation (Relation 1: DOT et Taux
                d'encaissement)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {organisationChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={700}>
                  <ComposedChart
                    data={organisationChartData}
                    layout="vertical"
                    margin={{ left: 120, right: 60 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      type="number"
                      tickFormatter={(value) =>
                        new Intl.NumberFormat("fr-FR", {
                          notation: "compact",
                        }).format(value)
                      }
                      style={{ fontSize: "12px" }}
                    />
                    <YAxis
                      dataKey="organisation"
                      type="category"
                      width={110}
                      tick={{ fontSize: 11 }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                      wrapperStyle={{ fontSize: "14px", paddingTop: "10px" }}
                    />
                    <Bar
                      dataKey="Montant TTC"
                      fill={COLORS.primary}
                      radius={[0, 4, 4, 0]}
                    />
                    <Bar
                      dataKey="Encaissement"
                      fill={COLORS.success}
                      radius={[0, 4, 4, 0]}
                    />
                    <Line
                      dataKey="Taux (%)"
                      stroke={COLORS.secondary}
                      strokeWidth={3}
                      dot={{ r: 4 }}
                      yAxisId="right"
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      domain={[0, 100]}
                      tickFormatter={(value) => `${value}%`}
                      style={{ fontSize: "12px" }}
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="Aucune donnée Organisation disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "date-fact" && (
          <Card>
            <CardHeader>
              <CardTitle>
                Encaissement par Date Fact (Relation 2: Mois et Taux
                d'encaissement)
              </CardTitle>
            </CardHeader>
            <CardContent>
              {dateFactChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={450}>
                  <ComposedChart
                    data={dateFactChartData}
                    margin={{ bottom: 20, right: 60 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="mois"
                      angle={0}
                      textAnchor="middle"
                      style={{ fontSize: "12px" }}
                    />
                    <YAxis
                      yAxisId="left"
                      tickFormatter={(value) =>
                        new Intl.NumberFormat("fr-FR", {
                          notation: "compact",
                        }).format(value)
                      }
                      style={{ fontSize: "12px" }}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      domain={[0, 100]}
                      tickFormatter={(value) => `${value}%`}
                      style={{ fontSize: "12px" }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                      wrapperStyle={{ fontSize: "14px", paddingTop: "10px" }}
                    />
                    <Bar
                      dataKey="Montant TTC"
                      fill={COLORS.primary}
                      radius={[4, 4, 0, 0]}
                      yAxisId="left"
                    />
                    <Bar
                      dataKey="Encaissement"
                      fill={COLORS.success}
                      radius={[4, 4, 0, 0]}
                      yAxisId="left"
                    />
                    <Line
                      dataKey="Taux (%)"
                      stroke={COLORS.secondary}
                      strokeWidth={3}
                      dot={{ r: 4 }}
                      yAxisId="right"
                      type="monotone"
                    />
                  </ComposedChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="Aucune donnée Date Fact disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "taux-encaissement" && (
          <Card>
            <CardHeader>
              <CardTitle>Distribution par Taux d'encaissement</CardTitle>
            </CardHeader>
            <CardContent>
              {tauxEncaissementChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={450}>
                  <BarChart
                    data={tauxEncaissementChartData}
                    margin={{ bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="range"
                      angle={0}
                      textAnchor="middle"
                      style={{ fontSize: "12px" }}
                    />
                    <YAxis
                      tickFormatter={(value) =>
                        new Intl.NumberFormat("fr-FR", {
                          notation: "compact",
                        }).format(value)
                      }
                      style={{ fontSize: "12px" }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Legend
                      wrapperStyle={{ fontSize: "14px", paddingTop: "10px" }}
                    />
                    <Bar
                      dataKey="Montant TTC"
                      fill={COLORS.primary}
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="Encaissement"
                      fill={COLORS.success}
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="Aucune donnée Taux disponible" />
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
                          <TableHead>Encaissement</TableHead>
                          <TableHead>Taux Encaissement</TableHead>
                          <TableHead>Montant Restant</TableHead>
                          <TableHead>Créé le</TableHead>
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
                            <TableCell className="text-right font-semibold text-green-600">
                              {record.encaissement
                                ? formatCurrency(record.encaissement)
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
                            <TableCell className="text-xs">
                              {record.created_at
                                ? new Date(record.created_at).toLocaleString(
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
        )}
      </div>
    </div>
  );
};

export default EncaissementARDotPage;
