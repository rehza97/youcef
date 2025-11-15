import React, { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { MultiSelect } from "@/components/ui/multi-select";
import {
  EnhancedMultiSeriesBarChart,
  CombinedBarChart,
} from "@/components/ui/charts";
import {
  getRevenueOverview,
  getRevenueByAccount,
  getRevenueByOrg,
  getRevenueFilters,
  exportRevenueData,
} from "../../services/api";
import { Download, RefreshCw } from "lucide-react";

const numberFr = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 });

const OverviewCard = ({ title, value, subtitle }) => (
  <Card>
    <CardHeader>
      <CardTitle className="text-sm font-medium">{title}</CardTitle>
    </CardHeader>
    <CardContent>
      <div className="text-2xl font-bold">{value}</div>
      {subtitle && (
        <p className="text-xs text-muted-foreground mt-1">{subtitle}</p>
      )}
    </CardContent>
  </Card>
);

const RevenuePage = () => {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState({
    by_month: {},
    by_month_objective: {},
    by_org_name: {},
    total_revenue: 0,
    total_revenue_ttc: 0,
    total_records: 0,
  });
  const [byAccount, setByAccount] = useState([]);
  const [byOrg, setByOrg] = useState([]);
  const [filters, setFilters] = useState({
    start_date: "",
    end_date: "",
    org_name: []
  });
  const [availableDots, setAvailableDots] = useState([]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [ovRes, accRes, orgRes] = await Promise.all([
        getRevenueOverview(filters),
        getRevenueByAccount(filters),
        getRevenueByOrg(filters),
      ]);
      setOverview(ovRes.data);
      setByAccount(accRes.data || []);
      setByOrg(orgRes.data || []);
    } finally {
      setLoading(false);
    }
  };

  const fetchFilters = async () => {
    try {
      const res = await getRevenueFilters();
      const dots = res.data.dots || [];

      // Extract unique DOT names from the data
      // The API returns park objects with a 'dot' field containing the DOT relationship
      const uniqueDots = new Set();
      dots.forEach((item) => {
        let dotName = null;

        // Handle different possible structures
        if (typeof item === 'string') {
          dotName = item;
        } else if (item && item.dot && typeof item.dot === 'object' && item.dot.name) {
          // If dot is an object with a name property
          dotName = item.dot.name;
        } else if (item && item.name) {
          // If the item itself has a name property
          dotName = item.name;
        } else if (item && item.org_name) {
          // If it's using org_name instead
          dotName = item.org_name;
        }

        if (dotName && typeof dotName === 'string') {
          uniqueDots.add(dotName);
        }
      });

      // Convert to array and create option objects
      const dotOptions = Array.from(uniqueDots).map((dotName) => ({
        id: dotName,
        name: dotName,
      }));

      setAvailableDots(dotOptions);
    } catch (err) {
      console.error("Error fetching available DOTs:", err);
    }
  };

  useEffect(() => {
    fetchFilters();
    fetchData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const monthCombinedSeries = useMemo(() => {
    const caEntries = Object.entries(overview.by_month || {});
    const objEntries = Object.entries(overview.by_month_objective || {});
    const months = [
      ...new Set([...caEntries.map(([k]) => k), ...objEntries.map(([k]) => k)]),
    ];
    months.sort((a, b) => (a > b ? 1 : -1));
    return months.map((k) => ({
      monthKey: k,
      label: new Date(k).toLocaleString("fr-FR", { month: "short" }),
      ca: Number((overview.by_month || {})[k] || 0),
      obj: Number((overview.by_month_objective || {})[k] || 0),
    }));
  }, [overview.by_month, overview.by_month_objective]);

  const accountSeries = useMemo(() => {
    return (byAccount || []).map((r) => ({
      label: r.cpt_comptable || "",
      value: Number(r.total_revenue || 0),
    }));
  }, [byAccount]);

  const orgSeries = useMemo(() => {
    return (byOrg || []).map((r) => ({
      label: r.org_name || "",
      value: Number(r.achievement_rate || 0),
    }));
  }, [byOrg]);

  const exportData = async (format = "csv") => {
    try {
      const filterParams = { ...filters, format };
      // Convert array to comma-separated string for API
      if (Array.isArray(filterParams.org_name) && filterParams.org_name.length > 0) {
        filterParams.org_name = filterParams.org_name.join(",");
      }

      const res = await exportRevenueData(filterParams);
      const mimeType = format === "xlsx"
        ? "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        : "text/csv";
      const blob = new Blob([res.data], { type: mimeType });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `revenue_export_${new Date().toISOString().slice(0, 10)}.${format === 'xlsx' ? 'xlsx' : 'csv'}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export error:", err);
    }
  };

  return (
    <div className="space-y-6 p-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-3xl font-bold">
          Chiffre d'Affaires - Visualisation
        </h1>
        <div className="flex gap-2">
          <Button variant="outline" onClick={fetchData} disabled={loading}>
            <RefreshCw
              className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`}
            />
            Actualiser
          </Button>
          <Button
            onClick={() => exportData("csv")}
            className="bg-green-600 hover:bg-green-700"
          >
            <Download className="h-4 w-4 mr-2" />
            CSV
          </Button>
          <Button
            onClick={() => exportData("xlsx")}
            className="bg-blue-600 hover:bg-blue-700"
          >
            <Download className="h-4 w-4 mr-2" />
            Excel
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6 grid grid-cols-1 sm:grid-cols-4 gap-4">
          <div>
            <Label>DOT (Organisation)</Label>
            <MultiSelect
              options={availableDots.map((dot) => ({
                label: dot.name,
                value: dot.id,
              }))}
              selected={filters.org_name}
              onChange={(values) =>
                setFilters((f) => ({ ...f, org_name: values }))
              }
              placeholder="Tous les DOTs"
            />
          </div>
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
          <div className="flex items-end">
            <Button onClick={fetchData} className="w-full">
              Appliquer
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <OverviewCard
          title="Chiffre d'affaires (CA)"
          value={`${numberFr.format(overview.total_revenue || 0)} DZD`}
        />
        <OverviewCard
          title="Objectif C.A"
          value={`${numberFr.format(overview.total_revenue_ttc || 0)} DZD`}
        />
        <OverviewCard
          title="Taux de réalisation C.A"
          value={`${numberFr.format(
            byOrg?.reduce((s, r) => s + (r.achievement_rate || 0), 0) /
              Math.max(byOrg?.length || 1, 1) || 0
          )} %`}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Combined histogram: C.A vs Objectif par mois */}
        <CombinedBarChart
          data={monthCombinedSeries.map((d) => ({
            label: d.label,
            seriesA: d.ca,
            seriesB: d.obj,
          }))}
          seriesALabel="Chiffre d'affaires"
          seriesBLabel="Objectif C.A"
          height={420}
        />

        {/* Histogram by account description (using cpt_comptable for now). */}
        <EnhancedMultiSeriesBarChart
          data={accountSeries}
          title="Distribution par Cpt Comptable"
          height={420}
        />
      </div>

      {/* DOT vs achievement rate */}
      <Card>
        <CardHeader>
          <CardTitle>TAUX DE RÉALISATION C.A par DOT</CardTitle>
        </CardHeader>
        <CardContent>
          <EnhancedMultiSeriesBarChart data={orgSeries} height={480} />
        </CardContent>
      </Card>
    </div>
  );
};

export default RevenuePage;
