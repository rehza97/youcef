import { useQuery } from "@tanstack/react-query";
import { notificationsAPI } from "../../services/api";

export default function NotificationList() {
  const {
    data: notifications = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ["notifications"],
    queryFn: async () => {
      const response = await notificationsAPI.fetchNotifications();
      return response.data;
    },
  });

  if (isLoading) return <div className="p-4 text-gray-500">Chargement...</div>;
  if (error)
    return <div className="p-4 text-red-500">Erreur lors du chargement</div>;
  if (!notifications.length) {
    return <div className="p-4 text-gray-500">Aucune notification</div>;
  }
  return (
    <ul className="divide-y divide-gray-200">
      {notifications.map((notif) => (
        <li key={notif.id} className="p-4 hover:bg-gray-50 cursor-pointer">
          <div className="font-semibold">{notif.title}</div>
          <div className="text-sm text-gray-600">{notif.body}</div>
          <div className="text-xs text-gray-400 mt-1">{notif.created_at}</div>
        </li>
      ))}
    </ul>
  );
}
