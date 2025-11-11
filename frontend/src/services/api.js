import axios from "axios";
import { debug } from "../lib/debug.js";

// Use environment variable with fallback
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || API_BASE_URL.replace('http://', 'ws://').replace('https://', 'wss://');
const IS_DEV = import.meta.env.VITE_ENV === 'development' || import.meta.env.DEV;

// Debug logging utility
const debugLog = (...args) => {
  if (IS_DEV && import.meta.env.VITE_ENABLE_DEBUG !== 'false') {
    console.log(...args);
  }
};

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 300000, // 30 second timeout
  withCredentials: false, // FastAPI doesn't use CSRF cookies
});

// Add debug interceptors
api.interceptors.request.use(
  (config) => {
    debug.apiCall(config.method?.toUpperCase(), config.url, {
      headers: config.headers,
      data: config.data,
    });
    return config;
  },
  (error) => {
    debug.error("API Request Error", error);
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    debug.apiResponse(response.status, response.config.url, response.data);
    return response;
  },
  (error) => {
    debug.apiResponse(
      error.response?.status || 0,
      error.config?.url || "unknown",
      error.response?.data || error.message
    );
    return Promise.reject(error);
  }
);

// Request interceptor - Add JWT Bearer token
api.interceptors.request.use(
  (config) => {
    // Add authentication token as Bearer token
    const token =
      sessionStorage.getItem("token") || localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Don't override Content-Type for multipart requests
    if (config.headers["Content-Type"] === "multipart/form-data") {
      // Let the browser set the correct boundary
      delete config.headers["Content-Type"];
    } else {
      // Sanitize request data only for non-multipart requests
      if (config.data && typeof config.data === "object") {
        config.data = sanitizeData(config.data);
      }
    }

    return config;
  },
  (error) => {
    console.error("Request interceptor error:", error);
    return Promise.reject(error);
  }
);

// Response interceptor - Handle errors and token refresh
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 errors (unauthorized)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        // Try to refresh token
        const refreshToken =
          sessionStorage.getItem("refreshToken") ||
          localStorage.getItem("refreshToken");
        if (refreshToken) {
          const refreshResponse = await axios.post(
            `${API_BASE_URL}/api/auth/refresh-token`,
            { refresh_token: refreshToken }
          );

          const newToken = refreshResponse.data.access_token;
          const newRefreshToken = refreshResponse.data.refresh_token;

          // Update stored tokens
          if (sessionStorage.getItem("token")) {
            sessionStorage.setItem("token", newToken);
            sessionStorage.setItem("refreshToken", newRefreshToken);
          } else {
            localStorage.setItem("token", newToken);
            localStorage.setItem("refreshToken", newRefreshToken);
          }

          // Retry original request with new token
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return api(originalRequest);
        }
      } catch (refreshError) {
        console.error("Token refresh failed:", refreshError);
      }

      // Clear tokens and redirect to login
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("refreshToken");
      localStorage.removeItem("token");
      localStorage.removeItem("refreshToken");
      localStorage.removeItem("user");
      sessionStorage.removeItem("user");

      // Dispatch custom event for logout
      window.dispatchEvent(new CustomEvent("auth:logout"));
    }

    return Promise.reject(error);
  }
);

// Utility functions
function sanitizeData(data) {
  if (typeof data !== "object" || data === null) return data;

  const sanitized = {};
  for (const [key, value] of Object.entries(data)) {
    if (typeof value === "string") {
      // Basic XSS protection - remove script tags
      sanitized[key] = value
        .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, "")
        .trim();
    } else if (typeof value === "object" && value !== null) {
      sanitized[key] = sanitizeData(value);
    } else {
      sanitized[key] = value;
    }
  }
  return sanitized;
}

// Authentication API methods
export const login = (credentials) => {
  if (!credentials.username || !credentials.password) {
    return Promise.reject({
      response: {
        data: {
          detail: "Username and password are required",
          code: "MISSING_CREDENTIALS",
        },
      },
    });
  }

  return api.post("/api/auth/login", {
    username: credentials.username.trim(),
    password: credentials.password,
  });
};

export const register = (userData) => {
  if (!userData.username || !userData.email || !userData.password) {
    return Promise.reject({
      response: {
        data: {
          detail: "Username, email, and password are required",
          code: "MISSING_FIELDS",
        },
      },
    });
  }

  return api.post("/api/auth/register", {
    username: userData.username.trim(),
    email: userData.email.trim(),
    password: userData.password,
  });
};

export const logout = () => api.post("/api/auth/logout");

export const refreshToken = (refreshToken) =>
  api.post("/api/auth/refresh-token", { refresh_token: refreshToken });

export const updateProfile = (profileData) =>
  api.put("/api/users/me", profileData);

export const protectedRoute = () => api.get("/api/auth/protected");

// Users API methods
export const getUsers = () => api.get("/api/users/");
export const getUser = (userId) => api.get(`/api/users/${userId}`);
export const getCurrentUser = () => api.get("/api/users/me");
export const updateCurrentUser = (userData) =>
  api.put("/api/users/me", userData);
export const searchUsers = (query) =>
  api.get(`/api/users/search?q=${encodeURIComponent(query)}`);

// User CRUD operations
export const createUser = (userData) => api.post("/api/users/", userData);
export const updateUser = (userId, userData) =>
  api.put(`/api/users/${userId}`, userData);
export const deleteUser = (userId) => api.delete(`/api/users/${userId}`);

// Roles
export const getRoles = () => api.get("/api/roles/roles/");
export const getRole = (roleId) => api.get(`/api/roles/roles/${roleId}`);
export const createRole = (roleData) => api.post("/api/roles/roles/", roleData);
export const updateRole = (roleId, roleData) =>
  api.put(`/api/roles/roles/${roleId}`, roleData);
