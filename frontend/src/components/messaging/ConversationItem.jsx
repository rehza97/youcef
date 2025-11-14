import React from "react";
import { Badge } from "@/components/ui/badge";

const ConversationItem = ({
  conversation,
  isSelected,
  onClick,
  formatDate,
  getStatusColor,
}) => {
  return (
    <div
      className={`p-3 rounded-lg cursor-pointer transition-all hover:bg-gray-50 ${
        isSelected ? "bg-blue-50 border border-blue-200" : ""
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-sm truncate">
            {conversation.name ||
              conversation.participants?.map((p) => p.username).join(", ") ||
              "Conversation"}
          </h3>
          <p className="text-xs text-gray-600 truncate mt-1">
            {conversation.last_message?.content || "Aucun message"}
          </p>
          {conversation.unread_count > 0 && (
            <div className="mt-1">
              <Badge className="bg-red-500 text-white text-xs">
                {conversation.unread_count} nouveau
                {conversation.unread_count > 1 ? "x" : ""}
              </Badge>
            </div>
          )}
        </div>
        <div className="text-right ml-2">
          <p className="text-xs text-gray-500">
            {formatDate(conversation.last_message?.created_at)}
          </p>
          <Badge
            className={`${getStatusColor(conversation.status)} text-xs mt-1`}
          >
            {conversation.status === "active" ? "Active" : "Bloquée"}
          </Badge>
        </div>
      </div>
    </div>
  );
};

export default ConversationItem;
