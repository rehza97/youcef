import { useState } from "react";
import { useNotificationsWebSocket } from "../../hooks/useNotificationsWebSocket";
import { notificationsAPI } from "../../api/notifications";
import { useNavigate } from "react-router-dom";
// import { Bell } from 'lucide-react'; // If using lucide icons
// import { DropdownMenu, DropdownMenuTrigger, DropdownMenuContent } from '../ui/dropdown-menu';

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const { notifications } = useNotificationsWebSocket();
  const unreadCount = notifications.filter((n) => !n.is_read).length;
  const navigate = useNavigate();

  const handleNotificationClick = async (notif) => {
    if (!notif.is_read) {
      await notificationsAPI.markAsRead(notif.id);
    }
    if (notif.conversation_id) {
      navigate(`/messaging?conversation=${notif.conversation_id}`);
    }
  };

  return (
    <div className="relative">
      <button
        className="relative p-2 rounded-full hover:bg-gray-100 focus:outline-none"
        aria-label="Voir les notifications"
        onClick={() => setOpen((o) => !o)}
      >
        {/* Replace with Shadcn/Lucide bell icon */}
        <span role="img" aria-label="cloche">
          🔔
        </span>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5">
            {unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white border border-gray-200 rounded shadow-lg z-50">
          <div className="p-4 font-bold border-b">Notifications</div>
          <ul className="max-h-64 overflow-y-auto">
            {notifications.length === 0 ? (
              <li className="p-4 text-gray-500">Aucune notification</li>
            ) : (
              notifications.map((notif) => (
                <li
                  key={notif.id}
                  className={`p-4 border-b last:border-b-0 hover:bg-gray-50 cursor-pointer ${notif.is_read ? '' : 'bg-blue-50'}`}
                  onClick={() => handleNotificationClick(notif)}
                >
                  <div className="font-semibold">{notif.subject}</div>
                  <div className="text-sm text-gray-600">{notif.message}</div>
                  <div className="text-xs text-gray-400 mt-1">
                    {notif.created_at}
                  </div>
                </li>
              ))
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
