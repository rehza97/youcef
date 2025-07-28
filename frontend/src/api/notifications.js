// This file is now deprecated - use notificationsAPI from services/api.js instead
import { notificationsAPI } from "../services/api";

// Re-export for backward compatibility
export { notificationsAPI };

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
