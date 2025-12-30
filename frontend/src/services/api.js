import axios from "axios";
import { debug } from "../lib/debug.js";

// Use environment variable with fallback
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8001";
const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL ||
  API_BASE_URL.replace("http://", "ws://").replace("https://", "wss://");
const IS_DEV =
  import.meta.env.VITE_ENV === "development" || import.meta.env.DEV;

// Debug logging utility
const debugLog = (...args) => {
  if (IS_DEV && import.meta.env.VITE_ENABLE_DEBUG !== "false") {
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
    // Don't log binary blob data (Excel, CSV, images, etc.)
    const isBlob =
      response.data instanceof Blob ||
      (typeof response.data === "object" &&
        response.data !== null &&
        response.data.constructor &&
        response.data.constructor.name === "Blob");
    const responseType = response.config.responseType;
    const contentType = response.headers["content-type"] || "";
    const isBinary =
      isBlob ||
      responseType === "blob" ||
      contentType.includes("application/vnd.openxmlformats") ||
      contentType.includes("application/vnd.ms-excel") ||
      contentType.includes("application/octet-stream");

    if (isBinary) {
      debug.apiResponse(
        response.status,
        response.config.url,
        `[Binary data: ${contentType || "blob"}]`
      );
    } else {
      debug.apiResponse(response.status, response.config.url, response.data);
    }
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
  // Only include user_id if provided (backend uses JWT token, so this is optional)
  const url =
    userId != null
      ? `/api/users/check-permission/${encodeURIComponent(
          codename
        )}?user_id=${userId}`
      : `/api/users/check-permission/${encodeURIComponent(codename)}`;
  return api.get(url);
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

// Get Message with Reactions
export const getMessageWithReactions = (messageId) => {
  if (!messageId) return Promise.reject(new Error("Message ID is required"));
  return api.get(`/api/messages/messages/${messageId}/with-reactions`);
};

// Get all reactions for a message
export const getMessageReactions = (messageId) => {
  if (!messageId) return Promise.reject(new Error("Message ID is required"));
  return api.get(`/api/messages/messages/${messageId}/reactions`);
};

// Remove a specific reaction
export const removeReaction = (messageId, reactionId) => {
  if (!messageId || !reactionId) {
    return Promise.reject(new Error("Message ID and reaction ID are required"));
  }
  return api.delete(
    `/api/messages/messages/${messageId}/reactions/${reactionId}`
  );
};

// Download file from message
export const downloadMessageFile = (messageId) => {
  if (!messageId) return Promise.reject(new Error("Message ID is required"));
  return api.get(`/api/messages/messages/${messageId}/download-file`, {
    responseType: "blob",
  });
};

// Get file info from message
export const getMessageFileInfo = (messageId) => {
  if (!messageId) return Promise.reject(new Error("Message ID is required"));
  return api.get(`/api/messages/messages/${messageId}/file-info`);
};

// Broadcast message to all users
export const broadcastMessage = (broadcastData) => {
  if (!broadcastData || !broadcastData.content) {
    return Promise.reject(new Error("Broadcast data and content are required"));
  }
  return api.post("/api/admin/broadcast/messages/all-users", broadcastData);
};

// Secure Messaging endpoints
export const editMessage = (messageId, data) => {
  if (!messageId || !data) {
    return Promise.reject(new Error("Message ID and data are required"));
  }
  return api.put(`/api/secure-messaging/messages/${messageId}`, data);
};

export const getSecureConversationMessages = (conversationId, params = {}) => {
  if (!conversationId) {
    return Promise.reject(new Error("Conversation ID is required"));
  }
  return api.get(
    `/api/secure-messaging/conversations/${conversationId}/messages`,
    { params }
  );
};

export const getConversationParticipants = (conversationId) => {
  if (!conversationId) {
    return Promise.reject(new Error("Conversation ID is required"));
  }
  return api.get(
    `/api/secure-messaging/conversations/${conversationId}/participants`
  );
};

// WebSocket Conversation Subscribers
export const getConversationSubscribers = (conversationId) => {
  if (!conversationId) {
    return Promise.reject(new Error("Conversation ID is required"));
  }
  return api.get(`/ws/conversations/${conversationId}/subscribers`);
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

export const getAvailableFileTypes = () =>
  api.get("/api/files/types/available");

export const updateFileClassification = (fileId, manualKpiType) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  if (!manualKpiType)
    return Promise.reject(new Error("Manual KPI type is required"));
  return api.patch(
    `/api/files/${fileId}/classification?manual_kpi_type=${encodeURIComponent(
      manualKpiType
    )}`
  );
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

// Broadcast Analytics API methods (NEW)
export const getBroadcastAnalytics = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);
  return api.get(
    `/api/admin/broadcast/analytics/summary?${queryParams.toString()}`
  );
};

// Broadcast Files API methods (NEW)
export const getBroadcastFiles = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.skip) queryParams.append("skip", params.skip);
  if (params.limit) queryParams.append("limit", params.limit);
  return api.get(`/api/admin/broadcast/files?${queryParams.toString()}`);
};

export const uploadBroadcastFile = (formData) => {
  if (!formData) return Promise.reject(new Error("Form data is required"));
  return api.post("/api/admin/broadcast/files", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 60000,
  });
};

export const deleteBroadcastFile = (fileId) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.delete(`/api/admin/broadcast/files/${fileId}`);
};

export const downloadBroadcastFile = (fileId) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.get(`/api/admin/broadcast/files/${fileId}/download`, {
    responseType: "blob",
  });
};

// File Distribution API methods (NEW)
export const broadcastFileToAllUsers = (data) => {
  if (!data || !data.file_id) {
    return Promise.reject(new Error("File ID is required"));
  }
  return api.post("/api/admin/broadcast/files/all-users", data);
};

export const broadcastFileToDot = (dotId, data) => {
  if (!dotId) return Promise.reject(new Error("DOT ID is required"));
  if (!data || !data.file_id) {
    return Promise.reject(new Error("File ID is required"));
  }
  return api.post(`/api/admin/broadcast/files/dot/${dotId}`, data);
};

export const broadcastFileToUsers = (data) => {
  if (!data || !data.file_id || !data.user_ids) {
    return Promise.reject(new Error("File ID and user IDs are required"));
  }
  return api.post("/api/admin/broadcast/files/users", data);
};