export const deleteRole = (roleId) => api.delete(`/api/roles/roles/${roleId}`);

// Permissions
export const getPermissions = () => api.get("/api/permissions/permissions/");
export const getPermission = (permissionId) =>
  api.get(`/api/permissions/permissions/${permissionId}`);
export const createPermission = (permissionData) =>
  api.post("/api/permissions/permissions/", permissionData);
export const updatePermission = (permissionId, permissionData) =>
  api.put(`/api/permissions/permissions/${permissionId}`, permissionData);
export const deletePermission = (permissionId) =>
  api.delete(`/api/permissions/permissions/${permissionId}`);

// Role assignments
export const assignRole = (userData) => {
  if (!userData.user_id || !userData.role_id) {
    return Promise.reject({
      response: {
        data: {
          detail: "User ID and Role ID are required",
          code: "MISSING_IDS",
        },
      },
    });
  }
  return api.post("/api/users/assign-role", userData);
};

export const removeUserRole = (userId, roleId) =>
  api.delete(`/api/users/${userId}/roles/${roleId}`);

export const checkRole = (roleName, userId) => {
  if (!roleName) return Promise.reject(new Error("Role name is required"));
  return api.get(
    `/api/users/check-role/${encodeURIComponent(roleName)}?user_id=${userId}`
  );
};

export const checkPermission = (codename, userId) => {
  if (!codename)
    return Promise.reject(new Error("Permission codename is required"));
  return api.get(
    `/api/users/check-permission/${encodeURIComponent(
      codename
    )}?user_id=${userId}`
  );
};

export const updateRolePermissions = (roleId, permissionIds) => {
  if (!roleId || !Array.isArray(permissionIds)) {
    return Promise.reject({
      response: {
        data: {
          detail: "Role ID and permissions array are required",
          code: "INVALID_PARAMS",
        },
      },
    });
  }
  return api.post(`/api/users/roles/${roleId}/update-permissions`, {
    permission_ids: permissionIds,
  });
};

export const getUserRoles = (userId) => api.get(`/api/users/${userId}/roles`);
export const getRolePermissions = (roleId) =>
  api.get(`/api/users/roles/${roleId}/permissions`);

// Notifications API methods
export const fetchNotifications = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.skip) queryParams.append("skip", params.skip);
  if (params.limit) queryParams.append("limit", params.limit);
  if (params.unread_only) queryParams.append("unread_only", params.unread_only);

  return api.get(`/api/notifications/?${queryParams.toString()}`);
};

export const getNotification = (notificationId) => {
  if (!notificationId)
    return Promise.reject(new Error("Notification ID is required"));
  return api.get(`/api/notifications/${notificationId}`);
};

export const createNotification = (notificationData) => {
  if (!notificationData.title || !notificationData.message) {
    return Promise.reject({
      response: {
        data: {
          detail: "Title and message are required",
          code: "MISSING_FIELDS",
        },
      },
    });
  }
  return api.post("/api/notifications/", notificationData);
};

export const updateNotification = (notificationId, notificationData) => {
  if (!notificationId)
    return Promise.reject(new Error("Notification ID is required"));
  return api.put(`/api/notifications/${notificationId}`, notificationData);
};

export const deleteNotification = (notificationId) => {
  if (!notificationId)
    return Promise.reject(new Error("Notification ID is required"));
  return api.delete(`/api/notifications/${notificationId}`);
};

export const markNotificationAsRead = (id) => {
  if (!id) return Promise.reject(new Error("Notification ID is required"));
  return api.put(`/api/notifications/${id}/read`);
};

export const markAllNotificationsAsRead = () =>
  api.put("/api/notifications/read-all");

export const updateNotificationPreferences = (prefs) =>
  api.put("/api/notifications/preferences", prefs);

export const getNotificationStats = () => api.get("/api/notifications/stats");

export const getNotificationPreferences = () =>
  api.get("/api/notifications/preferences");

// Messaging API methods
export const fetchConversations = () => api.get("/api/conversations/");

export const getConversation = (conversationId) => {
  if (!conversationId)
    return Promise.reject(new Error("Conversation ID is required"));
  return api.get(`/api/conversations/${conversationId}`);
};

// Create Conversation
export const createConversation = async (conversationData) => {
  // Ensure participant_ids is always an array
  const participantIds = Array.isArray(conversationData.participant_ids)
    ? conversationData.participant_ids
    : [];

  const requestData = {
    name: conversationData.name,
    conversation_type: conversationData.conversation_type || "group",
    participant_ids: participantIds,
    conversation_metadata: conversationData.conversation_metadata || {},
  };

  console.log("🔍 Sending conversation data:", requestData);

  const response = await api.post("/api/conversations/", requestData);
  return response.data;
};

export const updateConversation = (conversationId, data) => {
  if (!conversationId)
    return Promise.reject(new Error("Conversation ID is required"));
  return api.put(`/api/conversations/${conversationId}`, data);
};

export const deleteConversation = (conversationId) => {
  if (!conversationId)
    return Promise.reject(new Error("Conversation ID is required"));
  return api.delete(`/api/conversations/${conversationId}`);
};

export const fetchMessages = (conversationId, params = {}) => {
  if (!conversationId)
    return Promise.reject(new Error("Conversation ID is required"));

  const queryParams = new URLSearchParams();
  if (params.skip) queryParams.append("skip", params.skip);
  if (params.limit) queryParams.append("limit", params.limit);

  return api.get(
    `/api/messages/conversations/${conversationId}/messages?${queryParams.toString()}`
  );
};

export const getMessage = (messageId) => {
  if (!messageId) return Promise.reject(new Error("Message ID is required"));
  return api.get(`/api/messages/messages/${messageId}`);
};

