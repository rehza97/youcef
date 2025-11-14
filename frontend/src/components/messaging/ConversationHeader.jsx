import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Info, Users, MoreVertical, Phone, Video } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const ConversationHeader = ({ conversation, onDelete, onMute }) => {
  const [showInfo, setShowInfo] = useState(false);
  const [isMuted, setIsMuted] = useState(false);

  if (!conversation) {
    return null;
  }

  const participantsList = conversation.participants || [];
  const conversationName =
    conversation.name ||
    participantsList.map((p) => p.username).join(", ") ||
    "Conversation";

  return (
    <>
      <div className="p-4 border-b bg-gray-50 flex items-center justify-between">
        <div className="flex-1">
          <h3 className="font-semibold text-lg">{conversationName}</h3>
          <p className="text-sm text-gray-600">
            {participantsList.length} participant(s)
            {conversation.is_group && " • Groupe"}
          </p>
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowInfo(true)}
            className="text-blue-600 border-blue-200 hover:bg-blue-50"
          >
            <Info className="h-4 w-4 mr-2" />
            Infos
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => {
                  setIsMuted(!isMuted);
                  onMute?.(conversation.id, !isMuted);
                }}
              >
                {isMuted ? "Activer les notifications" : "Mettre en sourdine"}
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => onDelete?.(conversation.id)}
                className="text-red-600"
              >
                Supprimer la conversation
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Conversation Info Dialog */}
      <Dialog open={showInfo} onOpenChange={setShowInfo}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Informations de conversation</DialogTitle>
            <DialogDescription>
              Détails et participants de cette conversation
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6">
            {/* Conversation Details */}
            <div>
              <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                <Info className="h-4 w-4" />
                Conversation
              </h4>
              <div className="space-y-2 text-sm">
                <div>
                  <p className="text-gray-600">Nom</p>
                  <p className="font-medium">{conversationName}</p>
                </div>
                <div>
                  <p className="text-gray-600">Type</p>
                  <p className="font-medium">
                    {conversation.is_group ? "Groupe" : "Conversation directe"}
                  </p>
                </div>
                <div>
                  <p className="text-gray-600">Créée le</p>
                  <p className="font-medium">
                    {new Date(conversation.created_at).toLocaleDateString(
                      "fr-FR"
                    )}
                  </p>
                </div>
              </div>
            </div>

            {/* Participants */}
            <div>
              <h4 className="font-semibold text-sm mb-3 flex items-center gap-2">
                <Users className="h-4 w-4" />
                Participants ({participantsList.length})
              </h4>
              <div className="space-y-2">
                {participantsList.map((participant) => (
                  <div
                    key={participant.id}
                    className="flex items-center justify-between p-2 rounded-lg bg-gray-50 text-sm"
                  >
                    <div>
                      <p className="font-medium">{participant.username}</p>
                      <p className="text-xs text-gray-600">
                        {participant.email}
                      </p>
                    </div>
                    <div
                      className={`h-2 w-2 rounded-full ${
                        participant.is_online ? "bg-green-500" : "bg-gray-300"
                      }`}
                      title={
                        participant.is_online ? "En ligne" : "Hors ligne"
                      }
                    />
                  </div>
                ))}
              </div>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default ConversationHeader;
