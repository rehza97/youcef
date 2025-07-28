import { useQuery } from "@tanstack/react-query";
import { messagingAPI } from "../../services/api";
import { useChatWebSocket } from "../../hooks/useChatWebSocket";

export default function ChatWindow({ conversation }) {
  const {
    data: initialMessages = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ["messages", conversation?.id],
    queryFn: async () => {
      const response = await messagingAPI.fetchMessages(conversation.id);
      return response.data;
    },
    enabled: !!conversation,
  });

  const { messages: liveMessages, sendMessage } = useChatWebSocket(
    conversation?.id
  );

  // Merge initial and live messages (avoid duplicates by id)
  const allMessages = [
    ...initialMessages,
    ...liveMessages.filter(
      (lm) => !initialMessages.some((im) => im.id === lm.id)
    ),
  ];

  if (!conversation) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400">
        Sélectionnez une conversation
      </div>
    );
  }

  if (isLoading)
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400">
        Chargement...
      </div>
    );
  if (error)
    return (
      <div className="flex-1 flex items-center justify-center text-red-400">
        Erreur lors du chargement
      </div>
    );

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="p-4 border-b font-bold">
        {conversation.name || "Sans titre"}
      </div>
      <div className="flex-1 overflow-y-auto bg-gray-50">
        {allMessages.length === 0 ? (
          <div className="p-4 text-gray-500">Aucun message</div>
        ) : (
          <ul className="space-y-2 p-4">
            {allMessages.map((msg) => (
              <li
                key={msg.id || msg.temp_id}
                className="bg-white rounded p-2 shadow-sm"
              >
                <div className="font-semibold">{msg.sender_username}</div>
                <div>{msg.content}</div>
                <div className="text-xs text-gray-400 mt-1">
                  {msg.created_at}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
