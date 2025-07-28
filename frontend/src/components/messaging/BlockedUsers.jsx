export default function BlockedUsers({ blockedUsers = [] }) {
  return (
    <div className="p-4">
      <div className="font-bold mb-2">Utilisateurs bloqués</div>
      <ul className="flex flex-col gap-2">
        {blockedUsers.length === 0 && (
          <li className="text-gray-500">Aucun utilisateur bloqué</li>
        )}
        {blockedUsers.map((user) => (
          <li key={user.id} className="bg-gray-100 rounded px-2 py-1 text-sm">
            {user.username}
          </li>
        ))}
      </ul>
    </div>
  );
}
