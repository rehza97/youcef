import React, { useState, useEffect } from "react";
import {
  getParkAnalyticsOverview,
  getParkAnalyticsByTelecomType,
  getParkAnalyticsBySubscriberStatus,
  getParkAnalyticsByDOT,
  getParkAnalyticsByCustomerL2,
  getParkAnalyticsByCustomerL3,
  getParkAnalyticsAvailableFilters,
  exportParkAnalyticsData,
} from "../../services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  PieChart as RePieChart,
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Upload,
  Download,
  BarChart3,
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
  const [telecomTypeData, setTelecomTypeData] = useState([]);
  const [subscriberStatusData, setSubscriberStatusData] = useState([]);
  const [dotData, setDotData] = useState([]);
  const [customerL2Data, setCustomerL2Data] = useState([]);
  const [customerL3Data, setCustomerL3Data] = useState([]);
  const [availableFilters, setAvailableFilters] = useState({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    dot_filter: "all",
    actel_code_filter: "all",
    subscriber_status_filter: "all",
    telecom_type_filter: "all",
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [
        overviewRes,
        telecomRes,
        statusRes,
        dotRes,
        l2Res,
        l3Res,
        filtersRes,
      ] = await Promise.all([
        getParkAnalyticsOverview(),
        getParkAnalyticsByTelecomType(),
        getParkAnalyticsBySubscriberStatus(),
        getParkAnalyticsByDOT(),
        getParkAnalyticsByCustomerL2(),
        getParkAnalyticsByCustomerL3(),
        getParkAnalyticsAvailableFilters(),
      ]);

      setOverview(overviewRes.data || {});
      setTelecomTypeData(telecomRes.data?.distribution || []);
      setSubscriberStatusData(statusRes.data?.distribution || []);
      setDotData(dotRes.data?.distribution || []);
      setCustomerL2Data(l2Res.data?.distribution || []);
      setCustomerL3Data(l3Res.data?.distribution || []);
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

  // (Removed unused format helpers to satisfy linter)

  const exportData = async (format = "csv") => {
    try {
      // Convert "all" values to empty strings for API compatibility
      const apiFilters = {
        dot_filter: filters.dot_filter === "all" ? "" : filters.dot_filter,
        actel_code_filter:
          filters.actel_code_filter === "all" ? "" : filters.actel_code_filter,
        subscriber_status_filter:
          filters.subscriber_status_filter === "all"
            ? ""
            : filters.subscriber_status_filter,
        telecom_type_filter:
          filters.telecom_type_filter === "all"
            ? ""
            : filters.telecom_type_filter,
      };
      const response = await exportParkAnalyticsData(apiFilters, format);
      const data = response.data.data || response.data.distribution || [];

      if (data.length === 0) {
        toast.info("Aucune donnée disponible à exporter");
        return;
      }

      const headers = Object.keys(data[0] || {});
      let content = headers.join(",") + "\n";
      content += data
        .map((row) => headers.map((h) => `"${row[h] || ""}"`).join(","))
        .join("\n");
      const blob = new Blob([content], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `encaissement_parc_${
        new Date().toISOString().split("T")[0]
      }.csv`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success("Export CSV généré");
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur export",
      });
    }
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
        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={() => setShowFilters((s) => !s)}>
            Filtres
          </Button>
          <Button variant="outline" onClick={fetchData}>
            Actualiser
          </Button>
          <Button onClick={() => exportData("csv")}>Exporter CSV</Button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Abonnés Actifs
            </CardTitle>
            <Building className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview.total_active_subscribers || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              DOTs Accessibles
            </CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{overview.total_dots || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Activité 7 Jours
            </CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview.recent_activity || 0}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Dernière Mise à jour
            </CardTitle>
            <Percent className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {new Date(overview.last_updated || Date.now()).toLocaleString()}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
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
                  onValueChange={(v) =>
                    setFilters((p) => ({ ...p, dot_filter: v }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Tous" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous</SelectItem>
                    {availableFilters.dots?.map((d) => (
                      <SelectItem key={d.id} value={d.id.toString()}>
                        {d.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Statut</Label>
                <Select
                  value={filters.subscriber_status_filter}
                  onValueChange={(v) =>
                    setFilters((p) => ({ ...p, subscriber_status_filter: v }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Tous" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous</SelectItem>
                    {availableFilters.subscriber_statuses?.map((s) => (
                      <SelectItem key={s} value={s}>
                        {s}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Type Télécom</Label>
                <Select
                  value={filters.telecom_type_filter}
                  onValueChange={(v) =>
                    setFilters((p) => ({ ...p, telecom_type_filter: v }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Tous" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tous</SelectItem>
                    {availableFilters.telecom_types?.map((t) => (
                      <SelectItem key={t} value={t}>
                        {t}
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
                    setFilters((p) => ({
                      ...p,
                      actel_code_filter: e.target.value,
                    }))
                  }
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Tabs */}
      <div className="flex space-x-2 border-b">
        {[
          { id: "overview", label: "Aperçu", icon: BarChart3 },
          { id: "organisation", label: "Par Organisation", icon: Building },
          { id: "l2", label: "Par Customer L2", icon: FileText },
          { id: "l3", label: "Par Customer L3", icon: FileText },
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
            {/* Telecom type distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Distribution par Type Télécom</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <RePieChart>
                      <Pie
                        data={telecomTypeData}
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        dataKey="count"
                        nameKey="type"
                        label
                      >
                        {telecomTypeData.map((_, i) => (
                          <Cell
                            key={i}
                            fill={
                              [
                                "#0088FE",
                                "#00C49F",
                                "#FFBB28",
                                "#FF8042",
                                "#8884D8",
                              ][i % 5]
                            }
                          />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v) => v.toLocaleString()} />
                      <Legend />
                    </RePieChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Subscriber status distribution */}
            <Card>
              <CardHeader>
                <CardTitle>Distribution par Statut Abonné</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={subscriberStatusData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="status" />
                      <YAxis />
                      <Tooltip formatter={(v) => v.toLocaleString()} />
                      <Bar dataKey="count" fill="#7C3AED" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === "organisation" && (
          <Card>
            <CardHeader>
              <CardTitle>Abonnés par DOT</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-96">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={dotData}
                    margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="dot_name"
                      angle={-45}
                      textAnchor="end"
                      interval={0}
                      height={80}
                    />
                    <YAxis />
                    <Tooltip formatter={(v) => v.toLocaleString()} />
                    <Bar dataKey="count" fill="#10B981" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        )}

        {activeTab === "l2" && (
          <Card>
            <CardHeader>
              <CardTitle>Distribution par Customer L2</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-96">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={customerL2Data}
                    margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="description"
                      angle={-45}
                      textAnchor="end"
                      interval={0}
                      height={80}
                    />
                    <YAxis />
                    <Tooltip formatter={(v) => v.toLocaleString()} />
                    <Bar dataKey="count" fill="#3B82F6" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        )}

        {activeTab === "l3" && (
          <Card>
            <CardHeader>
              <CardTitle>Distribution par Customer L3</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-96">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={customerL3Data}
                    margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="description"
                      angle={-45}
                      textAnchor="end"
                      interval={0}
                      height={80}
                    />
                    <YAxis />
                    <Tooltip formatter={(v) => v.toLocaleString()} />
                    <Bar dataKey="count" fill="#F59E0B" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default EncaissementPage;
