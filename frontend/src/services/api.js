import axios from "axios";
import { debug } from "../lib/debug.js";

const API_BASE_URL = "http://127.0.0.1:8000"; // FastAPI backend URL

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

// Authentication API for FastAPI backend
export const authAPI = {
  login: (credentials) => {
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
  },

  register: (userData) => {
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
  },

  logout: () => api.post("/api/auth/logout"),

  refreshToken: (refreshToken) =>
    api.post("/api/auth/refresh-token", { refresh_token: refreshToken }),

  updateProfile: (profileData) => api.put("/api/users/me", profileData),

  // changePassword: (passwordData) =>
  //   api.post("/api/auth/change-password", passwordData),

  protected: () => api.get("/api/auth/protected"),
};

// Users API for FastAPI backend
export const usersAPI = {
  getUsers: () => api.get("/api/users/"),
  getUser: (userId) => api.get(`/api/users/${userId}`),
  getCurrentUser: () => api.get("/api/users/me"),
  updateCurrentUser: (userData) => api.put("/api/users/me", userData),
  searchUsers: (query) =>
    api.get(`/api/users/search?q=${encodeURIComponent(query)}`),

  // User CRUD operations
  createUser: (userData) => api.post("/api/users/", userData),
  updateUser: (userId, userData) => api.put(`/api/users/${userId}`, userData),
  deleteUser: (userId) => api.delete(`/api/users/${userId}`),

  getRoles: () => api.get("/api/users/roles/"),
  getRole: (roleId) => api.get(`/api/users/roles/${roleId}`),
  createRole: (roleData) => api.post("/api/users/roles/", roleData),
  updateRole: (roleId, roleData) =>
    api.put(`/api/users/roles/${roleId}`, roleData),
  deleteRole: (roleId) => api.delete(`/api/users/roles/${roleId}`),

  getPermissions: () => api.get("/api/users/permissions/"),
  getPermission: (permissionId) =>
    api.get(`/api/users/permissions/${permissionId}`),
  createPermission: (permissionData) =>
    api.post("/api/users/permissions/", permissionData),
  updatePermission: (permissionId, permissionData) =>
    api.put(`/api/users/permissions/${permissionId}`, permissionData),
  deletePermission: (permissionId) =>
    api.delete(`/api/users/permissions/${permissionId}`),

  assignRole: (userData) => {
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
  },

  removeUserRole: (userId, roleId) =>
    api.delete(`/api/users/${userId}/roles/${roleId}`),

  checkRole: (roleName, userId) => {
    if (!roleName) return Promise.reject(new Error("Role name is required"));
    return api.get(
      `/api/users/check-role/${encodeURIComponent(roleName)}?user_id=${userId}`
    );
  },

  checkPermission: (codename, userId) => {
    if (!codename)
      return Promise.reject(new Error("Permission codename is required"));
    return api.get(
      `/api/users/check-permission/${encodeURIComponent(
        codename
      )}?user_id=${userId}`
    );
  },

  updateRolePermissions: (roleId, permissionIds) => {
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
  },

  getUserRoles: (userId) => api.get(`/api/users/${userId}/roles`),
  getRolePermissions: (roleId) =>
    api.get(`/api/users/roles/${roleId}/permissions`),
};

// Notifications API for FastAPI backend
export const notificationsAPI = {
  fetchNotifications: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.skip) queryParams.append("skip", params.skip);
    if (params.limit) queryParams.append("limit", params.limit);
    if (params.unread_only)
      queryParams.append("unread_only", params.unread_only);

    return api.get(`/api/notifications/?${queryParams.toString()}`);
  },

  getNotification: (notificationId) => {
    if (!notificationId)
      return Promise.reject(new Error("Notification ID is required"));
    return api.get(`/api/notifications/${notificationId}`);
  },

  createNotification: (notificationData) => {
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
  },

  updateNotification: (notificationId, notificationData) => {
    if (!notificationId)
      return Promise.reject(new Error("Notification ID is required"));
    return api.put(`/api/notifications/${notificationId}`, notificationData);
  },

  deleteNotification: (notificationId) => {
    if (!notificationId)
      return Promise.reject(new Error("Notification ID is required"));
    return api.delete(`/api/notifications/${notificationId}`);
  },

  markAsRead: (id) => {
    if (!id) return Promise.reject(new Error("Notification ID is required"));
    return api.put(`/api/notifications/${id}/read`);
  },

  markAllAsRead: () => api.put("/api/notifications/read-all"),

  updatePreferences: (prefs) =>
    api.put("/api/notifications/preferences", prefs),

  getStats: () => api.get("/api/notifications/stats"),

  getPreferences: () => api.get("/api/notifications/preferences"),
};

