import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MultiSelect } from "@/components/ui/multi-select";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
} from "recharts";
import {
  getRevenueOverview,
  getRevenueByAccount,
  getRevenueByOrg,
  getRevenueFilters,
  exportRevenueData,
} from "../../services/api";
import { Download, RefreshCw, TrendingUp, Target, DollarSign } from "lucide-react";

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
  primary: "#4A90E2",    // Bleu
  secondary: "#E2734A",  // Orange
  success: "#5CB85C",    // Vert
  danger: "#D9534F",     // Rouge
};

/**
 * Tableau de Bord Card Component (Image style)
 */
const DashboardCard = ({ title, value, icon: Icon, color = "primary" }) => {
  const bgColors = {
    primary: "bg-blue-500",
    secondary: "bg-orange-500",
    success: "bg-green-500",
  };

  return (
    <Card className="border-2 hover:shadow-lg transition-shadow">
      <CardHeader className={`${bgColors[color]} text-white py-3`}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-bold uppercase tracking-wide">
            {title}
          </CardTitle>
          {Icon && <Icon className="h-10 w-10 opacity-80" />}
        </div>
      </CardHeader>
      <CardContent className="pt-6 text-center">
        <div className="text-3xl font-bold text-gray-900">{value}</div>
      </CardContent>
    </Card>
  );
};

/**
 * Custom Tooltip pour les graphiques
 */
const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-4 border-2 border-gray-300 rounded-lg shadow-xl">
        <p className="font-bold text-gray-900 mb-2">{label}</p>
        {payload.map((entry, index) => (
          <p key={index} style={{ color: entry.color }} className="text-sm font-semibold">
            {entry.name}: {formatNumber(entry.value)}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

const CustomTooltipPercent = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-white p-4 border-2 border-gray-300 rounded-lg shadow-xl">
        <p className="font-bold text-gray-900 mb-2">{label}</p>
        <p style={{ color: payload[0].color }} className="text-sm font-semibold">
          Taux: {formatPercent(payload[0].value)}
        </p>
      </div>
    );
  }
  return null;
};

/**
 * Main Revenue Page Component
 */