export const sendMessage = (conversationId, messageData) => {
  if (!conversationId || !messageData?.content?.trim()) {
    return Promise.reject({
      response: {
        data: {
          detail: "Conversation ID and message content are required",
          code: "INVALID_MESSAGE",
        },
      },
    });
  }

  return api.post(
    `/api/messages/conversations/${conversationId}/messages`,
    messageData
  );
};

export const updateMessage = (messageId, content, messageType = "text") => {
  if (!messageId || !content?.trim()) {
    return Promise.reject({
      response: {
        data: {
          detail: "Message ID and content are required",
          code: "INVALID_MESSAGE",
        },
      },
    });
  }

  return api.put(`/api/messages/messages/${messageId}`, {
    content: content.trim(),
    message_type: messageType,
  });
};

export const deleteMessage = (messageId) => {
  if (!messageId) return Promise.reject(new Error("Message ID is required"));
  return api.delete(`/api/messages/messages/${messageId}`);
};

export const addReaction = (messageId, reactionType) => {
  if (!messageId || !reactionType) {
    return Promise.reject(
      new Error("Message ID and reaction type are required")
    );
  }
  return api.post(`/api/messages/messages/${messageId}/react`, {
    reaction_type: reactionType,
  });
};

// Block/Unblock Users
export const blockUser = async (blockedId, reason = "") => {
  const response = await api.post("/api/blocks/", {
    blocked_id: blockedId,
    reason: reason,
  });
  return response.data;
};

export const unblockUser = async (blockedId) => {
  if (!blockedId) {
    throw new Error("Blocked user ID is required");
  }

  const response = await api.post("/api/blocks/unblock", {
    blocked_user_id: blockedId,
  });
  return response.data;
};

export const getBlockedUsers = () => api.get("/api/blocks/");
export const getBlocks = () => api.get("/api/blocks/");

export const sendFile = (formData) => {
  if (!formData) return Promise.reject(new Error("Form data is required"));
  return api.post("/api/messages/send-file", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000, // Longer timeout for file uploads
  });
};

export const sendMultiMessage = (formData) => {
  if (!formData) return Promise.reject(new Error("Form data is required"));
  return api.post("/api/messages/send-multi", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000, // Longer timeout for file uploads
  });
};

// File Upload API methods
export const uploadFile = (file, onUploadProgress = null) => {
  if (!file) return Promise.reject(new Error("File is required"));

  const formData = new FormData();
  formData.append("file", file);

  return api.post("/api/files/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 300000, // 5 minutes timeout for large file uploads
    onUploadProgress: onUploadProgress
      ? (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onUploadProgress(percentCompleted, progressEvent);
        }
      : undefined,
  });
};

export const uploadBatchFiles = (files, onUploadProgress = null) => {
  if (!files || files.length === 0)
    return Promise.reject(new Error("Files are required"));
  if (files.length > 10)
    return Promise.reject(new Error("Maximum 10 files allowed per batch"));

  const formData = new FormData();
  files.forEach((file) => {
    formData.append("files", file);
  });

  return api.post("/api/files/upload-batch", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 600000, // 10 minutes timeout for batch uploads
    onUploadProgress: onUploadProgress
      ? (progressEvent) => {
          const percentCompleted = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onUploadProgress(percentCompleted, progressEvent);
        }
      : undefined,
  });
};

export const getUserFiles = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.page) queryParams.append("page", params.page);
  if (params.per_page) queryParams.append("per_page", params.per_page);

  return api.get(`/api/files/?${queryParams.toString()}`);
};

export const getFile = (fileId) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.get(`/api/files/${fileId}`);
};

export const getFileDetails = (fileId) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.get(`/api/files/${fileId}`);
};

export const updateFile = (fileId, fileData) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.put(`/api/files/${fileId}`, fileData);
};

export const deleteFile = (fileId) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.delete(`/api/files/${fileId}`);
};

export const getFilePreviews = (fileId) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.get(`/api/files/${fileId}/previews`);
};

export const getOrGenerateFilePreview = (fileId, maxRows = 50) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.get(`/api/files/${fileId}/preview?max_rows=${maxRows}`);
};

export const generateFilePreview = (fileId, previewRequest) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.post(`/api/files/${fileId}/preview`, previewRequest);
};

export const getFileStatus = (fileId) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.get(`/api/files/${fileId}/status`);
};

export const downloadFile = (fileId) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.get(`/api/files/${fileId}/download`, {
    responseType: "blob",
  });
};

export const processFile = (fileId) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.post(`/api/files/${fileId}/process`);
};

export const cancelProcessing = (fileId) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.post(`/api/files/${fileId}/cancel-processing`);
};

export const getFileStats = () => api.get("/api/files/stats/summary");

export const getAvailableFileTypes = () => api.get("/api/files/types/available");

export const updateFileClassification = (fileId, manualKpiType) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  if (!manualKpiType) return Promise.reject(new Error("Manual KPI type is required"));
  return api.patch(`/api/files/${fileId}/classification?manual_kpi_type=${encodeURIComponent(manualKpiType)}`);
};

// Admin endpoints
export const getAllFiles = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.skip) queryParams.append("skip", params.skip);
  if (params.limit) queryParams.append("limit", params.limit);

  return api.get(`/api/files/admin/all?${queryParams.toString()}`);
};

export const adminDeleteFile = (fileId) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.delete(`/api/files/admin/${fileId}`);
};

// Health and general API methods
export const healthCheck = () => api.get("/health");
export const detailedHealthCheck = () => api.get("/api/health/detailed");

// Encaissement API methods (DEPRECATED - Use parkAnalyticsAPI instead)
export const uploadEncaissementData = (file) => {
  if (!file) return Promise.reject(new Error("File is required"));

  const formData = new FormData();
  formData.append("file", file);

  return api.post("/api/encaissement/upload-data", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000, // Longer timeout for file uploads
  });
};

