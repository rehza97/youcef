import api from "../services/api";

// Fonctions API pour les notifications
export const notificationsAPI = {
  fetchNotifications: () => api.get("/api/notifications/"),
  markAsRead: (id) => api.post(`/api/notifications/${id}/read/`),
  updatePreferences: (prefs) =>
    api.post("/api/notifications/preferences/", prefs),
};

// Legacy functions for backward compatibility
export async function fetchNotifications() {
  const response = await notificationsAPI.fetchNotifications();
  return response.data;
}

export async function markNotificationAsRead(id) {
  const response = await notificationsAPI.markAsRead(id);
  return response.data;
}

export async function updateNotificationPreferences(prefs) {
  const response = await notificationsAPI.updatePreferences(prefs);
  return response.data;
}
