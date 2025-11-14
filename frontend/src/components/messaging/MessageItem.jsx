import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  FileText,
  Image,
  Video,
  Mic,
  CheckCircle2,
  Clock,
  MoreVertical,
  Smile,
  Download,
  Trash2,
  Edit,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import MessageReactions from "./MessageReactions";

const MessageItem = ({
  message,
  isSentByCurrentUser,
  currentUserId,
  onDelete,
  onEdit,
  onReact,
  onDownload,
}) => {
  const [showReactions, setShowReactions] = useState(false);
  const [hovered, setHovered] = useState(false);

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
      return date.toLocaleDateString("fr-FR", {
        weekday: "short",
        hour: "2-digit",
        minute: "2-digit",
      });
    } else {
      return date.toLocaleDateString("fr-FR");
    }
  };

  return (
    <div
      className={`flex ${isSentByCurrentUser ? "justify-end" : "justify-start"}`}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div
        className={`max-w-xs lg:max-w-md relative group ${
          isSentByCurrentUser ? "mr-2" : "ml-2"
        }`}
      >
        {/* Message Content */}
        <div
          className={`px-4 py-2 rounded-lg ${
            isSentByCurrentUser
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
            <p className="text-xs opacity-75">{formatDate(message.created_at)}</p>
            {isSentByCurrentUser && (
              <div className="ml-2">{getMessageStatusIcon(message.status)}</div>
            )}
          </div>
        </div>

        {/* Message Actions */}
        {hovered && (
          <div className="absolute -top-8 right-0 flex gap-1 bg-white border rounded-lg shadow-lg p-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowReactions(true)}
              className="h-6 w-6 p-0"
              title="Ajouter une réaction"
            >
              <Smile className="h-4 w-4" />
            </Button>

            {message.message_type === "file" && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onDownload?.(message)}
                className="h-6 w-6 p-0"
                title="Télécharger"
              >
                <Download className="h-4 w-4" />
              </Button>
            )}

            {isSentByCurrentUser && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    title="Plus d'options"
                  >
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => onEdit?.(message)}>
                    <Edit className="h-4 w-4 mr-2" />
                    Modifier
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    onClick={() => onDelete?.(message.id)}
                    className="text-red-600"
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Supprimer
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>
        )}

        {/* Message Reactions */}
        {message.reactions && message.reactions.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-2">
            {Object.entries(
              message.reactions.reduce((acc, reaction) => {
                acc[reaction.emoji] = (acc[reaction.emoji] || 0) + 1;
                return acc;
              }, {})
            ).map(([emoji, count]) => (
              <button
                key={emoji}
                className="px-2 py-1 bg-gray-100 rounded-full text-sm hover:bg-gray-200 transition-colors"
                onClick={() => onReact?.(message.id, emoji)}
                title={`${count} réaction(s)`}
              >
                {emoji} {count > 1 ? count : ""}
              </button>
            ))}
          </div>
        )}

        {/* Reactions Picker */}
        {showReactions && (
          <MessageReactions
            messageId={message.id}
            onReactionSelect={(emoji) => {
              onReact?.(message.id, emoji);
              setShowReactions(false);
            }}
            onClose={() => setShowReactions(false)}
          />
        )}
      </div>
    </div>
  );
};

export default MessageItem;
