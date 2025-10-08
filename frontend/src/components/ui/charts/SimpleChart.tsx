import React, { useState, useEffect, useRef, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Download, Maximize2, Minimize2 } from "lucide-react";
import { Button } from "@/components/ui/button";

// Enhanced data interfaces
interface ChartDataItem {
  label: string;
  value: number;
  color?: string;
  category?: string;
}

interface MultiSeriesDataItem {
  label: string;
  series: { [key: string]: number };
  color?: string;
}

interface TooltipData {
  label: string;
  value: number;
  percentage?: number;
  x: number;
  y: number;
  color: string;
}

// Enhanced chart props
interface BaseChartProps {
  data: ChartDataItem[] | MultiSeriesDataItem[];
  width?: number;
  height?: number;
  className?: string;
  responsive?: boolean;
  animated?: boolean;
  showTooltip?: boolean;
  showLegend?: boolean;
  showGrid?: boolean;
  showValues?: boolean;
  exportable?: boolean;
  theme?: "light" | "dark";
  colors?: string[];
  title?: string;
  subtitle?: string;
}

interface BarChartProps extends BaseChartProps {
  variant?: "vertical" | "horizontal" | "stacked";
  barWidth?: number;
  barSpacing?: number;
  borderRadius?: number;
}

interface PieChartProps extends BaseChartProps {
  variant?: "pie" | "donut";
  innerRadius?: number;
  showPercentages?: boolean;
  labelPosition?: "inside" | "outside" | "legend";
}

interface LineChartProps extends BaseChartProps {
  variant?: "line" | "area" | "smooth";
  showDots?: boolean;
  showArea?: boolean;
  strokeWidth?: number;
}

// Color schemes
const COLOR_SCHEMES = {
  at: {
    primary: "#0066CC", // AT Blue
    secondary: "#00CC66", // AT Green
    accent: "#FF6B6B",
    warning: "#FFA726",
    info: "#42A5F5",
    success: "#66BB6A",
    muted: "#6B7280",
    background: "#F9FAFB",
  },
  modern: {
    primary: "#3B82F6",
    secondary: "#10B981",
    accent: "#F59E0B",
    warning: "#EF4444",
    info: "#8B5CF6",
    success: "#22C55E",
    muted: "#6B7280",
    background: "#F8FAFC",
  },
  dark: {
    primary: "#60A5FA",
    secondary: "#34D399",
    accent: "#FBBF24",
    warning: "#F87171",
    info: "#A78BFA",
    success: "#4ADE80",
    muted: "#9CA3AF",
    background: "#1F2937",
  },
};

// Responsive breakpoints
const BREAKPOINTS = {
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  "2xl": 1536,
};

// Utility functions
const getResponsiveSize = (
  containerWidth: number,
  baseSize: { width: number; height: number }
) => {
  if (containerWidth < BREAKPOINTS.sm) {
    return {
      width: Math.min(baseSize.width * 0.6, 300),
      height: Math.min(baseSize.height * 0.6, 200),
    };
  } else if (containerWidth < BREAKPOINTS.md) {
    return {
      width: Math.min(baseSize.width * 0.8, 500),
      height: Math.min(baseSize.height * 0.8, 350),
    };
  } else if (containerWidth < BREAKPOINTS.lg) {
    return {
      width: Math.min(baseSize.width * 0.9, 700),
      height: Math.min(baseSize.height * 0.9, 450),
    };
  }
  return baseSize;
};

const formatNumber = (num: number): string => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + "M";
  if (num >= 1000) return (num / 1000).toFixed(1) + "K";
  return num.toString();
};

