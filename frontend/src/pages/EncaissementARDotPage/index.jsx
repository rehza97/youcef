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
  LabelList,
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
  Search,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { toast } from "sonner";
import {
  getEncaissementOverview,
  getEncaissementByOrganisation,
  getEncaissementByDate,
  getEncaissementByEncaisseRate,
  getEncaissementByTypFact,
  getEncaissementByDateRglt,
  getEncaissementFilters,
  getEncaissementRecords,
  exportEncaissementRecords,
  getEncaissementColumnValues,
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

// Excel-style Filter Component
const ExcelFilter = ({
  column,
  label,
  values = [],
  selected = [],
  onFilterChange,
  onFetchValues,
  loading = false,
}) => {
  const [open, setOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [tempSelected, setTempSelected] = useState(selected);

  // Initialize tempSelected when dropdown opens
  useEffect(() => {
    if (open) {
      setTempSelected(selected);
      if (values.length === 0 && !loading) {
        onFetchValues();
      }
    }
  }, [open, selected, values.length, loading, onFetchValues]);

  const filteredValues = values.filter((val) =>
    val.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleToggle = (value) => {
    setTempSelected((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  };

  const handleSelectAll = () => {
    if (tempSelected.length === filteredValues.length) {
      setTempSelected([]);
    } else {
      setTempSelected([...filteredValues]);
    }
  };

  const handleApply = () => {
    onFilterChange(tempSelected);
    setOpen(false);
    setSearchTerm("");
  };

  const handleClear = () => {
    setTempSelected([]);
    onFilterChange([]);
    setOpen(false);
    setSearchTerm("");
  };

  const hasFilter = selected.length > 0;

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <button
          className={`flex items-center gap-1 px-1 py-0.5 rounded hover:bg-gray-100 ${
            hasFilter ? "bg-blue-100 text-blue-700" : ""
          }`}
          onClick={(e) => {
            e.stopPropagation();
            setOpen(true);
          }}
        >
          <Filter className="h-3 w-3" />
          {hasFilter && (
            <span className="text-xs font-semibold">{selected.length}</span>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        className="w-64 max-h-96 overflow-hidden flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-2 border-b">
          <div className="relative">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Rechercher..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-8 h-8 text-sm"
            />
          </div>
        </div>
        <div className="p-2 border-b flex items-center justify-between">
          <button
            onClick={handleSelectAll}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            {tempSelected.length === filteredValues.length &&
            filteredValues.length > 0
              ? "Tout désélectionner"
              : "Tout sélectionner"}
          </button>
          <span className="text-xs text-muted-foreground">
            {tempSelected.length} sélectionné(s)
          </span>
        </div>
        <div className="overflow-y-auto flex-1 max-h-64">
          {loading ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              Chargement...
            </div>
          ) : filteredValues.length === 0 ? (
            <div className="p-4 text-center text-sm text-muted-foreground">
              Aucun résultat trouvé.
            </div>
          ) : (
            filteredValues.map((value) => (
              <DropdownMenuCheckboxItem
                key={value}
                checked={tempSelected.includes(value)}
                onCheckedChange={() => handleToggle(value)}
                className="text-sm"
              >
                {value}
              </DropdownMenuCheckboxItem>
            ))
          )}
        </div>
        <DropdownMenuSeparator />
        <div className="p-2 flex gap-2 justify-end border-t">
          <Button
            variant="outline"
            size="sm"
            onClick={handleClear}
            className="h-7 text-xs"
          >
            Effacer
          </Button>
          <Button size="sm" onClick={handleApply} className="h-7 text-xs">
            OK
          </Button>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

// Column definitions for Encaissement AR DOT table
const ENCAISSEMENT_COLUMNS = [
  {
    key: "organisation",
    label: "Organisation",
    filterable: true,
    sortable: true,
  },
  { key: "source", label: "Source", filterable: true, sortable: false },
  {
    key: "n_fact",
    label: "N. Fact",
    filterable: true,
    sortable: true,
    format: "mono",
  },
  { key: "typ_fact", label: "Typ Fact", filterable: true, sortable: false },
  {
    key: "date_fact",
    label: "Date Fact",
    filterable: true,
    sortable: true,
    format: "date",
  },
  {
    key: "client",
    label: "Client",
    filterable: true,
    sortable: false,
    format: "truncate",
  },
  {
    key: "n_client",
    label: "N Client",
    filterable: true,
    sortable: false,
    format: "mono",
  },
  {
    key: "montant_ht",
    label: "Montant HT",
    filterable: true,
    sortable: false,
    format: "number",
  },
  {
    key: "montant_taxe",
    label: "Montant Taxe",
    filterable: true,
    sortable: false,
    format: "number",
  },
  {
    key: "montant_ttc",
    label: "Montant TTC",
    filterable: true,
    sortable: false,
    format: "number",
  },
  {
    key: "encaissement",
    label: "Encaissement",
    filterable: true,
    sortable: false,
    format: "number",
  },
  {
    key: "taux_encaissement",
    label: "Taux Encaissement",
    filterable: true,
    sortable: false,
    format: "percent",
  },
  {
    key: "montant_restant",
    label: "Montant Restant",
    filterable: true,
    sortable: false,
    format: "number",
  },
];

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
  warning: "#FFC107", // Yellow
};

/**
 * Get color based on encaissement rate ranges
 * < 20%: Red (danger)
 * 20.01% to 49.99%: Yellow (warning)
 * 50% to 74.99%: Orange (secondary)
 * 75% to 99%: Blue (primary)
 * >= 100%: Green (success)
 */
const getColorByEncaissementRate = (taux) => {
  if (taux >= 100) {
    return COLORS.success; // Green for >= 100%
  } else if (taux >= 75) {
    return COLORS.primary; // Blue for 75% to 99%
  } else if (taux >= 50) {
    return COLORS.secondary; // Orange for 50% to 74.99%
  } else if (taux >= 20.01) {
    return COLORS.warning; // Yellow for 20.01% to 49.99%
  } else {
    return COLORS.danger; // Red for < 20%
  }
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
    const data = payload[0].payload;
    return (
      <div className="bg-white p-4 border-2 border-gray-300 rounded-lg shadow-xl">
        <p className="font-bold text-gray-900 mb-2">{label}</p>
        {payload.map((entry, index) => (
          <div key={index}>
            <p style={{ color: entry.color }} className="text-sm font-semibold">
              {entry.name}:{" "}
              {entry.name.includes("Taux")
                ? formatPercent(entry.value)
                : formatCurrency(entry.value)}
            </p>
            {data.percentage !== undefined && (
              <p className="text-sm text-gray-600 mt-1">
                Pourcentage: {formatPercent(data.percentage)}
              </p>
            )}
          </div>
        ))}
      </div>
    );
  }
  return null;
};

// Custom label component to display percentage on bars
const CustomLabel = (props) => {
  const { x, y, width, payload } = props;
  if (!payload || payload.percentage === undefined) return null;
  if (width < 30) return null; // Don't show label if bar is too small
  return (
    <text
      x={x + width / 2}
      y={y - 5}
      fill="#666"
      textAnchor="middle"
      fontSize={11}
      fontWeight="500"
    >
      {formatPercent(payload.percentage)}
    </text>
  );
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
  const [monthSortOrder, setMonthSortOrder] = useState("desc"); // "asc" or "desc"

  // Filter state
  const [filters, setFilters] = useState({
    organisation: [], // DOT names (multi-select)
    date_fact_start: "", // Date Fact start (month)
    date_fact_end: "", // Date Fact end (month)
    search: "", // Global search
    year: "", // Year filter
    typ_fact: [], // Type Fact filter (multi-select)
    date_rglt_start: "", // Date Règlement start (month)
    date_rglt_end: "", // Date Règlement end (month)
  });

  // Available filter options
  const [filterOptions, setFilterOptions] = useState({
    organisations: [],
    months: [],
    taux_ranges: [],
    typ_fact: [], // Type Fact options
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
  const [byTypFact, setByTypFact] = useState([]);
  const [byDateRglt, setByDateRglt] = useState([]);

  // Preview data state
  const [previewData, setPreviewData] = useState([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewTotal, setPreviewTotal] = useState(0);
  const [previewPage, setPreviewPage] = useState(1);
  const [previewPageSize, setPreviewPageSize] = useState(10);

  // Column filters and values for Excel-style filtering
  const [columnFilters, setColumnFilters] = useState({});
  const [columnValues, setColumnValues] = useState({});
  const [loadingColumnValues, setLoadingColumnValues] = useState({});
  const [orderBy, setOrderBy] = useState("date_fact");
  const [orderDirection, setOrderDirection] = useState("desc");

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
        date_fact_start:
          filters.date_fact_start && filters.date_fact_start.trim() !== ""
            ? filters.date_fact_start
            : undefined,
        date_fact_end:
          filters.date_fact_end && filters.date_fact_end.trim() !== ""
            ? filters.date_fact_end
            : undefined,
        search: filters.search || undefined,
        year: yearToUse || undefined,
        typ_fact: filters.typ_fact.length > 0 ? filters.typ_fact : undefined,
        date_rglt_start:
          filters.date_rglt_start && filters.date_rglt_start.trim() !== ""
            ? filters.date_rglt_start
            : undefined,
        date_rglt_end:
          filters.date_rglt_end && filters.date_rglt_end.trim() !== ""
            ? filters.date_rglt_end
            : undefined,
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
      const [
        ovResForYears,
        ovResFiltered,
        orgRes,
        dateRes,
        tauxRes,
        typFactRes,
        dateRgltRes,
      ] = await Promise.all([
        getEncaissementOverview(overviewParamsForYears), // Get all years for dropdown
        getEncaissementOverview(filterParams), // Get filtered overview for display
        getEncaissementByOrganisation(filterParams),
        getEncaissementByDate(filterParams),
        getEncaissementByEncaisseRate(filterParams),
        getEncaissementByTypFact(filterParams),
        getEncaissementByDateRglt(filterParams),
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
      setByTypFact(typFactRes.data || []);
      setByDateRglt(dateRgltRes.data || []);

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
        typ_fact: res.data.types_facture || res.data.typ_fact || [],
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
   * Sorted by Encaissement amount (highest to lowest) - same as BY C.A visualization
   * Shows all DOTs (no limit)
   */
  const organisationChartData = useMemo(() => {
    return byOrganisation
      .map((item) => ({
        organisation: item.organisation || "Inconnu",
        "Montant TTC": item.total_montant_ttc || 0,
        Encaissement: item.total_encaissement || 0,
        "Taux (%)": item.taux_encaissement_moyen || 0,
      }))
      .sort((a, b) => b.Encaissement - a.Encaissement); // Sort by Encaissement amount (highest to lowest)
  }, [byOrganisation]);

  /**
   * CHART 2: Encaissement par Date Fact (Mois)
   */
  const dateFactChartData = useMemo(() => {
    // Backend already filters by year, so we just process the data
    if (!byDateFact || !Array.isArray(byDateFact) || byDateFact.length === 0) {
      return [];
    }

    const data = byDateFact
      .filter((item) => item != null) // Filter out null/undefined items
      .map((item) => ({
        mois: item.mois || item.date_fact || "Inconnu",
        "Montant TTC": item.total_montant_ttc || 0,
        Encaissement: item.total_encaissement || 0,
        "Taux (%)": item.taux_encaissement_moyen || 0,
      }))
      .sort((a, b) => a.mois.localeCompare(b.mois));

    // Calculate total for percentage
    const total = data.reduce((sum, item) => sum + item.Encaissement, 0);
    return data.map((item) => ({
      ...item,
      percentage: total > 0 ? (item.Encaissement / total) * 100 : 0,
    }));
  }, [byDateFact]);

  /**
   * CHART 3: DOT et Taux d'encaissement
   * Shows encaissement rate by DOT, sorted from highest to lowest taux (same as BY Taux C.A)
   * Shows all DOTs, including those with zero encaissement
   */
  const tauxEncaissementChartData = useMemo(() => {
    return byOrganisation
      .map((item) => ({
        organisation: item.organisation || "Inconnu",
        "Montant TTC": item.total_montant_ttc || 0,
        Encaissement: item.total_encaissement || 0,
        taux: item.taux_encaissement_moyen || 0, // Taux d'encaissement - main chart value
      }))
      .sort((a, b) => b.taux - a.taux) // Sort by taux d'encaissement from high to low
      .map((item, index) => ({
        ...item,
        rank: index + 1, // Add ranking number (1-based)
        label: `${index + 1}. ${item.organisation}`, // Label with rank number
      }));
  }, [byOrganisation]);

  /**
   * CHART 4: Encaissement par Type Fact
   */
  const typFactChartData = useMemo(() => {
    const data = byTypFact
      .map((item) => ({
        typ_fact: item.typ_fact || "Inconnu",
        "Montant TTC": item.total_montant_ttc || 0,
        Encaissement: item.total_encaissement || 0,
        "Taux (%)": item.taux_encaissement_moyen || 0,
      }))
      .sort((a, b) => b.Encaissement - a.Encaissement);

    // Calculate total for percentage
    const total = data.reduce((sum, item) => sum + item.Encaissement, 0);
    return data.map((item) => ({
      ...item,
      percentage: total > 0 ? (item.Encaissement / total) * 100 : 0,
    }));
  }, [byTypFact]);

  /**
   * CHART 5: Encaissement par Date Règlement
   */
  const dateRgltChartData = useMemo(() => {
    if (!byDateRglt || !Array.isArray(byDateRglt) || byDateRglt.length === 0) {
      return [];
    }

    const data = byDateRglt
      .filter((item) => item != null)
      .map((item) => ({
        date_rglt: item.date_rglt || "Inconnu",
        "Montant TTC": item.total_montant_ttc || 0,
        Encaissement: item.total_encaissement || 0,
        "Taux (%)": item.taux_encaissement_moyen || 0,
      }))
      .sort((a, b) => a.date_rglt.localeCompare(b.date_rglt));

    // Calculate total for percentage
    const total = data.reduce((sum, item) => sum + item.Encaissement, 0);
    return data.map((item) => ({
      ...item,
      percentage: total > 0 ? (item.Encaissement / total) * 100 : 0,
    }));
  }, [byDateRglt]);

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
          sortKey: item.mois || item.date_fact || "0000-00", // For sorting by date
        };
      })
      .filter((item) => item.value > 0) // Only show months with encaissement
      .sort((a, b) => {
        // Sort by date (month) based on sort order
        return monthSortOrder === "desc"
          ? b.sortKey.localeCompare(a.sortKey)
          : a.sortKey.localeCompare(b.sortKey);
      });
  }, [byDateFact, monthSortOrder]);

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
      search: "",
      year: "",
      typ_fact: [],
      date_rglt_start: "",
      date_rglt_end: "",
    });
    toast.success("Filtres réinitialisés");
  };

  // Fetch column values for Excel filter
  const fetchColumnValues = useCallback(
    async (column) => {
      if (columnValues[column] || loadingColumnValues[column]) return;

      try {
        setLoadingColumnValues((prev) => ({ ...prev, [column]: true }));
        const response = await getEncaissementColumnValues(column);
        setColumnValues((prev) => ({
          ...prev,
          [column]: response.data?.values || [],
        }));
      } catch (err) {
        console.error(`Error fetching values for column ${column}:`, err);
        // If endpoint doesn't exist yet, set empty array
        setColumnValues((prev) => ({
          ...prev,
          [column]: [],
        }));
      } finally {
        setLoadingColumnValues((prev) => ({ ...prev, [column]: false }));
      }
    },
    [columnValues, loadingColumnValues]
  );

  // Handle column filter change
  const handleColumnFilterChange = (column, values) => {
    setColumnFilters((prev) => ({
      ...prev,
      [column]: values.length > 0 ? values : undefined,
    }));
    setPreviewPage(1); // Reset to first page when filter changes
  };

  // Handle column sort
  const handleColumnSort = (column) => {
    if (orderBy === column) {
      // Toggle direction
      setOrderDirection(orderDirection === "asc" ? "desc" : "asc");
    } else {
      setOrderBy(column);
      setOrderDirection("asc");
    }
    setPreviewPage(1);
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

      // Add main filters
      if (filters.organisation && filters.organisation.length > 0) {
        params.organisation = filters.organisation.join(",");
      }

      // Add year filter
      if (filters.year) {
        params.year = filters.year;
      }

      // Merge column filters with main filters
      Object.keys(columnFilters).forEach((key) => {
        if (
          columnFilters[key] &&
          Array.isArray(columnFilters[key]) &&
          columnFilters[key].length > 0
        ) {
          params[key] = columnFilters[key].join(",");
        }
      });

      // Add sorting
      if (orderBy) {
        params.sort_by = orderBy;
        params.sort_order = orderDirection;
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
  }, [
    activeTab,
    previewPage,
    previewPageSize,
    filters,
    columnFilters,
    orderBy,
    orderDirection,
  ]);

  // Fetch preview data when tab changes or filters/page changes
  useEffect(() => {
    if (activeTab === "preview") {
      fetchPreviewData();
    }
  }, [
    activeTab,
    previewPage,
    previewPageSize,
    filters,
    columnFilters,
    orderBy,
    orderDirection,
    fetchPreviewData,
  ]);

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
      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <Card className="border-2">
          <CardContent className="pt-6 pb-6">
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-600">
                Montant TTC
              </div>
              <div className="text-xl font-bold text-gray-900">
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
              <div className="text-xl font-bold text-gray-900">
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
              <div className="text-xl font-bold text-gray-900">
                {formatPercent(displayOverview.taux_encaissement || 0)}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-2">
          <CardContent className="pt-6 pb-6">
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-600">Créance</div>
              <div className="text-xl font-bold text-gray-900">
                {formatCurrency(
                  (displayOverview.total_montant_ttc || 0) -
                    (displayOverview.total_encaissement || 0)
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-2">
          <CardContent className="pt-6 pb-6">
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-600">
                Taux de créance
              </div>
              <div className="text-xl font-bold text-gray-900">
                {formatPercent(100 - (displayOverview.taux_encaissement || 0))}
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
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4">
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
                  <Label>Date Fact - Début</Label>
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
                  <Label>Date Fact - Fin</Label>
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
                  <Label>Type Fact</Label>
                  <MultiSelect
                    options={filterOptions.typ_fact.map((name) => ({
                      label: name,
                      value: name,
                    }))}
                    selected={filters.typ_fact}
                    onChange={(values) =>
                      setFilters((f) => ({ ...f, typ_fact: values }))
                    }
                    placeholder="Tous les types"
                  />
                </div>

                <div>
                  <Label>Date Règlement - Début</Label>
                  <Input
                    type="month"
                    value={filters.date_rglt_start}
                    onChange={(e) =>
                      setFilters((f) => ({
                        ...f,
                        date_rglt_start: e.target.value,
                      }))
                    }
                  />
                </div>

                <div>
                  <Label>Date Règlement - Fin</Label>
                  <Input
                    type="month"
                    value={filters.date_rglt_end}
                    onChange={(e) =>
                      setFilters((f) => ({
                        ...f,
                        date_rglt_end: e.target.value,
                      }))
                    }
                  />
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
                          typ_fact: "Type Fact",
                          date_rglt_start: "Date Règlement Début",
                          date_rglt_end: "Date Règlement Fin",
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
          { id: "organisation", label: "BY Encaissement", icon: Building },
          { id: "typ-fact", label: "BY Type Fact", icon: FileText },
          { id: "date-fact", label: "BY Date Fact", icon: Calendar },
          { id: "date-rglt", label: "BY Date règlement", icon: Calendar },
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
                <div className="flex items-center justify-between">
                  <CardTitle>Secteur 3D (Encaissement / Mois)</CardTitle>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setMonthSortOrder(
                        monthSortOrder === "desc" ? "asc" : "desc"
                      )
                    }
                    className="flex items-center gap-2"
                  >
                    {monthSortOrder === "desc" ? (
                      <ArrowDown className="h-4 w-4" />
                    ) : (
                      <ArrowUp className="h-4 w-4" />
                    )}
                    <span className="text-xs">
                      {monthSortOrder === "desc"
                        ? "Plus récent"
                        : "Plus ancien"}
                    </span>
                  </Button>
                </div>
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
              <CardTitle>Encaissement par Organisation</CardTitle>
            </CardHeader>
            <CardContent className="w-full px-0">
              {organisationChartData.length > 0 ? (
                <div className="w-full" style={{ width: "100%", minWidth: 0 }}>
                  <ResponsiveContainer
                    width="100%"
                    height={Math.max(
                      400,
                      Math.min(800, organisationChartData.length * 20)
                    )}
                  >
                    <BarChart
                      data={organisationChartData}
                      margin={{ left: 20, right: 20, top: 10, bottom: 140 }}
                      style={{ width: "100%", minWidth: 0 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                      <XAxis
                        dataKey="organisation"
                        angle={-45}
                        textAnchor="end"
                        height={140}
                        tick={{ fontSize: 11 }}
                        interval={0}
                      />
                      <YAxis
                        type="number"
                        tickFormatter={(value) =>
                          new Intl.NumberFormat("fr-FR", {
                            notation: "compact",
                            maximumFractionDigits: 1,
                          }).format(value)
                        }
                        style={{ fontSize: "12px" }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend
                        wrapperStyle={{ fontSize: "14px", paddingTop: "10px" }}
                      />
                      <Bar
                        dataKey="Encaissement"
                        fill={COLORS.primary}
                        radius={[4, 4, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <EmptyState message="Aucune donnée Organisation disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "date-fact" && (
          <Card>
            <CardHeader>
              <CardTitle>Encaissement par Date Fact (Mois)</CardTitle>
            </CardHeader>
            <CardContent>
              {dateFactChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={450}>
                  <BarChart
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
                      wrapperStyle={{ fontSize: "14px", paddingTop: "10px" }}
                    />
                    <Bar
                      dataKey="Encaissement"
                      fill={COLORS.primary}
                      radius={[4, 4, 0, 0]}
                    >
                      <LabelList content={<CustomLabel />} />
                    </Bar>
                  </BarChart>
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
              <CardTitle>DOT et Taux de Réalisation Encaissement</CardTitle>
              {/* Color Legend for Encaissement Rate */}
              <div className="flex items-center gap-3 sm:gap-4 flex-wrap mt-4 pt-4 border-t">
                <div className="flex items-center gap-1.5">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: COLORS.danger }}
                  />
                  <span className="text-xs text-muted-foreground">
                    &lt; 20%
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: COLORS.warning }}
                  />
                  <span className="text-xs text-muted-foreground">
                    20% - 50%
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: COLORS.secondary }}
                  />
                  <span className="text-xs text-muted-foreground">
                    50% - 75%
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: COLORS.primary }}
                  />
                  <span className="text-xs text-muted-foreground">
                    75% - 99.99%
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: COLORS.success }}
                  />
                  <span className="text-xs text-muted-foreground">≥ 100%</span>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {tauxEncaissementChartData.length > 0 ? (
                <ResponsiveContainer
                  width="100%"
                  height={Math.max(
                    400,
                    Math.min(800, tauxEncaissementChartData.length * 20)
                  )}
                >
                  <BarChart
                    data={tauxEncaissementChartData}
                    margin={{ left: 20, right: 20, top: 10, bottom: 140 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="label"
                      angle={-45}
                      textAnchor="end"
                      height={140}
                      tick={{ fontSize: 11 }}
                      interval={0}
                    />
                    <YAxis
                      type="number"
                      tickFormatter={(value) => `${value.toFixed(0)}%`}
                      style={{ fontSize: "12px" }}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const data = payload[0].payload;
                          return (
                            <div className="bg-white p-3 border rounded shadow-lg">
                              <p className="font-semibold">
                                {data.organisation}
                              </p>
                              <p className="text-sm">
                                Taux: {formatPercent(data.taux)}
                              </p>
                              <p className="text-sm">
                                Encaissement:{" "}
                                {formatCurrency(data.Encaissement)}
                              </p>
                              <p className="text-sm">
                                Montant TTC:{" "}
                                {formatCurrency(data["Montant TTC"])}
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                    <Bar dataKey="taux" radius={[4, 4, 0, 0]}>
                      {tauxEncaissementChartData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={getColorByEncaissementRate(entry.taux)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="Aucune donnée Taux disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "typ-fact" && (
          <Card>
            <CardHeader>
              <CardTitle>Encaissement par Type Fact</CardTitle>
            </CardHeader>
            <CardContent>
              {typFactChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={450}>
                  <BarChart
                    data={typFactChartData}
                    margin={{ bottom: 80, left: 20, top: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="typ_fact"
                      angle={-45}
                      textAnchor="end"
                      interval={0}
                      style={{ fontSize: "10px" }}
                      height={100}
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
                      dataKey="Encaissement"
                      fill={COLORS.primary}
                      radius={[4, 4, 0, 0]}
                    >
                      <LabelList content={<CustomLabel />} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="Aucune donnée Type Fact disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "date-rglt" && (
          <Card>
            <CardHeader>
              <CardTitle>Encaissement par Date Règlement (Mois)</CardTitle>
            </CardHeader>
            <CardContent>
              {dateRgltChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={450}>
                  <BarChart
                    data={dateRgltChartData}
                    margin={{ bottom: 20, top: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="date_rglt"
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
                      dataKey="Encaissement"
                      fill={COLORS.primary}
                      radius={[4, 4, 0, 0]}
                    >
                      <LabelList content={<CustomLabel />} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="Aucune donnée Date Règlement disponible" />
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
                          {ENCAISSEMENT_COLUMNS.map((col) => (
                            <TableHead
                              key={col.key}
                              className={
                                col.key === "id"
                                  ? "sticky left-0 bg-background z-10"
                                  : ""
                              }
                            >
                              <div className="flex items-center justify-between gap-1 min-w-[120px]">
                                <span className="text-xs font-medium flex-1 truncate">
                                  {col.label}
                                </span>
                                <div className="flex items-center gap-1">
                                  {col.sortable && (
                                    <button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleColumnSort(col.key);
                                      }}
                                      className="hover:text-primary p-0.5"
                                      title="Trier"
                                    >
                                      {orderBy === col.key
                                        ? orderDirection === "asc"
                                          ? "↑"
                                          : "↓"
                                        : "⇅"}
                                    </button>
                                  )}
                                  {col.filterable && (
                                    <ExcelFilter
                                      column={col.key}
                                      label={col.label}
                                      values={columnValues[col.key] || []}
                                      selected={columnFilters[col.key] || []}
                                      onFilterChange={(values) =>
                                        handleColumnFilterChange(
                                          col.key,
                                          values
                                        )
                                      }
                                      onFetchValues={() =>
                                        fetchColumnValues(col.key)
                                      }
                                      loading={loadingColumnValues[col.key]}
                                    />
                                  )}
                                </div>
                              </div>
                            </TableHead>
                          ))}
                          <TableHead>Créé le</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {previewData.map((record) => (
                          <TableRow key={record.id}>
                            <TableCell className="font-mono text-xs sticky left-0 bg-background z-10">
                              {record.id || "-"}
                            </TableCell>
                            {ENCAISSEMENT_COLUMNS.map((col) => {
                              const value = record[col.key];
                              let displayValue = "-";

                              if (value !== null && value !== undefined) {
                                if (col.format === "date") {
                                  displayValue = new Date(
                                    value
                                  ).toLocaleDateString("fr-FR");
                                } else if (col.format === "mono") {
                                  displayValue = value;
                                } else if (col.format === "number") {
                                  displayValue = formatCurrency(value);
                                } else if (col.format === "percent") {
                                  displayValue = formatPercent(value);
                                } else if (col.format === "truncate") {
                                  displayValue = value;
                                } else {
                                  displayValue = value;
                                }
                              }

                              return (
                                <TableCell
                                  key={col.key}
                                  className={
                                    col.format === "mono"
                                      ? "font-mono text-xs"
                                      : col.format === "number" ||
                                        col.format === "percent"
                                      ? "text-right"
                                      : col.format === "truncate"
                                      ? "max-w-[200px] truncate"
                                      : col.format === "date"
                                      ? "text-xs"
                                      : ""
                                  }
                                >
                                  {displayValue}
                                </TableCell>
                              );
                            })}
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
