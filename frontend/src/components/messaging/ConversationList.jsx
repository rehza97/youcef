import { useQuery } from "@tanstack/react-query";
import { fetchConversations } from "../../services/api";

export default function ConversationList({ onSelect }) {
  const {
    data: conversations = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ["conversations"],
    queryFn: async () => {
      const response = await fetchConversations();
      return response.data;
    },
  });

  if (isLoading) return <div className="p-4 text-gray-500">Chargement...</div>;
  if (error)
    return <div className="p-4 text-red-500">Erreur lors du chargement</div>;

  return (
    <aside className="w-72 border-r h-full bg-white">
      <div className="p-4 font-bold border-b">Conversations</div>
      <ul className="divide-y divide-gray-200">
        {conversations.length === 0 && (
          <li className="p-4 text-gray-500">Aucune conversation</li>
        )}
        {conversations.map((conv) => (
          <li
            key={conv.id}
            className="p-4 hover:bg-gray-50 cursor-pointer"
            onClick={() => onSelect && onSelect(conv)}
          >
            <div className="font-semibold">{conv.name || "Sans titre"}</div>
            <div className="text-xs text-gray-400 mt-1">
              {conv.last_message?.created_at || ""}
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