// Secure Files Admin API methods (NEW)
export const getAllAdminFiles = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.skip) queryParams.append("skip", params.skip);
  if (params.limit) queryParams.append("limit", params.limit);
  if (params.security_level)
    queryParams.append("security_level", params.security_level);
  return api.get(`/api/secure-files/admin/all-files?${queryParams.toString()}`);
};

export const downloadAdminFile = (fileId) => {
  if (!fileId) return Promise.reject(new Error("File ID is required"));
  return api.get(`/api/secure-files/admin/all-files/${fileId}/download`, {
    responseType: "blob",
  });
};

// Helper function to get available DOTs
export const getAllDots = () => {
  return api.get("/api/parks/").catch(() => {
    // Fallback if parks endpoint not available
    return Promise.resolve({ data: [] });
  });
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

export const getEncaissementOverview = (filters = {}) => {
  const params = new URLSearchParams();
  if (
    filters.organisation &&
    Array.isArray(filters.organisation) &&
    filters.organisation.length > 0
  ) {
    filters.organisation.forEach((org) => params.append("organisation", org));
  }
  if (filters.date_fact_start)
    params.append("date_fact_start", filters.date_fact_start);
  if (filters.date_fact_end)
    params.append("date_fact_end", filters.date_fact_end);
  if (
    filters.taux_encaissement_min !== undefined &&
    filters.taux_encaissement_min !== ""
  ) {
    params.append("taux_encaissement_min", filters.taux_encaissement_min);
  }
  if (
    filters.taux_encaissement_max !== undefined &&
    filters.taux_encaissement_max !== ""
  ) {
    params.append("taux_encaissement_max", filters.taux_encaissement_max);
  }
  if (filters.search) params.append("search", filters.search);
  if (filters.year) params.append("year", filters.year);
  if (
    filters.typ_fact &&
    Array.isArray(filters.typ_fact) &&
    filters.typ_fact.length > 0
  ) {
    filters.typ_fact.forEach((typ) => params.append("typ_fact", typ));
  }
  if (filters.date_rglt_start)
    params.append("date_rglt_start", filters.date_rglt_start);
  if (filters.date_rglt_end)
    params.append("date_rglt_end", filters.date_rglt_end);
  const queryString = params.toString();
  return api.get(
    `/api/encaissement/overview${queryString ? `?${queryString}` : ""}`
  );
};

export const getEncaissementByOrganisation = (filters = {}) => {
  const params = new URLSearchParams();
  if (
    filters.organisation &&
    Array.isArray(filters.organisation) &&
    filters.organisation.length > 0
  ) {
    filters.organisation.forEach((org) => params.append("organisation", org));
  }
  if (filters.date_fact_start)
    params.append("date_fact_start", filters.date_fact_start);
  if (filters.date_fact_end)
    params.append("date_fact_end", filters.date_fact_end);
  if (
    filters.taux_encaissement_min !== undefined &&
    filters.taux_encaissement_min !== ""
  ) {
    params.append("taux_encaissement_min", filters.taux_encaissement_min);
  }
  if (
    filters.taux_encaissement_max !== undefined &&
    filters.taux_encaissement_max !== ""
  ) {
    params.append("taux_encaissement_max", filters.taux_encaissement_max);
  }
  if (filters.search) params.append("search", filters.search);
  if (filters.year) params.append("year", filters.year);
  if (filters.sort_by) params.append("sort_by", filters.sort_by);
  if (filters.order) params.append("order", filters.order);
  if (filters.limit) params.append("limit", filters.limit);
  if (
    filters.typ_fact &&
    Array.isArray(filters.typ_fact) &&
    filters.typ_fact.length > 0
  ) {
    filters.typ_fact.forEach((typ) => params.append("typ_fact", typ));
  }
  if (filters.date_rglt_start)
    params.append("date_rglt_start", filters.date_rglt_start);
  if (filters.date_rglt_end)
    params.append("date_rglt_end", filters.date_rglt_end);
  const queryString = params.toString();
  return api.get(
    `/api/encaissement/by-organisation${queryString ? `?${queryString}` : ""}`
  );
};

export const getEncaissementByDate = (filters = {}) => {
  const params = new URLSearchParams();
  if (
    filters.organisation &&
    Array.isArray(filters.organisation) &&
    filters.organisation.length > 0
  ) {
    filters.organisation.forEach((org) => params.append("organisation", org));
  }
  if (filters.date_fact_start)
    params.append("date_fact_start", filters.date_fact_start);
  if (filters.date_fact_end)
    params.append("date_fact_end", filters.date_fact_end);
  if (
    filters.taux_encaissement_min !== undefined &&
    filters.taux_encaissement_min !== ""
  ) {
    params.append("taux_encaissement_min", filters.taux_encaissement_min);
  }
  if (
    filters.taux_encaissement_max !== undefined &&
    filters.taux_encaissement_max !== ""
  ) {
    params.append("taux_encaissement_max", filters.taux_encaissement_max);
  }
  if (filters.search) params.append("search", filters.search);
  if (filters.year) params.append("year", filters.year);
  if (
    filters.typ_fact &&
    Array.isArray(filters.typ_fact) &&
    filters.typ_fact.length > 0
  ) {
    filters.typ_fact.forEach((typ) => params.append("typ_fact", typ));
  }
  if (filters.date_rglt_start)
    params.append("date_rglt_start", filters.date_rglt_start);
  if (filters.date_rglt_end)
    params.append("date_rglt_end", filters.date_rglt_end);
  const queryString = params.toString();
  return api.get(
    `/api/encaissement/by-date${queryString ? `?${queryString}` : ""}`
  );
};

export const getEncaissementByEncaisseRate = (filters = {}) => {
  const params = new URLSearchParams();
  if (
    filters.organisation &&
    Array.isArray(filters.organisation) &&
    filters.organisation.length > 0
  ) {
    filters.organisation.forEach((org) => params.append("organisation", org));
  }
  if (filters.date_fact_start)
    params.append("date_fact_start", filters.date_fact_start);
  if (filters.date_fact_end)
    params.append("date_fact_end", filters.date_fact_end);
  if (
    filters.taux_encaissement_min !== undefined &&
    filters.taux_encaissement_min !== ""
  ) {
    params.append("taux_encaissement_min", filters.taux_encaissement_min);
  }
  if (
    filters.taux_encaissement_max !== undefined &&
    filters.taux_encaissement_max !== ""
  ) {
    params.append("taux_encaissement_max", filters.taux_encaissement_max);
  }
  if (filters.search) params.append("search", filters.search);
  if (filters.year) params.append("year", filters.year);
  if (
    filters.typ_fact &&
    Array.isArray(filters.typ_fact) &&
    filters.typ_fact.length > 0
  ) {
    filters.typ_fact.forEach((typ) => params.append("typ_fact", typ));
  }
  if (filters.date_rglt_start)
    params.append("date_rglt_start", filters.date_rglt_start);
  if (filters.date_rglt_end)
    params.append("date_rglt_end", filters.date_rglt_end);
  const queryString = params.toString();
  return api.get(
    `/api/encaissement/by-encaisse-rate${queryString ? `?${queryString}` : ""}`
  );
};

export const getEncaissementByTypFact = (filters = {}) => {
  const params = new URLSearchParams();
  if (
    filters.organisation &&
    Array.isArray(filters.organisation) &&
    filters.organisation.length > 0
  ) {
    filters.organisation.forEach((org) => params.append("organisation", org));
  }
  if (filters.date_fact_start)
    params.append("date_fact_start", filters.date_fact_start);
  if (filters.date_fact_end)
    params.append("date_fact_end", filters.date_fact_end);
  if (
    filters.taux_encaissement_min !== undefined &&
    filters.taux_encaissement_min !== ""
  ) {
    params.append("taux_encaissement_min", filters.taux_encaissement_min);
  }
  if (
    filters.taux_encaissement_max !== undefined &&
    filters.taux_encaissement_max !== ""
  ) {
    params.append("taux_encaissement_max", filters.taux_encaissement_max);
  }
  if (filters.search) params.append("search", filters.search);
  if (filters.year) params.append("year", filters.year);
  if (
    filters.typ_fact &&
    Array.isArray(filters.typ_fact) &&
    filters.typ_fact.length > 0
  ) {
    filters.typ_fact.forEach((typ) => params.append("typ_fact", typ));
  }
  if (filters.date_rglt_start)
    params.append("date_rglt_start", filters.date_rglt_start);
  if (filters.date_rglt_end)
    params.append("date_rglt_end", filters.date_rglt_end);
  const queryString = params.toString();
  return api.get(
    `/api/encaissement/by-typ-fact${queryString ? `?${queryString}` : ""}`
  );
};

export const getEncaissementByDateRglt = (filters = {}) => {
  const params = new URLSearchParams();
  if (
    filters.organisation &&
    Array.isArray(filters.organisation) &&
    filters.organisation.length > 0
  ) {
    filters.organisation.forEach((org) => params.append("organisation", org));
  }
  if (filters.date_fact_start)
    params.append("date_fact_start", filters.date_fact_start);
  if (filters.date_fact_end)
    params.append("date_fact_end", filters.date_fact_end);
  if (
    filters.taux_encaissement_min !== undefined &&
    filters.taux_encaissement_min !== ""
  ) {
    params.append("taux_encaissement_min", filters.taux_encaissement_min);
  }
  if (
    filters.taux_encaissement_max !== undefined &&
    filters.taux_encaissement_max !== ""
  ) {
    params.append("taux_encaissement_max", filters.taux_encaissement_max);
  }
  if (filters.search) params.append("search", filters.search);
  if (filters.year) params.append("year", filters.year);
  if (
    filters.typ_fact &&
    Array.isArray(filters.typ_fact) &&
    filters.typ_fact.length > 0
  ) {
    filters.typ_fact.forEach((typ) => params.append("typ_fact", typ));
  }
  if (filters.date_rglt_start)
    params.append("date_rglt_start", filters.date_rglt_start);
  if (filters.date_rglt_end)
    params.append("date_rglt_end", filters.date_rglt_end);
  const queryString = params.toString();
  return api.get(
    `/api/encaissement/by-date-rglt${queryString ? `?${queryString}` : ""}`
  );
};

export const getEncaissementByTauxCreance = (filters = {}) => {
  const params = new URLSearchParams();
  if (
    filters.organisation &&
    Array.isArray(filters.organisation) &&
    filters.organisation.length > 0
  ) {
    filters.organisation.forEach((org) => params.append("organisation", org));
  }
  if (filters.date_fact_start)
    params.append("date_fact_start", filters.date_fact_start);
  if (filters.date_fact_end)
    params.append("date_fact_end", filters.date_fact_end);
  if (
    filters.taux_encaissement_min !== undefined &&
    filters.taux_encaissement_min !== ""
  ) {
    params.append("taux_encaissement_min", filters.taux_encaissement_min);
  }
  if (
    filters.taux_encaissement_max !== undefined &&
    filters.taux_encaissement_max !== ""
  ) {
    params.append("taux_encaissement_max", filters.taux_encaissement_max);
  }
  if (filters.search) params.append("search", filters.search);
  if (filters.year) params.append("year", filters.year);
  if (
    filters.typ_fact &&
    Array.isArray(filters.typ_fact) &&
    filters.typ_fact.length > 0
  ) {
    filters.typ_fact.forEach((typ) => params.append("typ_fact", typ));
  }
  if (filters.date_rglt_start)
    params.append("date_rglt_start", filters.date_rglt_start);
  if (filters.date_rglt_end)
    params.append("date_rglt_end", filters.date_rglt_end);
  const queryString = params.toString();
  return api.get(
    `/api/encaissement/by-taux-creance${queryString ? `?${queryString}` : ""}`
  );
};

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
    if (typeof value === "boolean") {
      params.append(key, value.toString());
    } else if (value && typeof value === "string" && value.trim() !== "") {
      params.append(key, value);
    } else if (value && typeof value !== "string") {
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
    if (typeof value === "boolean") {
      params.append(key, value.toString());
    } else if (value && typeof value === "string" && value.trim() !== "") {
      params.append(key, value);
    } else if (value && typeof value !== "string") {
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
    if (typeof value === "boolean") {
      params.append(key, value.toString());
    } else if (value && typeof value === "string" && value.trim() !== "") {
      params.append(key, value);
    } else if (value && typeof value !== "string") {
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
    if (typeof value === "boolean") {
      params.append(key, value.toString());
    } else if (value && typeof value === "string" && value.trim() !== "") {
      params.append(key, value);
    } else if (value && typeof value !== "string") {
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
    if (typeof value === "boolean") {
      params.append(key, value.toString());
    } else if (value && typeof value === "string" && value.trim() !== "") {
      params.append(key, value);
    } else if (value && typeof value !== "string") {
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
    if (typeof value === "boolean") {
      params.append(key, value.toString());
    } else if (value && typeof value === "string" && value.trim() !== "") {
      params.append(key, value);
    } else if (value && typeof value !== "string") {
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

export const getParkAnalyticsPreviewData = (
  filters = {},
  limit = 10,
  offset = 0
) => {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
    ...filters,
  });
  return api.get(`/api/park-analytics/preview-data?${params.toString()}`);
};

export const getParkAnalyticsColumnValues = (column, filters = {}) => {
  const params = new URLSearchParams({ column });
  // Add filter parameters if provided
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      if (Array.isArray(value) && value.length > 0) {
        params.append(key, value.join(","));
      } else if (typeof value === "string" && value.trim() !== "") {
        params.append(key, value);
      } else if (typeof value === "boolean") {
        params.append(key, value.toString());
      }
    }
  });
  return api.get(
    `/api/park-analytics/preview-data/column-values?${params.toString()}`
  );
};

export const exportParkAnalyticsData = (
  filters = {},
  exportType = "normal",
  onDownloadProgress = null
) => {
  // Extract format from filters if present, otherwise default to csv
  const format = filters.format || "csv";
  const { format: _, ...filterParams } = filters;

  const params = new URLSearchParams({
    format,
    export_type: exportType,
    ...filterParams,
  });

  const config = {
    responseType: "blob", // Important: tell axios we're expecting a blob
  };

  if (onDownloadProgress) {
    config.onDownloadProgress = onDownloadProgress;
  }

  return api.get(`/api/park-analytics/export?${params.toString()}`, config);
};

// Start async export with progress tracking
export const startParkAnalyticsExport = (
  filters = {},
  exportType = "normal"
) => {
  const format = filters.format || "csv";
  const { format: _, ...filterParams } = filters;

  const params = new URLSearchParams({
    format,
    export_type: exportType,
    ...filterParams,
  });

  return api.post(`/api/park-analytics/export-async?${params.toString()}`);
};

// Get export task status
export const getParkAnalyticsExportStatus = (taskId) => {
  return api.get(`/api/park-analytics/export-status/${taskId}`);
};

// Download completed export file
export const downloadParkAnalyticsExport = (taskId) => {
  return api.get(`/api/park-analytics/export-download/${taskId}`, {
    responseType: "blob",
  });
};

// Revenue Analytics API methods
export const getRevenueOverview = (params = {}) => {
  console.log(
    "🔍 [FRONTEND API] getRevenueOverview called with params:",
    params
  );
  console.log("🔍 [FRONTEND API] cpt_comptable in params:", {
    value: params.cpt_comptable,
    type: typeof params.cpt_comptable,
    isArray: Array.isArray(params.cpt_comptable),
    length: params.cpt_comptable?.length,
  });
  const query = new URLSearchParams();
  if (params.org_name) {
    (Array.isArray(params.org_name)
      ? params.org_name
      : [params.org_name]
    ).forEach((v) => query.append("org_name", v));
  }
  if (params.typ_fact) {
    (Array.isArray(params.typ_fact)
      ? params.typ_fact
      : [params.typ_fact]
    ).forEach((v) => query.append("typ_fact", v));
  }
  if (params.cpt_comptable) {
    console.log(
      "🔍 [FRONTEND API] Adding cpt_comptable to query:",
      params.cpt_comptable
    );
    (Array.isArray(params.cpt_comptable)
      ? params.cpt_comptable
      : [params.cpt_comptable]
    ).forEach((v) => {
      console.log("🔍 [FRONTEND API] Appending cpt_comptable value:", v);
      query.append("cpt_comptable", v);
    });
  }
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  if (params.start_date_fact)
    query.append("start_date_fact", params.start_date_fact);
  if (params.end_date_fact) query.append("end_date_fact", params.end_date_fact);
  if (params.taux_ca_min) query.append("taux_ca_min", params.taux_ca_min);
  if (params.taux_ca_max) query.append("taux_ca_max", params.taux_ca_max);
  if (params.search) query.append("search", params.search);
  const qs = query.toString();
  console.log("🔍 [FRONTEND API] Final query string for /overview:", qs);
  return api.get(`/api/revenue/overview${qs ? `?${qs}` : ""}`);
};

export const getDotCorporateMonthly = (params = {}) => {
  const query = new URLSearchParams();
  if (params.dot_names) {
    (Array.isArray(params.dot_names)
      ? params.dot_names
      : [params.dot_names]
    ).forEach((v) => query.append("dot_names", v));
  }
  if (params.org_name) {
    (Array.isArray(params.org_name)
      ? params.org_name
      : [params.org_name]
    ).forEach((v) => query.append("org_name", v));
  }
  if (params.typ_fact) {
    (Array.isArray(params.typ_fact)
      ? params.typ_fact
      : [params.typ_fact]
    ).forEach((v) => query.append("typ_fact", v));
  }
  if (params.cpt_comptable) {
    (Array.isArray(params.cpt_comptable)
      ? params.cpt_comptable
      : [params.cpt_comptable]
    ).forEach((v) => query.append("cpt_comptable", v));
  }
  if (params.year) query.append("year", params.year);
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  if (params.start_date_fact)
    query.append("start_date_fact", params.start_date_fact);
  if (params.end_date_fact) query.append("end_date_fact", params.end_date_fact);
  if (params.taux_ca_min !== undefined)
    query.append("taux_ca_min", params.taux_ca_min);
  if (params.taux_ca_max !== undefined)
    query.append("taux_ca_max", params.taux_ca_max);
  if (params.search) query.append("search", params.search);
  const qs = query.toString();
  return api.get(`/api/revenue/dot-corporate/monthly${qs ? `?${qs}` : ""}`);
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
  if (params.typ_fact) {
    (Array.isArray(params.typ_fact)
      ? params.typ_fact
      : [params.typ_fact]
    ).forEach((v) => query.append("typ_fact", v));
  }
  if (params.cpt_comptable) query.append("cpt_comptable", params.cpt_comptable);
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  if (params.start_date_fact)
    query.append("start_date_fact", params.start_date_fact);
  if (params.end_date_fact) query.append("end_date_fact", params.end_date_fact);
  if (params.taux_ca_min !== undefined)
    query.append("taux_ca_min", params.taux_ca_min);
  if (params.taux_ca_max !== undefined)
    query.append("taux_ca_max", params.taux_ca_max);
  if (params.search) query.append("search", params.search);
  return api.get(`/api/revenue/list?${query.toString()}`);
};

export const getRevenueByOrg = (params = {}) => {
  const query = new URLSearchParams();
  if (params.org_name) {
    (Array.isArray(params.org_name)
      ? params.org_name
      : [params.org_name]
    ).forEach((v) => query.append("org_name", v));
  }
  if (params.typ_fact) {
    (Array.isArray(params.typ_fact)
      ? params.typ_fact
      : [params.typ_fact]
    ).forEach((v) => query.append("typ_fact", v));
  }
  if (params.cpt_comptable) {
    (Array.isArray(params.cpt_comptable)
      ? params.cpt_comptable
      : [params.cpt_comptable]
    ).forEach((v) => query.append("cpt_comptable", v));
  }
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  if (params.start_date_fact)
    query.append("start_date_fact", params.start_date_fact);
  if (params.end_date_fact) query.append("end_date_fact", params.end_date_fact);
  if (params.taux_ca_min) query.append("taux_ca_min", params.taux_ca_min);
  if (params.taux_ca_max) query.append("taux_ca_max", params.taux_ca_max);
  if (params.search) query.append("search", params.search);
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
  if (params.typ_fact) {
    (Array.isArray(params.typ_fact)
      ? params.typ_fact
      : [params.typ_fact]
    ).forEach((v) => query.append("typ_fact", v));
  }
  if (params.cpt_comptable) {
    (Array.isArray(params.cpt_comptable)
      ? params.cpt_comptable
      : [params.cpt_comptable]
    ).forEach((v) => query.append("cpt_comptable", v));
  }
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  if (params.start_date_fact)
    query.append("start_date_fact", params.start_date_fact);
  if (params.end_date_fact) query.append("end_date_fact", params.end_date_fact);
  if (params.taux_ca_min) query.append("taux_ca_min", params.taux_ca_min);
  if (params.taux_ca_max) query.append("taux_ca_max", params.taux_ca_max);
  if (params.search) query.append("search", params.search);
  return api.get(
    `/api/revenue/by-account${query.toString() ? `?${query.toString()}` : ""}`
  );
};

export const getRevenueByTypeFact = (params = {}) => {
  const query = new URLSearchParams();
  if (params.org_name) {
    (Array.isArray(params.org_name)
      ? params.org_name
      : [params.org_name]
    ).forEach((v) => query.append("org_name", v));
  }
  if (params.typ_fact) {
    (Array.isArray(params.typ_fact)
      ? params.typ_fact
      : [params.typ_fact]
    ).forEach((v) => query.append("typ_fact", v));
  }
  if (params.cpt_comptable) {
    (Array.isArray(params.cpt_comptable)
      ? params.cpt_comptable
      : [params.cpt_comptable]
    ).forEach((v) => query.append("cpt_comptable", v));
  }
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  if (params.start_date_fact)
    query.append("start_date_fact", params.start_date_fact);
  if (params.end_date_fact) query.append("end_date_fact", params.end_date_fact);
  if (params.taux_ca_min) query.append("taux_ca_min", params.taux_ca_min);
  if (params.taux_ca_max) query.append("taux_ca_max", params.taux_ca_max);
  if (params.search) query.append("search", params.search);
  return api.get(
    `/api/revenue/by-type-fact${query.toString() ? `?${query.toString()}` : ""}`
  );
};

export const getRevenueByTauxCA = (params = {}) => {
  const query = new URLSearchParams();
  if (params.org_name) {
    (Array.isArray(params.org_name)
      ? params.org_name
      : [params.org_name]
    ).forEach((v) => query.append("org_name", v));
  }
  if (params.typ_fact) {
    (Array.isArray(params.typ_fact)
      ? params.typ_fact
      : [params.typ_fact]
    ).forEach((v) => query.append("typ_fact", v));
  }
  if (params.cpt_comptable) {
    (Array.isArray(params.cpt_comptable)
      ? params.cpt_comptable
      : [params.cpt_comptable]
    ).forEach((v) => query.append("cpt_comptable", v));
  }
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  if (params.start_date_fact)
    query.append("start_date_fact", params.start_date_fact);
  if (params.end_date_fact) query.append("end_date_fact", params.end_date_fact);
  if (params.taux_ca_min) query.append("taux_ca_min", params.taux_ca_min);
  if (params.taux_ca_max) query.append("taux_ca_max", params.taux_ca_max);
  if (params.search) query.append("search", params.search);
  return api.get(
    `/api/revenue/by-taux-ca${query.toString() ? `?${query.toString()}` : ""}`
  );
};

export const getRevenueByMonth = (params = {}) => {
  const query = new URLSearchParams();
  if (params.org_name) {
    (Array.isArray(params.org_name)
      ? params.org_name
      : [params.org_name]
    ).forEach((v) => query.append("org_name", v));
  }
  if (params.typ_fact) {
    (Array.isArray(params.typ_fact)
      ? params.typ_fact
      : [params.typ_fact]
    ).forEach((v) => query.append("typ_fact", v));
  }
  if (params.cpt_comptable) {
    (Array.isArray(params.cpt_comptable)
      ? params.cpt_comptable
      : [params.cpt_comptable]
    ).forEach((v) => query.append("cpt_comptable", v));
  }
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  if (params.start_date_fact)
    query.append("start_date_fact", params.start_date_fact);
  if (params.end_date_fact) query.append("end_date_fact", params.end_date_fact);
  if (params.taux_ca_min) query.append("taux_ca_min", params.taux_ca_min);
  if (params.taux_ca_max) query.append("taux_ca_max", params.taux_ca_max);
  if (params.search) query.append("search", params.search);
  return api.get(
    `/api/revenue/by-month${query.toString() ? `?${query.toString()}` : ""}`
  );
};

export const getRevenueFilters = async () => {
  // Return available filter options for revenue dashboard
  // Returns org_names, months, and achievement_rate_ranges
  try {
    const response = await api.get("/api/revenue/filters");
    return response;
  } catch (error) {
    console.error("Error fetching revenue filters:", error);
    // Fallback structure
    return {
      data: {
        org_names: [],
        months: [],
        achievement_rate_ranges: [
          { label: "0-25%", min: 0, max: 25 },
          { label: "25-50%", min: 25, max: 50 },
          { label: "50-75%", min: 50, max: 75 },
          { label: "75-100%", min: 75, max: 100 },
          { label: "100%+", min: 100, max: 999999 },
        ],
      },
    };
  }
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

// Start async revenue export
export const startRevenueExport = (filters = {}, exportType = "both") => {
  const format = filters.format || "xlsx";
  const { format: _, ...filterParams } = filters;

  // Build URLSearchParams, only including non-empty values
  const params = new URLSearchParams();
  params.append("format", format);
  params.append("export_type", exportType);

  // Only add filter params that have values
  // Handle arrays (for column filters) and single values
  Object.keys(filterParams).forEach((key) => {
    const value = filterParams[key];
    if (value !== undefined && value !== null && value !== "") {
      if (Array.isArray(value)) {
        // For arrays, append each value separately
        value.forEach((v) => {
          if (v !== undefined && v !== null && v !== "") {
            params.append(key, v);
          }
        });
      } else {
        params.append(key, value);
      }
    }
  });

  console.log(
    "🔍 [FRONTEND API] startRevenueExport - params:",
    params.toString()
  );
  return api.post(`/api/revenue/export-async?${params.toString()}`);
};

// Get revenue export task status
export const getRevenueExportStatus = (taskId) => {
  return api.get(`/api/revenue/export-status/${taskId}`);
};

// Download completed revenue export file
export const downloadRevenueExport = (taskId) => {
  return api.get(`/api/revenue/export-download/${taskId}`, {
    responseType: "blob",
  });
};

export const getRevenuePreviewData = (filters = {}, limit = 10, offset = 0) => {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  // Add all column filters - support ALL columns
  const allColumns = [
    "id",
    "file_upload_id",
    "dot_id",
    "org_name",
    "origine",
    "n_fact",
    "typ_fact",
    "n_client",
    "client",
    "delai_paie",
    "devise",
    "cpt_comptable",
    "periode_de_facturation",
    "creer_par",
    "uom",
    "tax",
    "n_ligne",
    "memo_line_id",
    "reference",
    "account_description_id",
    "revenue_objective_id",
  ];

  allColumns.forEach((col) => {
    if (filters[col]) {
      (Array.isArray(filters[col]) ? filters[col] : [filters[col]]).forEach(
        (v) => params.append(col, v)
      );
    }
  });

  // Date filters
  if (filters.start_date) params.append("start_date", filters.start_date);
  if (filters.end_date) params.append("end_date", filters.end_date);
  if (filters.start_date_fact)
    params.append("start_date_fact", filters.start_date_fact);
  if (filters.end_date_fact)
    params.append("end_date_fact", filters.end_date_fact);

  // Numeric range filters
  if (filters.taux_ca_min) params.append("taux_ca_min", filters.taux_ca_min);
  if (filters.taux_ca_max) params.append("taux_ca_max", filters.taux_ca_max);
  if (filters.chiffre_aff_exe_dzd_min)
    params.append("chiffre_aff_exe_dzd_min", filters.chiffre_aff_exe_dzd_min);
  if (filters.chiffre_aff_exe_dzd_max)
    params.append("chiffre_aff_exe_dzd_max", filters.chiffre_aff_exe_dzd_max);

  // Boolean filters - convert to string
  if (filters.termine_flag !== undefined) {
    const boolVal = Array.isArray(filters.termine_flag)
      ? filters.termine_flag
      : [filters.termine_flag];
    boolVal.forEach((v) => {
      if (v === "Oui" || v === true || v === "true")
        params.append("termine_flag", "true");
      else if (v === "Non" || v === false || v === "false")
        params.append("termine_flag", "false");
    });
  }
  if (filters.is_anomaly !== undefined) {
    const boolVal = Array.isArray(filters.is_anomaly)
      ? filters.is_anomaly
      : [filters.is_anomaly];
    boolVal.forEach((v) => {
      if (v === "Oui" || v === true || v === "true")
        params.append("is_anomaly", "true");
      else if (v === "Non" || v === false || v === "false")
        params.append("is_anomaly", "false");
    });
  }

  // Search
  if (filters.search) params.append("search", filters.search);

  // Ordering
  if (filters.order_by) params.append("order_by", filters.order_by);
  if (filters.order_direction)
    params.append("order_direction", filters.order_direction);

  return api.get(`/api/revenue/preview-data?${params.toString()}`);
};

export const getRevenueColumnValues = (column) => {
  return api.get(`/api/revenue/preview-data/column-values?column=${column}`);
};

export const getRevenueObjectivesPreview = (
  filters = {},
  limit = 10,
  offset = 0
) => {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  if (filters.dot_name) params.append("dot_name", filters.dot_name);

  return api.get(`/api/revenue/preview-objectives?${params.toString()}`);
};

export const getAccountDescriptionsPreview = (
  filters = {},
  limit = 10,
  offset = 0
) => {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });

  if (filters.search) params.append("search", filters.search);

  return api.get(
    `/api/revenue/preview-account-descriptions?${params.toString()}`
  );
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

// Revenue Objectives API methods
export const getRevenueObjectives = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.dot_name) queryParams.append("dot_name", params.dot_name);
  if (params.file_upload_id)
    queryParams.append("file_upload_id", params.file_upload_id);

  const queryString = queryParams.toString();
  return api.get(
    `/api/revenue/objectives${queryString ? `?${queryString}` : ""}`
  );
};

