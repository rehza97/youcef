export default function ParticipantsList({ participants = [] }) {
  return (
    <div className="p-4 border-t">
      <div className="font-bold mb-2">Participants</div>
      <ul className="flex flex-wrap gap-2">
        {participants.length === 0 && (
          <li className="text-gray-500">Aucun participant</li>
        )}
        {participants.map((user) => (
          <li key={user.id} className="bg-gray-100 rounded px-2 py-1 text-sm">
            {user.username}
          </li>
        ))}
      </ul>
    </div>
  );
}
