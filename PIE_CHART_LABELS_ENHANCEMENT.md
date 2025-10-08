# Pie Chart Labels Enhancement

## Overview

Enhanced the `EnhancedPieChart` component with comprehensive labeling options to improve data visualization and user experience.

## New Features Added

### 1. **Flexible Label Positioning**

- **`labelPosition`**: Choose from 3 positions:
  - `"inside"` - Labels inside the pie slices
  - `"outside"` - Labels outside with connecting lines
  - `"legend"` - Custom legend below the chart

### 2. **Rich Label Content**

- **`showPercentages`**: Show percentage values (e.g., "45.2%")
- **`showValues`**: Show actual numeric values (e.g., "258,482")
- **`showLabels`**: Toggle labels on/off completely

### 3. **Smart Label Filtering**

- **`minLabelPercentage`**: Only show labels for slices above this threshold
- Prevents cluttered labels on small slices
- Default: 3% (configurable)

### 4. **Enhanced Label Formatting**

- **French number formatting**: Uses `Intl.NumberFormat("fr-FR")`
- **Smart text truncation**: Long names are truncated with "..."
- **Multi-line labels**: Outside labels can show name, percentage, and value

## Usage Examples

### Basic Outside Labels (Current Implementation)

```jsx
<EnhancedPieChart
  data={telecomTypeData}
  height={450}
  showLabels={true}
  labelPosition="outside"
  showPercentages={true}
  showValues={true}
  minLabelPercentage={2}
/>
```

### Inside Labels (Percentage Only)

```jsx
<EnhancedPieChart
  data={data}
  labelPosition="inside"
  showPercentages={true}
  showValues={false}
  minLabelPercentage={5}
/>
```

### Legend Style

```jsx
<EnhancedPieChart
  data={data}
  labelPosition="legend"
  showPercentages={true}
  showValues={true}
/>
```

## Label Content Options

### Outside Labels

- **Name + Percentage**: `"PSTN\n45.2%"`
- **Name + Value**: `"PSTN\n258,482"`
- **Full Info**: `"PSTN\n45.2%\n258,482"`
- **Name Only**: `"PSTN"`

### Inside Labels

- **Percentage Only**: `"45.2%"`

### Legend Labels

- **Color indicator + Name + Percentage + Value**
- **Truncated names** (max 12 characters)
- **Responsive layout** with flex-wrap

## Technical Implementation

### Custom Label Function

```typescript
const renderLabel = (entry: any) => {
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
      entry.name.length > 8 ? `${entry.name.substring(0, 8)}...` : entry.name;
    if (showPercentages && showValues) {
      labelText = `${name}\n${percentage.toFixed(1)}%\n${new Intl.NumberFormat(
        "fr-FR"
      ).format(entry.value)}`;
    } else if (showPercentages) {
      labelText = `${name}\n${percentage.toFixed(1)}%`;
    } else if (showValues) {
      labelText = `${name}\n${new Intl.NumberFormat("fr-FR").format(
        entry.value
      )}`;
    } else {
      labelText = name;
    }
  }

  return labelText;
};
```

### Pie Chart Configuration

```typescript
<Pie
  data={chartData}
  dataKey="value"
  nameKey="name"
  cx="50%"
  cy="50%"
  outerRadius={height / 3}
  innerRadius={labelPosition === "legend" ? height / 6 : 0}
  fill="#8884d8"
  label={showLabels && labelPosition !== "legend" ? renderLabel : false}
  labelLine={labelPosition === "outside"}
>
```

## Benefits

### ✅ **Better Data Visibility**

- **Clear identification** of each slice
- **Exact values** and percentages shown
- **No more guessing** what each slice represents

### ✅ **Reduced Cognitive Load**

- **Smart filtering** prevents label clutter
- **Consistent formatting** across all labels
- **Intuitive positioning** options

### ✅ **Professional Appearance**

- **French locale formatting** (258,482 instead of 258482)
- **Proper text truncation** for long names
- **Clean legend layout** when needed

### ✅ **Flexible Configuration**

- **Multiple label styles** for different use cases
- **Configurable thresholds** for label visibility
- **Easy to customize** for specific requirements

## Current Implementation in EncaissementPage

The telecom type pie chart now shows:

- **Outside labels** with connecting lines
- **Name, percentage, and value** for each slice
- **Minimum 2% threshold** for label visibility
- **French number formatting** for values

## Before vs After

### Before

- Only tooltips on hover
- No visible labels on slices
- Users had to guess slice values
- Limited information visibility

### After

- **Rich labels** directly on chart
- **Multiple information types** (name, %, value)
- **Smart filtering** prevents clutter
- **Professional formatting** with French locale

## Files Modified

1. ✅ `frontend/src/components/ui/charts/EnhancedCharts.tsx` - Enhanced pie chart component
2. ✅ `frontend/src/pages/EncaissementPage/index.jsx` - Updated to use new label features

## Testing Checklist

- [x] Outside labels display correctly
- [x] French number formatting works (258,482)
- [x] Labels only show for slices > 2%
- [x] Long names are truncated properly
- [x] Tooltips still work on hover
- [x] Chart remains responsive
- [x] AT colors are maintained

---

**Date**: October 8, 2025  
**Status**: ✅ Complete  
**Enhancement**: Added comprehensive labeling system to pie charts