export const getRevenueObjective = (objectiveId) => {
  return api.get(`/api/revenue/objectives/${objectiveId}`);
};

// Account Descriptions API methods
export const getAccountDescriptions = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.cpt_comptable)
    queryParams.append("cpt_comptable", params.cpt_comptable);
  if (params.file_upload_id)
    queryParams.append("file_upload_id", params.file_upload_id);
  if (params.type_cpte) queryParams.append("type_cpte", params.type_cpte);

  const queryString = queryParams.toString();
  return api.get(
    `/api/revenue/account-descriptions${queryString ? `?${queryString}` : ""}`
  );
};

export const getAccountDescription = (accountId) => {
  return api.get(`/api/revenue/account-descriptions/${accountId}`);
};

// Revenue Journal API methods
export const getRevenueJournals = (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.org_name) queryParams.append("org_name", params.org_name);
  if (params.file_upload_id)
    queryParams.append("file_upload_id", params.file_upload_id);
  if (params.n_fact) queryParams.append("n_fact", params.n_fact);
  if (params.cpt_comptable)
    queryParams.append("cpt_comptable", params.cpt_comptable);
  if (params.start_date) queryParams.append("start_date", params.start_date);
  if (params.end_date) queryParams.append("end_date", params.end_date);
  if (params.page) queryParams.append("page", params.page);
  if (params.page_size) queryParams.append("page_size", params.page_size);

  const queryString = queryParams.toString();
  return api.get(`/api/revenue/journal${queryString ? `?${queryString}` : ""}`);
};