const RevenuePage = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [activeTab, setActiveTab] = useState("ca-objectif");

  // Data state
  const [overview, setOverview] = useState({
    total_revenue: 0,
    total_revenue_ttc: 0,
    total_records: 0,
    by_org_name: {},
    by_month: {},
    by_month_objective: {},
    anomalies_count: 0,
  });
  const [byAccount, setByAccount] = useState([]);
  const [byOrg, setByOrg] = useState([]);

  // Filters state
  const [filters, setFilters] = useState({
    start_date: "",
    end_date: "",
    org_name: [],
    achievement_rate_ranges: [],
  });

  // Available filter options
  const [availableFilters, setAvailableFilters] = useState({
    org_names: [],
    months: [],
    achievement_rate_ranges: [
      { label: "0-25%", min: 0, max: 25 },
      { label: "25-50%", min: 25, max: 50 },
      { label: "50-75%", min: 50, max: 75 },
      { label: "75-100%", min: 75, max: 100 },
      { label: "100%+", min: 100, max: 999999 },
    ],
  });

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
      const [ovRes, orgRes, accRes] = await Promise.all([
        getRevenueOverview(filters),
        getRevenueByOrg(filters),
        getRevenueByAccount(filters),
      ]);

      setOverview(ovRes.data || {});
      setByOrg(orgRes.data || []);
      setByAccount(accRes.data || []);
    } catch (error) {
      console.error("Error fetching data:", error);
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
      setAvailableFilters((prev) => ({
        ...prev,
        org_names: res.data.org_names || [],
        months: res.data.months || [],
      }));
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
    const totalObjective = Object.values(overview.by_month_objective || {}).reduce(
      (sum, val) => sum + (val || 0),
      0
    );

    if (totalObjective === 0) return 0;
    return (totalRevenue / totalObjective) * 100;
  }, [overview]);

  /**
   * CHART 1: C.A vs Objectif par mois (Image #3)
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
   * CHART 2: Description Cpt Comptable (Image #2)
   */
  const accountChartData = useMemo(() => {
    return byAccount
      .map((item) => ({
        compte: (item.cpt_comptable || "Inconnu").substring(0, 20), // Limiter longueur
        Total: item.total_revenue || 0,
      }))
      .sort((a, b) => b.Total - a.Total)
      .slice(0, 20); // Top 20
  }, [byAccount]);

  /**
   * CHART 3: DOT et Taux de réalisation (Image #1)
   */
  const dotTauxChartData = useMemo(() => {
    return byOrg
      .map((item) => ({
        dot: item.org_name || "Inconnu",
        taux: item.achievement_rate || 0,
      }))
      .sort((a, b) => b.taux - a.taux)
      .slice(0, 30); // Top 30
  }, [byOrg]);

  /**
   * Export handler
   */
  const handleExport = async (format = "xlsx") => {
    try {
      const exportParams = { ...filters, format };
      if (Array.isArray(exportParams.org_name) && exportParams.org_name.length > 0) {
        exportParams.org_name = exportParams.org_name.join(",");
      }

      const res = await exportRevenueData(exportParams);
      const mimeType =
        format === "xlsx"
          ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          : "text/csv";
      const blob = new Blob([res.data], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `revenue_export_${new Date().toISOString().slice(0, 10)}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Error exporting data:", error);
    }
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
            Tableau de Bord - Chiffre d'Affaires AR DOT
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Analyse du CA et taux de réalisation par DOT
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
            onClick={() => handleExport("xlsx")}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            <Download className="h-4 w-4 mr-2" />
            Excel
          </Button>
          <Button
            onClick={() => handleExport("csv")}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            <Download className="h-4 w-4 mr-2" />
            CSV
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Filtres</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* DOT Filter */}
            <div>
              <Label>DOT (Organisation)</Label>
              <MultiSelect
                options={availableFilters.org_names.map((name) => ({
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

            {/* Date Range */}
            <div>
              <Label>Date début</Label>
              <Input
                type="date"
                value={filters.start_date}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, start_date: e.target.value }))
                }
              />
            </div>

            <div>
              <Label>Date fin</Label>
              <Input
                type="date"
                value={filters.end_date}
                onChange={(e) =>
                  setFilters((f) => ({ ...f, end_date: e.target.value }))
                }
              />
            </div>
          </div>

          {/* Taux de réalisation filter */}
          <div className="mt-4">
            <Label className="mb-2 block">Taux de réalisation C.A</Label>
            <div className="flex flex-wrap gap-4">
              {availableFilters.achievement_rate_ranges.map((range, index) => (
                <div key={index} className="flex items-center space-x-2">
                  <Checkbox
                    id={`rate-${index}`}
                    checked={filters.achievement_rate_ranges.includes(range.label)}
                    onCheckedChange={(checked) => {
                      if (checked) {
                        setFilters((f) => ({
                          ...f,
                          achievement_rate_ranges: [
                            ...f.achievement_rate_ranges,
                            range.label,
                          ],
                        }));
                      } else {
                        setFilters((f) => ({
                          ...f,
                          achievement_rate_ranges: f.achievement_rate_ranges.filter(
                            (r) => r !== range.label
                          ),
                        }));
                      }
                    }}
                  />
                  <label
                    htmlFor={`rate-${index}`}
                    className="text-sm font-medium cursor-pointer"
                  >
                    {range.label}
                  </label>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 flex justify-end">
            <Button onClick={() => fetchData()} className="bg-blue-600 hover:bg-blue-700">
              Appliquer les filtres
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* TABLEAU DE BORD - Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <DashboardCard
          title="Chiffre d'affaires"
          value={formatNumber(overview.total_revenue)}
          icon={DollarSign}
          color="primary"
        />
        <DashboardCard
          title="Objectif C.A"
          value={formatNumber(
            Object.values(overview.by_month_objective || {}).reduce(
              (sum, val) => sum + (val || 0),
              0
            )
          )}
          icon={Target}
          color="secondary"
        />
        <DashboardCard
          title="Taux de réalisation C.A"
          value={formatPercent(globalAchievementRate)}
          icon={TrendingUp}
          color="success"
        />
      </div>

      {/* TABS WITH CHARTS */}
      <Card>
        <CardContent className="pt-6">
          <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
            <TabsList className="grid w-full grid-cols-3 mb-6">
              <TabsTrigger value="ca-objectif" className="text-sm">
                C.A vs Objectif par Mois
              </TabsTrigger>
              <TabsTrigger value="cpt-comptable" className="text-sm">
                Description Cpt Comptable
              </TabsTrigger>
              <TabsTrigger value="dot-taux" className="text-sm">
                DOT et Taux de Réalisation
              </TabsTrigger>
            </TabsList>

            {/* TAB 1: C.A vs Objectif (Image #3) */}
            <TabsContent value="ca-objectif" className="space-y-4">
              <div className="border-b pb-2">
                <h3 className="text-lg font-semibold text-gray-900">
                  Histogramme combiné (C.A et Objectif par mois de Date GL)
                </h3>
              </div>
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
                      new Intl.NumberFormat("fr-FR", { notation: "compact" }).format(value)
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
            </TabsContent>

            {/* TAB 2: Description Cpt Comptable (Image #2) */}
            <TabsContent value="cpt-comptable" className="space-y-4">
              <div className="border-b pb-2">
                <h3 className="text-lg font-semibold text-gray-900">
                  Histogramme (Description Cpt Comptable)
                </h3>
              </div>
              <ResponsiveContainer width="100%" height={450}>
                <BarChart data={accountChartData} margin={{ bottom: 80, left: 20 }}>
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
                      new Intl.NumberFormat("fr-FR", { notation: "compact" }).format(value)
                    }
                    style={{ fontSize: "12px" }}
                  />
                  <Tooltip content={<CustomTooltip />} />
                  <Legend wrapperStyle={{ fontSize: "14px", paddingTop: "10px" }} />
                  <Bar dataKey="Total" fill={COLORS.primary} radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </TabsContent>

            {/* TAB 3: DOT et Taux (Image #1) */}
            <TabsContent value="dot-taux" className="space-y-4">
              <div className="border-b pb-2">
                <h3 className="text-lg font-semibold text-gray-900">
                  TAUX DE RÉALISATION C.A par DOT
                </h3>
              </div>
              <ResponsiveContainer width="100%" height={700}>
                <BarChart
                  data={dotTauxChartData}
                  layout="vertical"
                  margin={{ left: 120, right: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
                  <XAxis
                    type="number"
                    tickFormatter={(value) => `${value.toFixed(0)}%`}
                    style={{ fontSize: "12px" }}
                  />
                  <YAxis
                    dataKey="dot"
                    type="category"
                    width={110}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip content={<CustomTooltipPercent />} />
                  <Bar dataKey="taux" radius={[0, 4, 4, 0]}>
                    {dotTauxChartData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.taux >= 100 ? COLORS.success : COLORS.primary}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </div>
  );
};

export default RevenuePage;
