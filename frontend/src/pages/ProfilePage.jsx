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

const ProfilePage = () => {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [userRoles, setUserRoles] = useState([]);
  const [editForm, setEditForm] = useState({});
  const { user: currentUser, updateUser } = useAuth();

  useEffect(() => {
    fetchProfile();
    fetchUserRoles();
  }, []);

  const fetchProfile = async () => {
    try {
      setLoading(true);
      const response = await usersAPI.getCurrentUser();
      setProfile(response.data);
      setEditForm({
        first_name: response.data.first_name || "",
        last_name: response.data.last_name || "",
        email: response.data.email || "",
        bio: response.data.bio || "",
        avatar_url: response.data.avatar_url || "",
      });
    } catch (error) {
      console.error("Erreur lors du chargement du profil:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchUserRoles = async () => {
    if (!currentUser?.id) return;

    try {
      const response = await usersAPI.getUserRoles(currentUser.id);
      setUserRoles(response.data);
    } catch (error) {
      console.error("Erreur lors du chargement des rôles:", error);
    }
  };

  const handleEdit = () => {
    setEditing(true);
  };

  const handleCancel = () => {
    setEditing(false);
    setEditForm({
      first_name: profile.first_name || "",
      last_name: profile.last_name || "",
      email: profile.email || "",
      bio: profile.bio || "",
      avatar_url: profile.avatar_url || "",
    });
  };

  const handleSave = async () => {
    try {
      const response = await usersAPI.updateCurrentUser(editForm);
      setProfile(response.data);
      setEditing(false);

      // Mettre à jour le contexte d'authentification
      if (updateUser) {
        updateUser(response.data);
      }

      alert("Profil mis à jour avec succès");
    } catch (error) {
      console.error("Erreur lors de la mise à jour du profil:", error);
      alert("Erreur lors de la mise à jour du profil");
    }
  };

  const handleInputChange = (field, value) => {
    setEditForm((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const formatDate = (dateString) => {
    if (!dateString) return "N/A";
    return new Date(dateString).toLocaleDateString("fr-FR", {
      year: "numeric",
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
          <p>Chargement du profil...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Profil</h1>
        <p className="text-gray-600">
          Gérer votre profil utilisateur et les paramètres du compte
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Informations principales */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Informations Personnelles</CardTitle>
                <Button
                  variant={editing ? "outline" : "default"}
                  onClick={editing ? handleCancel : handleEdit}
                >
                  {editing ? "Annuler" : "Modifier"}
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {editing ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Prénom
                      </label>
                      <Input
                        value={editForm.first_name}
                        onChange={(e) =>
                          handleInputChange("first_name", e.target.value)
                        }
                        placeholder="Votre prénom"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium mb-1">
                        Nom
                      </label>
                      <Input
                        value={editForm.last_name}
                        onChange={(e) =>
                          handleInputChange("last_name", e.target.value)
                        }
                        placeholder="Votre nom"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Email
                    </label>
                    <Input
                      type="email"
                      value={editForm.email}
                      onChange={(e) =>
                        handleInputChange("email", e.target.value)
                      }
                      placeholder="votre.email@exemple.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Bio
                    </label>
                    <Input
                      value={editForm.bio}
                      onChange={(e) => handleInputChange("bio", e.target.value)}
                      placeholder="Parlez-nous de vous..."
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      URL de l'avatar
                    </label>
                    <Input
                      value={editForm.avatar_url}
                      onChange={(e) =>
                        handleInputChange("avatar_url", e.target.value)
                      }
                      placeholder="https://exemple.com/avatar.jpg"
                    />
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleSave}>Sauvegarder</Button>
                    <Button variant="outline" onClick={handleCancel}>
                      Annuler
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-600">
                        Prénom
                      </label>
                      <p className="text-gray-900">
                        {profile.first_name || "Non défini"}
                      </p>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-600">
                        Nom
                      </label>
                      <p className="text-gray-900">
                        {profile.last_name || "Non défini"}
                      </p>
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600">
                      Email
                    </label>
                    <p className="text-gray-900">{profile.email}</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-600">
                      Bio
                    </label>
                    <p className="text-gray-900">
                      {profile.bio || "Aucune bio"}
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Informations du compte */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Informations du Compte</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex items-center gap-3">
                  <Avatar className="w-16 h-16">
                    <AvatarImage src={profile.avatar_url} />
                    <AvatarFallback>
                      {profile.username?.charAt(0).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                  <div>
                    <h3 className="font-semibold">{profile.username}</h3>
                    <p className="text-sm text-gray-600">Nom d'utilisateur</p>
                  </div>
                </div>

                <Separator />

                <div className="space-y-3">
                  <div>
                    <label className="block text-sm font-medium text-gray-600">
                      Statut
                    </label>
                    <Badge
                      variant={profile.is_active ? "default" : "secondary"}
                    >
                      {profile.is_active ? "Actif" : "Inactif"}
                    </Badge>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-600">
                      Type de compte
                    </label>
                    <div className="flex gap-1 mt-1">
                      {profile.is_staff && (
                        <Badge variant="outline">Staff</Badge>
                      )}
                      {profile.is_superuser && (
                        <Badge variant="destructive">Admin</Badge>
                      )}
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-600">
                      Date d'inscription
                    </label>
                    <p className="text-sm text-gray-900">
                      {formatDate(profile.date_joined)}
                    </p>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-600">
                      Dernière connexion
                    </label>
                    <p className="text-sm text-gray-900">
                      {formatDate(profile.last_login)}
                    </p>
                  </div>
                </div>

                <Separator />

                <div>
                  <label className="block text-sm font-medium text-gray-600 mb-2">
                    Rôles
                  </label>
                  {userRoles.length === 0 ? (
                    <p className="text-sm text-gray-500">Aucun rôle attribué</p>
                  ) : (
                    <div className="space-y-1">
                      {userRoles.map((userRole) => (
                        <Badge key={userRole.id} variant="outline">
                          {userRole.role?.name || "Rôle inconnu"}
                        </Badge>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Statistiques du compte */}
      <div className="mt-6">
        <Card>
          <CardHeader>
            <CardTitle>Statistiques du Compte</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {profile.id}
                </div>
                <div className="text-sm text-gray-600">ID Utilisateur</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">
                  {userRoles.length}
                </div>
                <div className="text-sm text-gray-600">Rôles attribués</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-600">
                  {profile.is_active ? "Oui" : "Non"}
                </div>
                <div className="text-sm text-gray-600">Compte actif</div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ProfilePage;
