import React from "react";
import {
  // Bar Chart Components
  ChartBarInteractive,
  ChartBarDefault,
  ChartBarHorizontal,
  ChartBarMultiple,
  ChartBarStacked,
  ChartBarLabel,
  ChartBarLabelCustom,
  ChartBarNegative,
  // Line Chart Components
  ChartLineDefault,
  ChartLineLinear,
  ChartLineStep,
  ChartLineMultiple,
  ChartLineDots,
  ChartLineDotsCustom,
  ChartLineDotsColors,
  ChartLineLabel,
  ChartLineLabelCustom,
  // Pie Chart Components
  ChartPieSimple,
  ChartPieSeparatorNone,
  ChartPieLabel,
  ChartPieLabelCustom,
  ChartPieLabelList,
  ChartPieLegend,
  ChartPieDonut,
  ChartPieDonutActive,
  ChartPieDonutText,
  ChartPieStacked,
  ChartPieInteractive,
  // Radial Chart Components
  ChartRadialSimple,
  ChartRadialLabel,
  ChartRadialGrid,
  ChartRadialText,
  ChartRadialShape,
  ChartRadialStacked,
  // Tooltip Chart Components
  ChartTooltipDefault,
  ChartTooltipIndicatorLine,
  ChartTooltipIndicatorNone,
  ChartTooltipLabelCustom,
  ChartTooltipLabelFormatter,
  ChartTooltipLabelNone,
  ChartTooltipFormatter,
  ChartTooltipIcons,
  ChartTooltipAdvanced,
} from "@/components/ui/charts";

export default function ChartsDemo() {
  return (
    <div className="container mx-auto p-6 space-y-8">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold mb-2">Chart Components</h1>
        <p className="text-muted-foreground">
          A collection of interactive chart components built with shadcn/ui and
          Recharts
        </p>
      </div>

      {/* Bar Charts Section */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Bar Charts</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartBarInteractive />
          <ChartBarDefault />
          <ChartBarHorizontal />
          <ChartBarMultiple />
          <ChartBarStacked />
          <ChartBarLabel />
          <ChartBarLabelCustom />
          <ChartBarNegative />
        </div>
      </section>

      {/* Line Charts Section */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Line Charts</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartLineDefault />
          <ChartLineLinear />
          <ChartLineStep />
          <ChartLineMultiple />
          <ChartLineDots />
          <ChartLineDotsCustom />
          <ChartLineDotsColors />
          <ChartLineLabel />
          <ChartLineLabelCustom />
        </div>
      </section>

      {/* Pie Charts Section */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Pie Charts</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartPieSimple />
          <ChartPieSeparatorNone />
          <ChartPieLabel />
          <ChartPieLabelCustom />
          <ChartPieLabelList />
          <ChartPieLegend />
          <ChartPieDonut />
          <ChartPieDonutActive />
          <ChartPieDonutText />
          <ChartPieStacked />
          <ChartPieInteractive />
        </div>
      </section>

      {/* Radial Charts Section */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Radial Charts</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartRadialSimple />
          <ChartRadialLabel />
          <ChartRadialGrid />
          <ChartRadialText />
          <ChartRadialShape />
          <ChartRadialStacked />
        </div>
      </section>

      {/* Tooltip Charts Section */}
      <section>
        <h2 className="text-2xl font-semibold mb-4">Tooltip Charts</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartTooltipDefault />
          <ChartTooltipIndicatorLine />
          <ChartTooltipIndicatorNone />
          <ChartTooltipLabelCustom />
          <ChartTooltipLabelFormatter />
          <ChartTooltipLabelNone />
          <ChartTooltipFormatter />
          <ChartTooltipIcons />
          <ChartTooltipAdvanced />
        </div>
      </section>
    </div>
  );
}