export const getEncaissementOverview = () =>
  api.get("/api/encaissement/overview");
export const getEncaissementByOrganisation = () =>
  api.get("/api/encaissement/by-organisation");
export const getEncaissementByDate = () => api.get("/api/encaissement/by-date");
export const getEncaissementByEncaisseRate = () =>
  api.get("/api/encaissement/by-encaisse-rate");

export const getEncaissementChartData = (chartType) => {
  if (!chartType) return Promise.reject(new Error("Chart type is required"));
  return api.get(
    `/api/encaissement/chart-data?chart_type=${encodeURIComponent(chartType)}`
  );
};

// Park Analytics API methods - Real data from Parc Corporate NGBSS
export const getParkAnalyticsOverview = (filters = {}) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value && value.trim() !== "") {
      params.append(key, value);
    }
  });
  const queryString = params.toString();
  return api.get(
    `/api/park-analytics/overview${queryString ? `?${queryString}` : ""}`
  );
};

export const getParkAnalyticsByTelecomType = (filters = {}) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value && value.trim() !== "") {
      params.append(key, value);
    }
  });
  const queryString = params.toString();
  return api.get(
    `/api/park-analytics/by-telecom-type${queryString ? `?${queryString}` : ""}`
  );
};

export const getParkAnalyticsBySubscriberStatus = (filters = {}) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value && value.trim() !== "") {
      params.append(key, value);
    }
  });
  const queryString = params.toString();
  return api.get(
    `/api/park-analytics/by-subscriber-status${
      queryString ? `?${queryString}` : ""
    }`
  );
};

export const getParkAnalyticsByCustomerL2 = (filters = {}) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value && value.trim() !== "") {
      params.append(key, value);
    }
  });
  const queryString = params.toString();
  return api.get(
    `/api/park-analytics/by-customer-l2${queryString ? `?${queryString}` : ""}`
  );
};

export const getParkAnalyticsByCustomerL3 = (filters = {}) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value && value.trim() !== "") {
      params.append(key, value);
    }
  });
  const queryString = params.toString();
  return api.get(
    `/api/park-analytics/by-customer-l3${queryString ? `?${queryString}` : ""}`
  );
};

export const getParkAnalyticsByDOT = (filters = {}) => {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value && value.trim() !== "") {
      params.append(key, value);
    }
  });
  const queryString = params.toString();
  return api.get(
    `/api/park-analytics/by-dot${queryString ? `?${queryString}` : ""}`
  );
};

export const getParkAnalyticsAvailableFilters = () =>
  api.get("/api/park-analytics/filters");

export const exportParkAnalyticsData = (filters = {}, format = "csv") => {
  const params = new URLSearchParams({
    format,
    ...filters,
  });

  return api.get(`/api/park-analytics/export?${params.toString()}`);
};

// Revenue Analytics API methods
export const getRevenueOverview = (params = {}) => {
  const query = new URLSearchParams();
  if (params.org_name) {
    (Array.isArray(params.org_name)
      ? params.org_name
      : [params.org_name]
    ).forEach((v) => query.append("org_name", v));
  }
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  const qs = query.toString();
  return api.get(`/api/revenue/overview${qs ? `?${qs}` : ""}`);
};

export const listRevenueJournals = (params = {}) => {
  const query = new URLSearchParams();
  if (params.page) query.append("page", params.page);
  if (params.page_size) query.append("page_size", params.page_size);
  if (params.org_name) {
    (Array.isArray(params.org_name)
      ? params.org_name
      : [params.org_name]
    ).forEach((v) => query.append("org_name", v));
  }
  if (params.cpt_comptable) query.append("cpt_comptable", params.cpt_comptable);
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  if (params.search) query.append("search", params.search);
  return api.get(`/api/revenue/list?${query.toString()}`);
};

export const getRevenueByOrg = (params = {}) => {
  const query = new URLSearchParams();
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  return api.get(
    `/api/revenue/by-org${query.toString() ? `?${query.toString()}` : ""}`
  );
};

export const getRevenueByAccount = (params = {}) => {
  const query = new URLSearchParams();
  if (params.org_name) {
    (Array.isArray(params.org_name)
      ? params.org_name
      : [params.org_name]
    ).forEach((v) => query.append("org_name", v));
  }
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  return api.get(
    `/api/revenue/by-account${query.toString() ? `?${query.toString()}` : ""}`
  );
};

export const exportRevenueData = (params = {}) => {
  const query = new URLSearchParams();
  if (params.org_name) {
    (Array.isArray(params.org_name)
      ? params.org_name
      : [params.org_name]
    ).forEach((v) => query.append("org_name", v));
  }
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  query.append("format", params.format || "xlsx");
  return api.get(`/api/revenue/export?${query.toString()}`, {
    responseType: params.format === "csv" ? undefined : "blob",
  });
};

// ETL Processing API methods
export const processParcCorporateNGBSS = (formData) => {
  if (!formData) return Promise.reject(new Error("Form data is required"));
  return api.post("/api/etl/parc-corporate-ngbss/process", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 300000, // 5 minutes for ETL processing
  });
};

export const getParcCorporateDataViews = (
  filePath,
  viewType = "overview",
  filters = {}
) => {
  if (!filePath) return Promise.reject(new Error("File path is required"));

  const params = new URLSearchParams();
  params.append("view_type", viewType);

  // Add filters
  if (filters.dot && filters.dot !== "all") {
    params.append("dot_filter", filters.dot);
  }
  if (filters.actel && filters.actel !== "all") {
    params.append("actel_filter", filters.actel);
  }
  if (filters.subscriber && filters.subscriber !== "all") {
    params.append("subscriber_filter", filters.subscriber);
  }

  // Encode file path for URL
  const encodedPath = encodeURIComponent(filePath);

  return api.get(
    `/api/etl/parc-corporate-ngbss/views/${encodedPath}?${params.toString()}`
  );
};