export const getRevenueJournal = (journalId) => {
  return api.get(`/api/revenue/journal/${journalId}`);
};

// Get available years from revenue journal table
export const getRevenueAvailableYears = () => {
  return api.get("/api/revenue/available-years");
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
  if (params.date_fact_from)
    query.append("date_fact_from", params.date_fact_from);
  if (params.date_fact_to) query.append("date_fact_to", params.date_fact_to);
  if (params.is_duplicate !== undefined)
    query.append("is_duplicate", params.is_duplicate);
  if (params.is_anomaly !== undefined)
    query.append("is_anomaly", params.is_anomaly);
  if (params.file_upload_id)
    query.append("file_upload_id", params.file_upload_id);
  if (params.year) query.append("year", params.year);
  if (params.sort_by) query.append("sort_by", params.sort_by);
  if (params.sort_order) query.append("sort_order", params.sort_order);
  return api.get(`/api/encaissement/records?${query.toString()}`);
};

// Get preview data with separate filters (for preview tab)
export const getEncaissementPreviewData = (params = {}) => {
  const query = new URLSearchParams();
  if (params.page) query.append("page", params.page);
  if (params.page_size) query.append("page_size", params.page_size);
  
  // Column filters (arrays)
  if (params.id && Array.isArray(params.id)) {
    params.id.forEach((v) => query.append("id", v));
  }
  if (params.file_upload_id && Array.isArray(params.file_upload_id)) {
    params.file_upload_id.forEach((v) => query.append("file_upload_id", v));
  }
  if (params.dot_id && Array.isArray(params.dot_id)) {
    params.dot_id.forEach((v) => query.append("dot_id", v));
  }
  if (params.organisation && Array.isArray(params.organisation)) {
    params.organisation.forEach((v) => query.append("organisation", v));
  }
  if (params.source && Array.isArray(params.source)) {
    params.source.forEach((v) => query.append("source", v));
  }
  if (params.n_fact && Array.isArray(params.n_fact)) {
    params.n_fact.forEach((v) => query.append("n_fact", v));
  }
  if (params.typ_fact && Array.isArray(params.typ_fact)) {
    params.typ_fact.forEach((v) => query.append("typ_fact", v));
  }
  if (params.client && Array.isArray(params.client)) {
    params.client.forEach((v) => query.append("client", v));
  }
  if (params.n_client && Array.isArray(params.n_client)) {
    params.n_client.forEach((v) => query.append("n_client", v));
  }
  if (params.mois && Array.isArray(params.mois)) {
    params.mois.forEach((v) => query.append("mois", v));
  }
  
  // Date filters
  if (params.date_fact_start) query.append("date_fact_start", params.date_fact_start);
  if (params.date_fact_end) query.append("date_fact_end", params.date_fact_end);
  if (params.date_rglt_start) query.append("date_rglt_start", params.date_rglt_start);
  if (params.date_rglt_end) query.append("date_rglt_end", params.date_rglt_end);
  
  // Numeric range filters
  if (params.montant_ht_min !== undefined) query.append("montant_ht_min", params.montant_ht_min);
  if (params.montant_ht_max !== undefined) query.append("montant_ht_max", params.montant_ht_max);
  if (params.montant_taxe_min !== undefined) query.append("montant_taxe_min", params.montant_taxe_min);
  if (params.montant_taxe_max !== undefined) query.append("montant_taxe_max", params.montant_taxe_max);
  if (params.montant_ttc_min !== undefined) query.append("montant_ttc_min", params.montant_ttc_min);
  if (params.montant_ttc_max !== undefined) query.append("montant_ttc_max", params.montant_ttc_max);
  if (params.encaissement_min !== undefined) query.append("encaissement_min", params.encaissement_min);
  if (params.encaissement_max !== undefined) query.append("encaissement_max", params.encaissement_max);
  if (params.taux_encaissement_min !== undefined) query.append("taux_encaissement_min", params.taux_encaissement_min);
  if (params.taux_encaissement_max !== undefined) query.append("taux_encaissement_max", params.taux_encaissement_max);
  if (params.montant_restant_min !== undefined) query.append("montant_restant_min", params.montant_restant_min);
  if (params.montant_restant_max !== undefined) query.append("montant_restant_max", params.montant_restant_max);
  
  // Boolean filters
  if (params.is_duplicate !== undefined) query.append("is_duplicate", params.is_duplicate);
  if (params.is_anomaly !== undefined) query.append("is_anomaly", params.is_anomaly);
  
  // Other filters
  if (params.search) query.append("search", params.search);
  if (params.year) query.append("year", params.year);
  if (params.sort_by) query.append("sort_by", params.sort_by);
  if (params.sort_order) query.append("sort_order", params.sort_order);
  
  return api.get(`/api/encaissement/preview-data?${query.toString()}`);
};

