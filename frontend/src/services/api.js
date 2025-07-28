import axios from "axios";

const API_BASE_URL = "http://localhost:8000";

// Create axios instance with base configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

// Auth API
export const authAPI = {
  register: (userData) => api.post("/api/register/", userData),
  login: (credentials) => api.post("/api/login/", credentials),
  logout: () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
  },
};

// Users API
export const usersAPI = {
  getUsers: () => api.get("/users/users/"),
  getRoles: () => api.get("/users/roles/"),
  getPermissions: () => api.get("/users/permissions/"),
  createPermission: (data) => api.post("/users/permissions/", data),
  assignRole: (userData) => api.post("/users/assign-role/", userData),
  checkRole: (roleName) => api.get(`/users/check-role/${roleName}/`),
  checkPermission: (codename) =>
    api.get(`/users/check-permission/${codename}/`),
  updateRolePermissions: (roleId, permissions) =>
    api.post(`/users/roles/${roleId}/update-permissions/`, { permissions }),
  createUser: (data) => api.post("/api/register/", data),
  updateUser: (id, data) => api.put(`/users/users/${id}/`, data),
  deleteUser: (id) => api.delete(`/users/users/${id}/`),
};

// Notifications API
export const notificationsAPI = {
  fetchNotifications: () => api.get("/api/notifications/"),
  markAsRead: (id) => api.post(`/api/notifications/${id}/read/`),
  updatePreferences: (prefs) =>
    api.post("/api/notifications/preferences/", prefs),
};

// Messaging API
export const messagingAPI = {
  fetchConversations: () => api.get("/api/messaging/conversations/"),
  fetchMessages: (conversationId) =>
    api.get(`/api/messaging/conversations/${conversationId}/messages/`),
  sendMessage: (conversationId, content) =>
    api.post(`/api/messaging/conversations/${conversationId}/messages/`, {
      content,
    }),
  createConversation: (data) => api.post("/api/messaging/conversations/", data),
  addReaction: (messageId, reactionType) =>
    api.post(`/api/messaging/messages/${messageId}/reactions/`, {
      reaction_type: reactionType,
    }),
  blockUser: (userId, reason) =>
    api.post("/api/messaging/blocks/", { blocked_user_id: userId, reason }),
  unblockUser: (userId) => api.delete(`/api/messaging/blocks/${userId}/`),
  getBlockedUsers: () => api.get("/api/messaging/blocks/"),
  sendMulti: (formData) =>
    api.post("/api/messaging/send-multi/", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
};

// General API
export const generalAPI = {
  healthCheck: () => api.get("/api/health/"),
  apiInfo: () => api.get("/api/info/"),
  protected: () => api.get("/api/protected/"),
};

export default api;
