import React, { useEffect, useMemo, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MultiSelect } from "@/components/ui/multi-select";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Checkbox } from "@/components/ui/checkbox";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";
import {
  getRevenueOverview,
  getRevenueByAccount,
  getRevenueByOrg,
  getRevenueByTypeFact,
  getRevenueByMonth,
  getRevenueByTauxCA,
  getRevenueFilters,
  exportRevenueData,
  startRevenueExport,
  downloadRevenueExport,
  getRevenueExportStatus,
  getRevenuePreviewData,
  getRevenueObjectivesPreview,
  getAccountDescriptionsPreview,
  getRevenueColumnValues,
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
  Download,
  RefreshCw,
  TrendingUp,
  Target,
  DollarSign,
  Filter,
  X,
  BarChart3,
  Building,
  FileText,
  AlertCircle,
  ChevronDown,
  Search,
  CheckCircle2,
  XCircle,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { useProcessing } from "../../contexts/ProcessingContext";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

// Formatage français avec séparateur de milliers et 2 décimales
const formatNumber = (value) => {
  if (value === null || value === undefined || isNaN(value)) return "0,00";
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
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
 * Get color based on achievement rate ranges
 * < 20%: Red (danger)
 * 20.01% to 49.99%: Yellow (warning)
 * 50% to 74.99%: Orange (secondary)
 * 75% to 99.99%: Blue (primary)
 * >= 100%: Green (success)
 */
const getColorByAchievementRate = (taux) => {
  if (taux >= 100) {
    return COLORS.success; // Green for >= 100%
  } else if (taux >= 75) {
    return COLORS.primary; // Blue for 75% to 99.99%
  } else if (taux >= 50) {
    return COLORS.secondary; // Orange for 50% to 74.99%
  } else if (taux >= 20.01) {
    return COLORS.warning; // Yellow for 20.01% to 49.99%
  } else {
    return COLORS.danger; // Red for < 20%
  }
};

// Sub-components
const OverviewCard = ({ title, value, icon: Icon, subtitle }) => (
  <Card>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
      {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
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
              {entry.name}: {formatNumber(entry.value)} DZD
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

const CustomTooltipPercent = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload; // Get full data object
    return (
      <div className="bg-white p-4 border-2 border-gray-300 rounded-lg shadow-xl">
        <p className="font-bold text-gray-900 mb-2">{data.dot || label}</p>
        <p
          style={{ color: payload[0].color }}
          className="text-sm font-semibold mb-1"
        >
          Taux de réalisation: {formatPercent(payload[0].value)}
        </p>
        {data.objectif_ca > 0 && (
          <p className="text-sm text-gray-700">
            Objectif C.A: {formatNumber(data.objectif_ca)} DZD
          </p>
        )}
        {data.total_revenue > 0 && (
          <p className="text-sm text-gray-700">
            Chiffre d'Affaires: {formatNumber(data.total_revenue)} DZD
          </p>
        )}
      </div>
    );
  }
  return null;
};

const CustomTooltipObjective = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload; // Get full data object
    return (
      <div className="bg-white p-4 border-2 border-gray-300 rounded-lg shadow-xl">
        <p className="font-bold text-gray-900 mb-2">{data.dot || label}</p>
        <p
          style={{ color: payload[0].color }}
          className="text-sm font-semibold mb-1"
        >
          Chiffre d'affaires: {formatNumber(payload[0].value)} DZD
        </p>
        {data.objectif_ca > 0 && (
          <p className="text-sm text-gray-700">
            Objectif C.A: {formatNumber(data.objectif_ca)} DZD
          </p>
        )}
        {data.taux > 0 && (
          <p className="text-sm text-gray-700">
            Taux de réalisation: {formatPercent(data.taux)}
          </p>
        )}
      </div>
    );
  }
  return null;
};

