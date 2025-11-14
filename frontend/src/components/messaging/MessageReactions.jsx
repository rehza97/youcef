import React from "react";
import { Button } from "@/components/ui/button";
import { X } from "lucide-react";

const EMOJI_REACTIONS = [
  "👍",
  "❤️",
  "😂",
  "😮",
  "😢",
  "🔥",
  "👏",
  "🎉",
  "🤔",
  "👀",
  "😍",
  "😡",
];

const MessageReactions = ({ messageId, onReactionSelect, onClose }) => {
  return (
    <div className="absolute -top-14 right-0 bg-white border border-gray-200 rounded-lg shadow-lg p-2 z-50">
      <div className="flex gap-1 flex-wrap max-w-xs justify-center">
        {EMOJI_REACTIONS.map((emoji) => (
          <Button
            key={emoji}
            variant="ghost"
            size="sm"
            onClick={() => onReactionSelect(emoji)}
            className="h-8 w-8 p-0 text-lg hover:bg-gray-100"
          >
            {emoji}
          </Button>
        ))}
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={onClose}
        className="absolute top-1 right-1 h-5 w-5 p-0"
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  );
};

export default MessageReactions;