// Messaging API for FastAPI backend
export const messagingAPI = {
  fetchConversations: () => api.get("/api/conversations/"),

  getConversation: (conversationId) => {
    if (!conversationId)
      return Promise.reject(new Error("Conversation ID is required"));
    return api.get(`/api/conversations/${conversationId}`);
  },

  // Create Conversation
  createConversation: async (conversationData) => {
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
  },

  updateConversation: (conversationId, data) => {
    if (!conversationId)
      return Promise.reject(new Error("Conversation ID is required"));
    return api.put(`/api/conversations/${conversationId}`, data);
  },

  deleteConversation: (conversationId) => {
    if (!conversationId)
      return Promise.reject(new Error("Conversation ID is required"));
    return api.delete(`/api/conversations/${conversationId}`);
  },

  fetchMessages: (conversationId, params = {}) => {
    if (!conversationId)
      return Promise.reject(new Error("Conversation ID is required"));

    const queryParams = new URLSearchParams();
    if (params.skip) queryParams.append("skip", params.skip);
    if (params.limit) queryParams.append("limit", params.limit);

    return api.get(
      `/api/messages/conversations/${conversationId}/messages?${queryParams.toString()}`
    );
  },

  getMessage: (messageId) => {
    if (!messageId) return Promise.reject(new Error("Message ID is required"));
    return api.get(`/api/messages/messages/${messageId}`);
  },

  sendMessage: (conversationId, messageData) => {
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
  },

  updateMessage: (messageId, content, messageType = "text") => {
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
  },

  deleteMessage: (messageId) => {
    if (!messageId) return Promise.reject(new Error("Message ID is required"));
    return api.delete(`/api/messages/messages/${messageId}`);
  },

  addReaction: (messageId, reactionType) => {
    if (!messageId || !reactionType) {
      return Promise.reject(
        new Error("Message ID and reaction type are required")
      );
    }
    return api.post(`/api/messages/messages/${messageId}/react`, {
      reaction_type: reactionType,
    });
  },

  // Block/Unblock Users
  blockUser: async (blockedId, reason = "") => {
    const response = await api.post("/api/blocks/", {
      blocked_id: blockedId,
      reason: reason,
    });
    return response.data;
  },

  unblockUser: async (blockedId) => {
    if (!blockedId) {
      throw new Error("Blocked user ID is required");
    }

    const response = await api.post("/api/blocks/unblock", {
      blocked_user_id: blockedId,
    });
    return response.data;
  },

  getBlockedUsers: () => api.get("/api/blocks/"),
  getBlocks: () => api.get("/api/blocks/"),

  sendFile: (formData) => {
    if (!formData) return Promise.reject(new Error("Form data is required"));
    return api.post("/api/messages/send-file", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 60000, // Longer timeout for file uploads
    });
  },

  sendMultiMessage: (formData) => {
    if (!formData) return Promise.reject(new Error("Form data is required"));
    return api.post("/api/messages/send-multi", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 60000, // Longer timeout for file uploads
    });
  },
};