// Column definitions for revenue_journal table - ALL columns are filterable
// Ordered as specified by user
const REVENUE_JOURNAL_COLUMNS = [
  { key: "org_name", label: "Org Name", filterable: true, sortable: true },
  { key: "origine", label: "Origine", filterable: true, sortable: false },
  {
    key: "n_fact",
    label: "N Fact",
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
    key: "n_client",
    label: "N Client",
    filterable: true,
    sortable: false,
    format: "mono",
  },
  {
    key: "client",
    label: "Client",
    filterable: true,
    sortable: false,
    format: "truncate",
  },
  { key: "delai_paie", label: "Delai Paie", filterable: true, sortable: false },
  { key: "devise", label: "Devise", filterable: true, sortable: false },
  {
    key: "obj_fact",
    label: "Obj Fact",
    filterable: true,
    sortable: false,
    format: "truncate",
  },
  {
    key: "cpt_comptable",
    label: "Cpt Comptable",
    filterable: true,
    sortable: false,
    format: "mono",
  },
  {
    key: "date_facture_gl",
    label: "Date facture GL",
    filterable: true,
    sortable: false,
    format: "date",
  },
  {
    key: "date_gl",
    label: "Date GL",
    filterable: true,
    sortable: true,
    format: "date",
  },
  {
    key: "periode_de_facturation",
    label: "Periode de facturation",
    filterable: true,
    sortable: false,
  },
  {
    key: "reference",
    label: "Reference",
    filterable: true,
    sortable: false,
    format: "truncate",
  },
  {
    key: "termine_flag",
    label: "Termine Flag",
    filterable: true,
    sortable: false,
    format: "boolean",
  },
  {
    key: "tax_amount",
    label: "Tax Amount",
    filterable: true,
    sortable: false,
    format: "number",
  },
  { key: "creer_par", label: "Creer Par", filterable: true, sortable: false },
  { key: "n_ligne", label: "N Ligne", filterable: true, sortable: false },
  {
    key: "description_ligne_de_produit",
    label: "Description (ligne de produit)",
    filterable: true,
    sortable: false,
    format: "truncate",
  },
  { key: "uom", label: "Uom", filterable: true, sortable: false },
  {
    key: "qte",
    label: "Qte",
    filterable: true,
    sortable: false,
    format: "number",
  },
  {
    key: "prix_uni",
    label: "Prix Uni",
    filterable: true,
    sortable: false,
    format: "number",
  },
  {
    key: "taux_change",
    label: "Taux Change",
    filterable: true,
    sortable: false,
    format: "number",
  },
  {
    key: "mnt_ht",
    label: "Mnt Ht",
    filterable: true,
    sortable: false,
    format: "number",
  },
  { key: "tax", label: "Tax", filterable: true, sortable: false },
  {
    key: "mnt_tax",
    label: "Mnt Tax",
    filterable: true,
    sortable: false,
    format: "number",
  },
  {
    key: "mnt_ttc",
    label: "Mnt Ttc",
    filterable: true,
    sortable: false,
    format: "number",
  },
  {
    key: "memo_line_id",
    label: "Memo Line Id",
    filterable: true,
    sortable: false,
  },
  {
    key: "chiffre_aff_exe_dzd",
    label: "Chiffre Aff Exe Dzd",
    filterable: true,
    sortable: true,
    format: "number",
  },
  // Additional columns not in the specified list (added at the end)
  { key: "id", label: "ID", filterable: true, sortable: true, format: "mono" },
  {
    key: "file_upload_id",
    label: "File Upload ID",
    filterable: true,
    sortable: false,
  },
  { key: "dot_id", label: "DOT ID", filterable: true, sortable: false },
  {
    key: "tva",
    label: "TVA",
    filterable: true,
    sortable: false,
    format: "percent",
  },
  {
    key: "chiffre_aff_exe_dzd_ttc",
    label: "Chiffre Aff Exe DZD TTC",
    filterable: true,
    sortable: false,
    format: "number",
  },
  {
    key: "taux_realisation_ca",
    label: "Taux Réalisation CA",
    filterable: true,
    sortable: true,
    format: "percent",
  },
  {
    key: "account_description_id",
    label: "Account Desc ID",
    filterable: true,
    sortable: false,
  },
  {
    key: "revenue_objective_id",
    label: "Revenue Obj ID",
    filterable: true,
    sortable: false,
  },
  {
    key: "is_anomaly",
    label: "Is Anomaly",
    filterable: true,
    sortable: false,
    format: "boolean",
  },
  {
    key: "anomaly_reason",
    label: "Anomaly Reason",
    filterable: true,
    sortable: false,
    format: "truncate",
  },
  {
    key: "created_at",
    label: "Créé le",
    filterable: true,
    sortable: true,
    format: "datetime",
  },
  {
    key: "updated_at",
    label: "Modifié le",
    filterable: true,
    sortable: false,
    format: "datetime",
  },
];

/**
 * Main Revenue Page Component
 */
