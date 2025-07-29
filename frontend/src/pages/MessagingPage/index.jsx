import React, { useState, useEffect } from "react";
import { messagingAPI } from "../../services/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../../components/ui/dialog";
import {
  MessageSquare,
  Send,
  Users,
  UserPlus,
  UserMinus,
  Search,
  Filter,
  MoreHorizontal,
  Eye,
  Edit,
  Trash2,
  Shield,
  AlertCircle,
} from "lucide-react";
import { toast } from "sonner";

const MessagingPage = () => {
  const [conversations, setConversations] = useState([]);
  const [blockedUsers, setBlockedUsers] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showBlockDialog, setShowBlockDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [blockReason, setBlockReason] = useState("");

  useEffect(() => {
    fetchConversations();
    fetchBlockedUsers();
  }, []);

  const fetchConversations = async () => {
    try {
      setLoading(true);
      const response = await messagingAPI.fetchConversations();
      setConversations(response.data.conversations || []);
    } catch (error) {
      console.error("Erreur lors du chargement des conversations:", error);
      toast.error("Erreur lors du chargement des conversations");
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
    try {
      const response = await messagingAPI.fetchMessages(conversation.id);
      setSelectedConversation({
        ...conversation,
        messages: response.data.messages || [],
      });
    } catch (error) {
      console.error("Erreur lors du chargement des messages:", error);
      toast.error("Erreur lors du chargement des messages");
    }
  };

  const handleSendMessage = async () => {
    if (!newMessage.trim() || !selectedConversation) return;

    try {
      const response = await messagingAPI.sendMessage(
        selectedConversation.id,
        newMessage
      );

      setSelectedConversation((prev) => ({
        ...prev,
        messages: [...(prev.messages || []), response.data.message],
      }));

      setNewMessage("");
      toast.success("Message envoyé avec succès");
    } catch (error) {
      console.error("Erreur lors de l'envoi du message:", error);
      toast.error("Erreur lors de l'envoi du message");
    }
  };

  const handleCreateConversation = async () => {
    try {
      const response = await messagingAPI.createConversation({
        name: `Conversation with ${selectedUser.username}`,
        conversation_type: "direct",
        participant_ids: [selectedUser.id],
      });

      setConversations((prev) => [...prev, response.data.conversation]);
      setShowCreateDialog(false);
      setSelectedUser(null);
      toast.success("Conversation créée avec succès");
    } catch (error) {
      console.error("Erreur lors de la création de la conversation:", error);
      toast.error("Erreur lors de la création de la conversation");
    }
  };

  const handleBlockUser = async (userId, reason = "") => {
    try {
      await messagingAPI.blockUser(userId, reason);

      setBlockedUsers((prev) => [
        ...prev,
        { id: userId, reason: reason, blocked_at: new Date().toISOString() },
      ]);

      setShowBlockDialog(false);
      setSelectedUser(null);
      setBlockReason("");
      toast.success("Utilisateur bloqué avec succès");
    } catch (error) {
      console.error("Erreur lors du blocage de l'utilisateur:", error);
      toast.error("Erreur lors du blocage de l'utilisateur");
    }
  };

  const handleUnblockUser = async (userId) => {
    try {
      await messagingAPI.unblockUser(userId);

      setBlockedUsers((prev) => prev.filter((user) => user.id !== userId));
      toast.success("Utilisateur débloqué avec succès");
    } catch (error) {
      console.error("Erreur lors du déblocage de l'utilisateur:", error);
      toast.error("Erreur lors du déblocage de l'utilisateur");
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleString("fr-FR");
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "active":
        return "bg-green-100 text-green-800";
      case "blocked":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Messagerie</h1>
        <p className="text-gray-600">
          Gérer les conversations et les utilisateurs bloqués
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Conversations */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5" />
                  Conversations
                </CardTitle>
                <Button
                  onClick={() => setShowCreateDialog(true)}
                  className="bg-[#38ada9] hover:bg-[#3c6382] text-white"
                >
                  <UserPlus className="h-4 w-4 mr-2" />
                  Nouvelle conversation
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                  <p>Chargement des conversations...</p>
                </div>
              ) : conversations.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p>Aucune conversation</p>
                  <p className="text-sm">
                    Commencez par créer une nouvelle conversation
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {conversations.map((conversation) => (
                    <div
                      key={conversation.id}
                      className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
                      onClick={() => handleConversationClick(conversation)}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h3 className="font-semibold">
                            {conversation.participants
                              ?.map((p) => p.username)
                              .join(", ") || "Conversation"}
                          </h3>
                          <p className="text-sm text-gray-600">
                            {conversation.last_message?.content ||
                              "Aucun message"}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-gray-500">
                            {formatDate(conversation.last_message?.created_at)}
                          </p>
                          <Badge
                            className={getStatusColor(conversation.status)}
                          >
                            {conversation.status === "active"
                              ? "Active"
                              : "Bloquée"}
                          </Badge>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Messages */}
          {selectedConversation && (
            <Card className="mt-6">
              <CardHeader>
                <CardTitle>
                  Messages -{" "}
                  {selectedConversation.participants
                    ?.map((p) => p.username)
                    .join(", ")}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4 max-h-96 overflow-y-auto">
                  {selectedConversation.messages?.map((message) => (
                    <div
                      key={message.id}
                      className={`flex ${
                        message.is_sender ? "justify-end" : "justify-start"
                      }`}
                    >
                      <div
                        className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                          message.is_sender
                            ? "bg-blue-500 text-white"
                            : "bg-gray-200 text-gray-900"
                        }`}
                      >
                        <p className="text-sm">{message.content}</p>
                        <p className="text-xs opacity-75 mt-1">
                          {formatDate(message.created_at)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex gap-2 mt-4">
                  <Input
                    value={newMessage}
                    onChange={(e) => setNewMessage(e.target.value)}
                    placeholder="Tapez votre message..."
                    onKeyPress={(e) => {
                      if (e.key === "Enter") {
                        handleSendMessage();
                      }
                    }}
                  />
                  <Button
                    onClick={handleSendMessage}
                    disabled={!newMessage.trim()}
                    className="bg-[#38ada9] hover:bg-[#3c6382] text-white"
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Utilisateurs bloqués */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Utilisateurs bloqués
              </CardTitle>
            </CardHeader>
            <CardContent>
              {blockedUsers.length === 0 ? (
                <div className="text-center text-gray-500 py-8">
                  <Shield className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p>Aucun utilisateur bloqué</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {blockedUsers.map((user) => (
                    <div key={user.id} className="border rounded-lg p-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <h4 className="font-medium">{user.username}</h4>
                          <p className="text-sm text-gray-600">
                            {user.reason || "Aucune raison spécifiée"}
                          </p>
                          <p className="text-xs text-gray-500">
                            {formatDate(user.blocked_at)}
                          </p>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleUnblockUser(user.id)}
                        >
                          <UserMinus className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Dialog pour créer une conversation */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Créer une nouvelle conversation</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="user">Sélectionner un utilisateur</Label>
              <Select
                value={selectedUser?.id || ""}
                onValueChange={(value) => {
                  // Simuler la sélection d'un utilisateur
                  setSelectedUser({
                    id: value,
                    username: `Utilisateur ${value}`,
                  });
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choisir un utilisateur" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Utilisateur 1</SelectItem>
                  <SelectItem value="2">Utilisateur 2</SelectItem>
                  <SelectItem value="3">Utilisateur 3</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => setShowCreateDialog(false)}
              >
                Annuler
              </Button>
              <Button
                onClick={handleCreateConversation}
                disabled={!selectedUser}
                className="bg-[#38ada9] hover:bg-[#3c6382] text-white"
              >
                Créer
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Dialog pour bloquer un utilisateur */}
      <Dialog open={showBlockDialog} onOpenChange={setShowBlockDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bloquer un utilisateur</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="user">Sélectionner un utilisateur</Label>
              <Select
                value={selectedUser?.id || ""}
                onValueChange={(value) => {
                  setSelectedUser({
                    id: value,
                    username: `Utilisateur ${value}`,
                  });
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choisir un utilisateur" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Utilisateur 1</SelectItem>
                  <SelectItem value="2">Utilisateur 2</SelectItem>
                  <SelectItem value="3">Utilisateur 3</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="reason">Raison du blocage (optionnel)</Label>
              <Input
                id="reason"
                value={blockReason}
                onChange={(e) => setBlockReason(e.target.value)}
                placeholder="Raison du blocage..."
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => setShowBlockDialog(false)}
              >
                Annuler
              </Button>
              <Button
                onClick={() => handleBlockUser(selectedUser?.id, blockReason)}
                disabled={!selectedUser}
                variant="destructive"
              >
                Bloquer
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MessagingPage;