// File Upload API for FastAPI backend
export const filesAPI = {
  uploadFile: (file) => {
    if (!file) return Promise.reject(new Error("File is required"));

    const formData = new FormData();
    formData.append("file", file);

    return api.post("/api/files/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 60000, // Longer timeout for file uploads
    });
  },

  getUserFiles: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.page) queryParams.append("page", params.page);
    if (params.per_page) queryParams.append("per_page", params.per_page);

    return api.get(`/api/files/?${queryParams.toString()}`);
  },

  getFile: (fileId) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.get(`/api/files/${fileId}`);
  },

  getFileDetails: (fileId) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.get(`/api/files/${fileId}`);
  },

  updateFile: (fileId, fileData) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.put(`/api/files/${fileId}`, fileData);
  },

  deleteFile: (fileId) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.delete(`/api/files/${fileId}`);
  },

  getFilePreviews: (fileId) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.get(`/api/files/${fileId}/previews`);
  },

  generateFilePreview: (fileId, previewRequest) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.post(`/api/files/${fileId}/preview`, previewRequest);
  },

  getFileStatus: (fileId) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.get(`/api/files/${fileId}/status`);
  },

  downloadFile: (fileId) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.get(`/api/files/${fileId}/download`, {
      responseType: "blob",
    });
  },

  processFile: (fileId) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.post(`/api/files/${fileId}/process`);
  },

  cancelProcessing: (fileId) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.post(`/api/files/${fileId}/cancel-processing`);
  },

  getFileStats: () => api.get("/api/files/stats/summary"),

  // Admin endpoints
  getAllFiles: (params = {}) => {
    const queryParams = new URLSearchParams();
    if (params.skip) queryParams.append("skip", params.skip);
    if (params.limit) queryParams.append("limit", params.limit);

    return api.get(`/api/files/admin/all?${queryParams.toString()}`);
  },

  adminDeleteFile: (fileId) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.delete(`/api/files/admin/${fileId}`);
  },
};

// Health and general API for FastAPI backend
export const generalAPI = {
  healthCheck: () => api.get("/health"),
  detailedHealthCheck: () => api.get("/api/health/detailed"),
  protected: () => api.get("/api/auth/protected"),
};

// Encaissement API for FastAPI backend
export const encaissementAPI = {
  uploadData: (file) => {
    if (!file) return Promise.reject(new Error("File is required"));

    const formData = new FormData();
    formData.append("file", file);

    return api.post("/api/encaissement/upload-data", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 60000, // Longer timeout for file uploads
    });
  },

  getOverview: () => api.get("/api/encaissement/overview"),

  getByOrganisation: () => api.get("/api/encaissement/by-organisation"),

  getByDate: () => api.get("/api/encaissement/by-date"),

  getByEncaisseRate: () => api.get("/api/encaissement/by-encaisse-rate"),

  getChartData: (chartType) => {
    if (!chartType) return Promise.reject(new Error("Chart type is required"));
    return api.get(
      `/api/encaissement/chart-data?chart_type=${encodeURIComponent(chartType)}`
    );
  },
};

// ETL Processing API for FastAPI backend
export const etlAPI = {
  // Process Parc Corporate NGBSS files
  processParcCorporateNGBSS: (formData) => {
    if (!formData) return Promise.reject(new Error("Form data is required"));
    return api.post("/api/etl/parc-corporate-ngbss/process", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 300000, // 5 minutes for ETL processing
    });
  },

  // Get data views from processed Parc Corporate NGBSS file
  getParcCorporateDataViews: (
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
  },

  // Process other ETL types
  processEncaissementETL: (formData) => {
    if (!formData) return Promise.reject(new Error("Form data is required"));
    return api.post("/api/etl/encaissement/process", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 300000, // 5 minutes for ETL processing
    });
  },

  processSubscriberParkETL: (formData) => {
    if (!formData) return Promise.reject(new Error("Form data is required"));
    return api.post("/api/etl/subscriber-park/process", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 300000, // 5 minutes for ETL processing
    });
  },

  // Validate files before processing
  validateETLFiles: (formData) => {
    if (!formData) return Promise.reject(new Error("Form data is required"));
    return api.post("/api/etl/validate-etl-files", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 60000, // 1 minute for validation
    });
  },

  // Download ETL result files
  downloadETLResult: (filePath) => {
    if (!filePath) return Promise.reject(new Error("File path is required"));
    const encodedPath = encodeURIComponent(filePath);
    return api.get(`/api/etl/encaissement/results/${encodedPath}`, {
      responseType: "blob",
    });
  },

  // Get ETL processing history
  getETLHistory: (limit = 50) => {
    return api.get(`/api/etl/encaissement/history?limit=${limit}`);
  },

  // Park Data API
  parkData: {
    // Get saved park data with pagination and filtering
    getSavedData: (params = {}) => {
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
    },

    // Get park data statistics
    getStats: () => {
      return api.get("/api/parks/data/stats");
    },
  },
};

// Comprehensive API object that includes all sections
const comprehensiveAPI = {
  // Axios instance for direct calls
  ...api,

  // Include all API sections
  general: generalAPI,
  encaissement: encaissementAPI,
  etl: etlAPI,

  // Add individual methods for backward compatibility
  ...filesAPI,
};

export default comprehensiveAPI;