export const processEncaissementETL = (formData) => {
  if (!formData) return Promise.reject(new Error("Form data is required"));
  return api.post("/api/etl/encaissement/process", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 300000, // 5 minutes for ETL processing
  });
};

export const processSubscriberParkETL = (formData) => {
  if (!formData) return Promise.reject(new Error("Form data is required"));
  return api.post("/api/etl/subscriber-park/process", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 300000, // 5 minutes for ETL processing
  });
};

export const validateETLFiles = (formData) => {
  if (!formData) return Promise.reject(new Error("Form data is required"));
  return api.post("/api/etl/validate-etl-files", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000, // 1 minute for validation
  });
};

export const downloadETLResult = (filePath) => {
  if (!filePath) return Promise.reject(new Error("File path is required"));
  const encodedPath = encodeURIComponent(filePath);
  return api.get(`/api/etl/encaissement/results/${encodedPath}`, {
    responseType: "blob",
  });
};

export const getETLHistory = (limit = 50) => {
  return api.get(`/api/etl/encaissement/history?limit=${limit}`);
};

// Park Data API methods
export const getParkDataSavedData = (params = {}) => {
  const queryParams = new URLSearchParams();

  if (params.page) queryParams.append("page", params.page);
  if (params.pageSize) queryParams.append("page_size", params.pageSize);
  if (params.search) queryParams.append("search", params.search);
  if (params.subscriberStatus)
    queryParams.append("subscriber_status", params.subscriberStatus);
  if (params.telecomType)
    queryParams.append("telecom_type", params.telecomType);
  if (params.offerType) queryParams.append("offer_type", params.offerType);

  const queryString = queryParams.toString();
  return api.get(`/api/parks/data${queryString ? `?${queryString}` : ""}`);
};

export const getParkDataStats = () => {
  return api.get("/api/parks/data/stats");
};

// ============================================================================
// Encaissement AR DOT API Methods (COMPLETE - 17 endpoints)
// ============================================================================

export const getEncaissementRecords = (params = {}) => {
  const query = new URLSearchParams();
  if (params.page) query.append("page", params.page);
  if (params.page_size) query.append("page_size", params.page_size);
  if (params.organisation) query.append("organisation", params.organisation);
  if (params.mois) query.append("mois", params.mois);
  if (params.n_fact) query.append("n_fact", params.n_fact);
  if (params.typ_fact) query.append("typ_fact", params.typ_fact);
  if (params.date_fact_from) query.append("date_fact_from", params.date_fact_from);
  if (params.date_fact_to) query.append("date_fact_to", params.date_fact_to);
  if (params.is_duplicate !== undefined) query.append("is_duplicate", params.is_duplicate);
  if (params.is_anomaly !== undefined) query.append("is_anomaly", params.is_anomaly);
  if (params.file_upload_id) query.append("file_upload_id", params.file_upload_id);
  if (params.sort_by) query.append("sort_by", params.sort_by);
  if (params.sort_order) query.append("sort_order", params.sort_order);
  return api.get(`/api/encaissement/records?${query.toString()}`);
};

export const getEncaissementRecordById = (recordId) => {
  if (!recordId) return Promise.reject(new Error("Record ID is required"));
  return api.get(`/api/encaissement/records/${recordId}`);
};

export const getEncaissementDashboardOverview = () =>
  api.get("/api/encaissement/dashboard/overview");

export const getEncaissementMonthlyAggregates = (year) => {
  const params = year ? `?year=${year}` : '';
  return api.get(`/api/encaissement/dashboard/monthly-aggregates${params}`);
};

export const getEncaissementMonthlyDistribution = (year) => {
  const params = year ? `?year=${year}` : '';
  return api.get(`/api/encaissement/dashboard/monthly-distribution${params}`);
};

export const getEncaissementDotAggregates = () =>
  api.get("/api/encaissement/dashboard/dot-aggregates");

export const getEncaissementAnomalies = (params = {}) => {
  const query = new URLSearchParams();
  if (params.page) query.append("page", params.page);
  if (params.page_size) query.append("page_size", params.page_size);
  if (params.organisation) query.append("organisation", params.organisation);
  if (params.anomaly_type) query.append("anomaly_type", params.anomaly_type);
  if (params.file_upload_id) query.append("file_upload_id", params.file_upload_id);
  return api.get(`/api/encaissement/anomalies?${query.toString()}`);
};

export const getEncaissementAnomalyStatistics = () =>
  api.get("/api/encaissement/anomalies/statistics");

export const getEncaissementStatisticsByOrganisation = (organisation) => {
  const params = organisation ? `?organisation=${encodeURIComponent(organisation)}` : '';
  return api.get(`/api/encaissement/statistics/by-organisation${params}`);
};

export const getEncaissementAvailableMonths = () =>
  api.get("/api/encaissement/metadata/available-months");

export const getEncaissementAvailableOrganisations = () =>
  api.get("/api/encaissement/metadata/available-organisations");

export const exportEncaissementRecords = (params = {}) => {
  const query = new URLSearchParams();
  if (params.organisation) query.append("organisation", params.organisation);
  if (params.mois) query.append("mois", params.mois);
  if (params.date_fact_from) query.append("date_fact_from", params.date_fact_from);
  if (params.date_fact_to) query.append("date_fact_to", params.date_fact_to);
  if (params.include_duplicates !== undefined) query.append("include_duplicates", params.include_duplicates);
  if (params.include_anomalies !== undefined) query.append("include_anomalies", params.include_anomalies);
  query.append("format", params.format || "json");
  return api.get(`/api/encaissement/export?${query.toString()}`, {
    responseType: params.format === "csv" ? "blob" : undefined,
  });
};

