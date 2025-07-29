// Debug utility for frontend
class DebugLogger {
  constructor() {
    this.enabled = true;
    this.prefix = "🔍 [DEBUG]";
  }

  log(message, data = null) {
    if (!this.enabled) return;

    const timestamp = new Date().toISOString();
    const logMessage = `${this.prefix} ${timestamp} - ${message}`;

    console.log(logMessage);
    if (data) {
      console.log("📊 Data:", data);
    }
  }

  error(message, error = null) {
    if (!this.enabled) return;

    const timestamp = new Date().toISOString();
    const logMessage = `❌ [ERROR] ${timestamp} - ${message}`;

    console.error(logMessage);
    if (error) {
      console.error("🚨 Error details:", error);
      console.error("🚨 Error stack:", error.stack);
    }
  }

  warn(message, data = null) {
    if (!this.enabled) return;

    const timestamp = new Date().toISOString();
    const logMessage = `⚠️ [WARN] ${timestamp} - ${message}`;

    console.warn(logMessage);
    if (data) {
      console.warn("📊 Data:", data);
    }
  }

  success(message, data = null) {
    if (!this.enabled) return;

    const timestamp = new Date().toISOString();
    const logMessage = `✅ [SUCCESS] ${timestamp} - ${message}`;

    console.log(logMessage);
    if (data) {
      console.log("📊 Data:", data);
    }
  }

  apiCall(method, url, data = null) {
    this.log(`🌐 API Call: ${method} ${url}`, data);
  }

  apiResponse(status, url, data = null) {
    if (status >= 200 && status < 300) {
      this.success(`API Response: ${status} ${url}`, data);
    } else {
      this.error(`API Error: ${status} ${url}`, data);
    }
  }

  websocket(event, data = null) {
    this.log(`🔌 WebSocket: ${event}`, data);
  }

  auth(action, data = null) {
    this.log(`🔐 Auth: ${action}`, data);
  }

  fileUpload(file, data = null) {
    this.log(`📁 File Upload: ${file.name} (${file.size} bytes)`, data);
  }
}

// Create global debug instance
window.debug = new DebugLogger();

// Export for use in components
export const debug = window.debug;

// Debug middleware for API calls
export const debugApiMiddleware = {
  request: (config) => {
    debug.apiCall(config.method?.toUpperCase(), config.url, {
      headers: config.headers,
      data: config.data,
    });
    return config;
  },

  response: (response) => {
    debug.apiResponse(response.status, response.config.url, response.data);
    return response;
  },

  error: (error) => {
    debug.apiResponse(
      error.response?.status || 0,
      error.config?.url || "unknown",
      error.response?.data || error.message
    );
    return Promise.reject(error);
  },
};

// Debug utility for components
export const debugComponent = (componentName) => {
  return {
    log: (message, data) => debug.log(`[${componentName}] ${message}`, data),
    error: (message, error) =>
      debug.error(`[${componentName}] ${message}`, error),
    warn: (message, data) => debug.warn(`[${componentName}] ${message}`, data),
    success: (message, data) =>
      debug.success(`[${componentName}] ${message}`, data),
    fileUpload: (file, data) =>
      debug.fileUpload(
        file,
        data
          ? { ...data, component: componentName }
          : { component: componentName }
      ),
  };
};
