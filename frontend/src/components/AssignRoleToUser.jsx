import { useEffect, useState } from "react";
import { getUsers, getRoles, assignRole } from "../services/api";
import { Button } from "@/components/ui/button";

export const AssignRoleToUser = () => {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [selectedUser, setSelectedUser] = useState("");
  const [selectedRole, setSelectedRole] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    const [usersRes, rolesRes] = await Promise.all([getUsers(), getRoles()]);
    setUsers(usersRes.data);
    setRoles(rolesRes.data);
    setLoading(false);
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    if (!selectedUser || !selectedRole) return;
    setLoading(true);
    await assignRole({ user_id: selectedUser, role_id: selectedRole });
    setMessage("Rôle attribué !");
    setLoading(false);
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow mt-8">
      <h2 className="text-xl font-semibold mb-4">
        Attribuer un rôle à un utilisateur
      </h2>
      {message && <div className="mb-4 text-green-600">{message}</div>}
      <form
        onSubmit={handleAssign}
        className="flex flex-col md:flex-row gap-4 items-center"
      >
        <select
          value={selectedUser}
          onChange={(e) => setSelectedUser(e.target.value)}
          className="border px-2 py-1 rounded"
          required
        >
          <option value="">Sélectionner un utilisateur</option>
          {users.map((user) => (
            <option key={user.id} value={user.id}>
              {user.username}
            </option>
          ))}
        </select>
        <select
          value={selectedRole}
          onChange={(e) => setSelectedRole(e.target.value)}
          className="border px-2 py-1 rounded"
          required
        >
          <option value="">Sélectionner un rôle</option>
          {roles.map((role) => (
            <option key={role.id} value={role.id}>
              {role.name}
            </option>
          ))}
        </select>
        <Button type="submit" disabled={loading}>
          {loading ? "Attribution..." : "Attribuer le rôle"}
        </Button>
      </form>
    </div>
  );
};
