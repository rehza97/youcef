import { toast } from "sonner";
import React from "react";

// Error types and their user-friendly messages
const ERROR_MESSAGES = {
  // Network errors
  NETWORK_ERROR: "Connection failed. Please check your internet connection.",
  TIMEOUT_ERROR: "Request timed out. Please try again.",

  // Authentication errors
  UNAUTHORIZED: "You are not authorized to perform this action.",
  FORBIDDEN: "Access denied. You don't have permission for this action.",
  INVALID_CREDENTIALS: "Invalid username or password.",
  TOKEN_EXPIRED: "Your session has expired. Please log in again.",

  // Validation errors
  INVALID_USERNAME: "Username must be at least 3 characters long.",
  INVALID_EMAIL: "Please enter a valid email address.",
  INVALID_PASSWORD: "Password must be at least 8 characters long.",
  PASSWORDS_DONT_MATCH: "Passwords do not match.",
  MISSING_FIELDS: "Please fill in all required fields.",
  MISSING_IDS: "User ID and Role ID are required.",
  INVALID_PARAMS: "Invalid parameters provided.",

  // Server errors
  SERVER_ERROR: "Server error. Please try again later.",
  SERVICE_UNAVAILABLE: "Service temporarily unavailable.",

  // API specific errors
  INVALID_MESSAGE: "Message content is required.",
  MISSING_PARTICIPANTS: "Please select at least one participant.",
  CONVERSATION_NOT_FOUND: "Conversation not found.",
  USER_NOT_FOUND: "User not found.",
  NOTIFICATION_NOT_FOUND: "Notification not found.",
  FILE_NOT_FOUND: "File not found.",
  ROLE_NOT_FOUND: "Role not found.",
  PERMISSION_NOT_FOUND: "Permission not found.",

  // File upload errors
  FILE_TOO_LARGE: "File size exceeds the maximum limit.",
  INVALID_FILE_TYPE: "File type not supported.",
  UPLOAD_FAILED: "File upload failed. Please try again.",
  MISSING_COLUMNS: "File is missing required columns.",

  // Permission errors
  MISSING_PERMISSION: "You don't have permission to perform this action.",
  ROLE_REQUIRED: "Role assignment is required.",
  ADMIN_ONLY: "This action requires administrator privileges.",

  // Duplicate errors
  USERNAME_EXISTS: "Username already exists.",
  EMAIL_EXISTS: "Email already exists.",
  ROLE_EXISTS: "Role already exists.",
  PERMISSION_EXISTS: "Permission already exists.",
  USER_ALREADY_BLOCKED: "User is already blocked.",

  // Default error
  UNKNOWN_ERROR: "An unexpected error occurred. Please try again.",
};

// Error severity levels
export const ERROR_SEVERITY = {
  LOW: "low",
  MEDIUM: "medium",
  HIGH: "high",
  CRITICAL: "critical",
};

// Error categories
export const ERROR_CATEGORY = {
  NETWORK: "network",
  AUTH: "authentication",
  VALIDATION: "validation",
  SERVER: "server",
  PERMISSION: "permission",
  FILE: "file",
  UNKNOWN: "unknown",
};

/**
 * Classify error based on response status and error code
 */
function classifyError(error) {
  const status = error.response?.status;
  const code = error.code || error.response?.data?.code;
  const detail = error.response?.data?.detail;

  // Network errors
  if (!error.response) {
    return {
      category: ERROR_CATEGORY.NETWORK,
      severity: ERROR_SEVERITY.HIGH,
      message:
        error.message === "Network Error"
          ? ERROR_MESSAGES.NETWORK_ERROR
          : ERROR_MESSAGES.TIMEOUT_ERROR,
    };
  }

  // Check for specific error codes from backend
  if (detail) {
    if (detail.includes("Username already")) {
      return {
        category: ERROR_CATEGORY.VALIDATION,
        severity: ERROR_SEVERITY.MEDIUM,
        message: ERROR_MESSAGES.USERNAME_EXISTS,
      };
    }
    if (detail.includes("Role already")) {
      return {
        category: ERROR_CATEGORY.VALIDATION,
        severity: ERROR_SEVERITY.MEDIUM,
        message: ERROR_MESSAGES.ROLE_EXISTS,
      };
    }
    if (detail.includes("Permission already")) {
      return {
        category: ERROR_CATEGORY.VALIDATION,
        severity: ERROR_SEVERITY.MEDIUM,
        message: ERROR_MESSAGES.PERMISSION_EXISTS,
      };
    }
    if (detail.includes("User already blocked")) {
      return {
        category: ERROR_CATEGORY.VALIDATION,
        severity: ERROR_SEVERITY.MEDIUM,
        message: ERROR_MESSAGES.USER_ALREADY_BLOCKED,
      };
    }
    if (detail.includes("missing columns")) {
      return {
        category: ERROR_CATEGORY.FILE,
        severity: ERROR_SEVERITY.MEDIUM,
        message: ERROR_MESSAGES.MISSING_COLUMNS,
      };
    }
  }

  // HTTP status based classification
  switch (status) {
    case 400:
      return {
        category: ERROR_CATEGORY.VALIDATION,
        severity: ERROR_SEVERITY.MEDIUM,
        message: detail || ERROR_MESSAGES.MISSING_FIELDS,
      };

    case 401:
      return {
        category: ERROR_CATEGORY.AUTH,
        severity: ERROR_SEVERITY.HIGH,
        message: ERROR_MESSAGES.UNAUTHORIZED,
      };

    case 403:
      return {
        category: ERROR_CATEGORY.PERMISSION,
        severity: ERROR_SEVERITY.HIGH,
        message: ERROR_MESSAGES.FORBIDDEN,
      };

    case 404:
      return {
        category: ERROR_CATEGORY.VALIDATION,
        severity: ERROR_SEVERITY.MEDIUM,
        message: detail || ERROR_MESSAGES.USER_NOT_FOUND,
      };

    case 422:
      return {
        category: ERROR_CATEGORY.VALIDATION,
        severity: ERROR_SEVERITY.MEDIUM,
        message: detail || ERROR_MESSAGES.MISSING_FIELDS,
      };

    case 500:
      return {
        category: ERROR_CATEGORY.SERVER,
        severity: ERROR_SEVERITY.HIGH,
        message: ERROR_MESSAGES.SERVER_ERROR,
      };

    case 503:
      return {
        category: ERROR_CATEGORY.SERVER,
        severity: ERROR_SEVERITY.HIGH,
        message: ERROR_MESSAGES.SERVICE_UNAVAILABLE,
      };

    default:
      return {
        category: ERROR_CATEGORY.UNKNOWN,
        severity: ERROR_SEVERITY.MEDIUM,
        message: detail || ERROR_MESSAGES.UNKNOWN_ERROR,
      };
  }
}

