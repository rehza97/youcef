// This file is now deprecated - use direct functions from services/api.js instead
import {
  fetchNotifications as apiFetchNotifications,
  markNotificationAsRead as apiMarkNotificationAsRead,
  updateNotificationPreferences as apiUpdateNotificationPreferences,
} from "../services/api";

// Backward-compatible shims

// Legacy functions for backward compatibility
export async function fetchNotifications() {
  const response = await apiFetchNotifications();
  return response.data;
}

export async function markNotificationAsRead(id) {
  const response = await apiMarkNotificationAsRead(id);
  return response.data;
}

export async function updateNotificationPreferences(prefs) {
  const response = await apiUpdateNotificationPreferences(prefs);
  return response.data;
}
