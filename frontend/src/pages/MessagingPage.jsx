import React, { useState, useEffect } from "react";
import { messagingAPI } from "../services/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "../components/ui/avatar";
import { Separator } from "../components/ui/separator";
import { useAuth } from "../contexts/AuthContext";

const MessagingPage = () => {
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [showCreateConversation, setShowCreateConversation] = useState(false);
  const [blockedUsers, setBlockedUsers] = useState([]);
  const [newConversation, setNewConversation] = useState({
    name: "",
    conversation_type: "group",
  });
  const { user: currentUser } = useAuth();

  useEffect(() => {
    fetchConversations();
    fetchBlockedUsers();
  }, []);

  const fetchConversations = async () => {
    try {
      setLoading(true);
      const response = await messagingAPI.fetchConversations();
      setConversations(response.data);
    } catch (error) {
      console.error("Erreur lors du chargement des conversations:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBlockedUsers = async () => {
    try {
      const response = await messagingAPI.getBlockedUsers();
      setBlockedUsers(response.data.blocked_users || []);
    } catch (error) {
      console.error(
        "Erreur lors du chargement des utilisateurs bloqués:",
        error
      );
    }
  };

  const handleConversationClick = async (conversation) => {
    setSelectedConversation(conversation);
    try {
      const response = await messagingAPI.fetchMessages(conversation.id);
      setMessages(response.data);
    } catch (error) {
      console.error("Erreur lors du chargement des messages:", error);
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !selectedConversation) return;

    try {
      await messagingAPI.sendMessage(selectedConversation.id, newMessage);
      setNewMessage("");
      // Recharger les messages
      const response = await messagingAPI.fetchMessages(
        selectedConversation.id
      );
      setMessages(response.data);
    } catch (error) {
      console.error("Erreur lors de l'envoi du message:", error);
    }
  };

  const handleCreateConversation = async () => {
    if (!newConversation.name.trim()) {
      alert("Le nom de la conversation est requis");
      return;
    }

    try {
      await messagingAPI.createConversation(newConversation);
      setNewConversation({ name: "", conversation_type: "group" });
      setShowCreateConversation(false);
      fetchConversations();
    } catch (error) {
      console.error("Erreur lors de la création de la conversation:", error);
    }
  };

  const handleBlockUser = async (userId, reason = "") => {
    try {
      await messagingAPI.blockUser(userId, reason);
      fetchBlockedUsers();
    } catch (error) {
      console.error("Erreur lors du blocage de l'utilisateur:", error);
    }
  };

  const handleUnblockUser = async (userId) => {
    try {
      await messagingAPI.unblockUser(userId);
      fetchBlockedUsers();
    } catch (error) {
      console.error("Erreur lors du déblocage de l'utilisateur:", error);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Messagerie</h1>
        <p className="text-gray-600">
          Chatter avec d'autres utilisateurs et gérer les conversations
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Liste des conversations */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Conversations</CardTitle>
                <Button
                  size="sm"
                  onClick={() => setShowCreateConversation(true)}
                >
                  Nouvelle conversation
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-center py-4">Chargement...</div>
              ) : conversations.length === 0 ? (
                <div className="text-center text-gray-500 py-4">
                  Aucune conversation
                </div>
              ) : (
                <div className="space-y-2">
                  {conversations.map((conversation) => (
                    <div
                      key={conversation.id}
                      className={`p-3 rounded-lg cursor-pointer hover:bg-gray-50 ${
                        selectedConversation?.id === conversation.id
                          ? "bg-blue-50 border border-blue-200"
                          : ""
                      }`}
                      onClick={() => handleConversationClick(conversation)}
                    >
                      <div className="flex items-center gap-3">
                        <Avatar className="w-10 h-10">
                          <AvatarFallback>
                            {conversation.name?.charAt(0)?.toUpperCase() || "?"}
                          </AvatarFallback>
                        </Avatar>
                        <div className="flex-1">
                          <h4 className="font-medium">
                            {conversation.name || "Conversation sans nom"}
                          </h4>
                          <p className="text-sm text-gray-500">
                            {conversation.conversation_type === "group"
                              ? "Groupe"
                              : "Privé"}
                          </p>
                        </div>
                        {conversation.participant_count && (
                          <Badge variant="outline">
                            {conversation.participant_count}
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Zone de chat */}
        <div className="lg:col-span-2">
          <Card className="h-[600px] flex flex-col">
            <CardHeader>
              <CardTitle>
                {selectedConversation
                  ? selectedConversation.name || "Conversation sans nom"
                  : "Sélectionnez une conversation"}
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col">
              {selectedConversation ? (
                <>
                  {/* Messages */}
                  <div className="flex-1 overflow-y-auto space-y-3 mb-4">
                    {messages.length === 0 ? (
                      <div className="text-center text-gray-500 py-8">
                        Aucun message dans cette conversation
                      </div>
                    ) : (
                      messages.map((message) => (
                        <div
                          key={message.id}
                          className={`flex ${
                            message.sender_id === currentUser?.id
                              ? "justify-end"
                              : "justify-start"
                          }`}
                        >
                          <div
                            className={`max-w-xs lg:max-w-md p-3 rounded-lg ${
                              message.sender_id === currentUser?.id
                                ? "bg-blue-500 text-white"
                                : "bg-gray-100 text-gray-900"
                            }`}
                          >
                            <div className="text-sm font-medium mb-1">
                              {message.sender_username || "Utilisateur inconnu"}
                            </div>
                            <div>{message.content}</div>
                            <div className="text-xs opacity-70 mt-1">
                              {new Date(message.created_at).toLocaleString(
                                "fr-FR"
                              )}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  {/* Zone de saisie */}
                  <div className="flex gap-2">
                    <Input
                      value={newMessage}
                      onChange={(e) => setNewMessage(e.target.value)}
                      onKeyPress={(e) =>
                        e.key === "Enter" && handleSendMessage()
                      }
                      placeholder="Tapez votre message..."
                      className="flex-1"
                    />
                    <Button
                      onClick={handleSendMessage}
                      disabled={!newMessage.trim()}
                    >
                      Envoyer
                    </Button>
                  </div>
                </>
              ) : (
                <div className="flex-1 flex items-center justify-center text-gray-500">
                  Sélectionnez une conversation pour commencer à chatter
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Modal de création de conversation */}
      {showCreateConversation && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">
              Créer une nouvelle conversation
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Nom de la conversation
                </label>
                <Input
                  value={newConversation.name}
                  onChange={(e) =>
                    setNewConversation({
                      ...newConversation,
                      name: e.target.value,
                    })
                  }
                  placeholder="Nom de la conversation"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Type de conversation
                </label>
                <select
                  value={newConversation.conversation_type}
                  onChange={(e) =>
                    setNewConversation({
                      ...newConversation,
                      conversation_type: e.target.value,
                    })
                  }
                  className="w-full p-2 border rounded-md"
                >
                  <option value="group">Groupe</option>
                  <option value="private">Privé</option>
                </select>
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-6">
              <Button
                variant="outline"
                onClick={() => setShowCreateConversation(false)}
              >
                Annuler
              </Button>
              <Button onClick={handleCreateConversation}>
                Créer la conversation
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Section des utilisateurs bloqués */}
      <div className="mt-8">
        <Card>
          <CardHeader>
            <CardTitle>Utilisateurs bloqués</CardTitle>
          </CardHeader>
          <CardContent>
            {blockedUsers.length === 0 ? (
              <p className="text-gray-500">Aucun utilisateur bloqué</p>
            ) : (
              <div className="space-y-2">
                {blockedUsers.map((block) => (
                  <div
                    key={block.id}
                    className="flex items-center justify-between p-3 border rounded"
                  >
                    <div>
                      <span className="font-medium">
                        Utilisateur ID: {block.blocked_id}
                      </span>
                      {block.reason && (
                        <p className="text-sm text-gray-500">
                          Raison: {block.reason}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleUnblockUser(block.blocked_id)}
                    >
                      Débloquer
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default MessagingPage;