/**
 * Handle API errors with consistent user feedback
 */
export function handleApiError(error, options = {}) {
  const {
    showToast = true,
    logError = true,
    fallbackMessage = null,
    onError = null,
  } = options;

  // Classify the error
  const errorInfo = classifyError(error);

  // Use fallback message if provided
  const message = fallbackMessage || errorInfo.message;

  // Log error for debugging
  if (logError) {
    console.error("API Error:", {
      message: error.message,
      status: error.response?.status,
      data: error.response?.data,
      url: error.config?.url,
      method: error.config?.method,
      category: errorInfo.category,
      severity: errorInfo.severity,
    });
  }

  // Show toast notification
  if (showToast) {
    const toastOptions = {
      duration: errorInfo.severity === ERROR_SEVERITY.CRITICAL ? 8000 : 4000,
    };

    switch (errorInfo.severity) {
      case ERROR_SEVERITY.CRITICAL:
        toast.error(message, toastOptions);
        break;
      case ERROR_SEVERITY.HIGH:
        toast.error(message, toastOptions);
        break;
      case ERROR_SEVERITY.MEDIUM:
        toast.warning(message, toastOptions);
        break;
      case ERROR_SEVERITY.LOW:
        toast.info(message, toastOptions);
        break;
      default:
        toast.error(message, toastOptions);
    }
  }

  // Call custom error handler if provided
  if (onError) {
    onError(error, errorInfo);
  }

  return {
    error,
    errorInfo,
    message,
  };
}

/**
 * Handle form validation errors
 */
export function handleValidationError(errors, options = {}) {
  const { showToast = true, field = null } = options;

  if (!errors || Object.keys(errors).length === 0) {
    return;
  }

  // Get the first error message
  const firstError = Object.values(errors)[0];
  const message = field ? `${field}: ${firstError}` : firstError;

  if (showToast) {
    toast.error(message);
  }

  return message;
}

/**
 * Handle file upload errors
 */
export function handleFileError(error, options = {}) {
  const { showToast = true, maxSize = null } = options;

  let message = ERROR_MESSAGES.UPLOAD_FAILED;

  if (error.code === "FILE_TOO_LARGE") {
    message = maxSize
      ? `File size must be less than ${maxSize}MB`
      : ERROR_MESSAGES.FILE_TOO_LARGE;
  } else if (error.code === "INVALID_FILE_TYPE") {
    message = ERROR_MESSAGES.INVALID_FILE_TYPE;
  }

  if (showToast) {
    toast.error(message);
  }

  return message;
}

/**
 * Handle permission errors
 */
export function handlePermissionError(permission, options = {}) {
  const { showToast = true, action = "perform this action" } = options;

  const message = `You don't have permission to ${action}. Required permission: ${permission}`;

  if (showToast) {
    toast.error(message);
  }

  return message;
}

/**
 * Create a custom error handler for specific components
 */
export function createErrorHandler(defaultOptions = {}) {
  return (error, options = {}) => {
    const mergedOptions = { ...defaultOptions, ...options };
    return handleApiError(error, mergedOptions);
  };
}

/**
 * Retry function with exponential backoff
 */
export async function retryWithBackoff(fn, maxRetries = 3, baseDelay = 1000) {
  let lastError;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      if (attempt === maxRetries) {
        throw error;
      }

      // Don't retry on client errors (4xx)
      if (error.response?.status >= 400 && error.response?.status < 500) {
        throw error;
      }

      // Wait with exponential backoff
      const delay = baseDelay * Math.pow(2, attempt);
      await new Promise((resolve) => setTimeout(resolve, delay));
    }
  }

  throw lastError;
}

/**
 * Error boundary helper for React components
 */
export function withErrorBoundary(Component, fallback = null) {
  return function ErrorBoundaryWrapper(props) {
    try {
      return React.createElement(Component, props);
    } catch (error) {
      console.error("Component Error:", error);

      if (fallback) {
        return fallback(error);
      }

      return React.createElement(
        "div",
        {
          className: "p-4 bg-red-50 border border-red-200 rounded-md",
        },
        [
          React.createElement(
            "h3",
            {
              key: "title",
              className: "text-red-800 font-medium",
            },
            "Something went wrong"
          ),
          React.createElement(
            "p",
            {
              key: "message",
              className: "text-red-600 text-sm mt-1",
            },
            "Please refresh the page and try again."
          ),
        ]
      );
    }
  };
}

// Export error messages for direct use
export { ERROR_MESSAGES };