export const getEncaissementRecordById = (recordId) => {
  if (!recordId) return Promise.reject(new Error("Record ID is required"));
  return api.get(`/api/encaissement/records/${recordId}`);
};

export const getEncaissementDashboardOverview = () =>
  api.get("/api/encaissement/dashboard/overview");

export const getEncaissementMonthlyAggregates = (year) => {
  const params = year ? `?year=${year}` : "";
  return api.get(`/api/encaissement/dashboard/monthly-aggregates${params}`);
};

export const getEncaissementMonthlyDistribution = (year) => {
  const params = year ? `?year=${year}` : "";
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
  if (params.file_upload_id)
    query.append("file_upload_id", params.file_upload_id);
  return api.get(`/api/encaissement/anomalies?${query.toString()}`);
};

export const getEncaissementAnomalyStatistics = () =>
  api.get("/api/encaissement/anomalies/statistics");

export const getEncaissementStatisticsByOrganisation = (organisation) => {
  const params = organisation
    ? `?organisation=${encodeURIComponent(organisation)}`
    : "";
  return api.get(`/api/encaissement/statistics/by-organisation${params}`);
};

export const getEncaissementAvailableMonths = () =>
  api.get("/api/encaissement/metadata/available-months");

export const getEncaissementAvailableOrganisations = () =>
  api.get("/api/encaissement/metadata/available-organisations");

