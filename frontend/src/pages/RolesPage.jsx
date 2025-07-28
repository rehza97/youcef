import { useEffect, useState } from "react";
import { usersAPI } from "../services/api";
import PageHeader from "../components/PageHeader";
import { Button } from "@/components/ui/button";

export default function RolesPage() {
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    usersAPI.getRoles().then((res) => {
      setRoles(res.data);
      setLoading(false);
    });
  }, []);

  return (
    <div className="w-full p-4 sm:p-8 flex flex-col items-center">
      <div className="w-full max-w-3xl">
        <PageHeader title="Gestion des rôles">
          <Button className="ml-auto bg-[#38ada9] hover:bg-[#3c6382] text-white">
            + Ajouter un rôle
          </Button>
        </PageHeader>
        <div className="bg-white p-6 rounded-xl shadow-md">
          <h2 className="text-xl font-semibold mb-4">Rôles ({roles.length})</h2>
          {loading ? (
            <div className="animate-pulse h-8 bg-gray-100 rounded mb-2 w-1/2" />
          ) : roles.length === 0 ? (
            <div className="text-gray-500">Aucun rôle trouvé.</div>
          ) : (
            <div className="space-y-2">
              {roles.map((role) => (
                <div
                  key={role.id}
                  className="p-4 bg-gray-50 rounded flex flex-col sm:flex-row sm:items-center justify-between hover:bg-gray-100 transition"
                >
                  <div>
                    <p className="font-medium">{role.name}</p>
                    <p className="text-sm text-gray-600">{role.description}</p>
                  </div>
                  <Button size="sm" variant="outline" className="mt-2 sm:mt-0">
                    Modifier
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
