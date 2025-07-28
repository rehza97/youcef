import React from "react";
import { Loader2, AlertCircle, CheckCircle, XCircle } from "lucide-react";
import { cn } from "../../lib/utils";

// Loading spinner component
export function Spinner({
  size = "default",
  className = "",
  color = "primary",
}) {
  const sizeClasses = {
    sm: "h-4 w-4",
    default: "h-6 w-6",
    lg: "h-8 w-8",
    xl: "h-12 w-12",
  };

  const colorClasses = {
    primary: "text-blue-600",
    secondary: "text-gray-600",
    white: "text-white",
    success: "text-green-600",
    error: "text-red-600",
  };

  return (
    <Loader2
      className={cn(
        "animate-spin",
        sizeClasses[size],
        colorClasses[color],
        className
      )}
    />
  );
}

// Loading skeleton component
export function Skeleton({ className = "", width = "w-full", height = "h-4" }) {
  return (
    <div
      className={cn(
        "animate-pulse bg-gray-200 dark:bg-gray-700 rounded",
        width,
        height,
        className
      )}
    />
  );
}

// Loading overlay component
export function LoadingOverlay({
  isLoading = false,
  children,
  message = "Loading...",
  className = "",
}) {
  if (!isLoading) return children;

  return (
    <div className={cn("relative", className)}>
      {children}
      <div className="absolute inset-0 bg-white/80 dark:bg-gray-900/80 flex items-center justify-center z-50">
        <div className="flex flex-col items-center space-y-3">
          <Spinner size="xl" />
          <p className="text-sm text-gray-600 dark:text-gray-400">{message}</p>
        </div>
      </div>
    </div>
  );
}

// Status indicator component
export function StatusIndicator({
  status = "loading",
  message = "",
  className = "",
}) {
  const statusConfig = {
    loading: {
      icon: Loader2,
      className: "text-blue-600 animate-spin",
      bgColor: "bg-blue-50 dark:bg-blue-900/20",
      borderColor: "border-blue-200 dark:border-blue-800",
    },
    success: {
      icon: CheckCircle,
      className: "text-green-600",
      bgColor: "bg-green-50 dark:bg-green-900/20",
      borderColor: "border-green-200 dark:border-green-800",
    },
    error: {
      icon: XCircle,
      className: "text-red-600",
      bgColor: "bg-red-50 dark:bg-red-900/20",
      borderColor: "border-red-200 dark:border-red-800",
    },
    warning: {
      icon: AlertCircle,
      className: "text-yellow-600",
      bgColor: "bg-yellow-50 dark:bg-yellow-900/20",
      borderColor: "border-yellow-200 dark:border-yellow-800",
    },
  };

  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div
      className={cn(
        "flex items-center space-x-2 p-3 rounded-md border",
        config.bgColor,
        config.borderColor,
        className
      )}
    >
      <Icon className={cn("h-5 w-5", config.className)} />
      {message && (
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {message}
        </span>
      )}
    </div>
  );
}

// Progress bar component
export function ProgressBar({
  progress = 0,
  className = "",
  showPercentage = false,
  color = "blue",
}) {
  const colorClasses = {
    blue: "bg-blue-600",
    green: "bg-green-600",
    red: "bg-red-600",
    yellow: "bg-yellow-600",
  };

  return (
    <div className={cn("w-full", className)}>
      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div
          className={cn(
            "h-2 rounded-full transition-all duration-300",
            colorClasses[color]
          )}
          style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
        />
      </div>
      {showPercentage && (
        <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
          {Math.round(progress)}% complete
        </p>
      )}
    </div>
  );
}

// Loading button component
export function LoadingButton({
  loading = false,
  children,
  loadingText = "Loading...",
  className = "",
  ...props
}) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center space-x-2",
        className
      )}
      disabled={loading}
      {...props}
    >
      {loading && <Spinner size="sm" />}
      <span>{loading ? loadingText : children}</span>
    </button>
  );
}

// Page loading component
export function PageLoader({ message = "Loading page...", className = "" }) {
  return (
    <div
      className={cn(
        "min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900",
        className
      )}
    >
      <div className="text-center">
        <Spinner size="xl" className="mx-auto mb-4" />
        <p className="text-gray-600 dark:text-gray-400">{message}</p>
      </div>
    </div>
  );
}

// Content loading component
export function ContentLoader({
  isLoading = false,
  children,
  skeleton = null,
  className = "",
}) {
  if (isLoading) {
    return (
      skeleton || (
        <div className={cn("space-y-3", className)}>
          <Skeleton height="h-4" width="w-3/4" />
          <Skeleton height="h-4" width="w-1/2" />
          <Skeleton height="h-4" width="w-5/6" />
        </div>
      )
    );
  }

  return children;
}

// Infinite scroll loading component
export function InfiniteScrollLoader({
  hasNextPage = false,
  isFetchingNextPage = false,
  onLoadMore = null,
  className = "",
}) {
  if (!hasNextPage) return null;

  return (
    <div className={cn("flex justify-center py-4", className)}>
      {isFetchingNextPage ? (
        <div className="flex items-center space-x-2">
          <Spinner size="sm" />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            Loading more...
          </span>
        </div>
      ) : (
        <button
          onClick={onLoadMore}
          className="text-sm text-blue-600 hover:text-blue-500 dark:text-blue-400 dark:hover:text-blue-300"
        >
          Load more
        </button>
      )}
    </div>
  );
}