export const exportEncaissementRecords = (params = {}) => {
  const query = new URLSearchParams();

  // Organisation filter - support both array and comma-separated string
  if (params.organisation) {
    if (Array.isArray(params.organisation)) {
      params.organisation.forEach((org) => query.append("organisation", org));
    } else {
      query.append("organisation", params.organisation);
    }
  }

  // Date filters - prefer date_fact_start/end, fallback to date_fact_from/to
  if (params.date_fact_start) {
    query.append("date_fact_start", params.date_fact_start);
  } else if (params.date_fact_from) {
    query.append("date_fact_from", params.date_fact_from);
  }

  if (params.date_fact_end) {
    query.append("date_fact_end", params.date_fact_end);
  } else if (params.date_fact_to) {
    query.append("date_fact_to", params.date_fact_to);
  }

  // Month filter
  if (params.mois) query.append("mois", params.mois);

  // Rate filters
  if (
    params.taux_encaissement_min !== undefined &&
    params.taux_encaissement_min !== ""
  ) {
    query.append("taux_encaissement_min", params.taux_encaissement_min);
  }
  if (
    params.taux_encaissement_max !== undefined &&
    params.taux_encaissement_max !== ""
  ) {
    query.append("taux_encaissement_max", params.taux_encaissement_max);
  }

  // Search filter
  if (params.search) query.append("search", params.search);

  // Year filter
  if (params.year) query.append("year", params.year);

  // Type Fact filter
  if (params.typ_fact) {
    if (Array.isArray(params.typ_fact)) {
      params.typ_fact.forEach((type) => query.append("typ_fact", type));
    } else {
      query.append("typ_fact", params.typ_fact);
    }
  }

  // Date Règlement filters
  if (params.date_rglt_start) {
    query.append("date_rglt_start", params.date_rglt_start);
  }
  if (params.date_rglt_end) {
    query.append("date_rglt_end", params.date_rglt_end);
  }

  // Other filters
  if (params.include_duplicates !== undefined)
    query.append("include_duplicates", params.include_duplicates);
  if (params.include_anomalies !== undefined)
    query.append("include_anomalies", params.include_anomalies);

  // Format
  query.append("format", params.format || "xlsx");
  const format = (params.format || "xlsx").toLowerCase();

  return api.get(`/api/encaissement/export?${query.toString()}`, {
    responseType: format === "csv" || format === "xlsx" ? "blob" : undefined,
  });
};

