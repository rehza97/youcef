import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
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
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Download, RefreshCw, TrendingUp, DollarSign, FileText, CreditCard } from "lucide-react";
import {
  getCreanceDashboardOverview,
  getCreanceByDotAggregates,
  getCreanceByAnneeAggregates,
  getCreanceByProduitAggregates,
  getCreanceByCustLev2Aggregates,
  getCreanceAvailableYears,
  getCreanceAvailableDots,
  getCreanceAvailableProducts,
  exportCreanceRecords,
} from "../../services/api";

// Number formatter for French locale
const numberFr = new Intl.NumberFormat("fr-FR", {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2,
});

const formatCurrency = (value) => {
  return `${numberFr.format(value || 0)} DZD`;
};

// Color palette for charts
const COLORS = [
  "#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8",
  "#82ca9d", "#ffc658", "#ff7c7c", "#8dd1e1", "#d084d0"
];

/**
 * Overview KPI Card Component
 */
const OverviewCard = ({ title, value, subtitle, icon: Icon, color = "blue" }) => (
  <Card className="hover:shadow-lg transition-shadow">
    <CardHeader className="flex flex-row items-center justify-between pb-2">
      <CardTitle className="text-sm font-medium text-muted-foreground">
        {title}
      </CardTitle>
      {Icon && (
        <Icon className={`h-5 w-5 text-${color}-600`} />
      )}
    </CardHeader>
    <CardContent>
      <div className={`text-2xl font-bold text-${color}-700`}>{value}</div>
      {subtitle && (
        <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
      )}
    </CardContent>
  </Card>
);

/**
 * Main Créance Périodique DOT Dashboard Page
 * Displays 5 visualizations as specified:
 * 1. OVERVIEW - KPI cards (Invoice Amount, Créance NET, etc.)
 * 2. Bar Chart - Créance NET by DOT
 * 3. Bar Chart - Créance NET by Year
 * 4. Bar Chart - Créance NET by Product
 * 5. Bar Chart - Créance NET by Customer Level 2
 */
