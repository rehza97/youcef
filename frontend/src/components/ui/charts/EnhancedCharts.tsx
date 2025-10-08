"use client";

import React, { useState, useEffect, useMemo, useCallback } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  XAxis,
  Pie,
  PieChart,
  Cell,
} from "recharts";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart";

// Algérie Telecom Color Scheme
const AT_COLORS = {
  primary: "#0066CC", // AT Blue
  secondary: "#00CC66", // AT Green
  accent: "#FF6B6B",
  warning: "#FFA726",
  info: "#42A5F5",
  success: "#66BB6A",
  muted: "#6B7280",
} as const;

const COLOR_PALETTE = [
  AT_COLORS.primary,
  AT_COLORS.secondary,
  AT_COLORS.accent,
  AT_COLORS.warning,
  AT_COLORS.info,
  AT_COLORS.success,
] as const;

// Shared number formatters to avoid recreation
const numberFormatter = new Intl.NumberFormat("fr-FR");
const compactNumberFormatter = new Intl.NumberFormat("fr-FR", {
  notation: "compact",
  maximumFractionDigits: 1,
});

interface ChartDataItem {
  label: string;
  value: number;
  color?: string;
}

interface ChartDataTransformed {
  name: string;
  value: number;
  color: string;
}

interface EnhancedBarChartProps {
  data: ChartDataItem[];
  title?: string;
  subtitle?: string;
  width?: number | string;
  height?: number;
  className?: string;
}

interface EnhancedPieChartProps {
  data: ChartDataItem[];
  title?: string;
  subtitle?: string;
  width?: number | string;
  height?: number;
  className?: string;
  showLabels?: boolean;
  labelPosition?: "inside" | "outside" | "legend";
  showPercentages?: boolean;
  showValues?: boolean;
  minLabelPercentage?: number;
}

// Enhanced Bar Chart with dynamic data
export const EnhancedBarChart: React.FC<EnhancedBarChartProps> = ({
  data,
  title,
  subtitle,
  width = "100%",
  height = 400,
  className,
}) => {
  // Transform data for Recharts - memoized to prevent unnecessary recalculations
  const chartData: ChartDataTransformed[] = useMemo(
    () =>
      data.map((item, index) => ({
        name: item.label,
        value: item.value,
        color: item.color || COLOR_PALETTE[index % COLOR_PALETTE.length],
      })),
    [data]
  );

  const chartConfig = useMemo(
    () =>
      ({
        value: {
          label: "Valeur",
          color: AT_COLORS.primary,
        },
      } satisfies ChartConfig),
    []
  );

  const formatValue = useCallback(
    (value: any) => [numberFormatter.format(Number(value)), "Valeur"],
    []
  );

  if (!data || data.length === 0) return null;

  return (
    <Card className={className}>
      {(title || subtitle) && (
        <CardHeader>
          {title && <CardTitle>{title}</CardTitle>}
          {subtitle && <CardDescription>{subtitle}</CardDescription>}
        </CardHeader>
      )}
      <CardContent>
        <div className="w-full">
          {/* eslint-disable-next-line react/forbid-dom-props */}
          <ChartContainer
            config={chartConfig}
            className={`h-[${height}px]`}
            style={{ width: typeof width === "number" ? `${width}px` : width }}
          >
            <BarChart
              accessibilityLayer
              data={chartData}
              width={typeof width === "number" ? width : undefined}
              margin={{
                top: 20,
                right: 30,
                left: 20,
                bottom: 80,
              }}
            >
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis
                dataKey="name"
                tickLine={false}
                tickMargin={10}
                axisLine={false}
                angle={-45}
                textAnchor="end"
                height={80}
                interval={0}
                aria-label="Catégories"
                tickFormatter={(value) =>
                  value.length > 15 ? `${value.substring(0, 15)}...` : value
                }
              />
              <ChartTooltip
                cursor={false}
                content={
                  <ChartTooltipContent hideLabel formatter={formatValue} />
                }
              />
              <Bar
                dataKey="value"
                fill={AT_COLORS.primary}
                radius={[4, 4, 0, 0]}
                name="Valeur"
              />
            </BarChart>
          </ChartContainer>
        </div>
      </CardContent>
    </Card>
  );
};