export const getEncaissementDuplicateGroups = (compositeKey) => {
  const params = compositeKey ? `?composite_key=${encodeURIComponent(compositeKey)}` : '';
  return api.get(`/api/encaissement/duplicates/groups${params}`);
};

// ============================================================================
// Créance Périodique DOT API Methods (COMPLETE - 17 endpoints)
// ============================================================================

export const getCreanceRecords = (params = {}) => {
  const query = new URLSearchParams();
  if (params.page) query.append("page", params.page);
  if (params.page_size) query.append("page_size", params.page_size);
  if (params.dot) query.append("dot", params.dot);
  if (params.actel) query.append("actel", params.actel);
  if (params.annee) query.append("annee", params.annee);
  if (params.mois) query.append("mois", params.mois);
  if (params.period_key) query.append("period_key", params.period_key);
  if (params.produit) query.append("produit", params.produit);
  if (params.cust_lev1) query.append("cust_lev1", params.cust_lev1);
  if (params.cust_lev2) query.append("cust_lev2", params.cust_lev2);
  if (params.cust_lev3) query.append("cust_lev3", params.cust_lev3);
  if (params.file_upload_id) query.append("file_upload_id", params.file_upload_id);
  if (params.sort_by) query.append("sort_by", params.sort_by);
  if (params.sort_order) query.append("sort_order", params.sort_order);
  return api.get(`/api/creance/records?${query.toString()}`);
};

export const getCreanceRecordById = (recordId) => {
  if (!recordId) return Promise.reject(new Error("Record ID is required"));
  return api.get(`/api/creance/records/${recordId}`);
};

export const getCreanceDashboardOverview = () =>
  api.get("/api/creance/dashboard/overview");

export const getCreanceByDotAggregates = () =>
  api.get("/api/creance/dashboard/by-dot");

export const getCreanceByAnneeAggregates = () =>
  api.get("/api/creance/dashboard/by-annee");

export const getCreanceByProduitAggregates = () =>
  api.get("/api/creance/dashboard/by-produit");

export const getCreanceByCustLev2Aggregates = () =>
  api.get("/api/creance/dashboard/by-cust-lev2");

export const getCreanceStatisticsByDot = (dot) => {
  const params = dot ? `?dot=${encodeURIComponent(dot)}` : '';
  return api.get(`/api/creance/statistics/by-dot${params}`);
};

export const getCreanceAvailablePeriods = () =>
  api.get("/api/creance/metadata/available-periods");

export const getCreanceAvailableYears = () =>
  api.get("/api/creance/metadata/available-years");

export const getCreanceAvailableDots = () =>
  api.get("/api/creance/metadata/available-dots");

export const getCreanceAvailableProducts = () =>
  api.get("/api/creance/metadata/available-products");

export const getCreanceAvailableCustLev2 = () =>
  api.get("/api/creance/metadata/available-cust-lev2");

export const exportCreanceRecords = (params = {}) => {
  const query = new URLSearchParams();
  if (params.dot) query.append("dot", params.dot);
  if (params.annee) query.append("annee", params.annee);
  if (params.period_key) query.append("period_key", params.period_key);
  if (params.produit) query.append("produit", params.produit);
  if (params.cust_lev2) query.append("cust_lev2", params.cust_lev2);
  query.append("format", params.format || "json");
  return api.get(`/api/creance/export?${query.toString()}`, {
    responseType: params.format === "csv" ? "blob" : undefined,
  });
};

// WebSocket Service
class WebSocketService {
  constructor() {
    this.connections = new Map();
    this.subscribers = new Map();
    this.reconnectTimers = new Map();
    this.isManuallyClosed = new Map();
    this.reconnectAttempts = new Map(); // connectionId -> number of attempts
    this.maxReconnectAttempts = 10; // Maximum reconnection attempts
    this.baseReconnectDelay = 1000; // Base delay in milliseconds
    this.maxReconnectDelay = 30000; // Maximum delay in milliseconds
    this.healthCheckInterval = 30000; // Health check every 30 seconds
    this.healthCheckTimers = new Map(); // connectionId -> setInterval ID
  }

  // Get authentication token
  getToken() {
    return sessionStorage.getItem("token") || localStorage.getItem("token");
  }

  // Get user from storage
  getUser() {
    const userStr =
      sessionStorage.getItem("user") || localStorage.getItem("user");
    return userStr ? JSON.parse(userStr) : null;
  }

