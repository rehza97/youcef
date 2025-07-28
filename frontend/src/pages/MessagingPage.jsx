import { useState } from "react";
import ConversationList from "../components/messaging/ConversationList";
import ChatWindow from "../components/messaging/ChatWindow";
import MessageInput from "../components/messaging/MessageInput";
import ParticipantsList from "../components/messaging/ParticipantsList";
import { useChatWebSocket } from "../hooks/useChatWebSocket";

export default function MessagingPage() {
  const [selectedConversation, setSelectedConversation] = useState(null);
  const { sendMessage } = useChatWebSocket(selectedConversation?.id);

  return (
    <div className="flex h-[80vh] bg-white rounded shadow overflow-hidden">
      <ConversationList onSelect={setSelectedConversation} />
      <div className="flex flex-col flex-1">
        <ChatWindow conversation={selectedConversation} />
        <MessageInput
          conversation={selectedConversation}
          onSend={sendMessage}
        />
        <ParticipantsList participants={[]} />
      </div>
    </div>
  );
}
