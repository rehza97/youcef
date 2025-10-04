// This file is now deprecated - use direct functions from services/api.js instead
import {
  fetchConversations as apiFetchConversations,
  fetchMessages as apiFetchMessages,
  sendMessage as apiSendMessage,
} from "../services/api";

// Backward-compatible shims

// Legacy functions for backward compatibility
export async function fetchConversations() {
  const response = await apiFetchConversations();
  return response.data;
}

export async function fetchMessages(conversationId) {
  const response = await apiFetchMessages(conversationId);
  return response.data;
}

export async function sendMessage(conversationId, content) {
  const response = await apiSendMessage(conversationId, content);
  return response.data;
}
