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
  getParkAnalyticsColumnValues,
  startParkAnalyticsExport,
  downloadParkAnalyticsExport,
} from "../../services/api";
import { useProcessing } from "../../contexts/ProcessingContext";
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
  Loader2,
  CheckCircle2,
  XCircle,
  Search,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
  DropdownMenuCheckboxItem,
} from "@/components/ui/dropdown-menu";
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

// Telecom Type Color Mapping
const TELECOM_COLORS = {
  UNKNOWN: "#8884D8",
  PSTN: "#0088FE",
  xDSL: "#00C49F",
  "Specialized Line": "#FFBB28",
  LTE: "#FF8042",
  FTTx: "#82CA9D",
  VOIP: "#FFC658",
  X25: "#FF7C7C",
  x25: "#FF7C7C",
  WIMAX: "#8DD1E1",
  WIFI: "#8DD1E1",
};

// Subscriber Status Color Mapping
const STATUS_COLORS = {
  Active: "#00C49F", // Green - active is good
  Suspend: "#FF8042", // Orange - suspended
  Barring: "#FF7C7C", // Red - barred
  Predeactivated: "#FFBB28", // Yellow - predeactivated
  Idle: "#8884D8", // Purple - idle
  Inactive: "#8DD1E1", // Light blue - inactive
  Suspended: "#FF8042", // Orange variant
};

// Customer L2 Code Color Mapping
const CUSTOMER_L2_COLORS = {
  201: "#0088FE", // Blue - Company
  301: "#00C49F", // Green - Administration & organization
  302: "#FFBB28", // Yellow - Officially agreed professional customer
  203: "#FF8042", // Orange - Liberal profession & Craftsman
  501: "#82CA9D", // Light green - Line of exploitation
  202: "#FFC658", // Gold - Trade
  410: "#8DD1E1", // Light blue - Officially agreed professional customer DOT
  UNKNOWN: "#8884D8", // Purple - Unknown
};

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