const exportChart = (
  svgElement: SVGSVGElement,
  format: "svg" | "png" | "pdf",
  filename: string
) => {
  const svgData = new XMLSerializer().serializeToString(svgElement);
  const svgBlob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });

  if (format === "svg") {
    const url = URL.createObjectURL(svgBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${filename}.svg`;
    link.click();
    URL.revokeObjectURL(url);
  } else if (format === "png") {
    const canvas = document.createElement("canvas");
    const ctx = canvas.getContext("2d");
    const img = new Image();

    img.onload = () => {
      canvas.width = img.width;
      canvas.height = img.height;
      ctx?.drawImage(img, 0, 0);

      canvas.toBlob((blob) => {
        if (blob) {
          const url = URL.createObjectURL(blob);
          const link = document.createElement("a");
          link.href = url;
          link.download = `${filename}.png`;
          link.click();
          URL.revokeObjectURL(url);
        }
      });
    };

    img.src = URL.createObjectURL(svgBlob);
  }
};

// Enhanced Tooltip Component
const ChartTooltip: React.FC<{
  data: TooltipData | null;
  visible: boolean;
  theme: "light" | "dark";
}> = ({ data, visible, theme }) => {
  if (!visible || !data) return null;

  const colors = COLOR_SCHEMES[theme === "dark" ? "dark" : "at"];

  return (
    <div
      className="absolute z-50 rounded-lg border bg-background p-3 shadow-lg"
      style={{
        left: data.x + 10,
        top: data.y - 10,
        transform: "translateY(-100%)",
      }}
    >
      <div className="flex items-center gap-2">
        <div
          className="h-3 w-3 rounded-full"
          style={{ backgroundColor: data.color }}
        />
        <div>
          <div className="text-sm font-medium">{data.label}</div>
          <div className="text-xs text-muted-foreground">
            {data.value.toLocaleString()}
            {data.percentage && ` (${data.percentage.toFixed(1)}%)`}
          </div>
        </div>
      </div>
    </div>
  );
};

// Enhanced Bar Chart Component
export const SimpleBarChart: React.FC<BarChartProps> = ({
  data,
  width = 800,
  height = 500,
  className,
  responsive = true,
  animated = true,
  showTooltip = true,
  showGrid = true,
  showValues = true,
  exportable = false,
  theme = "light",
  colors,
  title,
  subtitle,
  barWidth,
  barSpacing = 0.1,
  borderRadius = 4,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [containerSize, setContainerSize] = useState({ width, height });

  // Responsive sizing
  useEffect(() => {
    if (!responsive || !containerRef.current) return;

    const updateSize = () => {
      const containerWidth = containerRef.current?.clientWidth || width;
      const newSize = getResponsiveSize(containerWidth, { width, height });
      setContainerSize(newSize);
    };

    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, [responsive, width, height]);

  const currentSize = responsive ? containerSize : { width, height };
  const colorScheme = COLOR_SCHEMES[theme === "dark" ? "dark" : "at"];
  const chartColors = colors || [
    colorScheme.primary,
    colorScheme.secondary,
    colorScheme.accent,
    colorScheme.warning,
    colorScheme.info,
    colorScheme.success,
  ];

  if (!data || data.length === 0) return null;

  const chartData = data as ChartDataItem[];
  const maxValue = Math.max(...chartData.map((d) => d.value));
  const padding = { top: 40, right: 40, bottom: 120, left: 80 };
  const chartWidth = currentSize.width - padding.left - padding.right;
  const chartHeight = currentSize.height - padding.top - padding.bottom;
  const availableBarWidth = chartWidth / chartData.length;
  const actualBarWidth =
    barWidth || Math.max(availableBarWidth * (1 - barSpacing), 2);
  const barSpacingWidth = availableBarWidth - actualBarWidth;

  const handleMouseEnter = useCallback(
    (item: ChartDataItem, index: number, x: number, y: number) => {
      if (!showTooltip) return;

      const percentage = (item.value / maxValue) * 100;
      setTooltip({
        label: item.label,
        value: item.value,
        percentage,
        x: x + actualBarWidth / 2,
        y: y,
        color: item.color || chartColors[index % chartColors.length],
      });
      setTooltipVisible(true);
    },
    [showTooltip, maxValue, actualBarWidth, chartColors]
  );

  const handleMouseLeave = useCallback(() => {
    setTooltipVisible(false);
  }, []);

  const handleExport = useCallback(
    (format: "svg" | "png") => {
      if (!svgRef.current) return;
      const filename =
        title || `chart_${new Date().toISOString().split("T")[0]}`;
      exportChart(svgRef.current, format, filename);
    },
    [title]
  );

  const toggleFullscreen = useCallback(() => {
    setIsFullscreen(!isFullscreen);
  }, [isFullscreen]);

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative border rounded-lg bg-background",
        isFullscreen ? "fixed inset-0 z-50" : "p-4",
        className
      )}
    >
      {/* Header */}
      {(title || subtitle || exportable) && (
        <div className="mb-4 flex items-center justify-between">
          <div>
            {title && <h3 className="text-lg font-semibold">{title}</h3>}
            {subtitle && (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>
          <div className="flex gap-2">
            {exportable && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport("svg")}
                  className="h-8 w-8 p-0"
                >
                  <Download className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport("png")}
                  className="h-8 w-8 p-0"
                >
                  <Download className="h-4 w-4" />
                </Button>
              </>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={toggleFullscreen}
              className="h-8 w-8 p-0"
            >
              {isFullscreen ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      )}

      <svg
        ref={svgRef}
        width={currentSize.width}
        height={currentSize.height}
        className="overflow-visible"
      >
        {/* Grid lines */}
        {showGrid &&
          [0.25, 0.5, 0.75, 1].map((ratio, index) => {
            const y = padding.top + (1 - ratio) * chartHeight;
            return (
              <line
                key={index}
                x1={padding.left}
                y1={y}
                x2={currentSize.width - padding.right}
                y2={y}
                stroke={colorScheme.muted}
                strokeWidth="1"
                opacity="0.3"
              />
            );
          })}

        {/* Y-axis */}
        <line
          x1={padding.left}
          y1={padding.top}
          x2={padding.left}
          y2={currentSize.height - padding.bottom}
          stroke={colorScheme.muted}
          strokeWidth="2"
        />

        {/* X-axis */}
        <line
          x1={padding.left}
          y1={currentSize.height - padding.bottom}
          x2={currentSize.width - padding.right}
          y2={currentSize.height - padding.bottom}
          stroke={colorScheme.muted}
          strokeWidth="2"
        />

        {/* Bars */}
        {chartData.map((item, index) => {
          const barHeight = (item.value / maxValue) * chartHeight;
          const x =
            padding.left + index * availableBarWidth + barSpacingWidth / 2;
          const y = currentSize.height - padding.bottom - barHeight;
          const color = item.color || chartColors[index % chartColors.length];

          return (
            <g key={index}>
              <rect
                x={x}
                y={y}
                width={actualBarWidth}
                height={barHeight}
                fill={color}
                rx={borderRadius}
                className={cn(
                  "cursor-pointer transition-all duration-300",
                  animated && "hover:opacity-80 hover:scale-105"
                )}
                onMouseEnter={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  handleMouseEnter(item, index, rect.left, rect.top);
                }}
                onMouseLeave={handleMouseLeave}
                className="origin-bottom"
              />

              {/* Value labels */}
              {showValues && barHeight > 30 && (
                <text
                  x={x + actualBarWidth / 2}
                  y={y - 8}
                  textAnchor="middle"
                  className="text-xs font-semibold fill-foreground"
                >
                  {formatNumber(item.value)}
                </text>
              )}

              {/* X-axis labels */}
              <text
                x={x + actualBarWidth / 2}
                y={currentSize.height - padding.bottom + 20}
                textAnchor="start"
                className="text-xs fill-muted-foreground"
                transform={`rotate(-45, ${x + actualBarWidth / 2}, ${
                  currentSize.height - padding.bottom + 20
                })`}
              >
                {item.label.length > 20
                  ? `${item.label.substring(0, 20)}...`
                  : item.label}
              </text>
            </g>
          );
        })}

        {/* Y-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, index) => {
          const y = padding.top + (1 - ratio) * chartHeight;
          const value = Math.round(maxValue * ratio);
          return (
            <text
              key={index}
              x={padding.left - 10}
              y={y + 4}
              textAnchor="end"
              className="text-xs fill-muted-foreground"
            >
              {formatNumber(value)}
            </text>
          );
        })}
      </svg>

      {/* Tooltip */}
      <ChartTooltip data={tooltip} visible={tooltipVisible} theme={theme} />
    </div>
  );
};

// Enhanced Pie Chart Component
export const SimplePieChart: React.FC<PieChartProps> = ({
  data,
  width = 500,
  height = 500,
  className,
  responsive = true,
  animated = true,
  showTooltip = true,
  showLegend = true,
  exportable = false,
  theme = "light",
  colors,
  title,
  subtitle,
  variant = "pie",
  innerRadius,
  showPercentages = true,
  labelPosition = "legend",
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [containerSize, setContainerSize] = useState({ width, height });
  const [selectedSlice, setSelectedSlice] = useState<number | null>(null);

  // Responsive sizing
  useEffect(() => {
    if (!responsive || !containerRef.current) return;

    const updateSize = () => {
      const containerWidth = containerRef.current?.clientWidth || width;
      const newSize = getResponsiveSize(containerWidth, { width, height });
      setContainerSize(newSize);
    };

    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, [responsive, width, height]);

  const currentSize = responsive ? containerSize : { width, height };
  const colorScheme = COLOR_SCHEMES[theme === "dark" ? "dark" : "at"];
  const chartColors = colors || [
    colorScheme.primary,
    colorScheme.secondary,
    colorScheme.accent,
    colorScheme.warning,
    colorScheme.info,
    colorScheme.success,
  ];

  if (!data || data.length === 0) return null;

  const chartData = data as ChartDataItem[];
  const total = chartData.reduce((sum, item) => sum + item.value, 0);
  const centerX = currentSize.width / 2;
  const centerY = currentSize.height / 2 - (showLegend ? 30 : 0);
  const outerRadius = Math.min(currentSize.width, currentSize.height) / 3;
  const actualInnerRadius =
    variant === "donut" ? innerRadius || outerRadius * 0.4 : 0;

  const handleMouseEnter = useCallback(
    (item: ChartDataItem, index: number, x: number, y: number) => {
      if (!showTooltip) return;

      const percentage = (item.value / total) * 100;
      setTooltip({
        label: item.label,
        value: item.value,
        percentage,
        x: x,
        y: y,
        color: item.color || chartColors[index % chartColors.length],
      });
      setTooltipVisible(true);
    },
    [showTooltip, total, chartColors]
  );

  const handleMouseLeave = useCallback(() => {
    setTooltipVisible(false);
  }, []);

  const handleSliceClick = useCallback(
    (index: number) => {
      setSelectedSlice(selectedSlice === index ? null : index);
    },
    [selectedSlice]
  );

  const handleExport = useCallback(
    (format: "svg" | "png") => {
      if (!svgRef.current) return;
      const filename =
        title || `pie_chart_${new Date().toISOString().split("T")[0]}`;
      exportChart(svgRef.current, format, filename);
    },
    [title]
  );

  const toggleFullscreen = useCallback(() => {
    setIsFullscreen(!isFullscreen);
  }, [isFullscreen]);

  let currentAngle = -Math.PI / 2; // Start at top

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative border rounded-lg bg-background",
        isFullscreen ? "fixed inset-0 z-50" : "p-4",
        className
      )}
    >
      {/* Header */}
      {(title || subtitle || exportable) && (
        <div className="mb-4 flex items-center justify-between">
          <div>
            {title && <h3 className="text-lg font-semibold">{title}</h3>}
            {subtitle && (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>
          <div className="flex gap-2">
            {exportable && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport("svg")}
                  className="h-8 w-8 p-0"
                >
                  <Download className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport("png")}
                  className="h-8 w-8 p-0"
                >
                  <Download className="h-4 w-4" />
                </Button>
              </>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={toggleFullscreen}
              className="h-8 w-8 p-0"
            >
              {isFullscreen ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      )}

      <svg
        ref={svgRef}
        width={currentSize.width}
        height={currentSize.height}
        className="overflow-visible"
      >
        {/* Pie slices */}
        {chartData.map((item, index) => {
          const angle = (item.value / total) * 2 * Math.PI;
          const x1 = centerX + outerRadius * Math.cos(currentAngle);
          const y1 = centerY + outerRadius * Math.sin(currentAngle);
          const x2 = centerX + outerRadius * Math.cos(currentAngle + angle);
          const y2 = centerY + outerRadius * Math.sin(currentAngle + angle);

          const largeArcFlag = angle > Math.PI ? 1 : 0;
          const sweepFlag = 1;

          const pathData = [
            `M ${centerX} ${centerY}`,
            `L ${x1} ${y1}`,
            `A ${outerRadius} ${outerRadius} 0 ${largeArcFlag} ${sweepFlag} ${x2} ${y2}`,
            actualInnerRadius > 0
              ? `L ${
                  centerX + actualInnerRadius * Math.cos(currentAngle + angle)
                } ${
                  centerY + actualInnerRadius * Math.sin(currentAngle + angle)
                }`
              : "",
            actualInnerRadius > 0
              ? `A ${actualInnerRadius} ${actualInnerRadius} 0 ${largeArcFlag} 0 ${
                  centerX + actualInnerRadius * Math.cos(currentAngle)
                } ${centerY + actualInnerRadius * Math.sin(currentAngle)}`
              : "",
            "Z",
          ].join(" ");

          const color = item.color || chartColors[index % chartColors.length];
          const percentage = (item.value / total) * 100;
          const isSelected = selectedSlice === index;
          const isHovered = tooltipVisible && tooltip?.label === item.label;

          // Label position
          const labelAngle = currentAngle + angle / 2;
          const labelRadius = outerRadius * 0.7;
          const labelX = centerX + labelRadius * Math.cos(labelAngle);
          const labelY = centerY + labelRadius * Math.sin(labelAngle);

          currentAngle += angle;

          return (
            <g key={index}>
              <path
                d={pathData}
                fill={color}
                stroke="white"
                strokeWidth={isSelected || isHovered ? 4 : 2}
                className={cn(
                  "cursor-pointer transition-all duration-300",
                  animated && "hover:opacity-90",
                  isSelected && "drop-shadow-lg"
                )}
                onMouseEnter={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  handleMouseEnter(
                    item,
                    index,
                    rect.left + rect.width / 2,
                    rect.top + rect.height / 2
                  );
                }}
                onMouseLeave={handleMouseLeave}
                onClick={() => handleSliceClick(index)}
                className={cn(
                  "origin-center transition-transform duration-300",
                  isSelected && "scale-105"
                )}
              />

              {/* Percentage labels inside slices */}
              {showPercentages &&
                labelPosition === "inside" &&
                percentage > 5 && (
                  <text
                    x={labelX}
                    y={labelY}
                    textAnchor="middle"
                    className="text-sm font-bold fill-white"
                  >
                    {percentage.toFixed(1)}%
                  </text>
                )}
            </g>
          );
        })}

        {/* Center text for donut charts */}
        {variant === "donut" && (
          <text
            x={centerX}
            y={centerY}
            textAnchor="middle"
            className="text-2xl font-bold fill-foreground"
          >
            {total.toLocaleString()}
          </text>
        )}

        {/* Legend */}
        {showLegend && (
          <g>
            {chartData.map((item, index) => {
              const legendY = currentSize.height - 100 + (index % 4) * 25;
              const legendX = 20 + Math.floor(index / 4) * 150;
              const color =
                item.color || chartColors[index % chartColors.length];
              const percentage = (item.value / total) * 100;

              return (
                <g key={`legend-${index}`}>
                  <rect
                    x={legendX}
                    y={legendY - 8}
                    width={14}
                    height={14}
                    fill={color}
                    rx="2"
                    className="cursor-pointer"
                    onClick={() => handleSliceClick(index)}
                  />
                  <text
                    x={legendX + 20}
                    y={legendY + 2}
                    className="text-sm fill-foreground cursor-pointer"
                    onClick={() => handleSliceClick(index)}
                  >
                    {item.label.length > 15
                      ? `${item.label.substring(0, 15)}...`
                      : item.label}{" "}
                    ({percentage.toFixed(1)}%)
                  </text>
                </g>
              );
            })}
          </g>
        )}
      </svg>

      {/* Tooltip */}
      <ChartTooltip data={tooltip} visible={tooltipVisible} theme={theme} />
    </div>
  );
};

// Enhanced Line Chart Component
export const SimpleLineChart: React.FC<LineChartProps> = ({
  data,
  width = 400,
  height = 300,
  className,
  responsive = true,
  animated = true,
  showTooltip = true,
  showGrid = true,
  exportable = false,
  theme = "light",
  colors,
  title,
  subtitle,
  showDots = true,
  showArea = false,
  strokeWidth = 2,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [tooltipVisible, setTooltipVisible] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [containerSize, setContainerSize] = useState({ width, height });

  // Responsive sizing
  useEffect(() => {
    if (!responsive || !containerRef.current) return;

    const updateSize = () => {
      const containerWidth = containerRef.current?.clientWidth || width;
      const newSize = getResponsiveSize(containerWidth, { width, height });
      setContainerSize(newSize);
    };

    updateSize();
    window.addEventListener("resize", updateSize);
    return () => window.removeEventListener("resize", updateSize);
  }, [responsive, width, height]);

  const currentSize = responsive ? containerSize : { width, height };
  const colorScheme = COLOR_SCHEMES[theme === "dark" ? "dark" : "at"];
  const chartColors = colors || [
    colorScheme.primary,
    colorScheme.secondary,
    colorScheme.accent,
    colorScheme.warning,
    colorScheme.info,
    colorScheme.success,
  ];

  if (!data || data.length === 0) return null;

  const chartData = data as ChartDataItem[];
  const maxValue = Math.max(...chartData.map((d) => d.value));
  const minValue = Math.min(...chartData.map((d) => d.value));
  const range = maxValue - minValue || 1;

  const padding = { top: 40, right: 40, bottom: 80, left: 80 };
  const chartWidth = currentSize.width - padding.left - padding.right;
  const chartHeight = currentSize.height - padding.top - padding.bottom;
  const stepX = chartWidth / (chartData.length - 1);

  const points = chartData.map((item, index) => {
    const x = padding.left + index * stepX;
    const y = padding.top + ((maxValue - item.value) / range) * chartHeight;
    return { x, y, ...item };
  });

  const pathData = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
    .join(" ");

  const areaPathData = showArea
    ? `${pathData} L ${points[points.length - 1].x} ${
        currentSize.height - padding.bottom
      } L ${points[0].x} ${currentSize.height - padding.bottom} Z`
    : "";

  const handleMouseEnter = useCallback(
    (item: ChartDataItem, x: number, y: number) => {
      if (!showTooltip) return;

      setTooltip({
        label: item.label,
        value: item.value,
        x: x,
        y: y,
        color: chartColors[0],
      });
      setTooltipVisible(true);
    },
    [showTooltip, chartColors]
  );

  const handleMouseLeave = useCallback(() => {
    setTooltipVisible(false);
  }, []);

  const handleExport = useCallback(
    (format: "svg" | "png") => {
      if (!svgRef.current) return;
      const filename =
        title || `line_chart_${new Date().toISOString().split("T")[0]}`;
      exportChart(svgRef.current, format, filename);
    },
    [title]
  );

  const toggleFullscreen = useCallback(() => {
    setIsFullscreen(!isFullscreen);
  }, [isFullscreen]);

  return (
    <div
      ref={containerRef}
      className={cn(
        "relative border rounded-lg bg-background",
        isFullscreen ? "fixed inset-0 z-50" : "p-4",
        className
      )}
    >
      {/* Header */}
      {(title || subtitle || exportable) && (
        <div className="mb-4 flex items-center justify-between">
          <div>
            {title && <h3 className="text-lg font-semibold">{title}</h3>}
            {subtitle && (
              <p className="text-sm text-muted-foreground">{subtitle}</p>
            )}
          </div>
          <div className="flex gap-2">
            {exportable && (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport("svg")}
                  className="h-8 w-8 p-0"
                >
                  <Download className="h-4 w-4" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport("png")}
                  className="h-8 w-8 p-0"
                >
                  <Download className="h-4 w-4" />
                </Button>
              </>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={toggleFullscreen}
              className="h-8 w-8 p-0"
            >
              {isFullscreen ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      )}

      <svg
        ref={svgRef}
        width={currentSize.width}
        height={currentSize.height}
        className="overflow-visible"
      >
        {/* Grid lines */}
        {showGrid &&
          [0.25, 0.5, 0.75, 1].map((ratio, index) => {
            const y = padding.top + ratio * chartHeight;
            return (
              <line
                key={index}
                x1={padding.left}
                y1={y}
                x2={currentSize.width - padding.right}
                y2={y}
                stroke={colorScheme.muted}
                strokeWidth="1"
                opacity="0.3"
              />
            );
          })}

        {/* Y-axis */}
        <line
          x1={padding.left}
          y1={padding.top}
          x2={padding.left}
          y2={currentSize.height - padding.bottom}
          stroke={colorScheme.muted}
          strokeWidth="2"
        />

        {/* X-axis */}
        <line
          x1={padding.left}
          y1={currentSize.height - padding.bottom}
          x2={currentSize.width - padding.right}
          y2={currentSize.height - padding.bottom}
          stroke={colorScheme.muted}
          strokeWidth="2"
        />

        {/* Area fill */}
        {showArea && (
          <path
            d={areaPathData}
            fill={chartColors[0]}
            opacity="0.1"
            className="transition-opacity duration-300"
          />
        )}

        {/* Line */}
        <path
          d={pathData}
          fill="none"
          stroke={chartColors[0]}
          strokeWidth={strokeWidth}
          className={cn(
            "drop-shadow-sm transition-all duration-300",
            animated && "hover:stroke-width-3"
          )}
        />

        {/* Points */}
        {showDots &&
          points.map((point, index) => (
            <circle
              key={index}
              cx={point.x}
              cy={point.y}
              r="4"
              fill={chartColors[0]}
              className={cn(
                "cursor-pointer transition-all duration-300",
                animated && "hover:r-6 hover:fill-opacity-80"
              )}
              onMouseEnter={() => handleMouseEnter(point, point.x, point.y)}
              onMouseLeave={handleMouseLeave}
            />
          ))}

        {/* X-axis labels */}
        {points.map((point, index) => (
          <text
            key={index}
            x={point.x}
            y={currentSize.height - padding.bottom + 20}
            textAnchor="middle"
            className="text-xs fill-muted-foreground"
          >
            {point.label.length > 10
              ? `${point.label.substring(0, 10)}...`
              : point.label}
          </text>
        ))}

        {/* Y-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, index) => {
          const y = padding.top + ratio * chartHeight;
          const value = Math.round(minValue + range * (1 - ratio));
          return (
            <text
              key={index}
              x={padding.left - 10}
              y={y + 4}
              textAnchor="end"
              className="text-xs fill-muted-foreground"
            >
              {formatNumber(value)}
            </text>
          );
        })}
      </svg>

      {/* Tooltip */}
      <ChartTooltip data={tooltip} visible={tooltipVisible} theme={theme} />
    </div>
  );
};

// New Chart Variants

// Horizontal Bar Chart
export const SimpleHorizontalBarChart: React.FC<BarChartProps> = (props) => {
  return <SimpleBarChart {...props} variant="horizontal" />;
};

// Stacked Bar Chart
export const SimpleStackedBarChart: React.FC<BarChartProps> = (props) => {
  return <SimpleBarChart {...props} variant="stacked" />;
};

// Donut Chart
export const SimpleDonutChart: React.FC<PieChartProps> = (props) => {
  return <SimplePieChart {...props} variant="donut" />;
};

// Area Chart
export const SimpleAreaChart: React.FC<LineChartProps> = (props) => {
  return <SimpleLineChart {...props} variant="area" showArea={true} />;
};

// Multi-series Bar Chart
export const SimpleMultiSeriesBarChart: React.FC<
  {
    data: MultiSeriesDataItem[];
    series: string[];
  } & Omit<BarChartProps, "data">
> = ({ data, series, ...props }) => {
  // Convert multi-series data to individual bars
  const processedData: ChartDataItem[] = [];

  data.forEach((item) => {
    series.forEach((seriesName, seriesIndex) => {
      processedData.push({
        label: `${item.label} - ${seriesName}`,
        value: item.series[seriesName] || 0,
        category: seriesName,
        color: props.colors?.[seriesIndex],
      });
    });
  });

  return <SimpleBarChart {...props} data={processedData} />;
};
