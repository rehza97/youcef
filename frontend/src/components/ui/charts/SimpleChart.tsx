import React from "react";
import { cn } from "@/lib/utils";

interface ChartDataItem {
  label: string;
  value: number;
}

interface ChartProps {
  data: ChartDataItem[];
  width?: number;
  height?: number;
  className?: string;
}

// Simple SVG-based charts following shadcn patterns
// Uses Algérie Telecom colors (Blue: #0066CC, Green: #00CC66)

const COLORS = {
  primary: "#0066CC", // AT Blue
  secondary: "#00CC66", // AT Green
  muted: "#6B7280",
  background: "#F9FAFB",
};

export const SimpleBarChart: React.FC<ChartProps> = ({
  data,
  width = 400,
  height = 300,
  className,
}) => {
  if (!data || data.length === 0) return null;

  const maxValue = Math.max(...data.map((d) => d.value));
  const barWidth = (width - 80) / data.length;
  const chartHeight = height - 60;

  return (
    <div className={cn("p-4 border rounded-lg bg-background", className)}>
      <svg width={width} height={height} className="overflow-visible">
        {/* Y-axis */}
        <line
          x1="40"
          y1="20"
          x2="40"
          y2={height - 40}
          stroke="#E5E7EB"
          strokeWidth="1"
        />

        {/* X-axis */}
        <line
          x1="40"
          y1={height - 40}
          x2={width - 20}
          y2={height - 40}
          stroke="#E5E7EB"
          strokeWidth="1"
        />

        {/* Bars */}
        {data.map((item, index) => {
          const barHeight = (item.value / maxValue) * chartHeight;
          const x = 40 + index * barWidth + barWidth * 0.1;
          const y = height - 40 - barHeight;

          return (
            <g key={index}>
              <rect
                x={x}
                y={y}
                width={barWidth * 0.8}
                height={barHeight}
                fill={index % 2 === 0 ? COLORS.primary : COLORS.secondary}
                className="hover:opacity-80 transition-opacity"
              />
              <text
                x={x + barWidth * 0.4}
                y={height - 25}
                textAnchor="middle"
                className="text-xs fill-muted-foreground"
              >
                {item.label}
              </text>
              <text
                x={x + barWidth * 0.4}
                y={y - 5}
                textAnchor="middle"
                className="text-xs fill-foreground font-medium"
              >
                {item.value}
              </text>
            </g>
          );
        })}

        {/* Y-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, index) => {
          const y = height - 40 - ratio * chartHeight;
          const value = Math.round(maxValue * ratio);
          return (
            <text
              key={index}
              x="35"
              y={y + 4}
              textAnchor="end"
              className="text-xs fill-muted-foreground"
            >
              {value}
            </text>
          );
        })}
      </svg>
    </div>
  );
};

export const SimplePieChart: React.FC<ChartProps> = ({
  data,
  width = 300,
  height = 300,
  className,
}) => {
  if (!data || data.length === 0) return null;

  const total = data.reduce((sum, item) => sum + item.value, 0);
  const centerX = width / 2;
  const centerY = height / 2;
  const radius = Math.min(width, height) / 3;

  let currentAngle = -Math.PI / 2; // Start at top

  return (
    <div className={cn("p-4 border rounded-lg bg-background", className)}>
      <svg width={width} height={height}>
        {data.map((item, index) => {
          const angle = (item.value / total) * 2 * Math.PI;
          const x1 = centerX + radius * Math.cos(currentAngle);
          const y1 = centerY + radius * Math.sin(currentAngle);
          const x2 = centerX + radius * Math.cos(currentAngle + angle);
          const y2 = centerY + radius * Math.sin(currentAngle + angle);

          const largeArcFlag = angle > Math.PI ? 1 : 0;

          const pathData = [
            `M ${centerX} ${centerY}`,
            `L ${x1} ${y1}`,
            `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2}`,
            "Z",
          ].join(" ");

          const color = index % 2 === 0 ? COLORS.primary : COLORS.secondary;

          // Label position
          const labelAngle = currentAngle + angle / 2;
          const labelRadius = radius + 20;
          const labelX = centerX + labelRadius * Math.cos(labelAngle);
          const labelY = centerY + labelRadius * Math.sin(labelAngle);

          currentAngle += angle;

          return (
            <g key={index}>
              <path
                d={pathData}
                fill={color}
                className="hover:opacity-80 transition-opacity"
              />
              <text
                x={labelX}
                y={labelY}
                textAnchor="middle"
                className="text-xs fill-foreground font-medium"
              >
                {item.label}
              </text>
              <text
                x={labelX}
                y={labelY + 12}
                textAnchor="middle"
                className="text-xs fill-muted-foreground"
              >
                {Math.round((item.value / total) * 100)}%
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};

export const SimpleLineChart: React.FC<ChartProps> = ({
  data,
  width = 400,
  height = 300,
  className,
}) => {
  if (!data || data.length === 0) return null;

  const maxValue = Math.max(...data.map((d) => d.value));
  const minValue = Math.min(...data.map((d) => d.value));
  const range = maxValue - minValue || 1;

  const stepX = (width - 80) / (data.length - 1);
  const chartHeight = height - 60;

  const points = data.map((item, index) => {
    const x = 40 + index * stepX;
    const y = height - 40 - ((item.value - minValue) / range) * chartHeight;
    return { x, y, ...item };
  });

  const pathData = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
    .join(" ");

  return (
    <div className={cn("p-4 border rounded-lg bg-background", className)}>
      <svg width={width} height={height}>
        {/* Grid lines */}
        {[0.25, 0.5, 0.75].map((ratio, index) => {
          const y = height - 40 - ratio * chartHeight;
          return (
            <line
              key={index}
              x1="40"
              y1={y}
              x2={width - 20}
              y2={y}
              stroke="#F3F4F6"
              strokeWidth="1"
            />
          );
        })}

        {/* Axes */}
        <line
          x1="40"
          y1="20"
          x2="40"
          y2={height - 40}
          stroke="#E5E7EB"
          strokeWidth="1"
        />
        <line
          x1="40"
          y1={height - 40}
          x2={width - 20}
          y2={height - 40}
          stroke="#E5E7EB"
          strokeWidth="1"
        />

        {/* Line */}
        <path
          d={pathData}
          fill="none"
          stroke={COLORS.primary}
          strokeWidth="2"
          className="drop-shadow-sm"
        />

        {/* Points */}
        {points.map((point, index) => (
          <circle
            key={index}
            cx={point.x}
            cy={point.y}
            r="4"
            fill={COLORS.secondary}
            className="hover:r-6 transition-all cursor-pointer"
          />
        ))}

        {/* X-axis labels */}
        {points.map((point, index) => (
          <text
            key={index}
            x={point.x}
            y={height - 25}
            textAnchor="middle"
            className="text-xs fill-muted-foreground"
          >
            {point.label}
          </text>
        ))}

        {/* Y-axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, index) => {
          const y = height - 40 - ratio * chartHeight;
          const value = Math.round(minValue + range * ratio);
          return (
            <text
              key={index}
              x="35"
              y={y + 4}
              textAnchor="end"
              className="text-xs fill-muted-foreground"
            >
              {value}
            </text>
          );
        })}
      </svg>
    </div>
  );
};