// Enhanced Pie Chart with dynamic data
export const EnhancedPieChart: React.FC<EnhancedPieChartProps> = ({
  data,
  title,
  subtitle,
  height = 400,
  className,
  showLabels = true,
  labelPosition = "outside",
  showPercentages = true,
  showValues = false,
  minLabelPercentage = 3,
}) => {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;

    const updateSize = () => {
      const width = window.innerWidth;
      setIsMobile(width < 768);
    };

    const debouncedUpdateSize = () => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(updateSize, 150);
    };

    updateSize();
    window.addEventListener("resize", debouncedUpdateSize);
    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener("resize", debouncedUpdateSize);
    };
  }, []);

  // Transform data for Recharts - memoized
  const chartData: ChartDataTransformed[] = useMemo(
    () =>
      data.map((item, index) => ({
        name: item.label,
        value: item.value,
        color: item.color || COLOR_PALETTE[index % COLOR_PALETTE.length],
      })),
    [data]
  );

  const total = useMemo(
    () => chartData.reduce((sum, item) => sum + item.value, 0),
    [chartData]
  );

  // Responsive calculations - memoized
  const { responsiveHeight, responsiveRadius, responsiveMargin } = useMemo(
    () => ({
      responsiveHeight: isMobile ? Math.min(height, 300) : height,
      responsiveRadius: Math.min(height / 3, isMobile ? 100 : 150),
      responsiveMargin: isMobile ? 60 : labelPosition === "outside" ? 120 : 20,
    }),
    [isMobile, height, labelPosition]
  );

  const chartConfig = useMemo(
    () =>
      ({
        value: {
          label: "Valeur",
        },
      } satisfies ChartConfig),
    []
  );

  // Custom label function - memoized with useCallback
  const renderLabel = useCallback(
    (entry: any) => {
      if (!showLabels) return "";

      const percentage = (entry.value / total) * 100;
      if (percentage < minLabelPercentage) return "";

      let labelText = "";

      if (labelPosition === "inside") {
        if (showPercentages) {
          labelText = `${percentage.toFixed(1)}%`;
        }
      } else if (labelPosition === "outside") {
        const name =
          entry.name.length > 6
            ? `${entry.name.substring(0, 6)}...`
            : entry.name;
        if (showPercentages && showValues) {
          labelText = `${name}\n${percentage.toFixed(
            1
          )}%\n${compactNumberFormatter.format(entry.value)}`;
        } else if (showPercentages) {
          labelText = `${name}\n${percentage.toFixed(1)}%`;
        } else if (showValues) {
          labelText = `${name}\n${compactNumberFormatter.format(entry.value)}`;
        } else {
          labelText = name;
        }
      }

      return labelText;
    },
    [
      showLabels,
      total,
      minLabelPercentage,
      labelPosition,
      showPercentages,
      showValues,
    ]
  );

  const formatTooltip = useCallback(
    (value: any, _name: any, props: any) => [
      numberFormatter.format(Number(value)),
      props.payload.name,
    ],
    []
  );

  if (!data || data.length === 0) return null;

  return (
    <Card className={className}>
      {(title || subtitle) && (
        <CardHeader>
          {title && <CardTitle>{title}</CardTitle>}
          {subtitle && <CardDescription>{subtitle}</CardDescription>}
        </CardHeader>
      )}
      <CardContent className="p-4">
        <div className="relative overflow-hidden w-full">
          <ChartContainer
            config={chartConfig}
            className={`h-[${responsiveHeight}px] w-full`}
          >
            <PieChart
              margin={{
                top: 20,
                right: responsiveMargin,
                bottom: 20,
                left: responsiveMargin,
              }}
            >
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={responsiveRadius}
                innerRadius={
                  labelPosition === "legend" ? responsiveRadius / 2 : 0
                }
                fill="#8884d8"
                label={
                  showLabels && labelPosition !== "legend" && !isMobile
                    ? renderLabel
                    : false
                }
                labelLine={labelPosition === "outside" && !isMobile}
              >
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <ChartTooltip
                cursor={false}
                content={
                  <ChartTooltipContent hideLabel formatter={formatTooltip} />
                }
              />
            </PieChart>
          </ChartContainer>
        </div>

        {/* Legend for legend position or mobile fallback */}
        {(labelPosition === "legend" || (isMobile && showLabels)) && (
          <div className="mt-4 flex flex-wrap justify-center gap-2 sm:gap-4">
            {chartData.map((entry, index) => {
              const percentage = (entry.value / total) * 100;
              if (percentage < minLabelPercentage) return null;

              return (
                <div
                  key={index}
                  className="flex items-center gap-1 sm:gap-2 text-xs sm:text-sm"
                >
                  {/* eslint-disable-next-line react/forbid-dom-props */}
                  <div
                    className="w-2 h-2 sm:w-3 sm:h-3 rounded-full flex-shrink-0"
                    style={{ backgroundColor: entry.color }}
                    aria-hidden="true"
                  />
                  <span className="font-medium truncate max-w-[60px] sm:max-w-none">
                    {entry.name.length > (isMobile ? 6 : 12)
                      ? `${entry.name.substring(0, isMobile ? 6 : 12)}...`
                      : entry.name}
                  </span>
                  <span className="text-muted-foreground text-xs">
                    {showPercentages && `${percentage.toFixed(1)}%`}
                    {showValues &&
                      !isMobile &&
                      ` (${compactNumberFormatter.format(entry.value)})`}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
};

// Enhanced Multi-Series Bar Chart
interface EnhancedMultiSeriesBarChartProps {
  data: ChartDataItem[];
  title?: string;
  subtitle?: string;
  width?: number | string;
  height?: number;
  className?: string;
}

export const EnhancedMultiSeriesBarChart: React.FC<
  EnhancedMultiSeriesBarChartProps
> = ({ data, title, subtitle, width = "100%", height = 400, className }) => {
  // Transform data for Recharts with alternating colors - memoized
  const chartData: ChartDataTransformed[] = useMemo(
    () =>
      data.map((item, index) => ({
        name: item.label,
        value: item.value,
        color: item.color || COLOR_PALETTE[index % COLOR_PALETTE.length],
      })),
    [data]
  );

  const chartConfig = useMemo(
    () =>
      ({
        value: {
          label: "Valeur",
          color: AT_COLORS.primary,
        },
      } satisfies ChartConfig),
    []
  );

  const formatValue = useCallback(
    (value: any) => [numberFormatter.format(Number(value)), "Valeur"],
    []
  );

  if (!data || data.length === 0) return null;

  return (
    <Card className={className}>
      {(title || subtitle) && (
        <CardHeader>
          {title && <CardTitle>{title}</CardTitle>}
          {subtitle && <CardDescription>{subtitle}</CardDescription>}
        </CardHeader>
      )}
      <CardContent>
        <div className="w-full">
          {/* eslint-disable-next-line react/forbid-dom-props */}
          <ChartContainer
            config={chartConfig}
            className={`h-[${height}px]`}
            style={{ width: typeof width === "number" ? `${width}px` : width }}
          >
            <BarChart
              accessibilityLayer
              data={chartData}
              width={typeof width === "number" ? width : undefined}
              margin={{
                top: 20,
                right: 0,
                left: 50,
                bottom: 80,
              }}
            >
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis
                dataKey="name"
                tickLine={false}
                tickMargin={10}
                axisLine={false}
                angle={-45}
                textAnchor="end"
                height={80}
                interval={0}
                aria-label="Catégories"
                tickFormatter={(value) =>
                  value.length > 20 ? `${value.substring(0, 20)}...` : value
                }
              />
              <ChartTooltip
                cursor={false}
                content={
                  <ChartTooltipContent hideLabel formatter={formatValue} />
                }
              />
              <Bar
                dataKey="value"
                fill={AT_COLORS.primary}
                radius={[4, 4, 0, 0]}
                name="Valeur"
              />
            </BarChart>
          </ChartContainer>
        </div>
      </CardContent>
    </Card>
  );
};
