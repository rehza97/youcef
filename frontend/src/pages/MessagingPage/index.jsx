import React, { useState, useEffect, useRef } from "react";
import {
  fetchConversations,
  fetchMessages,
  sendMessage as apiSendMessage,
  sendFile as apiSendFile,
  createConversation as apiCreateConversation,
  blockUser as apiBlockUser,
  unblockUser as apiUnblockUser,
  getBlockedUsers,
  getUsers,
} from "../../services/api";
import { useChatWebSocket } from "../../hooks/useChatWebSocket";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  MessageSquare,
  Send,
  Users,
  UserPlus,
  UserMinus,
  Search,
  Filter,
  Shield,
  FileText,
  Image,
  Video,
  Paperclip,
  Phone,
  Mic,
  Loader2,
  XCircle,
  CheckCircle2,
  Clock,
  AlertCircle,
  MoreVertical,
  Download,
  Trash2,
  Wifi,
  WifiOff,
} from "lucide-react";
import { toast } from "sonner";
import { handleApiError } from "../../lib/error-handler";

const MessagingPage = () => {
  const [conversations, setConversations] = useState([]);
  const [blockedUsers, setBlockedUsers] = useState([]);
  const [allUsers, setAllUsers] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [newMessage, setNewMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showBlockDialog, setShowBlockDialog] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [blockReason, setBlockReason] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [filter, setFilter] = useState("all");
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileUploading, setFileUploading] = useState(false);

  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // WebSocket integration for real-time messaging
  const {
    messages: liveMessages,
    sendMessage: sendWebSocketMessage,
    isConnected: wsConnected,
    ping,
  } = useChatWebSocket(selectedConversation?.id);

  useEffect(() => {
    fetchConversationsHandler();
    fetchBlockedUsersHandler();
    fetchAllUsers();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [selectedConversation?.messages, liveMessages]);

  // Keep WebSocket connection alive
  useEffect(() => {
    if (wsConnected) {
      const pingInterval = setInterval(ping, 30000); // Ping every 30 seconds
      return () => clearInterval(pingInterval);
    }
  }, [wsConnected, ping]);

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

  const fetchBlockedUsersHandler = async () => {
    try {
      const response = await getBlockedUsers();
      setBlockedUsers(response.data.blocked_users || []);
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du chargement des utilisateurs bloqués",
      });
    }
  };

  const fetchAllUsers = async () => {
    try {
      const response = await getUsers();
      setAllUsers(response.data || []);
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du chargement des utilisateurs",
      });
    }
  };

  const handleConversationClick = async (conversation) => {
    try {
      const response = await fetchMessages(conversation.id);
      setSelectedConversation({
        ...conversation,
        messages: response.data.messages || [],
      });
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
      };

      // Use WebSocket for real-time messaging if connected
      if (wsConnected) {
        sendWebSocketMessage(newMessage.trim());
        setNewMessage("");
        setSending(false);
        return;
      }

      // Fallback to REST API if WebSocket not connected
      const response = await apiSendMessage(
        selectedConversation.id,
        messageData
      );

      setSelectedConversation((prev) => ({
        ...prev,
        messages: [...(prev.messages || []), response.data],
      }));

      setNewMessage("");
      toast.success("Message envoyé avec succès");
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors de l'envoi du message",
      });
    } finally {
      setSending(false);
    }
  };

  const handleSendFile = async () => {
    if (!selectedFile || !selectedConversation) return;

    try {
      setFileUploading(true);

      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("conversation_id", selectedConversation.id);
      formData.append("message_type", "file");
      formData.append("content", `Fichier: ${selectedFile.name}`);

      const response = await apiSendFile(formData);

      setSelectedConversation((prev) => ({
        ...prev,
        messages: [...(prev.messages || []), response.data],
      }));

      setSelectedFile(null);
      toast.success("Fichier envoyé avec succès");
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors de l'envoi du fichier",
      });
    } finally {
      setFileUploading(false);
    }
  };

  const handleCreateConversation = async () => {
    if (!selectedUser) return;

    try {
      const conversationData = {
        name: `Conversation avec ${selectedUser.username}`,
        conversation_type: "direct",
        participant_ids: [selectedUser.id],
      };

      console.log("🔍 Creating conversation with data:", conversationData);
      console.log("🔍 Selected user:", selectedUser);

      const response = await apiCreateConversation(conversationData);

      setConversations((prev) => [...prev, response.data]);
      setShowCreateDialog(false);
      setSelectedUser(null);
      toast.success("Conversation créée avec succès");
    } catch (error) {
      console.error("🚨 Create conversation error:", error);
      console.error("🚨 Error response:", error.response?.data);
      console.error("🚨 Error status:", error.response?.status);

      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors de la création de la conversation",
      });
    }
  };

  const handleBlockUser = async () => {
    if (!selectedUser) return;

    try {
      await apiBlockUser(selectedUser.id, blockReason);

      setBlockedUsers((prev) => [
        ...prev,
        {
          id: selectedUser.id,
          username: selectedUser.username,
          reason: blockReason,
          blocked_at: new Date().toISOString(),
        },
      ]);

      setShowBlockDialog(false);
      setSelectedUser(null);
      setBlockReason("");
      toast.success("Utilisateur bloqué avec succès");
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du blocage de l'utilisateur",
      });
    }
  };

  const handleUnblockUser = async (userId) => {
    try {
      await apiUnblockUser(userId);
      setBlockedUsers((prev) => prev.filter((user) => user.id !== userId));
      toast.success("Utilisateur débloqué avec succès");
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du déblocage de l'utilisateur",
      });
    }
  };

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
    } else if (diffInHours < 168) {
      // 7 days
      return date.toLocaleDateString("fr-FR", {
        weekday: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    } else {
      return date.toLocaleDateString("fr-FR");
    }
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

  const getMessageIcon = (messageType) => {
    switch (messageType) {
      case "file":
        return <FileText className="h-4 w-4 text-blue-500" />;
      case "image":
        return <Image className="h-4 w-4 text-green-500" />;
      case "video":
        return <Video className="h-4 w-4 text-purple-500" />;
      case "audio":
        return <Mic className="h-4 w-4 text-orange-500" />;
      default:
        return null;
    }
  };

  const getMessageStatusIcon = (status) => {
    switch (status) {
      case "sent":
        return <CheckCircle2 className="h-3 w-3 text-gray-400" />;
      case "delivered":
        return <CheckCircle2 className="h-3 w-3 text-blue-400" />;
      case "read":
        return <CheckCircle2 className="h-3 w-3 text-green-400" />;
      default:
        return <Clock className="h-3 w-3 text-gray-400" />;
    }
  };

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Validate file size (10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        toast.error("Le fichier est trop volumineux (max 10MB)");
        return;
      }
      setSelectedFile(file);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (selectedFile) {
        handleSendFile();
      } else {
        handleSendMessage();
      }
    }
  };

  const filteredConversations = conversations.filter((conversation) => {
    const matchesSearch =
      conversation.name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
      conversation.participants?.some((p) =>
        p.username?.toLowerCase().includes(searchTerm.toLowerCase())
      );

    if (filter === "all") return matchesSearch;
    if (filter === "active")
      return matchesSearch && conversation.status === "active";
    if (filter === "blocked")
      return matchesSearch && conversation.status === "blocked";
    return matchesSearch;
  });

  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Messagerie</h1>
        <p className="text-gray-600">
          Gérer les conversations et partager des fichiers avec vos utilisateurs
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Conversations */}
        <div className="lg:col-span-3">
          <Card className="h-[calc(100vh-200px)]">
            <CardHeader className="border-b">
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="h-5 w-5" />
                  Conversations
                </CardTitle>
                <div className="flex gap-2">
                  <Button
                    onClick={() => setShowCreateDialog(true)}
                    className="bg-[#38ada9] hover:bg-[#3c6382] text-white"
                    size="sm"
                  >
                    <UserPlus className="h-4 w-4 mr-2" />
                    Nouvelle
                  </Button>
                  <Button
                    onClick={() => setShowBlockDialog(true)}
                    variant="outline"
                    className="text-red-600 border-red-200 hover:bg-red-50"
                    size="sm"
                  >
                    <Shield className="h-4 w-4 mr-2" />
                    Bloquer
                  </Button>
                </div>
              </div>
            </CardHeader>

            <div className="flex h-full">
              {/* Conversations List */}
              <div className="w-1/3 border-r flex flex-col">
                <div className="p-4 border-b">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                    <Input
                      placeholder="Rechercher..."
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                      className="pl-10 h-10"
                    />
                  </div>
                  <div className="flex gap-1 mt-3">
                    <Button
                      variant={filter === "all" ? "default" : "ghost"}
                      size="sm"
                      onClick={() => setFilter("all")}
                      className="text-xs px-3"
                    >
                      Toutes
                    </Button>
                    <Button
                      variant={filter === "active" ? "default" : "ghost"}
                      size="sm"
                      onClick={() => setFilter("active")}
                      className="text-xs px-3"
                    >
                      Actives
                    </Button>
                    <Button
                      variant={filter === "blocked" ? "default" : "ghost"}
                      size="sm"
                      onClick={() => setFilter("blocked")}
                      className="text-xs px-3"
                    >
                      Bloquées
                    </Button>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto">
                  {loading ? (
                    <div className="text-center py-8">
                      <Loader2 className="h-8 w-8 animate-spin mx-auto mb-2 text-blue-600" />
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
                        <div
                          key={conversation.id}
                          className={`p-3 rounded-lg cursor-pointer transition-all hover:bg-gray-50 ${
                            selectedConversation?.id === conversation.id
                              ? "bg-blue-50 border border-blue-200"
                              : ""
                          }`}
                          onClick={() => handleConversationClick(conversation)}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1 min-w-0">
                              <h3 className="font-semibold text-sm truncate">
                                {conversation.name ||
                                  conversation.participants
                                    ?.map((p) => p.username)
                                    .join(", ") ||
                                  "Conversation"}
                              </h3>
                              <p className="text-xs text-gray-600 truncate mt-1">
                                {conversation.last_message?.content ||
                                  "Aucun message"}
                              </p>
                            </div>
                            <div className="text-right ml-2">
                              <p className="text-xs text-gray-500">
                                {formatDate(
                                  conversation.last_message?.created_at
                                )}
                              </p>
                              <Badge
                                className={`${getStatusColor(
                                  conversation.status
                                )} text-xs mt-1`}
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
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 flex flex-col">
                {selectedConversation ? (
                  <>
                    {/* Messages Header */}
                    <div className="p-4 border-b bg-gray-50">
                      <h3 className="font-semibold">
                        {selectedConversation.name ||
                          selectedConversation.participants
                            ?.map((p) => p.username)
                            .join(", ")}
                      </h3>
                      <p className="text-sm text-gray-600">
                        {selectedConversation.participants?.length || 0}{" "}
                        participant(s)
                      </p>
                    </div>

                    {/* Messages List */}
                    <div className="flex-1 overflow-y-auto p-4 space-y-4">
                      {/* Connection Status */}
                      <div className="flex items-center justify-center mb-2">
                        <div
                          className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs ${
                            wsConnected
                              ? "bg-green-100 text-green-800 border border-green-200"
                              : "bg-red-100 text-red-800 border border-red-200"
                          }`}
                        >
                          {wsConnected ? (
                            <Wifi className="h-3 w-3" />
                          ) : (
                            <WifiOff className="h-3 w-3" />
                          )}
                          {wsConnected
                            ? "Connecté en temps réel"
                            : "Mode hors ligne"}
                        </div>
                      </div>

                      {/* Merge live messages with existing messages */}
                      {(() => {
                        const allMessages = [
                          ...(selectedConversation.messages || []),
                          ...liveMessages.filter(
                            (lm) =>
                              !selectedConversation.messages?.some(
                                (em) => em.id === lm.id
                              )
                          ),
                        ].sort(
                          (a, b) =>
                            new Date(a.created_at) - new Date(b.created_at)
                        );

                        return allMessages.map((message, index) => (
                          <div
                            key={
                              message.id
                                ? `${message.id}-${message.created_at || index}`
                                : `temp-${index}-${Date.now()}`
                            }
                            className={`flex ${
                              message.sender_id === 1
                                ? "justify-end"
                                : "justify-start"
                            }`}
                          >
                            <div
                              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                                message.sender_id === 1
                                  ? "bg-blue-500 text-white"
                                  : "bg-gray-200 text-gray-900"
                              }`}
                            >
                              <div className="flex items-center gap-2 mb-1">
                                {getMessageIcon(message.message_type)}
                                <span className="text-xs opacity-75 font-medium">
                                  {message.sender_username || "Utilisateur"}
                                </span>
                              </div>
                              <p className="text-sm">{message.content}</p>
                              <div className="flex items-center justify-between mt-2">
                                <p className="text-xs opacity-75">
                                  {formatDate(message.created_at)}
                                </p>
                                {message.sender_id === 1 && (
                                  <div className="ml-2">
                                    {getMessageStatusIcon(message.status)}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        ));
                      })()}
                      <div ref={messagesEndRef} />
                    </div>

                    {/* Message Input */}
                    <div className="p-4 border-t bg-gray-50">
                      {selectedFile && (
                        <div className="flex items-center gap-3 p-3 bg-blue-50 rounded-lg mb-3">
                          <FileText className="h-5 w-5 text-blue-500 flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">
                              {selectedFile.name}
                            </p>
                            <p className="text-xs text-gray-600">
                              {formatFileSize(selectedFile.size)}
                            </p>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setSelectedFile(null)}
                            className="flex-shrink-0"
                          >
                            <XCircle className="h-4 w-4" />
                          </Button>
                        </div>
                      )}

                      <div className="flex gap-2">
                        <div className="flex-1">
                          <Input
                            value={newMessage}
                            onChange={(e) => setNewMessage(e.target.value)}
                            placeholder="Tapez votre message..."
                            onKeyPress={handleKeyPress}
                            className="h-10"
                            disabled={sending || fileUploading}
                          />
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => fileInputRef.current?.click()}
                          disabled={sending || fileUploading}
                          className="px-3"
                        >
                          <Paperclip className="h-4 w-4" />
                        </Button>
                        <Button
                          onClick={
                            selectedFile ? handleSendFile : handleSendMessage
                          }
                          disabled={
                            (!newMessage.trim() && !selectedFile) ||
                            sending ||
                            fileUploading
                          }
                          className="bg-[#38ada9] hover:bg-[#3c6382] text-white px-4"
                        >
                          {sending || fileUploading ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Send className="h-4 w-4" />
                          )}
                        </Button>
                      </div>

                      <input
                        ref={fileInputRef}
                        type="file"
                        className="hidden"
                        onChange={handleFileSelect}
                        accept="image/*,video/*,audio/*,.pdf,.doc,.docx,.txt,.zip,.rar"
                      />
                    </div>
                  </>
                ) : (
                  <div className="flex-1 flex items-center justify-center text-gray-500">
                    <div className="text-center">
                      <MessageSquare className="h-16 w-16 mx-auto mb-4 text-gray-300" />
                      <p className="text-lg font-medium">
                        Sélectionnez une conversation
                      </p>
                      <p className="text-sm">
                        Choisissez une conversation pour commencer à discuter
                      </p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </Card>
        </div>

        {/* Utilisateurs bloqués */}
        <div>
          <Card className="h-[calc(100vh-200px)]">
            <CardHeader className="border-b">
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Utilisateurs bloqués
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <div className="h-full overflow-y-auto">
                {blockedUsers.length === 0 ? (
                  <div className="text-center text-gray-500 py-8">
                    <Shield className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                    <p className="text-sm">Aucun utilisateur bloqué</p>
                  </div>
                ) : (
                  <div className="space-y-1 p-4">
                    {blockedUsers.map((user) => (
                      <div key={user.id} className="border rounded-lg p-3">
                        <div className="flex items-center justify-between">
                          <div className="flex-1 min-w-0">
                            <h4 className="font-medium text-sm">
                              {user.username}
                            </h4>
                            <p className="text-xs text-gray-600 truncate">
                              {user.reason || "Aucune raison spécifiée"}
                            </p>
                            <p className="text-xs text-gray-500 mt-1">
                              {formatDate(user.blocked_at)}
                            </p>
                          </div>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleUnblockUser(user.id)}
                            className="ml-2 text-green-600 border-green-200 hover:bg-green-50"
                          >
                            <UserMinus className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Dialog pour créer une conversation */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Créer une nouvelle conversation</DialogTitle>
            <DialogDescription>
              Sélectionnez un utilisateur pour créer une conversation privée
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="user">Sélectionner un utilisateur</Label>
              <Select
                value={selectedUser?.id?.toString() || ""}
                onValueChange={(value) => {
                  const user = allUsers.find((u) => u.id.toString() === value);
                  setSelectedUser(user);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choisir un utilisateur" />
                </SelectTrigger>
                <SelectContent>
                  {allUsers
                    .filter(
                      (user) =>
                        !conversations.some((conv) =>
                          conv.participants?.some((p) => p.id === user.id)
                        )
                    )
                    .map((user) => (
                      <SelectItem key={user.id} value={user.id.toString()}>
                        {user.username} ({user.email})
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setShowCreateDialog(false);
                  setSelectedUser(null);
                }}
              >
                Annuler
              </Button>
              <Button
                onClick={handleCreateConversation}
                disabled={!selectedUser}
                className="bg-[#38ada9] hover:bg-[#3c6382] text-white"
              >
                Créer la conversation
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
            <DialogDescription>
              Sélectionnez un utilisateur et spécifiez une raison pour le
              bloquer
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="user-block">Sélectionner un utilisateur</Label>
              <Select
                value={selectedUser?.id?.toString() || ""}
                onValueChange={(value) => {
                  const user = allUsers.find((u) => u.id.toString() === value);
                  setSelectedUser(user);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choisir un utilisateur" />
                </SelectTrigger>
                <SelectContent>
                  {allUsers
                    .filter(
                      (user) =>
                        !blockedUsers.some((blocked) => blocked.id === user.id)
                    )
                    .map((user) => (
                      <SelectItem key={user.id} value={user.id.toString()}>
                        {user.username} ({user.email})
                      </SelectItem>
                    ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="reason">Raison du blocage (optionnel)</Label>
              <Textarea
                id="reason"
                value={blockReason}
                onChange={(e) => setBlockReason(e.target.value)}
                placeholder="Spécifiez la raison du blocage..."
                rows={3}
                className="resize-none"
              />
            </div>
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setShowBlockDialog(false);
                  setSelectedUser(null);
                  setBlockReason("");
                }}
              >
                Annuler
              </Button>
              <Button
                onClick={handleBlockUser}
                disabled={!selectedUser}
                variant="destructive"
              >
                <Shield className="h-4 w-4 mr-2" />
                Bloquer l'utilisateur
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MessagingPage;
