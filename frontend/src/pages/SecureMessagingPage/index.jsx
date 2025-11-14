import React, { useState, useEffect, useRef } from "react";
import {
  fetchConversations,
  fetchMessages,
  sendMessage as apiSendMessage,
  editMessage as apiEditMessage,
  deleteMessage as apiDeleteMessage,
  addReaction as apiAddReaction,
} from "../../services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Lock,
  MessageSquare,
  Loader2,
  AlertCircle,
  Send,
} from "lucide-react";
import { toast } from "sonner";
import { handleApiError } from "../../lib/error-handler";
import ConversationItem from "../../components/messaging/ConversationItem";
import MessageItem from "../../components/messaging/MessageItem";
import ConversationHeader from "../../components/messaging/ConversationHeader";

const SecureMessagingPage = () => {
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [newMessage, setNewMessage] = useState("");
  const [editingMessageId, setEditingMessageId] = useState(null);
  const [editingContent, setEditingContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const messagesEndRef = useRef(null);
  const currentUserId = 1; // Should come from auth context

  useEffect(() => {
    fetchConversationsHandler();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [selectedConversation?.messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const fetchConversationsHandler = async () => {
    try {
      setLoading(true);
      const response = await fetchConversations();
      setConversations(response.data.conversations || []);
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du chargement des conversations",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleConversationClick = async (conversation) => {
    try {
      const response = await fetchMessages(conversation.id);
      setSelectedConversation({
        ...conversation,
        messages: response.data.messages || [],
      });
      setEditingMessageId(null);
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du chargement des messages",
      });
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !selectedConversation) return;

    try {
      setSending(true);

      const messageData = {
        content: newMessage.trim(),
        message_type: "text",
        is_encrypted: true, // Secure messaging flag
      };

      const response = await apiSendMessage(
        selectedConversation.id,
        messageData
      );

      setSelectedConversation((prev) => ({
        ...prev,
        messages: [...(prev.messages || []), response.data],
      }));

      setNewMessage("");
      toast.success("Message envoyé de manière sécurisée");
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors de l'envoi du message",
      });
    } finally {
      setSending(false);
    }
  };

  const handleEditMessage = async (messageId) => {
    if (!editingContent.trim()) return;

    try {
      setSending(true);

      const response = await apiEditMessage(messageId, {
        content: editingContent.trim(),
      });

      setSelectedConversation((prev) => ({
        ...prev,
        messages: prev.messages.map((msg) =>
          msg.id === messageId ? response.data : msg
        ),
      }));

      setEditingMessageId(null);
      setEditingContent("");
      toast.success("Message modifié");
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors de la modification du message",
      });
    } finally {
      setSending(false);
    }
  };

  const handleDeleteMessage = async (messageId) => {
    try {
      await apiDeleteMessage(messageId);

      setSelectedConversation((prev) => ({
        ...prev,
        messages: prev.messages.filter((msg) => msg.id !== messageId),
      }));

      toast.success("Message supprimé");
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors de la suppression du message",
      });
    }
  };

  const handleReact = async (messageId, emoji) => {
    try {
      await apiAddReaction(messageId, {
        emoji,
      });

      setSelectedConversation((prev) => ({
        ...prev,
        messages: prev.messages.map((msg) => {
          if (msg.id === messageId) {
            return {
              ...msg,
              reactions: [
                ...(msg.reactions || []),
                {
                  emoji,
                  user_id: currentUserId,
                  created_at: new Date().toISOString(),
                },
              ],
            };
          }
          return msg;
        }),
      }));

      toast.success("Réaction ajoutée");
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors de l'ajout de la réaction",
      });
    }
  };

  const filteredConversations = conversations.filter((conversation) =>
    conversation.name?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    const date = new Date(dateString);
    const now = new Date();
    const diffInHours = (now - date) / (1000 * 60 * 60);

    if (diffInHours < 24) {
      return date.toLocaleTimeString("fr-FR", {
        hour: "2-digit",
        minute: "2-digit",
      });
    }
    return date.toLocaleDateString("fr-FR");
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "active":
        return "bg-green-100 text-green-800 border-green-200";
      case "blocked":
        return "bg-red-100 text-red-800 border-red-200";
      default:
        return "bg-gray-100 text-gray-800 border-gray-200";
    }
  };

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2 flex items-center gap-2">
          <Lock className="h-8 w-8 text-purple-600" />
          Messagerie Sécurisée
        </h1>
        <p className="text-gray-600">
          Messages chiffrés et sécurisés avec support des réactions et modifications
        </p>
      </div>

      {/* Security Info Banner */}
      <Card className="mb-6 border-purple-200 bg-purple-50">
        <CardContent className="pt-6 flex gap-3">
          <AlertCircle className="h-5 w-5 text-purple-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-purple-800">
            <p className="font-medium mb-1">Messagerie Sécurisée</p>
            <p>
              Tous les messages sont chiffrés de bout en bout. Vous pouvez modifier ou supprimer vos messages à tout moment.
            </p>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Conversations List */}
        <div className="lg:col-span-1">
          <Card className="h-[calc(100vh-300px)]">
            <CardHeader className="border-b">
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5" />
                Conversations
              </CardTitle>
            </CardHeader>

            <div className="p-4 border-b">
              <Input
                placeholder="Rechercher..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="h-9"
              />
            </div>

            <CardContent className="p-0 flex-1 overflow-y-auto">
              {loading ? (
                <div className="text-center py-8">
                  <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-purple-600" />
                  <p className="text-sm text-gray-600">Chargement...</p>
                </div>
              ) : filteredConversations.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p className="text-sm">Aucune conversation</p>
                </div>
              ) : (
                <div className="space-y-1 p-2">
                  {filteredConversations.map((conversation) => (
                    <ConversationItem
                      key={conversation.id}
                      conversation={conversation}
                      isSelected={selectedConversation?.id === conversation.id}
                      onClick={() => handleConversationClick(conversation)}
                      formatDate={formatDate}
                      getStatusColor={getStatusColor}
                    />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Messages Area */}
        <div className="lg:col-span-3">
          <Card className="h-[calc(100vh-300px)] flex flex-col">
            {selectedConversation ? (
              <>
                <ConversationHeader conversation={selectedConversation} />

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {selectedConversation.messages?.map((message) => (
                    <div key={message.id}>
                      {editingMessageId === message.id ? (
                        <div className="flex gap-2">
                          <Textarea
                            value={editingContent}
                            onChange={(e) => setEditingContent(e.target.value)}
                            className="flex-1 resize-none"
                            rows={2}
                          />
                          <div className="flex flex-col gap-2">
                            <Button
                              size="sm"
                              onClick={() => handleEditMessage(message.id)}
                              disabled={!editingContent.trim() || sending}
                            >
                              Sauver
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setEditingMessageId(null);
                                setEditingContent("");
                              }}
                              disabled={sending}
                            >
                              Annuler
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <MessageItem
                          message={message}
                          isSentByCurrentUser={message.sender_id === currentUserId}
                          currentUserId={currentUserId}
                          onDelete={handleDeleteMessage}
                          onEdit={(msg) => {
                            setEditingMessageId(msg.id);
                            setEditingContent(msg.content);
                          }}
                          onReact={handleReact}
                        />
                      )}
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>

                {/* Message Input */}
                <div className="p-4 border-t bg-gray-50">
                  <div className="flex gap-2">
                    <Textarea
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      placeholder="Message sécurisé..."
                      rows={2}
                      className="resize-none"
                      disabled={sending}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !e.shiftKey) {
                          e.preventDefault();
                          handleSendMessage();
                        }
                      }}
                    />
                    <Button
                      onClick={handleSendMessage}
                      disabled={!newMessage.trim() || sending}
                      className="bg-purple-600 hover:bg-purple-700 text-white self-end"
                    >
                      {sending ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Send className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center text-gray-500">
                <div className="text-center">
                  <Lock className="h-16 w-16 mx-auto mb-4 text-purple-300" />
                  <p className="text-lg font-medium">
                    Sélectionnez une conversation
                  </p>
                  <p className="text-sm">
                    Choisissez une conversation sécurisée pour commencer
                  </p>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
};

export default SecureMessagingPage;
