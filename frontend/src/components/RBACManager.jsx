import { useEffect, useState } from "react";
import {
  getPermissions,
  createPermission,
  updatePermission,
  deletePermission,
  getRoles,
  createRole,
  updateRole,
  deleteRole,
  getRolePermissions,
  updateRolePermissions,
} from "../services/api";
import { Button } from "@/components/ui/button";

export const RBACManager = () => {
  const [permissions, setPermissions] = useState([]);
  const [roles, setRoles] = useState([]);
  const [selectedRole, setSelectedRole] = useState(null);
  const [selectedPermissions, setSelectedPermissions] = useState([]);
  const [newPermission, setNewPermission] = useState({
    codename: "",
    description: "",
  });
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    const [permsRes, rolesRes] = await Promise.all([
      getPermissions(),
      getRoles(),
    ]);
    setPermissions(permsRes.data);
    setRoles(rolesRes.data);
    setLoading(false);
  };

  const handleRoleSelect = (role) => {
    setSelectedRole(role);
    setSelectedPermissions(role.permissions.map((p) => p.id));
    setMessage("");
  };

  const handlePermissionToggle = (permId) => {
    setSelectedPermissions((prev) =>
      prev.includes(permId)
        ? prev.filter((id) => id !== permId)
        : [...prev, permId]
    );
  };

  const handleUpdateRolePermissions = async () => {
    if (!selectedRole) return;
    setLoading(true);
    await updateRolePermissions(selectedRole.id, selectedPermissions);
    setMessage("Permissions mises à jour !");
    fetchData();
    setLoading(false);
  };

  const handleCreatePermission = async (e) => {
    e.preventDefault();
    setLoading(true);
    await createPermission(newPermission);
    setNewPermission({ codename: "", description: "" });
    setMessage("Permission créée !");
    fetchData();
    setLoading(false);
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow mt-8">
      <h2 className="text-xl font-semibold mb-4">Gestion RBAC</h2>
      {message && <div className="mb-4 text-green-600">{message}</div>}
      <div className="grid md:grid-cols-2 gap-8">
        {/* Roles List */}
        <div>
          <h3 className="font-bold mb-2">Rôles</h3>
          <ul className="space-y-2">
            {roles.map((role) => (
              <li key={role.id}>
                <Button
                  variant={selectedRole?.id === role.id ? "default" : "outline"}
                  onClick={() => handleRoleSelect(role)}
                  className="w-full justify-start"
                >
                  {role.name}
                </Button>
              </li>
            ))}
          </ul>
        </div>
        {/* Permissions List & Assignment */}
        <div>
          <h3 className="font-bold mb-2">Permissions</h3>
          {selectedRole ? (
            <>
              <div className="mb-2 text-gray-700">
                Attribuer des permissions à <b>{selectedRole.name}</b> :
              </div>
              <div className="flex flex-wrap gap-2 mb-4">
                {permissions.map((perm) => (
                  <label key={perm.id} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={selectedPermissions.includes(perm.id)}
                      onChange={() => handlePermissionToggle(perm.id)}
                    />
                    <span>{perm.codename}</span>
                  </label>
                ))}
              </div>
              <Button onClick={handleUpdateRolePermissions} disabled={loading}>
                {loading ? "Enregistrement..." : "Enregistrer les permissions"}
              </Button>
            </>
          ) : (
            <div className="text-gray-500">
              Sélectionnez un rôle pour gérer les permissions.
            </div>
          )}
          <hr className="my-6" />
          <h4 className="font-semibold mb-2">Créer une nouvelle permission</h4>
          <form
            onSubmit={handleCreatePermission}
            className="flex flex-col gap-2"
          >
            <input
              type="text"
              placeholder="Code (ex: can_view_dashboard)"
              value={newPermission.codename}
              onChange={(e) =>
                setNewPermission({ ...newPermission, codename: e.target.value })
              }
              required
              className="border px-2 py-1 rounded"
            />
            <input
              type="text"
              placeholder="Description"
              value={newPermission.description}
              onChange={(e) =>
                setNewPermission({
                  ...newPermission,
                  description: e.target.value,
                })
              }
              className="border px-2 py-1 rounded"
            />
            <Button type="submit" disabled={loading}>
              {loading ? "Création..." : "Créer la permission"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
};
