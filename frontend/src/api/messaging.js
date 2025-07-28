// This file is now deprecated - use messagingAPI from services/api.js instead
import { messagingAPI } from "../services/api";

// Re-export for backward compatibility
export { messagingAPI };

// Legacy functions for backward compatibility
export async function fetchConversations() {
  const response = await messagingAPI.fetchConversations();
  return response.data;
}

export async function fetchMessages(conversationId) {
  const response = await messagingAPI.fetchMessages(conversationId);
  return response.data;
}

export async function sendMessage(conversationId, content) {
  const response = await messagingAPI.sendMessage(conversationId, content);
  return response.data;
}
