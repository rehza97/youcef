# Chart Width Control Guide

## Overview

All enhanced chart components now support width control through the `width` prop. You can control the width using different methods depending on your needs.

## Width Control Options

### 1. **Percentage Width (Responsive)**

```jsx
<EnhancedPieChart
  data={data}
  width="100%"     // Full width of container
  height={400}
/>

<EnhancedBarChart
  data={data}
  width="50%"      // Half width of container
  height={400}
/>
```

### 2. **Fixed Pixel Width**

```jsx
<EnhancedPieChart
  data={data}
  width={600}      // Fixed 600px width
  height={400}
/>

<EnhancedMultiSeriesBarChart
  data={data}
  width={800}      // Fixed 800px width
  height={550}
/>
```

### 3. **CSS Units**

```jsx
<EnhancedPieChart
  data={data}
  width="calc(100% - 40px)"  // Full width minus padding
  height={400}
/>

<EnhancedBarChart
  data={data}
  width="min(600px, 100%)"   // Maximum 600px or full width
  height={400}
/>
```

## Usage Examples

### **Responsive Grid Layout**

```jsx
// Two-column layout
<div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
  <EnhancedPieChart
    data={telecomData}
    width="100%" // Takes full width of grid cell
    height={400}
    showLabels={true}
    labelPosition="outside"
  />

  <EnhancedBarChart
    data={statusData}
    width="100%" // Takes full width of grid cell
    height={400}
  />
</div>
```

### **Fixed Width Charts**

```jsx
// Sidebar with fixed width charts
<div className="w-80 space-y-4">
  <EnhancedPieChart
    data={data}
    width={300} // Fixed width for sidebar
    height={250}
    showLabels={true}
    labelPosition="legend"
  />

  <EnhancedBarChart
    data={data}
    width={300} // Fixed width for sidebar
    height={200}
  />
</div>
```

### **Flexible Container**

```jsx
// Chart that adapts to container
<div className="w-full max-w-4xl mx-auto">
  <EnhancedMultiSeriesBarChart
    data={dotData}
    width="100%" // Adapts to container width
    height={550}
  />
</div>
```

## Component-Specific Examples

### **Pie Chart Width Control**

```jsx
// Small pie chart for dashboard
<EnhancedPieChart
  data={telecomTypeData}
  width={300}
  height={300}
  showLabels={true}
  labelPosition="outside"
  showPercentages={true}
  showValues={true}
  minLabelPercentage={2}
/>

// Large pie chart for full screen
<EnhancedPieChart
  data={telecomTypeData}
  width="100%"
  height={500}
  showLabels={true}
  labelPosition="legend"
  showPercentages={true}
/>
```

### **Bar Chart Width Control**

```jsx
// Compact bar chart
<EnhancedBarChart
  data={subscriberStatusData}
  width="100%"
  height={400}
/>

// Wide bar chart for many categories
<EnhancedMultiSeriesBarChart
  data={customerL3Data}
  width={1200}
  height={550}
/>
```

## Responsive Width Strategies

### **Breakpoint-Based Widths**

```jsx
const [chartWidth, setChartWidth] = useState("100%");

useEffect(() => {
  const updateWidth = () => {
    if (window.innerWidth < 768) {
      setChartWidth("100%"); // Mobile: full width
    } else if (window.innerWidth < 1024) {
      setChartWidth("80%"); // Tablet: 80% width
    } else {
      setChartWidth(600); // Desktop: fixed 600px
    }
  };

  updateWidth();
  window.addEventListener("resize", updateWidth);
  return () => window.removeEventListener("resize", updateWidth);
}, []);

<EnhancedPieChart data={data} width={chartWidth} height={400} />;
```

### **Container Query Approach**

```jsx
// Using CSS container queries (modern approach)
<div className="@container">
  <EnhancedPieChart
    data={data}
    width="100%"
    height={400}
    className="@lg:w-[600px] @xl:w-[800px]"
  />
</div>
```

## Layout Examples

### **Dashboard Layout**

```jsx
<div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
  {/* Overview charts */}
  <div className="col-span-1 md:col-span-2">
    <EnhancedPieChart
      data={telecomData}
      width="100%"
      height={400}
      title="Telecom Distribution"
    />
  </div>

  <div className="col-span-1">
    <EnhancedBarChart
      data={statusData}
      width="100%"
      height={400}
      title="Status Overview"
    />
  </div>

  {/* Full-width detailed charts */}
  <div className="col-span-full">
    <EnhancedMultiSeriesBarChart
      data={dotData}
      width="100%"
      height={550}
      title="DOT Distribution"
    />
  </div>
</div>
```

### **Sidebar Layout**

```jsx
<div className="flex gap-6">
  {/* Main content */}
  <div className="flex-1">
    <EnhancedMultiSeriesBarChart
      data={mainData}
      width="100%"
      height={600}
      title="Main Analysis"
    />
  </div>

  {/* Sidebar */}
  <div className="w-80 space-y-4">
    <EnhancedPieChart
      data={summaryData}
      width="100%"
      height={250}
      title="Summary"
      labelPosition="legend"
    />

    <EnhancedBarChart
      data={quickData}
      width="100%"
      height={200}
      title="Quick Stats"
    />
  </div>
</div>
```

## Performance Considerations

### **Fixed vs Responsive Widths**

- **Fixed widths** (e.g., `width={600}`): Better performance, no resize calculations
- **Responsive widths** (e.g., `width="100%"`): More flexible, but requires resize handling

### **Memoization for Dynamic Widths**

```jsx
const memoizedWidth = useMemo(() => {
  return window.innerWidth > 1024 ? 800 : "100%";
}, [screenSize]);
```

## Current Implementation in EncaissementPage

The charts are currently using responsive widths:

```jsx
<EnhancedPieChart
  data={telecomTypeData}
  width="100%" // Takes full width of card
  height={400}
  showLabels={true}
  labelPosition="outside"
  showPercentages={true}
  showValues={true}
  minLabelPercentage={2}
/>
```

## Best Practices

### ✅ **Do:**

- Use `width="100%"` for responsive layouts
- Use fixed widths for consistent sizing
- Consider container constraints
- Test on different screen sizes

### ❌ **Don't:**

- Mix fixed and percentage widths in the same layout
- Use extremely large fixed widths (>1200px)
- Ignore mobile constraints
- Forget to test responsive behavior

---

**Date**: October 8, 2025  
**Status**: ✅ Complete  
**Feature**: Added width control to all chart components
