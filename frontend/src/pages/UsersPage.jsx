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
import { Avatar, AvatarFallback, AvatarImage } from "../components/ui/avatar";
import { Separator } from "../components/ui/separator";
import { useAuth } from "../contexts/AuthContext";

const UsersPage = () => {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedUser, setSelectedUser] = useState(null);
  const [showUserDetails, setShowUserDetails] = useState(false);
  const { user: currentUser } = useAuth();

  useEffect(() => {
    fetchUsers();
    fetchRoles();
  }, []);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await usersAPI.getUsers();
      setUsers(response.data);
    } catch (error) {
      console.error("Erreur lors du chargement des utilisateurs:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchRoles = async () => {
    try {
      const response = await usersAPI.getRoles();
      setRoles(response.data);
    } catch (error) {
      console.error("Erreur lors du chargement des rôles:", error);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      fetchUsers();
      return;
    }

    try {
      setLoading(true);
      const response = await usersAPI.searchUsers(searchQuery);
      setUsers(response.data);
    } catch (error) {
      console.error("Erreur lors de la recherche:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleAssignRole = async (userId, roleId) => {
    try {
      await usersAPI.assignRole({ user_id: userId, role_id: roleId });
      // Rafraîchir la liste des utilisateurs
      fetchUsers();
    } catch (error) {
      console.error("Erreur lors de l'attribution du rôle:", error);
    }
  };

  const handleUserClick = (user) => {
    setSelectedUser(user);
    setShowUserDetails(true);
  };

  const filteredUsers = users.filter(
    (user) =>
      user.username.toLowerCase().includes(searchQuery.toLowerCase()) ||
      user.email.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Utilisateurs</h1>
        <p className="text-gray-600">
          Gérer les comptes utilisateurs et les permissions
        </p>
      </div>

      {/* Barre de recherche */}
      <Card className="mb-6">
        <CardContent className="p-4">
          <div className="flex gap-4">
            <Input
              placeholder="Rechercher par nom d'utilisateur ou email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && handleSearch()}
              className="flex-1"
            />
            <Button onClick={handleSearch} disabled={loading}>
              {loading ? "Recherche..." : "Rechercher"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Liste des utilisateurs */}
      <div className="grid gap-4">
        {loading ? (
          <Card>
            <CardContent className="p-6">
              <div className="text-center">Chargement des utilisateurs...</div>
            </CardContent>
          </Card>
        ) : filteredUsers.length === 0 ? (
          <Card>
            <CardContent className="p-6">
              <div className="text-center text-gray-500">
                Aucun utilisateur trouvé
              </div>
            </CardContent>
          </Card>
        ) : (
          filteredUsers.map((user) => (
            <Card key={user.id} className="hover:shadow-md transition-shadow">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <Avatar>
                      <AvatarImage src={user.avatar_url} />
                      <AvatarFallback>
                        {user.username.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <h3 className="font-semibold text-lg">{user.username}</h3>
                      <p className="text-gray-600">{user.email}</p>
                      <div className="flex gap-2 mt-1">
                        {user.is_active ? (
                          <Badge variant="default">Actif</Badge>
                        ) : (
                          <Badge variant="secondary">Inactif</Badge>
                        )}
                        {user.is_staff && (
                          <Badge variant="outline">Staff</Badge>
                        )}
                        {user.is_superuser && (
                          <Badge variant="destructive">Admin</Badge>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleUserClick(user)}
                    >
                      Détails
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Modal de détails utilisateur */}
      {showUserDetails && selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h2 className="text-xl font-bold mb-4">Détails de l'utilisateur</h2>
            <div className="space-y-3">
              <div>
                <strong>Nom d'utilisateur:</strong> {selectedUser.username}
              </div>
              <div>
                <strong>Email:</strong> {selectedUser.email}
              </div>
              <div>
                <strong>Prénom:</strong>{" "}
                {selectedUser.first_name || "Non défini"}
              </div>
              <div>
                <strong>Nom:</strong> {selectedUser.last_name || "Non défini"}
              </div>
              <div>
                <strong>Date d'inscription:</strong>{" "}
                {new Date(selectedUser.date_joined).toLocaleDateString("fr-FR")}
              </div>
              <div>
                <strong>Dernière connexion:</strong>{" "}
                {selectedUser.last_login
                  ? new Date(selectedUser.last_login).toLocaleDateString(
                      "fr-FR"
                    )
                  : "Jamais"}
              </div>
            </div>

            <Separator className="my-4" />

            <div className="mb-4">
              <h3 className="font-semibold mb-2">Attribuer un rôle:</h3>
              <div className="flex gap-2 flex-wrap">
                {roles.map((role) => (
                  <Button
                    key={role.id}
                    variant="outline"
                    size="sm"
                    onClick={() => handleAssignRole(selectedUser.id, role.id)}
                  >
                    {role.name}
                  </Button>
                ))}
              </div>
            </div>

            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => setShowUserDetails(false)}
              >
                Fermer
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default UsersPage;
