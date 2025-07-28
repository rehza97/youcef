import axios from "axios";

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

// Request interceptor - Add JWT Bearer token
api.interceptors.request.use(
  (config) => {
    // Add authentication token as Bearer token
    const token =
      sessionStorage.getItem("token") || localStorage.getItem("token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Sanitize request data
    if (config.data && typeof config.data === "object") {
      config.data = sanitizeData(config.data);
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
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(";").shift();
  return null;
}

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

  getRoles: () => api.get("/api/users/roles/"),
  getRole: (roleId) => api.get(`/api/users/roles/${roleId}`),
  createRole: (roleData) => api.post("/api/users/roles/", roleData),

  getPermissions: () => api.get("/api/users/permissions/"),
  getPermission: (permissionId) =>
    api.get(`/api/users/permissions/${permissionId}`),
  createPermission: (permissionData) =>
    api.post("/api/users/permissions", permissionData),

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

  markAsRead: (id) => {
    if (!id) return Promise.reject(new Error("Notification ID is required"));
    return api.put(`/api/notifications/${id}/read`);
  },

  markAllAsRead: () => api.put("/api/notifications/read-all"),

  updatePreferences: (prefs) =>
    api.put("/api/notifications/preferences", prefs),

  getStats: () => api.get("/api/notifications/stats"),

  getPreferences: () => api.get("/api/notifications/preferences"),

  createNotification: (notificationData) =>
    api.post("/api/notifications/", notificationData),
};

// Messaging API for FastAPI backend
export const messagingAPI = {
  fetchConversations: () => api.get("/api/messaging/conversations"),

  getConversation: (conversationId) => {
    if (!conversationId)
      return Promise.reject(new Error("Conversation ID is required"));
    return api.get(`/api/messaging/conversations/${conversationId}`);
  },

  fetchMessages: (conversationId, params = {}) => {
    if (!conversationId)
      return Promise.reject(new Error("Conversation ID is required"));

    const queryParams = new URLSearchParams();
    if (params.skip) queryParams.append("skip", params.skip);
    if (params.limit) queryParams.append("limit", params.limit);

    return api.get(
      `/api/messaging/conversations/${conversationId}/messages?${queryParams.toString()}`
    );
  },

  sendMessage: (conversationId, content, messageType = "text") => {
    if (!conversationId || !content?.trim()) {
      return Promise.reject({
        response: {
          data: {
            detail: "Conversation ID and message content are required",
            code: "INVALID_MESSAGE",
          },
        },
      });
    }

    return api.post(`/api/messaging/conversations/${conversationId}/messages`, {
      content: content.trim(),
      message_type: messageType,
    });
  },

  createConversation: (data) => {
    if (!data.name || !data.conversation_type) {
      return Promise.reject({
        response: {
          data: {
            detail: "Conversation name and type are required",
            code: "MISSING_FIELDS",
          },
        },
      });
    }
    return api.post("/api/messaging/conversations", data);
  },

  addReaction: (messageId, reactionType) => {
    if (!messageId || !reactionType) {
      return Promise.reject(
        new Error("Message ID and reaction type are required")
      );
    }
    return api.post(`/api/messaging/messages/${messageId}/react`, {
      reaction_type: reactionType,
    });
  },

  blockUser: (userId, reason = "") => {
    if (!userId) return Promise.reject(new Error("User ID is required"));
    return api.post("/api/messaging/blocks", {
      blocked_user_id: userId,
      reason: reason.trim(),
    });
  },

  unblockUser: (userId) => {
    if (!userId) return Promise.reject(new Error("User ID is required"));
    return api.post("/api/messaging/blocks/unblock", {
      blocked_user_id: userId,
    });
  },

  getBlockedUsers: () => api.get("/api/messaging/blocks"),
  getBlocks: () => api.get("/api/messaging/blocks"),

  sendMultiMessage: (formData) => {
    if (!formData) return Promise.reject(new Error("Form data is required"));
    return api.post("/api/messaging/send-multi", formData, {
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

  getFileDetails: (fileId) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.get(`/api/files/${fileId}`);
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

  deleteFile: (fileId) => {
    if (!fileId) return Promise.reject(new Error("File ID is required"));
    return api.delete(`/api/files/${fileId}`);
  },

  getFileStats: () => api.get("/api/files/stats/summary"),
};

// Health and general API for FastAPI backend
export const generalAPI = {
  healthCheck: () => api.get("/health"),
  detailedHealthCheck: () => api.get("/api/health/detailed"),
  protected: () => api.get("/api/auth/protected"),
};

export default api;