  // Create WebSocket connection
  connect(endpoint, options = {}) {
    const user = this.getUser();
    const token = this.getToken();

    if (!user || !token) {
      console.error("No user or token available for WebSocket connection");
      return null;
    }

    const connectionId = `${endpoint}_${user.id}`;

    // Return existing connection if available
    if (this.connections.has(connectionId)) {
      const ws = this.connections.get(connectionId);
      if (
        ws.readyState === WebSocket.OPEN ||
        ws.readyState === WebSocket.CONNECTING
      ) {
        return ws;
      }
    }

    // Build WebSocket URL with authentication
    const baseUrl = WS_BASE_URL;
    let wsUrl = `${baseUrl}${endpoint}`;

    // Add query parameters
    const params = new URLSearchParams();
    if (options.userId !== false) {
      params.append("user_id", user.id);
    }
    if (options.token !== false) {
      params.append("token", token);
    }

    // Add custom parameters
    Object.entries(options.params || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        params.append(key, value);
      }
    });

    if (params.toString()) {
      wsUrl += `?${params.toString()}`;
    }

    console.log(`🔌 Creating WebSocket connection: ${wsUrl}`);

    const ws = new WebSocket(wsUrl);
    this.connections.set(connectionId, ws);
    this.isManuallyClosed.set(connectionId, false);

    // Set up event handlers
    ws.onopen = () => {
      console.log(`✅ WebSocket connected: ${endpoint}`);
      // Reset reconnection attempts on successful connection
      this.reconnectAttempts.set(connectionId, 0);
      // Clear any existing reconnect timer
      const existingTimer = this.reconnectTimers.get(connectionId);
      if (existingTimer) {
        clearTimeout(existingTimer);
        this.reconnectTimers.delete(connectionId);
      }
      // Start health check monitoring
      this.startHealthCheck(connectionId, endpoint, options);
      if (options.onOpen) options.onOpen(ws);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        if (options.onMessage) options.onMessage(message, ws);

        // Notify subscribers
        this.notifySubscribers(connectionId, message);
      } catch (error) {
        console.error(
          `Error parsing WebSocket message for ${endpoint}:`,
          error
        );
      }
    };

    ws.onclose = (event) => {
      console.log(
        `🔌 WebSocket closed: ${endpoint} - ${event.code} ${event.reason}`
      );
      this.connections.delete(connectionId);

      if (options.onClose) options.onClose(event, ws);

      // Stop health check monitoring
      this.stopHealthCheck(connectionId);

      // Check if this is an auth error (401/403 or specific codes)
      if (event.code === 4001 || event.code === 4003 || event.code === 403) {
        console.warn(`🔐 Authentication failed for WebSocket: ${endpoint}`);
        console.warn(
          `💡 Token may be invalid. Please log out and log back in.`
        );

        // Don't try to reconnect with invalid token
        return;
      }

      // Auto-reconnect if not manually closed
      // Always attempt reconnection unless manually closed or auth error
      if (
        !this.isManuallyClosed.get(connectionId) &&
        options.autoReconnect !== false
      ) {
        console.log(
          `🔄 Connection lost for ${endpoint}, scheduling reconnection...`
        );
        this.scheduleReconnect(connectionId, endpoint, options);
      } else if (this.isManuallyClosed.get(connectionId)) {
        console.log(
          `🔕 Connection manually closed for ${endpoint}, not reconnecting`
        );
      }
    };

    ws.onerror = (error) => {
      console.error(`❌ WebSocket error: ${endpoint}`, error);
      if (options.onError) options.onError(error, ws);
    };

    return ws;
  }

  // Subscribe to messages for a specific connection
  subscribe(connectionId, handler) {
    if (!this.subscribers.has(connectionId)) {
      this.subscribers.set(connectionId, new Set());
    }
    this.subscribers.get(connectionId).add(handler);

    return () => {
      const subscribers = this.subscribers.get(connectionId);
      if (subscribers) {
        subscribers.delete(handler);
        if (subscribers.size === 0) {
          this.subscribers.delete(connectionId);
        }
      }
    };
  }

  // Notify all subscribers for a connection
  notifySubscribers(connectionId, message) {
    const subscribers = this.subscribers.get(connectionId);
    if (subscribers) {
      subscribers.forEach((handler) => {
        try {
          handler(message);
        } catch (error) {
          console.error("Error in WebSocket subscriber:", error);
        }
      });
    }
  }

  // Send message through WebSocket
  send(connectionId, message) {
    const ws = this.connections.get(connectionId);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
      return true;
    }
    return false;
  }

  // Close all connections
  closeAll() {
    this.connections.forEach((ws, connectionId) => {
      this.close(connectionId);
    });
  }

  // Get connection status
  isConnected(connectionId) {
    const ws = this.connections.get(connectionId);
    return ws && ws.readyState === WebSocket.OPEN;
  }

  // Get all connection statuses
  getAllConnectionStatuses() {
    const statuses = {};
    this.connections.forEach((ws, connectionId) => {
      statuses[connectionId] = {
        connected: ws.readyState === WebSocket.OPEN,
        state: ws.readyState,
        stateText: this.getWebSocketStateText(ws.readyState),
      };
    });
    return statuses;
  }

  // Get WebSocket state as text
  getWebSocketStateText(readyState) {
    switch (readyState) {
      case WebSocket.CONNECTING:
        return "connecting";
      case WebSocket.OPEN:
        return "connected";
      case WebSocket.CLOSING:
        return "closing";
      case WebSocket.CLOSED:
        return "disconnected";
      default:
        return "unknown";
    }
  }

  // Force reconnect a specific connection
  forceReconnect(connectionId) {
    const ws = this.connections.get(connectionId);
    if (ws) {
      console.log(`🔄 Force reconnecting: ${connectionId}`);
      this.close(connectionId);
      // The connection will be recreated on next use
    }
  }

  // Enhanced auto-reconnection with exponential backoff
  scheduleReconnect(connectionId, endpoint, options) {
    const attempts = this.reconnectAttempts.get(connectionId) || 0;

    if (attempts >= this.maxReconnectAttempts) {
      console.warn(`❌ Max reconnection attempts reached for ${endpoint}`);
      return;
    }

    // Calculate delay with exponential backoff
    const delay = Math.min(
      this.baseReconnectDelay * Math.pow(2, attempts),
      this.maxReconnectDelay
    );

    console.log(
      `🔄 Scheduling reconnection ${attempts + 1}/${
        this.maxReconnectAttempts
      } for ${endpoint} in ${delay}ms`
    );

    const timer = setTimeout(() => {
      console.log(
        `🔄 Attempting to reconnect WebSocket: ${endpoint} (attempt ${
          attempts + 1
        })`
      );
      this.reconnectAttempts.set(connectionId, attempts + 1);
      this.connect(endpoint, options);
    }, delay);

    this.reconnectTimers.set(connectionId, timer);
  }

  // Health check monitoring
  startHealthCheck(connectionId, endpoint, options) {
    // Clear any existing health check
    this.stopHealthCheck(connectionId);

    const timer = setInterval(() => {
      const ws = this.connections.get(connectionId);
      if (ws && ws.readyState === WebSocket.OPEN) {
        // Send ping to check connection health
        try {
          ws.send(JSON.stringify({ type: "ping" }));
        } catch (error) {
          console.warn(`Health check failed for ${endpoint}:`, error);
          // Trigger reconnection
          this.scheduleReconnect(connectionId, endpoint, options);
        }
      } else {
        console.warn(`Health check detected dead connection for ${endpoint}`);
        // Trigger reconnection
        this.scheduleReconnect(connectionId, endpoint, options);
      }
    }, this.healthCheckInterval);

    this.healthCheckTimers.set(connectionId, timer);
  }

  // Stop health check monitoring
  stopHealthCheck(connectionId) {
    const timer = this.healthCheckTimers.get(connectionId);
    if (timer) {
      clearInterval(timer);
      this.healthCheckTimers.delete(connectionId);
    }
  }

  // Enhanced close method
  close(connectionId) {
    this.isManuallyClosed.set(connectionId, true);

    // Clear reconnect timer
    const timer = this.reconnectTimers.get(connectionId);
    if (timer) {
      clearTimeout(timer);
      this.reconnectTimers.delete(connectionId);
    }

    // Stop health check
    this.stopHealthCheck(connectionId);

    // Close WebSocket
    const ws = this.connections.get(connectionId);
    if (ws) {
      ws.close();
      this.connections.delete(connectionId);
    }
  }

  // Reconnect all connections that need reconnection
  reconnectAllIfNeeded() {
    const user = this.getUser();
    const token = this.getToken();

    if (!user || !token) {
      console.log("No user or token available for reconnection");
      return;
    }

    // Check all connections and reconnect if needed
    for (const [connectionId, ws] of this.connections.entries()) {
      if (
        ws.readyState !== WebSocket.OPEN &&
        ws.readyState !== WebSocket.CONNECTING
      ) {
        console.log(`🔄 Reconnecting dead connection: ${connectionId}`);
        // Extract endpoint from connectionId
        const endpoint = connectionId.substring(
          0,
          connectionId.lastIndexOf("_")
        );
        const endpointPath = this.getEndpointPath(endpoint);
        if (endpointPath) {
          this.connect(endpointPath, { autoReconnect: true });
        }
      }
    }
  }

  // Get endpoint path from connection type
  getEndpointPath(endpoint) {
    const endpointMap = {
      processing: "/ws/processing/",
      notifications: "/ws/notifications/",
      chat: "/ws/chat/",
    };
    return endpointMap[endpoint];
  }
}

