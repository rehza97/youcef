import { useEffect, useState } from "react";
import { usersAPI } from "../services/api";
import PageHeader from "../components/PageHeader";
import { Button } from "@/components/ui/button";

export default function PermissionsPage() {
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    usersAPI.getPermissions().then((res) => {
      setPermissions(res.data);
      setLoading(false);
    });
  }, []);

  return (
    <div className="w-full p-4 sm:p-8 flex flex-col items-center">
      <div className="w-full max-w-3xl">
        <PageHeader title="Gestion des permissions">
          <Button className="ml-auto bg-[#38ada9] hover:bg-[#3c6382] text-white">
            + Ajouter une permission
          </Button>
        </PageHeader>
        <div className="bg-white p-6 rounded-xl shadow-md">
          <h2 className="text-xl font-semibold mb-4">
            Permissions ({permissions.length})
          </h2>
          {loading ? (
            <div className="animate-pulse h-8 bg-gray-100 rounded mb-2 w-1/2" />
          ) : permissions.length === 0 ? (
            <div className="text-gray-500">Aucune permission trouvée.</div>
          ) : (
            <div className="space-y-2">
              {permissions.map((perm) => (
                <div
                  key={perm.id}
                  className="p-4 bg-gray-50 rounded flex flex-col sm:flex-row sm:items-center justify-between hover:bg-gray-100 transition"
                >
                  <div>
                    <p className="font-medium">{perm.codename}</p>
                    <p className="text-sm text-gray-600">{perm.description}</p>
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
