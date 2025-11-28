import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MultiSelect } from "@/components/ui/multi-select";
import { Checkbox } from "@/components/ui/checkbox";
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
import { Download, RefreshCw, TrendingUp, Target, DollarSign } from "lucide-react";
import {
  getRevenueOverview,
  getRevenueByAccount,
  getRevenueByOrg,
  getRevenueFilters,
  exportRevenueData,
} from "../../services/api";

// French number formatter with thousand separator and 2 decimals
const formatNumber = (value) => {
  if (value === null || value === undefined) return "0,00";
  return new Intl.NumberFormat("fr-FR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
};

const formatCurrency = (value) => {
  return `${formatNumber(value)} DZD`;
};

const formatPercent = (value) => {
  return `${formatNumber(value)}%`;
};

// Color palette matching the images
const COLORS = {
  primary: "#1e88e5",
  secondary: "#43a047",
  accent: "#fb8c00",
  danger: "#e53935",
};

/**
 * Overview Card Component (Tableau de Bord style)
 */
const DashboardCard = ({ title, value, subtitle, icon: Icon, color = "primary" }) => {
  const colorMap = {
    primary: "bg-blue-500",
    secondary: "bg-green-500",
    accent: "bg-orange-500",
    danger: "bg-red-500",
  };

  return (
    <Card className="hover:shadow-lg transition-shadow border-2">
      <CardHeader className={`${colorMap[color]} text-white py-3`}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold uppercase">{title}</CardTitle>
          {Icon && <Icon className="h-8 w-8" />}
        </div>
      </CardHeader>
      <CardContent className="pt-6">
        <div className="text-3xl font-bold text-gray-900">{value}</div>
        {subtitle && (
          <p className="text-sm text-gray-600 mt-2">{subtitle}</p>
        )}
      </CardContent>
    </Card>
  );
};

/**
 * Main Revenue Enhanced Page Component
 */
const RevenueEnhancedPage = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Overview data
  const [overview, setOverview] = useState({
    total_revenue: 0,
    total_revenue_ttc: 0,
    total_records: 0,
    by_org_name: {},
    by_month: {},
    by_month_objective: {},
    anomalies_count: 0,
  });

  // Chart data
  const [byOrg, setByOrg] = useState([]);
  const [byAccount, setByAccount] = useState([]);

  // Filters state
  const [filters, setFilters] = useState({
    start_date: "",
    end_date: "",
    org_name: [],
    achievement_rate_ranges: [], // New: Taux de réalisation filter
  });

  // Available filter options
  const [availableFilters, setAvailableFilters] = useState({
    org_names: [],
    months: [],
    achievement_rate_ranges: [],
  });

  /**
   * Fetch dashboard data
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

      setOverview(ovRes.data);
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
   * Fetch available filter values
   */
  const fetchFilters = async () => {
    try {
      const res = await getRevenueFilters();
      setAvailableFilters(res.data);
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
      (sum, val) => sum + val,
      0
    );

    if (totalObjective === 0) return 0;
    return (totalRevenue / totalObjective) * 100;
  }, [overview]);

  /**
   * VISUALIZATION 1: Combined Bar Chart (C.A vs Objectif par mois)
   * Format: [{mois, ca, objectif}]
   */
  const monthlyChartData = useMemo(() => {
    const months = [
      ...new Set([
        ...Object.keys(overview.by_month || {}),
        ...Object.keys(overview.by_month_objective || {}),
      ]),
    ].sort();

    return months.map((month) => {
      // Format: "2024-01" → "Jan"
      const date = new Date(month + "-01");
      const monthName = date.toLocaleString("fr-FR", { month: "short" });

      return {
        mois: monthName,
        "C.A": overview.by_month[month] || 0,
        Objectif: overview.by_month_objective[month] || 0,
      };
    });
  }, [overview.by_month, overview.by_month_objective]);

  /**
   * VISUALIZATION 2: DOT Taux de réalisation (Horizontal bar chart)
   * Format: [{dot, taux}]
   */
  const dotChartData = useMemo(() => {
    return byOrg
      .map((item) => ({
        dot: item.org_name || "Inconnu",
        taux: item.achievement_rate || 0,
      }))
      .sort((a, b) => b.taux - a.taux) // Sort by taux descending
      .slice(0, 20); // Top 20 only for readability
  }, [byOrg]);

  /**
   * Export data handler
   */
  const handleExport = async (format = "xlsx") => {
    try {
      const exportParams = {
        ...filters,
        format,
      };

      // Convert arrays to comma-separated strings for API
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

  /**
   * Custom tooltip for bar charts
   */
  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
          <p className="font-semibold mb-2">{label}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color }} className="text-sm">
              {entry.name}: {formatCurrency(entry.value)}
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
        <div className="bg-white p-3 border border-gray-300 rounded shadow-lg">
          <p className="font-semibold mb-2">{label}</p>
          <p style={{ color: payload[0].color }} className="text-sm">
            Taux: {formatPercent(payload[0].value)}
          </p>
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
            Tableau de Bord - Chiffre d'Affaires
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

          {/* Taux de réalisation filter (Checkboxes) */}
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
                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
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

      {/* OVERVIEW - Tableau de Bord (Image #3) */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <DashboardCard
          title="Chiffre d'affaires"
          value={formatCurrency(overview.total_revenue)}
          icon={DollarSign}
          color="primary"
        />
        <DashboardCard
          title="Objectif C.A"
          value={formatCurrency(
            Object.values(overview.by_month_objective || {}).reduce(
              (sum, val) => sum + val,
              0
            )
          )}
          icon={Target}
          color="accent"
        />
        <DashboardCard
          title="Taux de réalisation C.A"
          value={formatPercent(globalAchievementRate)}
          subtitle={`${overview.total_records} enregistrements`}
          icon={TrendingUp}
          color="secondary"
        />
      </div>

      {/* VISUALIZATION 1: Histogramme combiné (C.A et Objectif par mois) - Image #4 */}
      <Card>
        <CardHeader>
          <CardTitle>Histogramme combiné (C.A et Objectif par mois de Date GL)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={monthlyChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="mois"
                angle={-45}
                textAnchor="end"
                height={80}
              />
              <YAxis
                tickFormatter={(value) =>
                  new Intl.NumberFormat("fr-FR", {notation: "compact"}).format(value)
                }
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Bar dataKey="C.A" fill={COLORS.primary} />
              <Bar dataKey="Objectif" fill={COLORS.secondary} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* VISUALIZATION 2: Histogramme (DOT et Taux de réalisation) - Image #5 */}
      <Card>
        <CardHeader>
          <CardTitle>TAUX DE RÉALISATION C.A par DOT</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={600}>
            <BarChart
              data={dotChartData}
              layout="vertical"
              margin={{ left: 150 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                type="number"
                tickFormatter={(value) => `${value}%`}
              />
              <YAxis
                dataKey="dot"
                type="category"
                width={140}
                tick={{ fontSize: 12 }}
              />
              <Tooltip content={<CustomTooltipPercent />} />
              <Bar dataKey="taux" fill={COLORS.primary}>
                {dotChartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.taux >= 100 ? COLORS.secondary : COLORS.primary}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
};

export default RevenueEnhancedPage;