// Create singleton instance
const wsService = new WebSocketService();

// Global event listeners for automatic reconnection
if (typeof window !== "undefined") {
  // Reconnect on page visibility change (tab focus)
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      console.log("🔄 Page became visible, checking WebSocket connections...");
      wsService.reconnectAllIfNeeded();
    }
  });

  // Reconnect on window focus
  window.addEventListener("focus", () => {
    console.log("🔄 Window focused, checking WebSocket connections...");
    wsService.reconnectAllIfNeeded();
  });

  // Reconnect on online event
  window.addEventListener("online", () => {
    console.log(
      "🔄 Network came online, reconnecting WebSocket connections..."
    );
    wsService.reconnectAllIfNeeded();
  });
}

// WebSocket API methods
export const createProcessingWebSocket = (
  onMessage,
  onOpen,
  onClose,
  onError
) => {
  const user = wsService.getUser();
  if (!user) return null;

  const connectionId = `processing_${user.id}`;

  wsService.connect("/ws/processing/", {
    onMessage,
    onOpen,
    onClose,
    onError,
    autoReconnect: true,
    reconnectDelay: 1500,
  });

  return {
    connectionId,
    subscribe: (handler) => wsService.subscribe(connectionId, handler),
    send: (message) => wsService.send(connectionId, message),
    close: () => wsService.close(connectionId),
    isConnected: () => wsService.isConnected(connectionId),
    reconnect: () => wsService.forceReconnect(connectionId),
    getStatus: () => wsService.getAllConnectionStatuses()[connectionId],
  };
};

export const createNotificationsWebSocket = (
  onMessage,
  onOpen,
  onClose,
  onError
) => {
  const user = wsService.getUser();
  if (!user) return null;

  const connectionId = `notifications_${user.id}`;

  wsService.connect("/ws/notifications/", {
    params: { user_id: user.id },
    onMessage,
    onOpen,
    onClose,
    onError,
    autoReconnect: true,
    reconnectDelay: 1500,
  });

  return {
    connectionId,
    subscribe: (handler) => wsService.subscribe(connectionId, handler),
    send: (message) => wsService.send(connectionId, message),
    close: () => wsService.close(connectionId),
    isConnected: () => wsService.isConnected(connectionId),
    reconnect: () => wsService.forceReconnect(connectionId),
    getStatus: () => wsService.getAllConnectionStatuses()[connectionId],
  };
};

export const createChatWebSocket = (
  conversationId,
  onMessage,
  onOpen,
  onClose,
  onError
) => {
  const user = wsService.getUser();
  if (!user) return null;

  const connectionId = `chat_${user.id}_${conversationId}`;

  wsService.connect("/ws/chat/", {
    params: { conversation_id: conversationId },
    onMessage,
    onOpen,
    onClose,
    onError,
    autoReconnect: true,
    reconnectDelay: 1500,
  });

  return {
    connectionId,
    subscribe: (handler) => wsService.subscribe(connectionId, handler),
    send: (message) => wsService.send(connectionId, message),
    close: () => wsService.close(connectionId),
    isConnected: () => wsService.isConnected(connectionId),
    reconnect: () => wsService.forceReconnect(connectionId),
    getStatus: () => wsService.getAllConnectionStatuses()[connectionId],
  };
};

// Export API_BASE_URL for direct fetch usage
export { API_BASE_URL };

// Default export - the main axios instance
export default api;
