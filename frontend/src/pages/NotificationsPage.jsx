import NotificationList from "../components/notifications/NotificationList";
import NotificationPreferences from "../components/notifications/NotificationPreferences";

export default function NotificationsPage() {
  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-4">Centre de notifications</h1>
      <NotificationList />
      <div className="mt-8">
        <NotificationPreferences />
      </div>
    </div>
  );
}
