import api from "../services/api";

// Fonctions API pour la messagerie
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
};

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