const RevenuePage = () => {
  // WebSocket context
  const { subscribeTask } = useProcessing();

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState({
    isOpen: false,
    taskId: null,
    status: "idle",
    progress: 0,
    message: "",
    filename: null,
    downloadUrl: null,
  });
  const [exportStatus, setExportStatus] = useState("");
  const [activeTab, setActiveTab] = useState("overview");
  const [showFilters, setShowFilters] = useState(false);

  // Filter state
  const [filters, setFilters] = useState({
    org_name: [], // DOT names (multi-select)
    typ_fact: [], // Type Fact (multi-select)
    date_fact_start: "", // Date Fact start (month)
    date_fact_end: "", // Date Fact end (month)
    date_gl_start: "", // Date GL start (month)
    date_gl_end: "", // Date GL end (month)
    cpt_comptable: [], // Cpt Comptable codes (multi-select)
    taux_ca_min: "", // Taux CA minimum
    taux_ca_max: "", // Taux CA maximum
    search: "", // Global search
  });

  // Available filter options
  const [filterOptions, setFilterOptions] = useState({
    org_names: [],
    typ_fact_list: [],
    date_fact_months: [],
    months: [], // Date GL months
    cpt_comptable_list: [],
    achievement_rate_ranges: [],
  });

  // Data state
  const [overview, setOverview] = useState({
    total_revenue: 0,
    total_revenue_ttc: 0,
    total_records: 0,
    by_org_name: {},
    by_month: {},
    by_month_objective: {},
    total_objective: 0,
    anomalies_count: 0,
  });
  const [byAccount, setByAccount] = useState([]);
  const [byOrg, setByOrg] = useState([]);
  const [byTypeFact, setByTypeFact] = useState([]);
  const [byMonth, setByMonth] = useState([]);
  const [byTauxCA, setByTauxCA] = useState([]);

  // Preview data state
  const [previewData, setPreviewData] = useState([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewTotal, setPreviewTotal] = useState(0);
  const [previewPage, setPreviewPage] = useState(1);
  const [previewPageSize, setPreviewPageSize] = useState(10);
  const [previewTableType, setPreviewTableType] = useState("journal"); // "journal", "objectives", "account-descriptions"

  // Column filters and values
  const [columnFilters, setColumnFilters] = useState({});
  const [columnValues, setColumnValues] = useState({});
  const [loadingColumnValues, setLoadingColumnValues] = useState({});
  const [orderBy, setOrderBy] = useState("date_gl");
  const [orderDirection, setOrderDirection] = useState("desc");

  /**
   * Fetch data
   */
  const fetchData = async (showRefreshing = false) => {
    if (showRefreshing) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      // Build filter params for API calls
      const filterParams = {
        org_name: filters.org_name.length > 0 ? filters.org_name : undefined,
        typ_fact: filters.typ_fact.length > 0 ? filters.typ_fact : undefined,
        cpt_comptable:
          filters.cpt_comptable.length > 0 ? filters.cpt_comptable : undefined,
        start_date: filters.date_gl_start || undefined,
        end_date: filters.date_gl_end || undefined,
        start_date_fact: filters.date_fact_start || undefined,
        end_date_fact: filters.date_fact_end || undefined,
        taux_ca_min: filters.taux_ca_min || undefined,
        taux_ca_max: filters.taux_ca_max || undefined,
        search: filters.search || undefined,
      };

      // Log filter params before sending
      console.log("🔍 [FRONTEND] Filter params before cleanup:", {
        cpt_comptable: filterParams.cpt_comptable,
        cpt_comptable_type: typeof filterParams.cpt_comptable,
        cpt_comptable_isArray: Array.isArray(filterParams.cpt_comptable),
        cpt_comptable_length: filterParams.cpt_comptable?.length,
        all_filters: filterParams,
      });

      // Remove undefined values
      Object.keys(filterParams).forEach(
        (key) => filterParams[key] === undefined && delete filterParams[key]
      );

      console.log("🔍 [FRONTEND] Filter params after cleanup:", {
        cpt_comptable: filterParams.cpt_comptable,
        cpt_comptable_type: typeof filterParams.cpt_comptable,
        cpt_comptable_isArray: Array.isArray(filterParams.cpt_comptable),
        cpt_comptable_length: filterParams.cpt_comptable?.length,
        all_filters: filterParams,
      });

      // Load all data simultaneously
      const [ovRes, orgRes, accRes, typeFactRes, monthRes, tauxCARes] =
        await Promise.all([
          getRevenueOverview(filterParams),
          getRevenueByOrg(filterParams),
          getRevenueByAccount(filterParams),
          getRevenueByTypeFact(filterParams),
          getRevenueByMonth(filterParams),
          getRevenueByTauxCA(filterParams),
        ]);

      setOverview(ovRes.data || {});
      setByOrg(orgRes.data || []);
      setByAccount(accRes.data || []);
      setByTypeFact(typeFactRes.data || []);
      setByMonth(monthRes.data || []);
      setByTauxCA(tauxCARes.data || []);

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
      const res = await getRevenueFilters();

      setFilterOptions({
        org_names: res.data.org_names || [],
        typ_fact_list: res.data.typ_fact_list || [],
        date_fact_months: res.data.date_fact_months || [],
        months: res.data.months || [], // Date GL months
        cpt_comptable_list: res.data.cpt_comptable_list || [],
        achievement_rate_ranges: res.data.achievement_rate_ranges || [
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

  /**
   * Calculate global achievement rate
   */
  const globalAchievementRate = useMemo(() => {
    const totalRevenue = overview.total_revenue || 0;
    const totalObjective = overview.total_objective || 0;

    if (totalObjective === 0) return 0;
    return (totalRevenue / totalObjective) * 100;
  }, [overview]);

  /**
   * CHART 1: C.A vs Objectif par mois
   */
  const monthlyChartData = useMemo(() => {
    const months = [
      ...new Set([
        ...Object.keys(overview.by_month || {}),
        ...Object.keys(overview.by_month_objective || {}),
      ]),
    ].sort();

    return months.map((month) => {
      const date = new Date(month + "-01");
      const monthName = date.toLocaleString("fr-FR", { month: "short" });

      return {
        mois: monthName,
        "Somme de_Chiffre d'affaires": overview.by_month[month] || 0,
        "Somme de_Objectif C.A": overview.by_month_objective[month] || 0,
      };
    });
  }, [overview.by_month, overview.by_month_objective]);

  /**
   * CHART 2: Description Cpt Comptable with percentages
   */
  const accountChartData = useMemo(() => {
    const data = byAccount
      .map((item) => ({
        compte: (item.description || item.cpt_comptable || "Inconnu").substring(
          0,
          50
        ),
        Total: item.total_revenue || 0,
      }))
      .sort((a, b) => b.Total - a.Total)
      .slice(0, 20);

    const total = data.reduce((sum, item) => sum + item.Total, 0);
    return data.map((item) => ({
      ...item,
      percentage: total > 0 ? (item.Total / total) * 100 : 0,
    }));
  }, [byAccount]);

  /**
   * CHART: BY Type Fact with percentages
   */
  const typeFactChartData = useMemo(() => {
    const total = byTypeFact.reduce(
      (sum, item) => sum + (item.total_revenue || 0),
      0
    );
    return byTypeFact.map((item) => ({
      ...item,
      percentage: total > 0 ? ((item.total_revenue || 0) / total) * 100 : 0,
    }));
  }, [byTypeFact]);

  /**
   * CHART: BY Date GL with percentages
   */
  const monthChartData = useMemo(() => {
    const total = byMonth.reduce(
      (sum, item) => sum + (item.total_revenue || 0),
      0
    );
    return byMonth.map((item) => ({
      ...item,
      percentage: total > 0 ? ((item.total_revenue || 0) / total) * 100 : 0,
    }));
  }, [byMonth]);

  /**
   * CHART: DOT et Chiffre d'affaires (CA)
   * Shows revenue by DOT, sorted from highest to lowest CA
   */
  const dotCAChartData = useMemo(() => {
    return byOrg
      .map((item) => ({
        dot: item.org_name || "Inconnu",
        objectif_ca: item.objective || 0, // Objective for tooltip
        taux: item.achievement_rate || 0, // Achievement rate for tooltip
        total_revenue: item.total_revenue || 0, // Chiffre d'affaires (CA) - main chart value
      }))
      .filter((item) => item.total_revenue > 0) // Only show DOTs with revenue
      .sort((a, b) => b.total_revenue - a.total_revenue) // Sort by CA from high to low
      .map((item, index) => ({
        ...item,
        rank: index + 1, // Add ranking number (1-based)
        label: `${index + 1}. ${item.dot}`, // Label with rank number
      }));
  }, [byOrg]);

  /**
   * CHART: DOT et Taux de Réalisation C.A
   * Shows achievement rate by DOT, sorted from highest to lowest taux
   */
  const dotTauxChartData = useMemo(() => {
    return byOrg
      .map((item) => ({
        dot: item.org_name || "Inconnu",
        objectif_ca: item.objective || 0, // Objective for tooltip
        taux: item.achievement_rate || 0, // Achievement rate - main chart value
        total_revenue: item.total_revenue || 0, // Total revenue for tooltip
      }))
      .filter((item) => item.total_revenue > 0) // Only show DOTs with revenue
      .sort((a, b) => b.taux - a.taux) // Sort by achievement rate from high to low
      .map((item, index) => ({
        ...item,
        rank: index + 1, // Add ranking number (1-based)
        label: `${index + 1}. ${item.dot}`, // Label with rank number
      }));
  }, [byOrg]);

  /**
   * Export handler - uses async export with "both" mode (normal + anomalies)
   */
  const handleExport = async (format = "xlsx") => {
    try {
      setExporting(true);

      // Map filter names to API parameter names
      const exportParams = {
        format,
        org_name:
          filters.org_name.length > 0
            ? Array.isArray(filters.org_name)
              ? filters.org_name.join(",")
              : filters.org_name
            : undefined,
        typ_fact:
          filters.typ_fact.length > 0
            ? Array.isArray(filters.typ_fact)
              ? filters.typ_fact.join(",")
              : filters.typ_fact
            : undefined,
        cpt_comptable:
          filters.cpt_comptable.length > 0
            ? Array.isArray(filters.cpt_comptable)
              ? filters.cpt_comptable.join(",")
              : filters.cpt_comptable
            : undefined,
        start_date: filters.date_gl_start || undefined,
        end_date: filters.date_gl_end || undefined,
        start_date_fact: filters.date_fact_start || undefined,
        end_date_fact: filters.date_fact_end || undefined,
        taux_ca_min: filters.taux_ca_min || undefined,
        taux_ca_max: filters.taux_ca_max || undefined,
        search: filters.search || undefined,
      };

      // Log filter params BEFORE cleanup
      console.log("🔍 [EXPORT] Filter params BEFORE cleanup:", {
        date_gl_start: filters.date_gl_start,
        date_gl_end: filters.date_gl_end,
        date_fact_start: filters.date_fact_start,
        date_fact_end: filters.date_fact_end,
        search: filters.search,
        exportParams_start_date: exportParams.start_date,
        exportParams_end_date: exportParams.end_date,
        exportParams_start_date_fact: exportParams.start_date_fact,
        exportParams_end_date_fact: exportParams.end_date_fact,
        exportParams_search: exportParams.search,
      });

      // Remove empty strings and undefined values
      Object.keys(exportParams).forEach((key) => {
        if (
          exportParams[key] === undefined ||
          exportParams[key] === "" ||
          exportParams[key] === null
        ) {
          delete exportParams[key];
        }
      });

      console.log(
        "🚀 [EXPORT] Starting async revenue export with filters AFTER cleanup:",
        exportParams
      );

      // Start async export with "both" mode to get normal + anomalies
      const response = await startRevenueExport(exportParams, "both");

      const taskId = response.data.task_id;

      // Open progress dialog
      setExportProgress({
        isOpen: true,
        taskId,
        status: "processing",
        progress: 0,
        message: "Démarrage de l'export...",
        filename: null,
        downloadUrl: null,
      });

      toast.info("Export démarré en arrière-plan");
    } catch (err) {
      console.error("❌ Export failed:", err);
      toast.error("Erreur lors du démarrage de l'export");
    } finally {
      setExporting(false);
    }
  };

  const handleDownloadExport = async () => {
    try {
      const response = await downloadRevenueExport(exportProgress.taskId);

      // Response is a blob
      const blob = response.data;
      const filename =
        exportProgress.filename ||
        `revenue_export_${new Date().toISOString().split("T")[0]}.zip`;

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success("Export téléchargé avec succès");
      setExportProgress((prev) => ({ ...prev, isOpen: false }));
    } catch (error) {
      toast.error("Erreur lors du téléchargement de l'export");
    }
  };

  // WebSocket listener for export progress
  useEffect(() => {
    const handleExportUpdate = (message) => {
      if (
        message.type === "processing_update" &&
        message.task_id === exportProgress.taskId
      ) {
        const updateData = message.data;
        setExportProgress((prev) => ({
          ...prev,
          status: updateData.status || prev.status,
          progress: updateData.progress || prev.progress,
          message: updateData.message || prev.message,
          filename: updateData.filename || prev.filename,
          downloadUrl: updateData.download_url || prev.downloadUrl,
        }));
      }
    };

    if (exportProgress.taskId && subscribeTask) {
      subscribeTask(exportProgress.taskId, handleExportUpdate);
    }

    return () => {
      // Cleanup handled by ProcessingContext
    };
  }, [exportProgress.taskId, subscribeTask]);

  const applyFilters = () => {
    // Fetch all data with current filters - this will update all tabs
    fetchData();
    toast.success("Filtres appliqués");
  };

  const resetFilters = () => {
    setFilters({
      org_name: [],
      typ_fact: [],
      date_fact_start: "",
      date_fact_end: "",
      date_gl_start: "",
      date_gl_end: "",
      cpt_comptable: [],
      taux_ca_min: "",
      taux_ca_max: "",
      search: "",
    });
    toast.success("Filtres réinitialisés");
  };

  // Fetch preview data
  const fetchPreviewData = useCallback(async () => {
    if (activeTab !== "preview") return;

    try {
      setPreviewLoading(true);

      const offset = (previewPage - 1) * previewPageSize;

      let response;
      if (previewTableType === "objectives") {
        response = await getRevenueObjectivesPreview(
          { dot_name: filters.search },
          previewPageSize,
          offset
        );
      } else if (previewTableType === "account-descriptions") {
        response = await getAccountDescriptionsPreview(
          {
            search: filters.search || undefined,
            cpt_comptable:
              filters.cpt_comptable.length > 0
                ? filters.cpt_comptable
                : undefined,
          },
          previewPageSize,
          offset
        );
      } else {
        // For "journal" - revenue_journal table
        // Build filter params - merge main filters with column filters
        const filterParams = {
          ...columnFilters, // Include all column-specific filters
          org_name:
            filters.org_name.length > 0
              ? filters.org_name
              : columnFilters.org_name || undefined,
          typ_fact:
            filters.typ_fact.length > 0
              ? filters.typ_fact
              : columnFilters.typ_fact || undefined,
          cpt_comptable:
            filters.cpt_comptable.length > 0
              ? filters.cpt_comptable
              : columnFilters.cpt_comptable || undefined,
          start_date: filters.date_gl_start || undefined,
          end_date: filters.date_gl_end || undefined,
          start_date_fact: filters.date_fact_start || undefined,
          end_date_fact: filters.date_fact_end || undefined,
          taux_ca_min:
            filters.taux_ca_min || columnFilters.taux_ca_min || undefined,
          taux_ca_max:
            filters.taux_ca_max || columnFilters.taux_ca_max || undefined,
          search: filters.search || undefined,
          order_by: orderBy,
          order_direction: orderDirection,
        };

        // Log filter params BEFORE cleanup
        console.log("🔍 [PREVIEW] Filter params BEFORE cleanup:", {
          date_gl_start: filters.date_gl_start,
          date_gl_end: filters.date_gl_end,
          date_fact_start: filters.date_fact_start,
          date_fact_end: filters.date_fact_end,
          search: filters.search,
          filterParams_start_date: filterParams.start_date,
          filterParams_end_date: filterParams.end_date,
          filterParams_start_date_fact: filterParams.start_date_fact,
          filterParams_end_date_fact: filterParams.end_date_fact,
          filterParams_search: filterParams.search,
        });

        // Remove undefined values
        Object.keys(filterParams).forEach(
          (key) => filterParams[key] === undefined && delete filterParams[key]
        );

        // Log filter params AFTER cleanup
        console.log("🔍 [PREVIEW] Filter params AFTER cleanup:", filterParams);

        response = await getRevenuePreviewData(
          filterParams,
          previewPageSize,
          offset
        );
      }

      const records = response.data?.records || [];
      console.log("Preview data received:", records.length, "records");
      console.log("First record sample:", records[0]);
      setPreviewData(records);
      setPreviewTotal(response.data?.total_available || 0);
    } catch (err) {
      console.error("Error fetching preview data:", err);
      toast.error("Erreur lors du chargement des données de prévisualisation");
    } finally {
      setPreviewLoading(false);
    }
  }, [activeTab, previewTableType, previewPage, previewPageSize, filters]);

  // Fetch column values for a specific column
  const fetchColumnValues = useCallback(
    async (column) => {
      if (columnValues[column] || loadingColumnValues[column]) return;

      try {
        setLoadingColumnValues((prev) => ({ ...prev, [column]: true }));
        const response = await getRevenueColumnValues(column);
        setColumnValues((prev) => ({
          ...prev,
          [column]: response.data?.values || [],
        }));
      } catch (err) {
        console.error(`Error fetching values for column ${column}:`, err);
      } finally {
        setLoadingColumnValues((prev) => ({ ...prev, [column]: false }));
      }
    },
    [columnValues, loadingColumnValues]
  );

  // Fetch preview data when tab changes or filters/page changes
  useEffect(() => {
    if (activeTab === "preview") {
      fetchPreviewData();
    }
  }, [
    activeTab,
    previewTableType,
    previewPage,
    previewPageSize,
    filters,
    columnFilters,
    orderBy,
    orderDirection,
    fetchPreviewData,
  ]);

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
  const totalObjective = overview.total_objective || 0;

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-3xl font-bold">Chiffre d'Affaire DOT Corporate</h1>
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

      {/* Export Progress Dialog */}
      <Dialog
        open={exportProgress.isOpen}
        onOpenChange={(open) =>
          setExportProgress((prev) => ({ ...prev, isOpen: open }))
        }
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Progression de l'Export</DialogTitle>
            <DialogDescription>
              {exportProgress.status === "completed"
                ? "Export terminé avec succès!"
                : exportProgress.status === "failed"
                ? "Erreur lors de l'export"
                : "Votre export est en cours de traitement..."}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            {exportProgress.status === "processing" && (
              <>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">
                      {exportProgress.message || "Traitement en cours..."}
                    </span>
                    <span className="font-semibold">
                      {Math.round(exportProgress.progress)}%
                    </span>
                  </div>
                  <Progress value={exportProgress.progress} className="h-2" />
                </div>
                <p className="text-xs text-muted-foreground text-center">
                  Veuillez patienter, cette opération peut prendre quelques
                  instants...
                </p>
              </>
            )}
            {exportProgress.status === "completed" && (
              <div className="space-y-4">
                <div className="flex items-center justify-center space-x-2 text-green-600">
                  <CheckCircle2 className="h-6 w-6" />
                  <span className="font-semibold">Export terminé!</span>
                </div>
                {exportProgress.filename && (
                  <p className="text-sm text-center text-muted-foreground">
                    Fichier: {exportProgress.filename}
                  </p>
                )}
                <Button
                  onClick={handleDownloadExport}
                  className="w-full"
                  size="lg"
                >
                  <Download className="h-4 w-4 mr-2" />
                  Télécharger l'export
                </Button>
              </div>
            )}
            {exportProgress.status === "failed" && (
              <div className="space-y-4">
                <div className="flex items-center justify-center space-x-2 text-red-600">
                  <XCircle className="h-6 w-6" />
                  <span className="font-semibold">Échec de l'export</span>
                </div>
                <p className="text-sm text-center text-muted-foreground">
                  {exportProgress.message ||
                    "Une erreur s'est produite lors de l'export"}
                </p>
                <Button
                  variant="outline"
                  onClick={() =>
                    setExportProgress((prev) => ({ ...prev, isOpen: false }))
                  }
                  className="w-full"
                >
                  Fermer
                </Button>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Total Revenue - Hero Card */}
      <Card className="bg-gradient-to-r from-blue-500 to-blue-600 text-white">
        <CardContent className="pt-6">
          <div className="text-center">
            <div className="text-6xl font-bold mb-2">
              {formatNumber(overview.total_revenue || 0)} DZD
            </div>
            <div className="text-xl font-medium opacity-90">
              Chiffre d'affaires
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Secondary Stats Cards - Horizontal Layout */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-2">
          <CardContent className="pt-6 pb-6">
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-600">
                Chiffre d'affaires (CA)
              </div>
              <div className="text-3xl font-bold text-gray-900">
                {formatNumber(overview.total_revenue || 0)} DZD
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-2">
          <CardContent className="pt-6 pb-6">
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-600">
                Objectif C.A
              </div>
              <div className="text-3xl font-bold text-gray-900">
                {formatNumber(totalObjective)} DZD
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="border-2">
          <CardContent className="pt-6 pb-6">
            <div className="space-y-2">
              <div className="text-sm font-medium text-gray-600">
                Taux de réalisation C.A
              </div>
              <div className="text-3xl font-bold text-gray-900">
                {formatPercent(globalAchievementRate)}
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
                  <Label>DOT</Label>
                  <MultiSelect
                    options={filterOptions.org_names.map((name) => ({
                      label: name,
                      value: name,
                    }))}
                    selected={filters.org_name}
                    onChange={(values) =>
                      setFilters((f) => ({ ...f, org_name: values }))
                    }
                    placeholder="Tous les DOTs"
                  />
                </div>

                <div>
                  <Label>Type Fact</Label>
                  <MultiSelect
                    options={filterOptions.typ_fact_list.map((type) => ({
                      label: type,
                      value: type,
                    }))}
                    selected={filters.typ_fact}
                    onChange={(values) =>
                      setFilters((f) => ({ ...f, typ_fact: values }))
                    }
                    placeholder="Tous les statuts"
                  />
                </div>

                <div>
                  <Label>Compte comptable</Label>
                  <MultiSelect
                    options={filterOptions.cpt_comptable_list.map((item) => ({
                      label: `${item.code} - ${
                        item.description || "Sans description"
                      }`,
                      value: item.code,
                    }))}
                    selected={filters.cpt_comptable}
                    onChange={(values) => {
                      console.log(
                        "🔍 [FRONTEND] Compte comptable filter changed:",
                        {
                          values: values,
                          values_type: typeof values,
                          values_isArray: Array.isArray(values),
                          values_length: values?.length,
                          values_content: values,
                        }
                      );
                      setFilters((f) => ({ ...f, cpt_comptable: values }));
                    }}
                    placeholder="Tous les comptes comptables"
                    showSelectAll={true}
                  />
                </div>

                <div>
                  <Label>Recherche</Label>
                  <Input
                    placeholder="Recherche dans tous les champs..."
                    value={filters.search || ""}
                    onChange={(e) =>
                      setFilters((f) => ({ ...f, search: e.target.value }))
                    }
                  />
                </div>
              </div>

              {/* Secondary Filters */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <Label>Date Fact - Début (Mois)</Label>
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
                  <Label>Date Fact - Fin (Mois)</Label>
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
                  <Label>Date GL - Début (Mois)</Label>
                  <Input
                    type="month"
                    value={filters.date_gl_start}
                    onChange={(e) =>
                      setFilters((f) => ({
                        ...f,
                        date_gl_start: e.target.value,
                      }))
                    }
                  />
                </div>

                <div>
                  <Label>Date GL - Fin (Mois)</Label>
                  <Input
                    type="month"
                    value={filters.date_gl_end}
                    onChange={(e) =>
                      setFilters((f) => ({
                        ...f,
                        date_gl_end: e.target.value,
                      }))
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
                          org_name: "DOT",
                          typ_fact: "Type Fact",
                          date_fact_start: "Date Fact Début",
                          date_fact_end: "Date Fact Fin",
                          date_gl_start: "Date GL Début",
                          date_gl_end: "Date GL Fin",
                          cpt_comptable: "Compte comptable",
                          taux_ca_min: "Taux Min",
                          taux_ca_max: "Taux Max",
                          search: "Recherche",
                        };

                        const displayValue = Array.isArray(value)
                          ? key === "cpt_comptable"
                            ? value
                                .map((code) => {
                                  const item =
                                    filterOptions.cpt_comptable_list.find(
                                      (c) => c.code === code
                                    );
                                  return item
                                    ? `${code} - ${
                                        item.description?.substring(0, 30) ||
                                        "Sans description"
                                      }`
                                    : code;
                                })
                                .join(", ")
                            : `${value.length} sélectionné(s)`
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
          { id: "dot", label: "BY C.A", icon: Building },
          { id: "type-fact", label: "BY Type Fact", icon: FileText },
          { id: "date-gl", label: "BY Date GL", icon: BarChart3 },
          { id: "cpt-comptable", label: "BY Cpt Comptable", icon: FileText },
          { id: "taux-ca", label: "BY Taux C.A", icon: TrendingUp },
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
          <Card>
            <CardHeader>
              <CardTitle>C.A vs Objectif par Mois</CardTitle>
            </CardHeader>
            <CardContent>
              {monthlyChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={450}>
                  <BarChart data={monthlyChartData} margin={{ bottom: 20 }}>
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
                    <Bar
                      dataKey="Somme de_Chiffre d'affaires"
                      fill={COLORS.primary}
                      radius={[4, 4, 0, 0]}
                    />
                    <Bar
                      dataKey="Somme de_Objectif C.A"
                      fill={COLORS.secondary}
                      radius={[4, 4, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="Aucune donnée disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "dot" && (
          <Card>
            <CardHeader>
              <CardTitle>DOT et Chiffre d'affaires</CardTitle>
            </CardHeader>
            <CardContent>
              {dotCAChartData.length > 0 ? (
                <ResponsiveContainer
                  width="100%"
                  height={Math.max(
                    400,
                    Math.min(800, dotCAChartData.length * 20)
                  )}
                >
                  <BarChart
                    data={dotCAChartData}
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
                      tickFormatter={(value) =>
                        new Intl.NumberFormat("fr-FR", {
                          notation: "compact",
                          maximumFractionDigits: 1,
                        }).format(value)
                      }
                      style={{ fontSize: "12px" }}
                    />
                    <Tooltip content={<CustomTooltipObjective />} />
                    <Bar
                      dataKey="total_revenue"
                      radius={[4, 4, 0, 0]}
                      fill={COLORS.primary}
                    >
                      {dotCAChartData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS.primary} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="Aucune donnée DOT disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "type-fact" && (
          <Card>
            <CardHeader>
              <CardTitle>Revenue par Type Fact</CardTitle>
            </CardHeader>
            <CardContent>
              {typeFactChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={450}>
                  <BarChart
                    data={typeFactChartData}
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
                      dataKey="total_revenue"
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

        {activeTab === "date-gl" && (
          <Card>
            <CardHeader>
              <CardTitle>Revenue par Date GL (Mois)</CardTitle>
            </CardHeader>
            <CardContent>
              {monthChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={450}>
                  <BarChart
                    data={monthChartData}
                    margin={{ bottom: 20, top: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="month"
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
                      dataKey="total_revenue"
                      fill={COLORS.primary}
                      radius={[4, 4, 0, 0]}
                    >
                      <LabelList content={<CustomLabel />} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="Aucune donnée Date GL disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "cpt-comptable" && (
          <Card>
            <CardHeader>
              <CardTitle>Description Cpt Comptable</CardTitle>
            </CardHeader>
            <CardContent>
              {accountChartData.length > 0 ? (
                <ResponsiveContainer width="100%" height={450}>
                  <BarChart
                    data={accountChartData}
                    margin={{ bottom: 80, left: 20, top: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                    <XAxis
                      dataKey="compte"
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
                      dataKey="Total"
                      fill={COLORS.primary}
                      radius={[4, 4, 0, 0]}
                    >
                      <LabelList content={<CustomLabel />} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="Aucune donnée Compte Comptable disponible" />
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "taux-ca" && (
          <Card>
            <CardHeader>
              <CardTitle>DOT et Taux de Réalisation C.A</CardTitle>
              {/* Color Legend */}
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
                    20.01% - 49.99%
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div
                    className="w-4 h-4 rounded"
                    style={{ backgroundColor: COLORS.secondary }}
                  />
                  <span className="text-xs text-muted-foreground">
                    50% - 74.99%
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
              {dotTauxChartData.length > 0 ? (
                <ResponsiveContainer
                  width="100%"
                  height={Math.max(
                    400,
                    Math.min(800, dotTauxChartData.length * 20)
                  )}
                >
                  <BarChart
                    data={dotTauxChartData}
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
                    <Tooltip content={<CustomTooltipPercent />} />
                    <Bar dataKey="taux" radius={[4, 4, 0, 0]}>
                      {dotTauxChartData.map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={getColorByAchievementRate(entry.taux)}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <EmptyState message="Aucune donnée DOT disponible" />
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
                    <Label htmlFor="preview-table-type" className="text-sm">
                      Table:
                    </Label>
                    <Select
                      value={previewTableType}
                      onValueChange={(value) => {
                        setPreviewTableType(value);
                        setPreviewPage(1);
                      }}
                    >
                      <SelectTrigger id="preview-table-type" className="w-48">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="journal">
                          Journal (Revenue Journal)
                        </SelectItem>
                        <SelectItem value="objectives">Objectif C.A</SelectItem>
                        <SelectItem value="account-descriptions">
                          Description Cpt Comptable
                        </SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
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
                          {previewTableType === "objectives" ? (
                            <>
                              <TableHead>ID</TableHead>
                              <TableHead>DOT Name</TableHead>
                              <TableHead>Objectif C.A</TableHead>
                              <TableHead>DOT ID</TableHead>
                              <TableHead>File Upload ID</TableHead>
                              <TableHead>Créé le</TableHead>
                              <TableHead>Modifié le</TableHead>
                            </>
                          ) : previewTableType === "account-descriptions" ? (
                            <>
                              <TableHead>ID</TableHead>
                              <TableHead>Cpt Comptable</TableHead>
                              <TableHead>Description</TableHead>
                              <TableHead>Aut BDG</TableHead>
                              <TableHead>Aut Imp</TableHead>
                              <TableHead>Type Cpte</TableHead>
                              <TableHead>Auxil</TableHead>
                              <TableHead>Let</TableHead>
                              <TableHead>File Upload ID</TableHead>
                              <TableHead>Créé le</TableHead>
                              <TableHead>Modifié le</TableHead>
                            </>
                          ) : (
                            <>
                              {/* All columns from revenue_journal with filters and sorting */}
                              {REVENUE_JOURNAL_COLUMNS.map((col) => (
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
                                      {/* All columns have filters now */}
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
                                    </div>
                                  </div>
                                </TableHead>
                              ))}
                            </>
                          )}
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {previewData.map((record, rowIndex) => (
                          <TableRow key={record.id || rowIndex}>
                            {previewTableType === "objectives" ? (
                              <>
                                <TableCell className="font-mono text-xs">
                                  {record.id || "-"}
                                </TableCell>
                                <TableCell>{record.dot_name || "-"}</TableCell>
                                <TableCell className="text-right">
                                  {formatNumber(record.objectif_ca || 0)}
                                </TableCell>
                                <TableCell>{record.dot_id || "-"}</TableCell>
                                <TableCell>
                                  {record.file_upload_id || "-"}
                                </TableCell>
                                <TableCell className="text-xs">
                                  {record.created_at
                                    ? new Date(
                                        record.created_at
                                      ).toLocaleString("fr-FR")
                                    : "-"}
                                </TableCell>
                                <TableCell className="text-xs">
                                  {record.updated_at
                                    ? new Date(
                                        record.updated_at
                                      ).toLocaleString("fr-FR")
                                    : "-"}
                                </TableCell>
                              </>
                            ) : previewTableType === "account-descriptions" ? (
                              <>
                                <TableCell className="font-mono text-xs">
                                  {record.id || "-"}
                                </TableCell>
                                <TableCell className="font-mono text-xs">
                                  {record.cpt_comptable || "-"}
                                </TableCell>
                                <TableCell className="max-w-[300px] truncate">
                                  {record.description_cpt_comptable || "-"}
                                </TableCell>
                                <TableCell>{record.aut_bdg || "-"}</TableCell>
                                <TableCell>{record.aut_imp || "-"}</TableCell>
                                <TableCell>{record.type_cpte || "-"}</TableCell>
                                <TableCell>{record.auxil || "-"}</TableCell>
                                <TableCell>{record.let || "-"}</TableCell>
                                <TableCell>
                                  {record.file_upload_id || "-"}
                                </TableCell>
                                <TableCell className="text-xs">
                                  {record.created_at
                                    ? new Date(
                                        record.created_at
                                      ).toLocaleString("fr-FR")
                                    : "-"}
                                </TableCell>
                                <TableCell className="text-xs">
                                  {record.updated_at
                                    ? new Date(
                                        record.updated_at
                                      ).toLocaleString("fr-FR")
                                    : "-"}
                                </TableCell>
                              </>
                            ) : (
                              <>
                                {/* Dynamically render all columns from revenue_journal */}
                                {REVENUE_JOURNAL_COLUMNS.map((col) => {
                                  const value = record[col.key];
                                  let displayValue = "-";

                                  if (value !== null && value !== undefined) {
                                    if (col.format === "date") {
                                      displayValue = new Date(
                                        value
                                      ).toLocaleDateString("fr-FR");
                                    } else if (col.format === "datetime") {
                                      displayValue = new Date(
                                        value
                                      ).toLocaleString("fr-FR");
                                    } else if (col.format === "number") {
                                      displayValue = formatNumber(value);
                                    } else if (col.format === "percent") {
                                      displayValue = formatPercent(value);
                                    } else if (col.format === "boolean") {
                                      displayValue = value ? "Oui" : "Non";
                                    } else {
                                      displayValue = String(value);
                                    }
                                  }

                                  return (
                                    <TableCell
                                      key={col.key}
                                      className={`
                                        ${
                                          col.key === "id"
                                            ? "sticky left-0 bg-background z-10"
                                            : ""
                                        }
                                        ${
                                          col.format === "mono"
                                            ? "font-mono text-xs"
                                            : ""
                                        }
                                        ${
                                          col.format === "truncate"
                                            ? "max-w-[200px] truncate"
                                            : ""
                                        }
                                        ${
                                          col.format === "number" ||
                                          col.format === "percent"
                                            ? "text-right"
                                            : ""
                                        }
                                        ${
                                          col.format === "date" ||
                                          col.format === "datetime"
                                            ? "text-xs"
                                            : ""
                                        }
                                      `}
                                    >
                                      {displayValue}
                                    </TableCell>
                                  );
                                })}
                              </>
                            )}
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

export default RevenuePage;
