import React, { useState, useEffect } from "react";
import { parkAnalyticsAPI } from "../../services/api";
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

  useEffect(() => {
    fetchAllData();
  }, []);

  const fetchAllData = async () => {
    try {
      setLoading(true);
      const [
        overviewRes,
        telecomRes,
        statusRes,
        l2Res,
        l3Res,
        dotRes,
        filtersRes,
      ] = await Promise.all([
        parkAnalyticsAPI.getOverview(),
        parkAnalyticsAPI.getByTelecomType(),
        parkAnalyticsAPI.getBySubscriberStatus(),
        parkAnalyticsAPI.getByCustomerL2(),
        parkAnalyticsAPI.getByCustomerL3(),
        parkAnalyticsAPI.getByDOT(),
        parkAnalyticsAPI.getAvailableFilters(),
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

  const handleExport = async (format = "csv") => {
    try {
      const response = await parkAnalyticsAPI.exportData(filters, format);

      // Create and download file
      const data = response.data.data;
      const headers = Object.keys(data[0] || {});

      let content = "";
      if (format === "csv") {
        content = headers.join(",") + "\n";
        content += data
          .map((row) =>
            headers.map((header) => `"${row[header] || ""}"`).join(",")
          )
          .join("\n");
      }

      const blob = new Blob([content], {
        type: format === "csv" ? "text/csv" : "application/vnd.ms-excel",
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `parc_corporate_ngbss_${
        new Date().toISOString().split("T")[0]
      }.${format}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      toast.success(`Données exportées en ${format.toUpperCase()}`);
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors de l'export",
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
            label={({ name, percentage }) => `${name}: ${percentage}%`}
            outerRadius={80}
            fill="#8884d8"
            dataKey={dataKey}
            nameKey={nameKey}
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={
                  TELECOM_COLORS[entry[nameKey]] ||
                  COLORS[index % COLORS.length]
                }
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value, name) => [value.toLocaleString(), name]}
          />
          <Legend />
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
            onClick={() => handleExport("csv")}
            className="flex items-center space-x-2"
          >
            <Download className="h-4 w-4" />
            <span>Exporter CSV</span>
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
                    {availableFilters.dots?.map((dot) => (
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
                  Total Abonnés Actifs
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
    </div>
  );
};

export default ParcCorporateNGBSSPage;
