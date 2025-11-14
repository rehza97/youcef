import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { MultiSelect } from "@/components/ui/multi-select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Send,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Users,
} from "lucide-react";
import { toast } from "sonner";
import {
  getBroadcastFiles,
  broadcastFileToAllUsers,
  broadcastFileToDot,
  broadcastFileToUsers,
  getUsers,
  getAllDots,
} from "../../services/api";
import { handleApiError } from "../../lib/error-handler";

const FileDistribution = () => {
  const [files, setFiles] = useState([]);
  const [users, setUsers] = useState([]);
  const [dots, setDots] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [distributionType, setDistributionType] = useState("all");
  const [selectedDot, setSelectedDot] = useState(null);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [distributing, setDistributing] = useState(false);
  const [result, setResult] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [filesRes, usersRes, dotsRes] = await Promise.all([
        getBroadcastFiles(),
        getUsers(),
        getAllDots(),
      ]);
      setFiles(filesRes.data.files || []);
      setUsers(usersRes.data || []);
      setDots(dotsRes.data || []);
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors du chargement des données",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDistribute = async () => {
    if (!selectedFile) {
      toast.error("Veuillez sélectionner un fichier");
      return;
    }

    if (
      distributionType === "dot" &&
      !selectedDot
    ) {
      toast.error("Veuillez sélectionner un DOT");
      return;
    }

    if (
      distributionType === "users" &&
      selectedUsers.length === 0
    ) {
      toast.error("Veuillez sélectionner au moins un utilisateur");
      return;
    }

    try {
      setDistributing(true);

      let response;
      switch (distributionType) {
        case "all":
          response = await broadcastFileToAllUsers({
            file_id: selectedFile.id,
          });
          break;
        case "dot":
          response = await broadcastFileToDot(selectedDot, {
            file_id: selectedFile.id,
          });
          break;
        case "users":
          response = await broadcastFileToUsers({
            file_id: selectedFile.id,
            user_ids: selectedUsers,
          });
          break;
        default:
          throw new Error("Type de distribution invalide");
      }

      setResult(response.data);
      toast.success("Fichier distribué avec succès");

      setTimeout(() => {
        setIsOpen(false);
        resetForm();
      }, 2000);
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors de la distribution",
      });
    } finally {
      setDistributing(false);
    }
  };

  const resetForm = () => {
    setSelectedFile(null);
    setDistributionType("all");
    setSelectedDot(null);
    setSelectedUsers([]);
    setResult(null);
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="pt-6">
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
            <p className="text-sm text-gray-600">Chargement...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Send className="h-5 w-5" />
            Distribution de Fichiers
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-gray-600 mb-4">
            Distribuez les fichiers de diffusion aux utilisateurs, DOTs ou à tous les utilisateurs.
          </p>
          <Button
            onClick={() => setIsOpen(true)}
            className="bg-green-600 hover:bg-green-700 text-white"
          >
            <Send className="h-4 w-4 mr-2" />
            Distribuer un Fichier
          </Button>
        </CardContent>
      </Card>

      {/* Distribution Dialog */}
      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Distribuer un Fichier</DialogTitle>
            <DialogDescription>
              Sélectionnez un fichier et les destinataires
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {result && (
              <div className="p-4 bg-green-50 border border-green-200 rounded-lg flex gap-3">
                <CheckCircle2 className="h-5 w-5 text-green-600 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-green-800">
                  <p className="font-medium">Distribution réussie</p>
                  <p>
                    {result.message ||
                      `Fichier distribué à ${
                        result.recipient_count || 0
                      } utilisateur(s)`}
                  </p>
                </div>
              </div>
            )}

            {/* File Selection */}
            <div>
              <Label htmlFor="file-select">Sélectionner un Fichier</Label>
              <Select
                value={selectedFile?.id?.toString() || ""}
                onValueChange={(value) => {
                  const file = files.find((f) => f.id.toString() === value);
                  setSelectedFile(file);
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Choisir un fichier" />
                </SelectTrigger>
                <SelectContent>
                  {files.map((file) => (
                    <SelectItem key={file.id} value={file.id.toString()}>
                      {file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Distribution Type */}
            <div>
              <Label htmlFor="distribution-type">Type de Distribution</Label>
              <Select value={distributionType} onValueChange={setDistributionType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">À Tous les Utilisateurs</SelectItem>
                  <SelectItem value="dot">À un DOT Spécifique</SelectItem>
                  <SelectItem value="users">À des Utilisateurs Spécifiques</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* DOT Selection */}
            {distributionType === "dot" && (
              <div>
                <Label htmlFor="dot-select">Sélectionner un DOT</Label>
                <Select
                  value={selectedDot || ""}
                  onValueChange={setSelectedDot}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Choisir un DOT" />
                  </SelectTrigger>
                  <SelectContent>
                    {dots.map((dot) => (
                      <SelectItem key={dot.id} value={dot.id.toString()}>
                        {dot.name || dot.id}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Users Selection */}
            {distributionType === "users" && (
              <div>
                <Label>Sélectionner les Utilisateurs</Label>
                <MultiSelect
                  options={users.map((user) => ({
                    label: `${user.username} (${user.email})`,
                    value: user.id.toString(),
                  }))}
                  selected={selectedUsers}
                  onChange={setSelectedUsers}
                  placeholder="Sélectionner les utilisateurs..."
                />
              </div>
            )}

            {/* Info Alert */}
            {distributionType === "all" && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg flex gap-3">
                <AlertCircle className="h-4 w-4 text-blue-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-blue-800">
                  Ce fichier sera envoyé à TOUS les utilisateurs du système.
                </p>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2 justify-end pt-4">
              <Button
                variant="outline"
                onClick={() => {
                  setIsOpen(false);
                  resetForm();
                }}
                disabled={distributing}
              >
                Annuler
              </Button>
              <Button
                onClick={handleDistribute}
                disabled={!selectedFile || distributing}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                {distributing ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Distribution...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4 mr-2" />
                    Distribuer
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
};

export default FileDistribution;
