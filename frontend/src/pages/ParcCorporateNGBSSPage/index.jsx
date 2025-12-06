import React, { useState, useEffect, useContext } from "react";
import {
  getParkAnalyticsOverview,
  getParkAnalyticsByTelecomType,
  getParkAnalyticsBySubscriberStatus,
  getParkAnalyticsByCustomerL2,
  getParkAnalyticsByCustomerL3,
  getParkAnalyticsByDOT,
  getParkAnalyticsAvailableFilters,
  exportParkAnalyticsData,
  startParkAnalyticsExport,
  downloadParkAnalyticsExport,
} from "../../services/api";
import { WebSocketContext } from "../../contexts/WebSocketContext";
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../../components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../../components/ui/dialog";
import { Progress } from "../../components/ui/progress";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import {
  Download,
  BarChart3,
  PieChart as PieChartIcon,
  TrendingUp,
  Users,
  Building,
  Filter,
  RefreshCw,
  Loader2,
  CheckCircle2,
  XCircle,
} from "lucide-react";
import { toast } from "sonner";
import { handleApiError } from "../../lib/error-handler";

// Color palettes for charts
const COLORS = [
  "#0088FE",
  "#00C49F",
  "#FFBB28",
  "#FF8042",
  "#8884D8",
  "#82CA9D",
  "#FFC658",
  "#FF7C7C",
  "#8DD1E1",
  "#D084D0",
];

const TELECOM_COLORS = {
  UNKNOWN: "#8884D8",
  PSTN: "#0088FE",
  xDSL: "#00C49F",
  "Specialized Line": "#FFBB28",
  LTE: "#FF8042",
  FTTx: "#82CA9D",
  VOIP: "#FFC658",
  x25: "#FF7C7C",
  WIFI: "#8DD1E1",
};

