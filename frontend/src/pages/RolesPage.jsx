import React, { useState, useEffect } from "react";
import { usersAPI } from "../services/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { useAuth } from "../contexts/AuthContext";

const RolesPage = () => {
  const [roles, setRoles] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreateRole, setShowCreateRole] = useState(false);
  const [selectedRole, setSelectedRole] = useState(null);
  const [newRole, setNewRole] = useState({ name: "", description: "" });
  const { user: currentUser } = useAuth();

  useEffect(() => {
    fetchRoles();
    fetchPermissions();
  }, []);

  const fetchRoles = async () => {
    try {
      setLoading(true);
      const response = await usersAPI.getRoles();
      setRoles(response.data);
    } catch (error) {
      console.error("Erreur lors du chargement des rôles:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchPermissions = async () => {
    try {
      const response = await usersAPI.getPermissions();
      setPermissions(response.data);
    } catch (error) {
      console.error("Erreur lors du chargement des permissions:", error);
    }
  };

  const handleCreateRole = async () => {
    if (!newRole.name.trim()) {
      alert("Le nom du rôle est requis");
      return;
    }

    try {
      await usersAPI.createRole(newRole);
      setNewRole({ name: "", description: "" });
      setShowCreateRole(false);
      fetchRoles();
    } catch (error) {
      console.error("Erreur lors de la création du rôle:", error);
    }
  };

  const handleRoleClick = (role) => {
    setSelectedRole(role);
  };

  const handleUpdateRolePermissions = async (roleId, permissionIds) => {
    try {
      await usersAPI.updateRolePermissions(roleId, permissionIds);
      alert("Permissions mises à jour avec succès");
    } catch (error) {
      console.error("Erreur lors de la mise à jour des permissions:", error);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Rôles</h1>
        <p className="text-gray-600">
          Configurer les rôles utilisateurs et leurs permissions associées
        </p>
      </div>

      {/* Bouton pour créer un nouveau rôle */}
      <div className="mb-6">
        <Button onClick={() => setShowCreateRole(true)}>
          Créer un nouveau rôle
        </Button>
      </div>

      {/* Modal de création de rôle */}
      {showCreateRole && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Créer un nouveau rôle</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Nom du rôle
                </label>
                <Input
                  value={newRole.name}
                  onChange={(e) =>
                    setNewRole({ ...newRole, name: e.target.value })
                  }
                  placeholder="Nom du rôle"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">
                  Description
                </label>
                <Input
                  value={newRole.description}
                  onChange={(e) =>
                    setNewRole({ ...newRole, description: e.target.value })
                  }
                  placeholder="Description du rôle"
                />
              </div>
            </div>
            <div className="flex gap-2 justify-end mt-6">
              <Button
                variant="outline"
                onClick={() => setShowCreateRole(false)}
              >
                Annuler
              </Button>
              <Button onClick={handleCreateRole}>Créer le rôle</Button>
            </div>
          </div>
        </div>
      )}

      {/* Liste des rôles */}
      <div className="grid gap-4">
        {loading ? (
          <Card>
            <CardContent className="p-6">
              <div className="text-center">Chargement des rôles...</div>
            </CardContent>
          </Card>
        ) : roles.length === 0 ? (
          <Card>
            <CardContent className="p-6">
              <div className="text-center text-gray-500">Aucun rôle trouvé</div>
            </CardContent>
          </Card>
        ) : (
          roles.map((role) => (
            <Card key={role.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg">{role.name}</h3>
                    <p className="text-gray-600">
                      {role.description || "Aucune description"}
                    </p>
                    <div className="flex gap-2 mt-2">
                      <Badge variant="outline">ID: {role.id}</Badge>
                      {role.is_active !== undefined && (
                        <Badge
                          variant={role.is_active ? "default" : "secondary"}
                        >
                          {role.is_active ? "Actif" : "Inactif"}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRoleClick(role)}
                    >
                      Gérer les permissions
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Modal de gestion des permissions */}
      {selectedRole && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto">
            <h2 className="text-xl font-bold mb-4">
              Permissions pour le rôle: {selectedRole.name}
            </h2>

            <div className="mb-4">
              <p className="text-gray-600 mb-4">
                Sélectionnez les permissions à attribuer à ce rôle:
              </p>

              <div className="grid grid-cols-2 gap-2">
                {permissions.map((permission) => (
                  <div
                    key={permission.id}
                    className="flex items-center gap-2 p-2 border rounded"
                  >
                    <input
                      type="checkbox"
                      id={`permission-${permission.id}`}
                      className="rounded"
                    />
                    <label
                      htmlFor={`permission-${permission.id}`}
                      className="text-sm"
                    >
                      {permission.name}
                    </label>
                  </div>
                ))}
              </div>
            </div>

            <Separator className="my-4" />

            <div className="flex gap-2 justify-end">
              <Button variant="outline" onClick={() => setSelectedRole(null)}>
                Fermer
              </Button>
              <Button
                onClick={() => {
                  // Logique pour sauvegarder les permissions sélectionnées
                  const selectedPermissions = permissions
                    .filter(
                      (_, index) =>
                        document.getElementById(
                          `permission-${permissions[index].id}`
                        ).checked
                    )
                    .map((p) => p.id);

                  handleUpdateRolePermissions(
                    selectedRole.id,
                    selectedPermissions
                  );
                  setSelectedRole(null);
                }}
              >
                Sauvegarder les permissions
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default RolesPage;
