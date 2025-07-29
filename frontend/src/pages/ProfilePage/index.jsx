import React, { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "../../components/ui/avatar";
import { Badge } from "../../components/ui/badge";
import { Separator } from "../../components/ui/separator";
import { useAuth } from "../../contexts/AuthContext";
import { usersAPI } from "../../services/api";
import { handleApiError } from "../../lib/error-handler";
import { toast } from "sonner";
import {
  User,
  Mail,
  Phone,
  MapPin,
  Calendar,
  Edit,
  Save,
  X,
  Camera,
  Loader2,
  AlertCircle,
  CheckCircle,
  Clock,
  Shield,
} from "lucide-react";

const ProfilePage = () => {
  const { user, updateUser } = useAuth();
  const [isEditing, setIsEditing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [profileData, setProfileData] = useState({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    phone: "",
    location: "",
    avatar: "",
  });
  const [originalData, setOriginalData] = useState({});
  const [validationErrors, setValidationErrors] = useState({});

  useEffect(() => {
    fetchUserProfile();
  }, []);

  const fetchUserProfile = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await usersAPI.getCurrentUser();
      const userData = response.data;

      // Map backend data to frontend format
      const mappedData = {
        username: userData.username || "",
        email: userData.email || "",
        first_name: userData.first_name || "",
        last_name: userData.last_name || "",
        phone: userData.phone || "",
        location: userData.location || "",
        avatar: userData.avatar || "",
      };

      setProfileData(mappedData);
      setOriginalData(mappedData);
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du chargement du profil",
      });
      setError("Impossible de charger le profil utilisateur");
    } finally {
      setLoading(false);
    }
  };

  const validateForm = () => {
    const errors = {};

    if (!profileData.email) {
      errors.email = "L'email est requis";
    } else if (!/\S+@\S+\.\S+/.test(profileData.email)) {
      errors.email = "Format d'email invalide";
    }

    if (!profileData.first_name) {
      errors.first_name = "Le prénom est requis";
    }

    if (!profileData.last_name) {
      errors.last_name = "Le nom est requis";
    }

    if (profileData.phone && !/^[\+]?[0-9\s\-\(\)]+$/.test(profileData.phone)) {
      errors.phone = "Format de téléphone invalide";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSave = async () => {
    if (!validateForm()) {
      toast.error("Veuillez corriger les erreurs de validation");
      return;
    }

    try {
      setSaving(true);

      // Prepare data for backend (only send changed fields)
      const updateData = {};
      Object.keys(profileData).forEach((key) => {
        if (profileData[key] !== originalData[key]) {
          updateData[key] = profileData[key];
        }
      });

      if (Object.keys(updateData).length === 0) {
        toast.info("Aucune modification à sauvegarder");
        setIsEditing(false);
        return;
      }

      const response = await usersAPI.updateCurrentUser(updateData);
      const updatedUser = response.data;

      // Update local state
      setProfileData((prev) => ({
        ...prev,
        ...updatedUser,
      }));
      setOriginalData((prev) => ({
        ...prev,
        ...updatedUser,
      }));

      // Update auth context
      if (updateUser) {
        updateUser(updatedUser);
      }

      setIsEditing(false);
      setValidationErrors({});
      toast.success("Profil mis à jour avec succès");
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors de la sauvegarde du profil",
      });
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setProfileData(originalData);
    setValidationErrors({});
    setIsEditing(false);
  };

  const handleInputChange = (field, value) => {
    setProfileData((prev) => ({
      ...prev,
      [field]: value,
    }));

    // Clear validation error when user starts typing
    if (validationErrors[field]) {
      setValidationErrors((prev) => ({
        ...prev,
        [field]: null,
      }));
    }
  };

  const getJoinDate = () => {
    if (!user?.created_at) return "N/A";
    return new Date(user.created_at).toLocaleDateString("fr-FR", {
      year: "numeric",
      month: "long",
    });
  };

  const getLastLogin = () => {
    if (!user?.last_login) return "Jamais";
    const lastLogin = new Date(user.last_login);
    const now = new Date();
    const diffInHours = Math.floor((now - lastLogin) / (1000 * 60 * 60));

    if (diffInHours < 1) return "À l'instant";
    if (diffInHours < 24)
      return `Il y a ${diffInHours} heure${diffInHours > 1 ? "s" : ""}`;
    return lastLogin.toLocaleDateString("fr-FR");
  };

  const getUserRoles = () => {
    if (!user?.roles || user.roles.length === 0) return ["Utilisateur"];
    return user.roles.map((role) => role.name);
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center space-y-4">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <p className="text-gray-600">Chargement du profil...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="flex items-center justify-center h-64">
          <div className="flex flex-col items-center space-y-4">
            <AlertCircle className="h-8 w-8 text-red-600" />
            <p className="text-gray-600">{error}</p>
            <Button onClick={fetchUserProfile} variant="outline">
              Réessayer
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Profil</h1>
        <p className="text-gray-600 mt-2">
          Gérez vos informations personnelles et paramètres de compte
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Profile Header */}
        <div className="lg:col-span-3">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center space-x-6">
                <div className="relative">
                  <Avatar className="h-24 w-24">
                    <AvatarImage src={profileData.avatar} alt="Profile" />
                    <AvatarFallback>
                      {profileData.first_name?.[0] || ""}
                      {profileData.last_name?.[0] || ""}
                    </AvatarFallback>
                  </Avatar>
                  {isEditing && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="absolute -bottom-2 -right-2 h-8 w-8 rounded-full p-0"
                      disabled
                    >
                      <Camera className="h-4 w-4" />
                    </Button>
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-2xl font-semibold text-gray-900">
                        {profileData.first_name} {profileData.last_name}
                      </h2>
                      <p className="text-gray-600">{profileData.email}</p>
                      <div className="flex items-center space-x-2 mt-2">
                        {getUserRoles().map((role, index) => (
                          <Badge key={index} variant="secondary">
                            {role}
                          </Badge>
                        ))}
                        <span className="text-sm text-gray-500">
                          Membre depuis {getJoinDate()}
                        </span>
                      </div>
                    </div>
                    <div className="flex space-x-2">
                      {!isEditing ? (
                        <Button
                          onClick={() => setIsEditing(true)}
                          variant="outline"
                          size="sm"
                        >
                          <Edit className="h-4 w-4 mr-2" />
                          Modifier le profil
                        </Button>
                      ) : (
                        <>
                          <Button
                            onClick={handleSave}
                            size="sm"
                            disabled={saving}
                          >
                            {saving ? (
                              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            ) : (
                              <Save className="h-4 w-4 mr-2" />
                            )}
                            {saving ? "Sauvegarde..." : "Sauvegarder"}
                          </Button>
                          <Button
                            onClick={handleCancel}
                            variant="outline"
                            size="sm"
                            disabled={saving}
                          >
                            <X className="h-4 w-4 mr-2" />
                            Annuler
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Personal Information */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Informations Personnelles</CardTitle>
              <CardDescription>
                Mettez à jour vos informations personnelles et coordonnées
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="first_name">Prénom</Label>
                  <Input
                    id="first_name"
                    value={profileData.first_name}
                    onChange={(e) =>
                      handleInputChange("first_name", e.target.value)
                    }
                    disabled={!isEditing}
                    className={
                      validationErrors.first_name ? "border-red-500" : ""
                    }
                  />
                  {validationErrors.first_name && (
                    <p className="text-sm text-red-500">
                      {validationErrors.first_name}
                    </p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="last_name">Nom</Label>
                  <Input
                    id="last_name"
                    value={profileData.last_name}
                    onChange={(e) =>
                      handleInputChange("last_name", e.target.value)
                    }
                    disabled={!isEditing}
                    className={
                      validationErrors.last_name ? "border-red-500" : ""
                    }
                  />
                  {validationErrors.last_name && (
                    <p className="text-sm text-red-500">
                      {validationErrors.last_name}
                    </p>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={profileData.email}
                  onChange={(e) => handleInputChange("email", e.target.value)}
                  disabled={!isEditing}
                  className={validationErrors.email ? "border-red-500" : ""}
                />
                {validationErrors.email && (
                  <p className="text-sm text-red-500">
                    {validationErrors.email}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="phone">Téléphone</Label>
                <Input
                  id="phone"
                  value={profileData.phone}
                  onChange={(e) => handleInputChange("phone", e.target.value)}
                  disabled={!isEditing}
                  className={validationErrors.phone ? "border-red-500" : ""}
                  placeholder="+33 1 23 45 67 89"
                />
                {validationErrors.phone && (
                  <p className="text-sm text-red-500">
                    {validationErrors.phone}
                  </p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="location">Localisation</Label>
                <Input
                  id="location"
                  value={profileData.location}
                  onChange={(e) =>
                    handleInputChange("location", e.target.value)
                  }
                  disabled={!isEditing}
                  placeholder="Ville, Pays"
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Account Information */}
        <div>
          <Card>
            <CardHeader>
              <CardTitle>Informations du Compte</CardTitle>
              <CardDescription>
                Détails de votre compte et paramètres
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium text-gray-500">
                  Nom d'utilisateur
                </Label>
                <p className="text-sm text-gray-900">{profileData.username}</p>
              </div>

              <Separator />

              <div className="space-y-2">
                <Label className="text-sm font-medium text-gray-500">
                  Rôles
                </Label>
                <div className="flex flex-wrap gap-1">
                  {getUserRoles().map((role, index) => (
                    <Badge key={index} variant="secondary">
                      {role}
                    </Badge>
                  ))}
                </div>
              </div>

              <Separator />

              <div className="space-y-2">
                <Label className="text-sm font-medium text-gray-500">
                  Membre Depuis
                </Label>
                <p className="text-sm text-gray-900">{getJoinDate()}</p>
              </div>

              <Separator />

              <div className="space-y-2">
                <Label className="text-sm font-medium text-gray-500">
                  Dernière Connexion
                </Label>
                <p className="text-sm text-gray-900">{getLastLogin()}</p>
              </div>

              <Separator />

              <div className="space-y-2">
                <Label className="text-sm font-medium text-gray-500">
                  Statut du Compte
                </Label>
                <div className="flex items-center space-x-2">
                  <CheckCircle className="h-4 w-4 text-green-500" />
                  <span className="text-sm text-green-600">Actif</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};

export default ProfilePage;