const ParcCorporateNGBSSPage = () => {
  // WebSocket context
  const { subscribe, unsubscribe } = useContext(WebSocketContext);

  // State for data
  const [overview, setOverview] = useState({});
  const [telecomTypeData, setTelecomTypeData] = useState([]);
  const [subscriberStatusData, setSubscriberStatusData] = useState([]);
  const [customerL2Data, setCustomerL2Data] = useState([]);
  const [customerL3Data, setCustomerL3Data] = useState([]);
  const [dotData, setDotData] = useState([]);
  const [availableFilters, setAvailableFilters] = useState({});

  // State for UI
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [filters, setFilters] = useState({
    dot_filter: "",
    actel_code_filter: "",
    subscriber_status_filter: "",
    telecom_type_filter: "",
  });
  const [showFilters, setShowFilters] = useState(false);

  // Export progress state
  const [exportProgress, setExportProgress] = useState({
    isOpen: false,
    taskId: null,
    status: 'idle', // idle, processing, completed, failed
    progress: 0,
    message: '',
    filename: null,
    downloadUrl: null,
  });

  // Convert frontend filter format to backend API format
  const buildFilterParams = () => {
    const params = {};
    
    if (filters.dot_filter) {
      params.dot_ids = filters.dot_filter;
    }
    if (filters.actel_code_filter) {
      params.actel_codes = filters.actel_code_filter;
    }
    if (filters.subscriber_status_filter) {
      params.subscriber_statuses = filters.subscriber_status_filter;
    }
    if (filters.telecom_type_filter) {
      params.telecom_types = filters.telecom_type_filter;
    }
    
    return params;
  };

  useEffect(() => {
    fetchAllData();
  }, []);

  // Refetch data when filters change
  useEffect(() => {
    fetchAllData();
  }, [filters]);

  const fetchAllData = async () => {
    try {
      setLoading(true);
      const filterParams = buildFilterParams();
      
      const [
        overviewRes,
        telecomRes,
        statusRes,
        l2Res,
        l3Res,
        dotRes,
        filtersRes,
      ] = await Promise.all([
        getParkAnalyticsOverview(filterParams),
        getParkAnalyticsByTelecomType(filterParams),
        getParkAnalyticsBySubscriberStatus(filterParams),
        getParkAnalyticsByCustomerL2(filterParams),
        getParkAnalyticsByCustomerL3(filterParams),
        getParkAnalyticsByDOT(filterParams),
        getParkAnalyticsAvailableFilters(),
      ]);

      setOverview(overviewRes.data || {});
      setTelecomTypeData(telecomRes.data?.distribution || []);
      setSubscriberStatusData(statusRes.data?.distribution || []);
      setCustomerL2Data(l2Res.data?.distribution || []);
      setCustomerL3Data(l3Res.data?.distribution || []);
      setDotData(dotRes.data?.distribution || []);
      setAvailableFilters(filtersRes.data || {});
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du chargement des données",
      });
    } finally {
      setLoading(false);
    }
  };

  // WebSocket listener for export progress
  useEffect(() => {
    const handleExportUpdate = (data) => {
      if (data.type === 'processing_update' && data.task_id === exportProgress.taskId) {
        const updateData = data.data;
        setExportProgress(prev => ({
          ...prev,
          status: updateData.status || prev.status,
          progress: updateData.progress || prev.progress,
          message: updateData.message || prev.message,
          filename: updateData.filename || prev.filename,
          downloadUrl: updateData.download_url || prev.downloadUrl,
        }));
      }
    };

    if (exportProgress.taskId) {
      subscribe('export-update', handleExportUpdate);
    }

    return () => {
      if (exportProgress.taskId) {
        unsubscribe('export-update', handleExportUpdate);
      }
    };
  }, [exportProgress.taskId, subscribe, unsubscribe]);

  const handleExport = async (format = "csv", exportType = "normal") => {
    try {
      // Start async export
      const filterParams = { ...filters, format };
      const response = await startParkAnalyticsExport(filterParams, exportType);

      const taskId = response.data.task_id;

      // Open progress dialog
      setExportProgress({
        isOpen: true,
        taskId,
        status: 'processing',
        progress: 0,
        message: 'Starting export...',
        filename: null,
        downloadUrl: null,
      });

      toast.info("Export started in background");
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Error starting export",
      });
    }
  };

  const handleDownloadExport = async () => {
    try {
      const response = await downloadParkAnalyticsExport(exportProgress.taskId);

      // Response is a blob
      const blob = response.data;
      const filename = exportProgress.filename || `parc_export_${new Date().toISOString().split('T')[0]}.zip`;

      // Create download link
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success("Export downloaded successfully");
      setExportProgress(prev => ({ ...prev, isOpen: false }));
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Error downloading export",
      });
    }
  };

  const renderPieChart = (data, title, dataKey = "count", nameKey = "type") => (
    <div className="h-80">
      <h3 className="text-lg font-semibold mb-4 text-center">{title}</h3>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={({ name, percentage }) => {
              // Only show percentage on pie slices, not full names
              return percentage > 3 ? `${percentage}%` : "";
            }}
            dataKey={dataKey}
            nameKey={nameKey}
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip formatter={(value, name) => [value.toLocaleString(), name]} />
          <Legend
            wrapperStyle={{ fontSize: '12px' }}
            formatter={(value, entry) => {
              const item = data.find(d => d[nameKey] === value);
              if (item) {
                return `${value} (${item.percentage}% - ${item[dataKey].toLocaleString()})`;
              }
              return value;
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );

  const renderBarChart = (data, title, dataKey = "count", nameKey = "type") => (
    <div className="h-80">
      <h3 className="text-lg font-semibold mb-4 text-center">{title}</h3>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey={nameKey}
            angle={-45}
            textAnchor="end"
            height={100}
            fontSize={12}
          />
          <YAxis />
          <Tooltip
            formatter={(value, name) => [value.toLocaleString(), "Abonnés"]}
          />
          <Bar dataKey={dataKey} fill="#0088FE" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Parc Corporate NGBSS</h1>
          <p className="text-gray-600">
            Tableau de bord analytique en temps réel
          </p>
        </div>
        <div className="flex items-center space-x-4">
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center space-x-2"
          >
            <Filter className="h-4 w-4" />
            <span>Filtres</span>
          </Button>
          <Button
            onClick={fetchAllData}
            variant="outline"
            className="flex items-center space-x-2"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Actualiser</span>
          </Button>
          <Button
            onClick={() => handleExport("excel", "both")}
            className="flex items-center space-x-2"
            variant="default"
          >
            <Download className="h-4 w-4" />
            <span>Export (Both Files)</span>
          </Button>
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <Card>
          <CardHeader>
            <CardTitle>Filtres</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <Label>DOT</Label>
                <Select
                  value={filters.dot_filter}
                  onValueChange={(value) =>
                    setFilters((prev) => ({ ...prev, dot_filter: value }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner DOT" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Tous</SelectItem>
                    {availableFilters.dots
                      ?.slice()
                      .sort((a, b) => a.name.localeCompare(b.name))
                      .map((dot) => (
                        <SelectItem key={dot.id} value={dot.id.toString()}>
                          {dot.name}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Statut Abonné</Label>
                <Select
                  value={filters.subscriber_status_filter}
                  onValueChange={(value) =>
                    setFilters((prev) => ({
                      ...prev,
                      subscriber_status_filter: value,
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner statut" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Tous</SelectItem>
                    {availableFilters.subscriber_statuses?.map((status) => (
                      <SelectItem key={status} value={status}>
                        {status}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Type Télécom</Label>
                <Select
                  value={filters.telecom_type_filter}
                  onValueChange={(value) =>
                    setFilters((prev) => ({
                      ...prev,
                      telecom_type_filter: value,
                    }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Sélectionner type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">Tous</SelectItem>
                    {availableFilters.telecom_types?.map((type) => (
                      <SelectItem key={type} value={type}>
                        {type}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Code Actel</Label>
                <Input
                  placeholder="Rechercher code actel"
                  value={filters.actel_code_filter}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      actel_code_filter: e.target.value,
                    }))
                  }
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  Total Parc Abonnés
                </p>
                <p className="text-3xl font-bold text-blue-600">
                  {overview.total_active_subscribers?.toLocaleString() || "0"}
                </p>
              </div>
              <Users className="h-8 w-8 text-blue-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">Total DOTs</p>
                <p className="text-3xl font-bold text-green-600">
                  {overview.total_dots || "0"}
                </p>
              </div>
              <Building className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  Activité Récente
                </p>
                <p className="text-3xl font-bold text-orange-600">
                  {overview.recent_activity?.toLocaleString() || "0"}
                </p>
                <p className="text-xs text-gray-500">7 derniers jours</p>
              </div>
              <TrendingUp className="h-8 w-8 text-orange-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">
                  Dernière MAJ
                </p>
                <p className="text-sm font-bold text-purple-600">
                  {overview.last_updated
                    ? new Date(overview.last_updated).toLocaleString("fr-FR")
                    : "N/A"}
                </p>
              </div>
              <RefreshCw className="h-8 w-8 text-purple-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="overview">Aperçu</TabsTrigger>
          <TabsTrigger value="telecom">Type Télécom</TabsTrigger>
          <TabsTrigger value="status">Statut Abonné</TabsTrigger>
          <TabsTrigger value="customer-l2">Customer L2</TabsTrigger>
          <TabsTrigger value="customer-l3">Customer L3</TabsTrigger>
          <TabsTrigger value="dot">Par DOT</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-6">
                {renderPieChart(
                  telecomTypeData,
                  "Distribution par Type Télécom",
                  "count",
                  "type"
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                {renderPieChart(
                  subscriberStatusData,
                  "Distribution par Statut Abonné",
                  "count",
                  "status"
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="telecom" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-6">
                {renderPieChart(
                  telecomTypeData,
                  "Distribution par Type Télécom",
                  "count",
                  "type"
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                {renderBarChart(
                  telecomTypeData,
                  "Abonnés par Type Télécom",
                  "count",
                  "type"
                )}
              </CardContent>
            </Card>
          </div>

          {/* Data Table */}
          <Card>
            <CardHeader>
              <CardTitle>Détails par Type Télécom</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type Télécom</TableHead>
                    <TableHead>Nombre d'Abonnés</TableHead>
                    <TableHead>Pourcentage</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {telecomTypeData.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">{item.type}</TableCell>
                      <TableCell>{item.count.toLocaleString()}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{item.percentage}%</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="status" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-6">
                {renderPieChart(
                  subscriberStatusData,
                  "Distribution par Statut",
                  "count",
                  "status"
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                {renderBarChart(
                  subscriberStatusData,
                  "Abonnés par Statut",
                  "count",
                  "status"
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="customer-l2" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-6">
                {renderPieChart(
                  customerL2Data.slice(0, 10),
                  "Distribution par Code Customer L2",
                  "count",
                  "description"
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                {renderBarChart(
                  customerL2Data.slice(0, 10),
                  "Top 10 Customer L2",
                  "count",
                  "code"
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="customer-l3" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-6">
                {renderPieChart(
                  customerL3Data.slice(0, 10),
                  "Distribution par Code Customer L3",
                  "count",
                  "description"
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                {renderBarChart(
                  customerL3Data.slice(0, 10),
                  "Top 10 Customer L3",
                  "count",
                  "code"
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="dot" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardContent className="p-6">
                {renderPieChart(
                  dotData,
                  "Distribution par DOT",
                  "count",
                  "dot_name"
                )}
              </CardContent>
            </Card>

            <Card>
              <CardContent className="p-6">
                {renderBarChart(
                  dotData,
                  "Abonnés par DOT",
                  "count",
                  "dot_name"
                )}
              </CardContent>
            </Card>
          </div>

          {/* DOT Data Table */}
          <Card>
            <CardHeader>
              <CardTitle>Détails par DOT</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>DOT</TableHead>
                    <TableHead>Nombre d'Abonnés</TableHead>
                    <TableHead>Pourcentage</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {dotData.map((item, index) => (
                    <TableRow key={index}>
                      <TableCell className="font-medium">
                        {item.dot_name}
                      </TableCell>
                      <TableCell>{item.count.toLocaleString()}</TableCell>
                      <TableCell>
                        <Badge variant="outline">{item.percentage}%</Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Export Progress Dialog */}
      <Dialog open={exportProgress.isOpen} onOpenChange={(open) => setExportProgress(prev => ({ ...prev, isOpen: open }))}>
        <DialogContent className="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>Export Progress</DialogTitle>
            <DialogDescription>
              {exportProgress.status === 'completed' ? 'Export completed successfully!' : 'Please wait while your data is being exported...'}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">Progress</span>
                <span className="font-medium">{exportProgress.progress}%</span>
              </div>
              <Progress value={exportProgress.progress} className="h-2" />
            </div>

            {/* Status Icon and Message */}
            <div className="flex items-start space-x-3">
              {exportProgress.status === 'processing' && (
                <Loader2 className="h-5 w-5 animate-spin text-blue-500 mt-0.5" />
              )}
              {exportProgress.status === 'completed' && (
                <CheckCircle2 className="h-5 w-5 text-green-500 mt-0.5" />
              )}
              {exportProgress.status === 'failed' && (
                <XCircle className="h-5 w-5 text-red-500 mt-0.5" />
              )}
              <div className="flex-1 space-y-1">
                <p className="text-sm font-medium">
                  {exportProgress.status === 'completed' && 'Export Ready'}
                  {exportProgress.status === 'processing' && 'Processing...'}
                  {exportProgress.status === 'failed' && 'Export Failed'}
                </p>
                <p className="text-sm text-muted-foreground">{exportProgress.message}</p>
                {exportProgress.filename && (
                  <p className="text-xs text-muted-foreground mt-2">
                    File: {exportProgress.filename}
                  </p>
                )}
              </div>
            </div>

            {/* Download Button */}
            {exportProgress.status === 'completed' && (
              <Button
                onClick={handleDownloadExport}
                className="w-full"
                variant="default"
              >
                <Download className="h-4 w-4 mr-2" />
                Download Export
              </Button>
            )}

            {/* Close Button */}
            {(exportProgress.status === 'completed' || exportProgress.status === 'failed') && (
              <Button
                onClick={() => setExportProgress(prev => ({ ...prev, isOpen: false }))}
                className="w-full"
                variant="outline"
              >
                Close
              </Button>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ParcCorporateNGBSSPage;