// Start async encaissement export
export const startEncaissementExport = (filters = {}) => {
  const format = filters.format || "xlsx";
  const { format: _, ...filterParams } = filters;

  // Build URLSearchParams, only including non-empty values
  const params = new URLSearchParams();
  params.append("format", format);

  // Only add filter params that have values
  // Handle arrays (for column filters) and single values
  Object.keys(filterParams).forEach((key) => {
    const value = filterParams[key];
    if (value !== undefined && value !== null && value !== "") {
      if (Array.isArray(value)) {
        // For arrays, append each value separately
        value.forEach((v) => {
          if (v !== undefined && v !== null && v !== "") {
            params.append(key, v);
          }
        });
      } else {
        params.append(key, value);
      }
    }
  });

  console.log(
    "🔍 [FRONTEND API] startEncaissementExport - params:",
    params.toString()
  );
  return api.post(`/api/encaissement/export-async?${params.toString()}`);
};

// Get encaissement export task status
export const getEncaissementExportStatus = (taskId) => {
  return api.get(`/api/encaissement/export-status/${taskId}`);
};

// Download completed encaissement export file
export const downloadEncaissementExport = (taskId) => {
  return api.get(`/api/encaissement/export-download/${taskId}`, {
    responseType: "blob",
  });
};

export const getEncaissementDuplicateGroups = (compositeKey) => {
  const params = compositeKey
    ? `?composite_key=${encodeURIComponent(compositeKey)}`
    : "";
  return api.get(`/api/encaissement/duplicates/groups${params}`);
};