const EncaissementPage = () => {
  // WebSocket context
  const { subscribeTask } = useProcessing();

  // State management
  const [overview, setOverview] = useState({});
  const [telecomTypeData, setTelecomTypeData] = useState([]);
  const [subscriberStatusData, setSubscriberStatusData] = useState([]);
  const [dotData, setDotData] = useState([]);
  const [customerL2Data, setCustomerL2Data] = useState([]);
  const [customerL3Data, setCustomerL3Data] = useState([]);
  const [availableFilters, setAvailableFilters] = useState({});
  const [dotActelMapping, setDotActelMapping] = useState({});
  const [l2L3Mapping, setL2L3Mapping] = useState({});
  const [statusTelecomMapping, setStatusTelecomMapping] = useState({});
  const [statusOfferMapping, setStatusOfferMapping] = useState({});
  const [telecomStatusMapping, setTelecomStatusMapping] = useState({});
  const [telecomOfferMapping, setTelecomOfferMapping] = useState({});
  const [offerStatusMapping, setOfferStatusMapping] = useState({});
  const [offerTelecomMapping, setOfferTelecomMapping] = useState({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportProgress_old, setExportProgress_old] = useState(0);

  // New export progress state for async export
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
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [showFilters, setShowFilters] = useState(false);

  // Preview data state
  const [previewData, setPreviewData] = useState([]);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewTotal, setPreviewTotal] = useState(0);
  const [previewPage, setPreviewPage] = useState(1);
  const [previewPageSize, setPreviewPageSize] = useState(10);

  // Column filters for Excel-like filtering
  const [columnFilters, setColumnFilters] = useState({});
  const [columnValues, setColumnValues] = useState({});
  const [loadingColumnValues, setLoadingColumnValues] = useState({});

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
    include_exclusion_2b: false, // Exclude 2B records by default (like anomalies)
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
          } else if (typeof value === "boolean") {
            // Include boolean values (e.g., include_exclusion_2b)
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
        setDotActelMapping(filtersRes.data?.dot_actel_mapping || {});
        setL2L3Mapping(filtersRes.data?.l2_l3_mapping || {});
        setStatusTelecomMapping(filtersRes.data?.status_telecom_mapping || {});
        setStatusOfferMapping(filtersRes.data?.status_offer_mapping || {});
        setTelecomStatusMapping(filtersRes.data?.telecom_status_mapping || {});
        setTelecomOfferMapping(filtersRes.data?.telecom_offer_mapping || {});
        setOfferStatusMapping(filtersRes.data?.offer_status_mapping || {});
        setOfferTelecomMapping(filtersRes.data?.offer_telecom_mapping || {});

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

  // Fetch column values for a specific column from backend
  // Respects active filters so only relevant values are shown
  const fetchColumnValues = useCallback(
    async (columnKey) => {
      if (columnValues[columnKey] || loadingColumnValues[columnKey]) return;

      try {
        setLoadingColumnValues((prev) => ({ ...prev, [columnKey]: true }));

        // Build filter params from main filters and other column filters
        // This ensures column values respect active filters
        // Exclude the current column from filters to avoid circular filtering
        const filterParams = {};

        // Map to know which main filter key corresponds to which column
        const columnToMainFilter = {
          dot_name: "dot_ids",
          actel_code: "actel_codes",
          subscriber_status: "subscriber_statuses",
          telecom_type: "telecom_types",
          offer_name: "offer_names",
          offer_type: "offer_types",
          customer_l2_code: "customer_l2_codes",
          customer_l3_code: "customer_l3_codes",
        };

        const columnToBackendParam = {
          dot_name: "dot_ids",
          actel_code: "actel_codes",
          subscriber_status: "subscriber_statuses",
          telecom_type: "telecom_types",
          offer_name: "offer_names",
          offer_type: "offer_types",
          customer_l2_code: "customer_l2_codes",
          customer_l3_code: "customer_l3_codes",
        };

        // Get the main filter key for the current column (to exclude it)
        const currentColumnMainFilter = columnToMainFilter[columnKey];

        // Add main filters (excluding the current column to avoid circular filtering)
        Object.entries(filters).forEach(([key, value]) => {
          // Skip if this is the main filter for the current column
          if (key === currentColumnMainFilter) return;

          if (Array.isArray(value) && value.length > 0) {
            filterParams[key] = value.join(",");
          } else if (typeof value === "string" && value.trim() !== "") {
            filterParams[key] = value;
          } else if (typeof value === "boolean") {
            // Include boolean values (e.g., include_exclusion_2b)
            filterParams[key] = value;
          }
        });

        // Add other column filters (but exclude the current column to avoid circular filtering)
        Object.entries(columnFilters).forEach(([colKey, values]) => {
          // Skip the current column being fetched to avoid circular filtering
          if (colKey === columnKey) return;

          if (Array.isArray(values) && values.length > 0) {
            const backendParam = columnToBackendParam[colKey];
            if (backendParam) {
              // Only add if not already set by main filters (main filters take precedence)
              if (!filterParams[backendParam]) {
                filterParams[backendParam] = values.join(",");
              }
            }
          }
        });

        // Fetch values from backend with active filters
        const response = await getParkAnalyticsColumnValues(
          columnKey,
          filterParams
        );
        const values = response.data?.values || [];

        setColumnValues((prev) => ({
          ...prev,
          [columnKey]: values,
        }));
      } catch (err) {
        console.error(`Error fetching values for column ${columnKey}:`, err);
        handleApiError(err, {
          showToast: false,
          fallbackMessage: `Erreur lors du chargement des valeurs pour ${columnKey}`,
        });
      } finally {
        setLoadingColumnValues((prev) => ({ ...prev, [columnKey]: false }));
      }
    },
    [columnValues, loadingColumnValues, filters, columnFilters]
  );

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
        } else if (typeof value === "boolean") {
          // Include boolean values (e.g., include_exclusion_2b)
          filterParams[key] = value;
        }
      });

      // Add column filters - map to backend parameter names where applicable
      const columnToBackendParam = {
        dot_name: "dot_ids", // Note: would need dot name to ID mapping
        actel_code: "actel_codes",
        subscriber_status: "subscriber_statuses",
        telecom_type: "telecom_types",
        offer_name: "offer_names",
        offer_type: "offer_types",
        customer_l2_code: "customer_l2_codes",
        customer_l3_code: "customer_l3_codes",
      };

      Object.entries(columnFilters).forEach(([colKey, values]) => {
        if (Array.isArray(values) && values.length > 0) {
          const backendParam = columnToBackendParam[colKey];
          if (backendParam) {
            // Use backend filtering
            filterParams[backendParam] = values.join(",");
          }
          // Other columns will be filtered client-side
        }
      });

      const offset = (previewPage - 1) * previewPageSize;
      const response = await getParkAnalyticsPreviewData(
        filterParams,
        previewPageSize,
        offset
      );

      let records = response.data?.records || [];

      // Apply client-side filtering for columns not supported by backend
      // Backend supports: dot_ids, actel_codes, subscriber_statuses, telecom_types,
      // offer_names, offer_types, customer_l2_codes, customer_l3_codes
      // Filter other columns client-side on current page
      Object.entries(columnFilters).forEach(([colKey, values]) => {
        if (values && values.length > 0) {
          // Skip if already handled by backend
          if (columnToBackendParam[colKey]) {
            return;
          }

          // Apply client-side filtering
          records = records.filter((record) => {
            const recordValue = record[colKey];
            if (recordValue === null || recordValue === undefined) return false;
            const strValue = String(recordValue);
            return values.includes(strValue);
          });
        }
      });

      setPreviewData(records);
      setPreviewTotal(response.data?.total_available || 0);
    } catch (err) {
      console.error("Error fetching preview data:", err);
      handleApiError(err, {
        showToast: true,
        fallbackMessage:
          "Erreur lors du chargement des données de prévisualisation",
      });
    } finally {
      setPreviewLoading(false);
    }
  }, [activeTab, filters, columnFilters, previewPage, previewPageSize]);

  // Handle column filter change
  const handleColumnFilterChange = (column, values) => {
    setColumnFilters((prev) => ({
      ...prev,
      [column]: values.length > 0 ? values : undefined,
    }));
    setPreviewPage(1); // Reset to first page when filter changes
  };

  // Fetch preview data when tab changes or filters/page changes
  useEffect(() => {
    if (activeTab === "preview") {
      fetchPreviewData();
    }
  }, [
    activeTab,
    filters,
    columnFilters,
    previewPage,
    previewPageSize,
    fetchPreviewData,
  ]);

  const handleFilterChange = (key, value) => {
    setFilters((prev) => {
      const newFilters = { ...prev, [key]: value };

      // When DOTs change, filter out Actel Codes that don't belong to selected DOTs
      if (key === "dot_ids") {
        if (value && value.length > 0) {
          const selectedDotIds = value;
          const validActelCodes = new Set();

          selectedDotIds.forEach((dotId) => {
            const codes = dotActelMapping[dotId] || [];
            codes.forEach((code) => validActelCodes.add(code));
          });

          // Filter out Actel Codes that don't belong to selected DOTs
          const filteredActelCodes = (prev.actel_codes || []).filter((code) =>
            validActelCodes.has(code)
          );

          newFilters.actel_codes = filteredActelCodes;
        } else {
          // If no DOTs selected, keep all selected Actel Codes
          // (they will be available in the dropdown)
        }
      }

      // When L2 codes change, filter out L3 codes that don't belong to selected L2 codes
      if (key === "customer_l2_codes") {
        if (value && value.length > 0) {
          const selectedL2Codes = value;
          const validL3Codes = new Set();

          selectedL2Codes.forEach((l2Code) => {
            const l3Codes = l2L3Mapping[l2Code] || [];
            l3Codes.forEach((l3) => validL3Codes.add(l3.code));
          });

          // Filter out L3 codes that don't belong to selected L2 codes
          const filteredL3Codes = (prev.customer_l3_codes || []).filter(
            (l3Code) => validL3Codes.has(l3Code)
          );

          newFilters.customer_l3_codes = filteredL3Codes;
        } else {
          // If no L2 codes selected, keep all selected L3 codes
          // (they will be available in the dropdown)
        }
      }

      // When Subscriber Status changes, filter Telecom Types and Offer Names
      if (key === "subscriber_statuses") {
        if (value && value.length > 0) {
          const selectedStatuses = value;
          const validTelecoms = new Set();
          const validOffers = new Set();

          selectedStatuses.forEach((status) => {
            (statusTelecomMapping[status] || []).forEach((t) =>
              validTelecoms.add(t)
            );
            (statusOfferMapping[status] || []).forEach((o) =>
              validOffers.add(o)
            );
          });

          // Filter out invalid selections - only keep items that are in the valid set
          if (validTelecoms.size > 0) {
            newFilters.telecom_types = (prev.telecom_types || []).filter((t) =>
              validTelecoms.has(t)
            );
          }
          if (validOffers.size > 0) {
            newFilters.offer_names = (prev.offer_names || []).filter((o) =>
              validOffers.has(o)
            );
          }
        }
      }

      // When Telecom Type changes, filter Subscriber Statuses and Offer Names
      if (key === "telecom_types") {
        if (value && value.length > 0) {
          const selectedTelecoms = value;
          const validStatuses = new Set();
          const validOffers = new Set();

          selectedTelecoms.forEach((telecom) => {
            (telecomStatusMapping[telecom] || []).forEach((s) =>
              validStatuses.add(s)
            );
            (telecomOfferMapping[telecom] || []).forEach((o) =>
              validOffers.add(o)
            );
          });

          // Filter out invalid selections - only keep items that are in the valid set
          if (validStatuses.size > 0) {
            newFilters.subscriber_statuses = (
              prev.subscriber_statuses || []
            ).filter((s) => validStatuses.has(s));
          }
          if (validOffers.size > 0) {
            newFilters.offer_names = (prev.offer_names || []).filter((o) =>
              validOffers.has(o)
            );
          }
        }
      }

      // When Offer Name changes, filter Subscriber Statuses and Telecom Types
      if (key === "offer_names") {
        if (value && value.length > 0) {
          const selectedOffers = value;
          const validStatuses = new Set();
          const validTelecoms = new Set();

          selectedOffers.forEach((offer) => {
            (offerStatusMapping[offer] || []).forEach((s) =>
              validStatuses.add(s)
            );
            (offerTelecomMapping[offer] || []).forEach((t) =>
              validTelecoms.add(t)
            );
          });

          // Filter out invalid selections - only keep items that are in the valid set
          if (validStatuses.size > 0) {
            newFilters.subscriber_statuses = (
              prev.subscriber_statuses || []
            ).filter((s) => validStatuses.has(s));
          }
          if (validTelecoms.size > 0) {
            newFilters.telecom_types = (prev.telecom_types || []).filter((t) =>
              validTelecoms.has(t)
            );
          }
        }
      }

      return newFilters;
    });
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

  const exportData = async (format = "excel", exportType = "normal") => {
    if (!validateDateRange()) return;

    try {
      setExporting(true);

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

      console.log(
        "🚀 Starting async export with filters:",
        exportFilters,
        "type:",
        exportType
      );

      // Start async export with specified type: normal, anomalies, 2b, or all
      const response = await startParkAnalyticsExport(
        exportFilters,
        exportType
      );

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
      handleApiError(err, {
        showToast: true,
        fallbackMessage: "Erreur lors du démarrage de l'export",
      });
    } finally {
      setExporting(false);
    }
  };

  const handleDownloadExport = async () => {
    try {
      const response = await downloadParkAnalyticsExport(exportProgress.taskId);

      // Response is a blob
      const blob = response.data;
      const filename =
        exportProgress.filename ||
        `parc_export_${new Date().toISOString().split("T")[0]}.zip`;

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
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du téléchargement de l'export",
      });
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
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                disabled={exporting}
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Download className="h-4 w-4 mr-2" />
                Exporter
                {exporting && <Loader2 className="h-4 w-4 ml-2 animate-spin" />}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel>Données Normales</DropdownMenuLabel>
              <DropdownMenuItem
                onClick={() => exportData("csv", "normal")}
                disabled={exporting}
              >
                <Download className="h-4 w-4 mr-2" />
                CSV - Données Normales
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => exportData("excel", "normal")}
                disabled={exporting}
              >
                <Download className="h-4 w-4 mr-2" />
                Excel - Données Normales
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuLabel>Anomalies</DropdownMenuLabel>
              <DropdownMenuItem
                onClick={() => exportData("csv", "anomalies")}
                disabled={exporting}
              >
                <Download className="h-4 w-4 mr-2" />
                CSV - Anomalies
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => exportData("excel", "anomalies")}
                disabled={exporting}
              >
                <Download className="h-4 w-4 mr-2" />
                Excel - Anomalies
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuLabel>Facturation Groupée (2B)</DropdownMenuLabel>
              <DropdownMenuItem
                onClick={() => exportData("csv", "2b")}
                disabled={exporting}
              >
                <Download className="h-4 w-4 mr-2" />
                CSV - Facturation 2B
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => exportData("excel", "2b")}
                disabled={exporting}
              >
                <Download className="h-4 w-4 mr-2" />
                Excel - Facturation 2B
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuLabel>Tout Exporter (ZIP)</DropdownMenuLabel>
              <DropdownMenuItem
                onClick={() => exportData("excel", "all")}
                disabled={exporting}
              >
                <Download className="h-4 w-4 mr-2" />
                Tout (Normal + Anomalies + 2B)
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
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
                  {Math.round(exportProgress_old)}%
                </span>
              </div>
              <Progress value={exportProgress_old} className="h-2" />
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
              {/* Primary Filters - Row 1 */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <Label>DOT</Label>
                  <MultiSelect
                    options={(availableFilters.dots || [])
                      .map((d) => ({
                        label: d.name,
                        value: d.id.toString(),
                      }))
                      .sort((a, b) => a.label.localeCompare(b.label))}
                    selected={filters.dot_ids}
                    onChange={(values) => handleFilterChange("dot_ids", values)}
                    placeholder="Tous les DOTs"
                  />
                </div>

                <div>
                  <Label>Statut Abonné</Label>
                  <MultiSelect
                    options={(() => {
                      // Filter based on selected Telecom Types and Offer Names
                      // Use intersection: show only statuses that exist with BOTH selected telecoms AND offers
                      let filteredStatuses =
                        availableFilters.subscriber_statuses || [];

                      if (
                        filters.telecom_types &&
                        filters.telecom_types.length > 0
                      ) {
                        const validStatuses = new Set();
                        filters.telecom_types.forEach((telecom) => {
                          const statuses = telecomStatusMapping[telecom] || [];
                          statuses.forEach((s) => validStatuses.add(s));
                        });
                        filteredStatuses = filteredStatuses.filter((s) =>
                          validStatuses.has(s)
                        );
                      }

                      if (
                        filters.offer_names &&
                        filters.offer_names.length > 0
                      ) {
                        const validStatuses = new Set();
                        filters.offer_names.forEach((offer) => {
                          const statuses = offerStatusMapping[offer] || [];
                          statuses.forEach((s) => validStatuses.add(s));
                        });
                        // Intersection: keep only statuses that are in both sets
                        filteredStatuses = filteredStatuses.filter((s) =>
                          validStatuses.has(s)
                        );
                      }

                      return filteredStatuses
                        .map((s) => ({
                          label: s,
                          value: s,
                        }))
                        .sort((a, b) => a.label.localeCompare(b.label));
                    })()}
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
                    options={(() => {
                      // Filter based on selected Subscriber Statuses and Offer Names
                      let filteredTelecoms =
                        availableFilters.telecom_types || [];

                      if (
                        filters.subscriber_statuses &&
                        filters.subscriber_statuses.length > 0
                      ) {
                        const validTelecoms = new Set();
                        filters.subscriber_statuses.forEach((status) => {
                          const telecoms = statusTelecomMapping[status] || [];
                          telecoms.forEach((t) => validTelecoms.add(t));
                        });
                        filteredTelecoms = filteredTelecoms.filter((t) =>
                          validTelecoms.has(t)
                        );
                      }

                      if (
                        filters.offer_names &&
                        filters.offer_names.length > 0
                      ) {
                        const validTelecoms = new Set();
                        filters.offer_names.forEach((offer) => {
                          const telecoms = offerTelecomMapping[offer] || [];
                          telecoms.forEach((t) => validTelecoms.add(t));
                        });
                        filteredTelecoms = filteredTelecoms.filter((t) =>
                          validTelecoms.has(t)
                        );
                      }

                      return filteredTelecoms
                        .map((t) => ({
                          label: t,
                          value: t,
                        }))
                        .sort((a, b) => a.label.localeCompare(b.label));
                    })()}
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
                    options={(() => {
                      // If DOTs are selected, filter Actel Codes to show only those belonging to selected DOTs
                      if (filters.dot_ids && filters.dot_ids.length > 0) {
                        const selectedDotIds = filters.dot_ids;
                        const filteredCodes = new Set();

                        selectedDotIds.forEach((dotId) => {
                          const codes = dotActelMapping[dotId] || [];
                          codes.forEach((code) => filteredCodes.add(code));
                        });

                        return Array.from(filteredCodes)
                          .sort()
                          .map((code) => ({
                            label: code,
                            value: code,
                          }));
                      }

                      // If no DOTs selected, show all Actel Codes
                      return (
                        availableFilters.actel_codes
                          ?.map((code) => ({
                            label: code,
                            value: code,
                          }))
                          .sort((a, b) => a.label.localeCompare(b.label)) || []
                      );
                    })()}
                    selected={filters.actel_codes}
                    onChange={(values) =>
                      handleFilterChange("actel_codes", values)
                    }
                    placeholder={
                      filters.dot_ids && filters.dot_ids.length > 0
                        ? "Codes Actel des DOTs sélectionnés"
                        : "Tous les codes"
                    }
                  />
                </div>
              </div>

              {/* Secondary Filters - Row 2 */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <Label>Nom d'Offre</Label>
                  <MultiSelect
                    options={(() => {
                      // Filter based on selected Subscriber Statuses and Telecom Types
                      let filteredOffers = availableFilters.offer_names || [];

                      if (
                        filters.subscriber_statuses &&
                        filters.subscriber_statuses.length > 0
                      ) {
                        const validOffers = new Set();
                        filters.subscriber_statuses.forEach((status) => {
                          const offers = statusOfferMapping[status] || [];
                          offers.forEach((o) => validOffers.add(o));
                        });
                        filteredOffers = filteredOffers.filter((o) =>
                          validOffers.has(o)
                        );
                      }

                      if (
                        filters.telecom_types &&
                        filters.telecom_types.length > 0
                      ) {
                        const validOffers = new Set();
                        filters.telecom_types.forEach((telecom) => {
                          const offers = telecomOfferMapping[telecom] || [];
                          offers.forEach((o) => validOffers.add(o));
                        });
                        filteredOffers = filteredOffers.filter((o) =>
                          validOffers.has(o)
                        );
                      }

                      return filteredOffers
                        .map((offer) => ({
                          label: offer,
                          value: offer,
                        }))
                        .sort((a, b) => a.label.localeCompare(b.label));
                    })()}
                    selected={filters.offer_names}
                    onChange={(values) =>
                      handleFilterChange("offer_names", values)
                    }
                    placeholder="Toutes les offres"
                  />
                </div>

                <div>
                  <Label>Code Client 2</Label>
                  <MultiSelect
                    options={
                      availableFilters.customer_l2_codes
                        ?.map((l2) => ({
                          label: `${l2.code} - ${l2.description}`,
                          value: l2.code,
                        }))
                        .sort((a, b) => a.label.localeCompare(b.label)) || []
                    }
                    selected={filters.customer_l2_codes}
                    onChange={(values) =>
                      handleFilterChange("customer_l2_codes", values)
                    }
                    placeholder="Tous L2"
                  />
                </div>

                <div>
                  <Label>Code Client 3</Label>
                  <MultiSelect
                    options={(() => {
                      // If L2 codes are selected, filter L3 codes to show only those belonging to selected L2 codes
                      if (
                        filters.customer_l2_codes &&
                        filters.customer_l2_codes.length > 0
                      ) {
                        const selectedL2Codes = filters.customer_l2_codes;
                        const filteredL3Codes = new Set();

                        selectedL2Codes.forEach((l2Code) => {
                          const l3Codes = l2L3Mapping[l2Code] || [];
                          l3Codes.forEach((l3) => filteredL3Codes.add(l3.code));
                        });

                        // Get full L3 info from available filters
                        return (
                          availableFilters.customer_l3_codes
                            ?.filter((l3) => filteredL3Codes.has(l3.code))
                            .map((l3) => ({
                              label: `${l3.code} - ${l3.description}`,
                              value: l3.code,
                            }))
                            .sort((a, b) => a.label.localeCompare(b.label)) ||
                          []
                        );
                      }

                      // If no L2 codes selected, show all L3 codes
                      return (
                        availableFilters.customer_l3_codes
                          ?.map((l3) => ({
                            label: `${l3.code} - ${l3.description}`,
                            value: l3.code,
                          }))
                          .sort((a, b) => a.label.localeCompare(b.label)) || []
                      );
                    })()}
                    selected={filters.customer_l3_codes}
                    onChange={(values) =>
                      handleFilterChange("customer_l3_codes", values)
                    }
                    placeholder={
                      filters.customer_l2_codes &&
                      filters.customer_l2_codes.length > 0
                        ? "Codes L3 des L2 sélectionnés"
                        : "Tous L3"
                    }
                  />
                </div>

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
                        : typeof value === "string"
                        ? value.trim() !== ""
                        : typeof value === "boolean"
                        ? value === true
                        : value != null && value !== "";

                      if (isActive) {
                        const labels = {
                          dot_ids: "DOT",
                          actel_codes: "Code Actel",
                          subscriber_statuses: "Statut",
                          telecom_types: "Type Télécom",
                          offer_names: "Offre",
                          offer_types: "Type Offre",
                          customer_l2_codes: "Code Client 2",
                          customer_l3_codes: "Code Client 3",
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
                          color: TELECOM_COLORS[d.type] || undefined, // Use specific color if available
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
                          color: STATUS_COLORS[d.status] || undefined, // Use specific color if available
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
                        color: CUSTOMER_L2_COLORS[d.code] || undefined, // Use specific color if available
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
                    color: TELECOM_COLORS[d.type] || undefined, // Use specific color if available
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
                    color: CUSTOMER_L2_COLORS[d.code] || undefined, // Use specific color if available
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
                          {[
                            { key: "id", label: "ID", filterable: false },
                            {
                              key: "extraction_date",
                              label: "Date Extraction",
                              filterable: true,
                            },
                            { key: "dot_name", label: "DOT", filterable: true },
                            {
                              key: "actel_code",
                              label: "Code Actel",
                              filterable: true,
                            },
                            {
                              key: "customer_code",
                              label: "Code Client",
                              filterable: true,
                            },
                            {
                              key: "service_number",
                              label: "Numéro Service",
                              filterable: true,
                            },
                            {
                              key: "related_service_number",
                              label: "Service Relié",
                              filterable: true,
                            },
                            {
                              key: "customer_full_name",
                              label: "Nom Client",
                              filterable: true,
                            },
                            {
                              key: "username",
                              label: "Username",
                              filterable: true,
                            },
                            {
                              key: "customer_l1_code",
                              label: "L1 Code",
                              filterable: true,
                            },
                            {
                              key: "customer_l1_description",
                              label: "L1 Description",
                              filterable: true,
                            },
                            {
                              key: "customer_l2_code",
                              label: "L2 Code",
                              filterable: true,
                            },
                            {
                              key: "customer_l2_description",
                              label: "L2 Description",
                              filterable: true,
                            },
                            {
                              key: "customer_l3_code",
                              label: "L3 Code",
                              filterable: true,
                            },
                            {
                              key: "customer_l3_description",
                              label: "L3 Description",
                              filterable: true,
                            },
                            {
                              key: "telecom_type",
                              label: "Type Télécom",
                              filterable: true,
                            },
                            {
                              key: "offer_type",
                              label: "Type Offre",
                              filterable: true,
                            },
                            {
                              key: "offer_name",
                              label: "Nom Offre",
                              filterable: true,
                            },
                            {
                              key: "rental_fees",
                              label: "Frais Location",
                              filterable: true,
                            },
                            {
                              key: "subscriber_status",
                              label: "Statut Abonné",
                              filterable: true,
                            },
                            {
                              key: "status_date",
                              label: "Date Statut",
                              filterable: false,
                            },
                            {
                              key: "creation_date",
                              label: "Date Création",
                              filterable: false,
                            },
                            {
                              key: "active_date",
                              label: "Date Activation",
                              filterable: false,
                            },
                            {
                              key: "expiry_date",
                              label: "Date Expiration",
                              filterable: false,
                            },
                            { key: "csr_name", label: "CSR", filterable: true },
                            {
                              key: "department_name",
                              label: "Département",
                              filterable: true,
                            },
                            { key: "state", label: "État", filterable: true },
                            { key: "area", label: "Zone", filterable: true },
                            { key: "town", label: "Ville", filterable: true },
                            { key: "grid", label: "Grille", filterable: true },
                            { key: "street", label: "Rue", filterable: true },
                            {
                              key: "street_number",
                              label: "Numéro Rue",
                              filterable: true,
                            },
                            {
                              key: "building_no",
                              label: "Bâtiment",
                              filterable: true,
                            },
                            { key: "unit", label: "Unité", filterable: true },
                            { key: "floor", label: "Étage", filterable: true },
                            {
                              key: "house_no",
                              label: "Numéro Maison",
                              filterable: true,
                            },
                            {
                              key: "additional_address_info",
                              label: "Info Adresse",
                              filterable: true,
                            },
                            {
                              key: "province",
                              label: "Province",
                              filterable: true,
                            },
                            {
                              key: "district",
                              label: "District",
                              filterable: true,
                            },
                            {
                              key: "postal_code",
                              label: "Code Postal",
                              filterable: true,
                            },
                            { key: "iccid", label: "ICCID", filterable: true },
                            { key: "imsi", label: "IMSI", filterable: true },
                            {
                              key: "contact_number",
                              label: "Contact",
                              filterable: true,
                            },
                            {
                              key: "created_at",
                              label: "Créé le",
                              filterable: false,
                            },
                            {
                              key: "updated_at",
                              label: "Modifié le",
                              filterable: false,
                            },
                          ].map((col) => (
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
                                {col.filterable && (
                                  <ExcelFilter
                                    column={col.key}
                                    label={col.label}
                                    values={columnValues[col.key] || []}
                                    selected={columnFilters[col.key] || []}
                                    onFilterChange={(values) =>
                                      handleColumnFilterChange(col.key, values)
                                    }
                                    onFetchValues={() =>
                                      fetchColumnValues(col.key)
                                    }
                                    loading={loadingColumnValues[col.key]}
                                  />
                                )}
                              </div>
                            </TableHead>
                          ))}
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
                                ? new Date(
                                    record.extraction_date
                                  ).toLocaleDateString("fr-FR")
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
                                ? new Date(
                                    record.status_date
                                  ).toLocaleDateString("fr-FR")
                                : "-"}
                            </TableCell>
                            <TableCell className="text-xs">
                              {record.creation_date
                                ? new Date(
                                    record.creation_date
                                  ).toLocaleDateString("fr-FR")
                                : "-"}
                            </TableCell>
                            <TableCell className="text-xs">
                              {record.active_date
                                ? new Date(
                                    record.active_date
                                  ).toLocaleDateString("fr-FR")
                                : "-"}
                            </TableCell>
                            <TableCell className="text-xs">
                              {record.expiry_date
                                ? new Date(
                                    record.expiry_date
                                  ).toLocaleDateString("fr-FR")
                                : "-"}
                            </TableCell>
                            <TableCell>{record.csr_name || "-"}</TableCell>
                            <TableCell>
                              {record.department_name || "-"}
                            </TableCell>
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
                            <TableCell>
                              {record.contact_number || "-"}
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

      {/* Export Progress Dialog */}
      <Dialog
        open={exportProgress.isOpen}
        onOpenChange={(open) =>
          setExportProgress((prev) => ({ ...prev, isOpen: open }))
        }
      >
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Progression de l'Export</DialogTitle>
            <DialogDescription>
              {exportProgress.status === "completed"
                ? "Export terminé avec succès !"
                : "Veuillez patienter pendant l'export de vos données..."}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Progression</span>
                <span className="font-medium">{exportProgress.progress}%</span>
              </div>
              <Progress value={exportProgress.progress} className="h-2" />
            </div>

            {/* Status Icon and Message */}
            <div className="flex items-start space-x-3">
              {exportProgress.status === "processing" && (
                <Loader2 className="h-5 w-5 animate-spin text-blue-500 mt-0.5" />
              )}
              {exportProgress.status === "completed" && (
                <CheckCircle2 className="h-5 w-5 text-green-500 mt-0.5" />
              )}
              {exportProgress.status === "failed" && (
                <XCircle className="h-5 w-5 text-red-500 mt-0.5" />
              )}
              <div className="flex-1 space-y-1">
                <p className="text-sm font-medium">
                  {exportProgress.status === "completed" && "Export Prêt"}
                  {exportProgress.status === "processing" &&
                    "Traitement en cours..."}
                  {exportProgress.status === "failed" && "Échec de l'Export"}
                </p>
                <p className="text-sm text-muted-foreground">
                  {exportProgress.message}
                </p>
                {exportProgress.filename && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Fichier : {exportProgress.filename}
                  </p>
                )}
              </div>
            </div>

            {/* Download Button */}
            {exportProgress.status === "completed" && (
              <Button
                onClick={handleDownloadExport}
                className="w-full"
                variant="default"
              >
                <Download className="h-4 w-4 mr-2" />
                Télécharger l'Export
              </Button>
            )}

            {/* Close Button */}
            {(exportProgress.status === "completed" ||
              exportProgress.status === "failed") && (
              <Button
                onClick={() =>
                  setExportProgress((prev) => ({ ...prev, isOpen: false }))
                }
                className="w-full"
                variant="outline"
              >
                Fermer
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default EncaissementPage;