const CreancePeriodiqueDotPage = () => {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Overview statistics
  const [overview, setOverview] = useState({
    total_invoice_amt_ht: 0,
    total_invoice_amt: 0,
    total_open_amt: 0,
    total_creance_ht: 0,
    total_creance_net: 0,
    total_creance_brut: 0,
    total_avoir_amt: 0,
    nombre_lignes: 0,
  });

  // Aggregates for visualizations
  const [byDotAggregates, setByDotAggregates] = useState([]);
  const [byAnneeAggregates, setByAnneeAggregates] = useState([]);
  const [byProduitAggregates, setByProduitAggregates] = useState([]);
  const [byCustLev2Aggregates, setByCustLev2Aggregates] = useState([]);

  // Filters
  const [filters, setFilters] = useState({
    year: new Date().getFullYear(),
  });

  // Available metadata
  const [availableYears, setAvailableYears] = useState([]);
  const [availableDots, setAvailableDots] = useState([]);
  const [availableProducts, setAvailableProducts] = useState([]);

  /**
   * Fetch all dashboard data
   */
  const fetchData = async (showRefreshing = false) => {
    if (showRefreshing) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      // Fetch all data in parallel using centralized API methods
      const [
        overviewRes,
        byDotRes,
        byAnneeRes,
        byProduitRes,
        byCustLev2Res,
        availableYearsRes,
        availableDotsRes,
        availableProductsRes,
      ] = await Promise.all([
        getCreanceDashboardOverview(),
        getCreanceByDotAggregates(),
        getCreanceByAnneeAggregates(),
        getCreanceByProduitAggregates(),
        getCreanceByCustLev2Aggregates(),
        getCreanceAvailableYears(),
        getCreanceAvailableDots(),
        getCreanceAvailableProducts(),
      ]);

      // Update state with response data
      setOverview(overviewRes.data);
      setByDotAggregates(byDotRes.data);
      setByAnneeAggregates(byAnneeRes.data);
      setByProduitAggregates(byProduitRes.data);
      setByCustLev2Aggregates(byCustLev2Res.data);
      setAvailableYears(availableYearsRes.data);
      setAvailableDots(availableDotsRes.data);
      setAvailableProducts(availableProductsRes.data);
    } catch (error) {
      console.error("Error fetching dashboard data:", error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * Format DOT data for bar chart
   */
  const dotChartData = useMemo(() => {
    return byDotAggregates.map((item) => ({
      dot: item.dot || "N/A",
      creance_net: item.total_creance_net,
      creance_brut: item.total_creance_brut,
      open_amt: item.total_open_amt,
    }));
  }, [byDotAggregates]);

  /**
   * Format year data for bar chart
   */
  const anneeChartData = useMemo(() => {
    return byAnneeAggregates.map((item) => ({
      annee: item.annee || "N/A",
      creance_net: item.total_creance_net,
      creance_brut: item.total_creance_brut,
      invoice_amt: item.total_invoice_amt,
    }));
  }, [byAnneeAggregates]);

  /**
   * Format product data for bar chart
   */
  const produitChartData = useMemo(() => {
    return byProduitAggregates.map((item) => ({
      produit: item.produit || "N/A",
      creance_net: item.total_creance_net,
      creance_brut: item.total_creance_brut,
    }));
  }, [byProduitAggregates]);

  /**
   * Format customer level 2 data for bar chart
   */
  const custLev2ChartData = useMemo(() => {
    return byCustLev2Aggregates.map((item) => ({
      cust_lev2: item.cust_lev2 || "N/A",
      creance_net: item.total_creance_net,
      creance_brut: item.total_creance_brut,
    }));
  }, [byCustLev2Aggregates]);

  /**
   * Export data to CSV
   */
  const exportCSV = async () => {
    try {
      const response = await exportCreanceRecords({ format: "csv" });
      const blob = new Blob([response.data], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `creance_periodique_dot_export_${new Date().toISOString().slice(0, 10)}.csv`;
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
  const renderBarTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white p-3 border border-gray-200 rounded shadow-lg">
          <p className="font-semibold mb-2">{label}</p>
          {payload.map((entry, index) => (
            <p key={index} className="text-sm" style={{ color: entry.color }}>
              {entry.name}: {formatCurrency(entry.value)}
            </p>
          ))}
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
            Créance Périodique DOT
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Tableau de bord - Suivi des créances par période et organisation
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
            onClick={exportCSV}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* VISUALIZATION 1: OVERVIEW - KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <OverviewCard
          title="Montant Facture HT"
          value={formatCurrency(overview.total_invoice_amt_ht)}
          subtitle={`${overview.nombre_lignes} lignes`}
          icon={FileText}
          color="blue"
        />
        <OverviewCard
          title="Créance NET"
          value={formatCurrency(overview.total_creance_net)}
          subtitle="Montant net de créance"
          icon={DollarSign}
          color="green"
        />
        <OverviewCard
          title="Créance BRUT"
          value={formatCurrency(overview.total_creance_brut)}
          subtitle="Montant brut de créance"
          icon={TrendingUp}
          color="purple"
        />
        <OverviewCard
          title="Montant Ouvert"
          value={formatCurrency(overview.total_open_amt)}
          subtitle="Montant restant ouvert"
          icon={CreditCard}
          color="orange"
        />
      </div>

      {/* VISUALIZATION 2: Bar Chart - Créance NET by DOT */}
      <Card>
        <CardHeader>
          <CardTitle>Créance NET par DOT</CardTitle>
          <p className="text-sm text-muted-foreground">
            Montant de créance nette par organisation
          </p>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={dotChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="dot" />
              <YAxis />
              <Tooltip content={renderBarTooltip} />
              <Legend />
              <Bar dataKey="creance_net" fill="#0088FE" name="Créance NET" />
              <Bar dataKey="creance_brut" fill="#00C49F" name="Créance BRUT" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* VISUALIZATION 3: Bar Chart - Créance NET by Year */}
      <Card>
        <CardHeader>
          <CardTitle>Créance NET par Année</CardTitle>
          <p className="text-sm text-muted-foreground">
            Évolution de la créance nette par année
          </p>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart data={anneeChartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="annee" />
              <YAxis />
              <Tooltip content={renderBarTooltip} />
              <Legend />
              <Bar dataKey="creance_net" fill="#00C49F" name="Créance NET" />
              <Bar dataKey="invoice_amt" fill="#FFBB28" name="Montant Facture" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* VISUALIZATION 4 & 5: Product and Customer Level 2 Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* VISUALIZATION 4: Bar Chart - Créance NET by Product */}
        <Card>
          <CardHeader>
            <CardTitle>Créance NET par Produit</CardTitle>
            <p className="text-sm text-muted-foreground">
              Répartition de la créance par type de produit
            </p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={produitChartData} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="produit" type="category" width={120} />
                <Tooltip content={renderBarTooltip} />
                <Legend />
                <Bar dataKey="creance_net" fill="#FFBB28" name="Créance NET" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* VISUALIZATION 5: Bar Chart - Créance NET by Customer Level 2 */}
        <Card>
          <CardHeader>
            <CardTitle>Créance NET par Catégorie Client</CardTitle>
            <p className="text-sm text-muted-foreground">
              Répartition de la créance par catégorie client (CUST_LEV2)
            </p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={custLev2ChartData} layout="horizontal">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="cust_lev2" type="category" width={120} />
                <Tooltip content={renderBarTooltip} />
                <Legend />
                <Bar dataKey="creance_net" fill="#FF8042" name="Créance NET" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Additional Summary */}
      <Card className="border-blue-200 bg-blue-50">
        <CardHeader>
          <CardTitle className="text-blue-700">
            Résumé Financier
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-white p-3 rounded border border-blue-200">
              <p className="text-xs text-gray-600">Facture HT</p>
              <p className="text-lg font-bold text-blue-600">
                {formatCurrency(overview.total_invoice_amt_ht)}
              </p>
            </div>
            <div className="bg-white p-3 rounded border border-blue-200">
              <p className="text-xs text-gray-600">Facture TTC</p>
              <p className="text-lg font-bold text-blue-600">
                {formatCurrency(overview.total_invoice_amt)}
              </p>
            </div>
            <div className="bg-white p-3 rounded border border-blue-200">
              <p className="text-xs text-gray-600">Avoir</p>
              <p className="text-lg font-bold text-blue-600">
                {formatCurrency(overview.total_avoir_amt)}
              </p>
            </div>
            <div className="bg-white p-3 rounded border border-blue-200">
              <p className="text-xs text-gray-600">Créance HT</p>
              <p className="text-lg font-bold text-blue-600">
                {formatCurrency(overview.total_creance_ht)}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default CreancePeriodiqueDotPage;