// ===================================================================
// Encaissement AR DOT - Enhanced Visualization Endpoints
// ===================================================================

/**
 * Get monthly chart data for combined histogram (Encaissement & Montant TTC by month)
 */
export const getEncaissementMonthlyChartData = (filters = {}) => {
  const query = new URLSearchParams();
  if (filters.organisations)
    query.append("organisations", filters.organisations);
  if (filters.mois) query.append("mois", filters.mois);
  if (filters.taux_min !== undefined)
    query.append("taux_min", filters.taux_min);
  if (filters.taux_max !== undefined)
    query.append("taux_max", filters.taux_max);
  return api.get(`/api/encaissement/monthly-chart-data?${query.toString()}`);
};

/**
 * Get monthly pie data for 3D pie chart (Encaissement by month)
 */
export const getEncaissementMonthlyPieData = (filters = {}) => {
  const query = new URLSearchParams();
  if (filters.organisations)
    query.append("organisations", filters.organisations);
  if (filters.mois) query.append("mois", filters.mois);
  if (filters.taux_min !== undefined)
    query.append("taux_min", filters.taux_min);
  if (filters.taux_max !== undefined)
    query.append("taux_max", filters.taux_max);
  return api.get(`/api/encaissement/monthly-pie-data?${query.toString()}`);
};

/**
 * Get DOT and Taux d'encaissement data for histogram
 */
export const getEncaissementDotTauxData = (filters = {}) => {
  const query = new URLSearchParams();
  if (filters.organisations)
    query.append("organisations", filters.organisations);
  if (filters.mois) query.append("mois", filters.mois);
  if (filters.taux_min !== undefined)
    query.append("taux_min", filters.taux_min);
  if (filters.taux_max !== undefined)
    query.append("taux_max", filters.taux_max);
  return api.get(`/api/encaissement/dot-taux-data?${query.toString()}`);
};

/**
 * Get available filters for Encaissement AR DOT
 */
export const getEncaissementFilters = () =>
  api.get("/api/encaissement/filters");

export const getEncaissementColumnValues = (column) => {
  return api.get(
    `/api/encaissement/preview-data/column-values?column=${column}`
  );
};

/**
 * Export Encaissement AR DOT data with French formatting
 */
export const exportEncaissementARDot = (filters = {}, format = "xlsx") => {
  const query = new URLSearchParams();
  if (filters.organisations)
    query.append("organisations", filters.organisations);
  if (filters.mois) query.append("mois", filters.mois);
  if (filters.taux_min !== undefined)
    query.append("taux_min", filters.taux_min);
  if (filters.taux_max !== undefined)
    query.append("taux_max", filters.taux_max);
  query.append("format", format);

  return api.get(`/api/encaissement/export?${query.toString()}`, {
    responseType: "blob",
  });
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
  if (params.file_upload_id)
    query.append("file_upload_id", params.file_upload_id);
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
  const params = dot ? `?dot=${encodeURIComponent(dot)}` : "";
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
