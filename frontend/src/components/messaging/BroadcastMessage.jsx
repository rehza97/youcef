import React, { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Broadcast, AlertCircle, CheckCircle2, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { broadcastMessage as apiBroadcast } from "../../services/api";
import { handleApiError } from "../../lib/error-handler";

const BroadcastMessage = ({ currentUser }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [priority, setPriority] = useState("normal");
  const [sending, setSending] = useState(false);
  const [recipients, setRecipients] = useState("all_users");

  const handleBroadcast = async () => {
    if (!message.trim()) {
      toast.error("Le message ne peut pas être vide");
      return;
    }

    try {
      setSending(true);

      const broadcastData = {
        content: message.trim(),
        priority,
        recipient_type: recipients,
        sender_id: currentUser?.id,
      };

      await apiBroadcast(broadcastData);

      toast.success("Message diffusé à tous les utilisateurs");
      setMessage("");
      setPriority("normal");
      setRecipients("all_users");
      setIsOpen(false);
    } catch (error) {
      handleApiError(error, {
        showToast: true,
        fallbackMessage: "Erreur lors de la diffusion du message",
      });
    } finally {
      setSending(false);
    }
  };

  // Check if user has permission to broadcast (typically admin only)
  const hasPermission = currentUser?.role === "ADMIN" || currentUser?.role === "SUPER_USER";

  if (!hasPermission) {
    return null;
  }

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button
          className="bg-purple-600 hover:bg-purple-700 text-white"
          size="sm"
        >
          <Broadcast className="h-4 w-4 mr-2" />
          Diffuser un message
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Broadcast className="h-5 w-5 text-purple-600" />
            Diffuser un message à tous les utilisateurs
          </DialogTitle>
          <DialogDescription>
            Les messages de diffusion seront envoyés à tous les utilisateurs du
            système
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Recipients */}
          <div>
            <Label htmlFor="recipients">Destinataires</Label>
            <Select value={recipients} onValueChange={setRecipients}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all_users">Tous les utilisateurs</SelectItem>
                <SelectItem value="active_users">
                  Utilisateurs actifs uniquement
                </SelectItem>
                <SelectItem value="admins">Administrateurs uniquement</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Priority */}
          <div>
            <Label htmlFor="priority">Priorité</Label>
            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Basse</SelectItem>
                <SelectItem value="normal">Normale</SelectItem>
                <SelectItem value="high">Haute</SelectItem>
                <SelectItem value="urgent">Urgente</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Message */}
          <div>
            <Label htmlFor="broadcast-message">Message</Label>
            <Textarea
              id="broadcast-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Entrez le message à diffuser..."
              rows={5}
              className="resize-none"
            />
            <p className="text-xs text-gray-600 mt-1">
              {message.length} caractères
            </p>
          </div>

          {/* Info Alert */}
          <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg flex gap-3">
            <AlertCircle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-amber-800">
              <p className="font-medium">Important</p>
              <p>
                Ce message sera envoyé à {recipients === "all_users" ? "TOUS" : "aux"}{" "}
                utilisateurs. Assurez-vous que le contenu est approprié.
              </p>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2 justify-end pt-4">
            <Button
              variant="outline"
              onClick={() => {
                setIsOpen(false);
                setMessage("");
              }}
              disabled={sending}
            >
              Annuler
            </Button>
            <Button
              onClick={handleBroadcast}
              disabled={!message.trim() || sending}
              className="bg-purple-600 hover:bg-purple-700 text-white"
            >
              {sending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Envoi...
                </>
              ) : (
                <>
                  <Broadcast className="h-4 w-4 mr-2" />
                  Diffuser
                </>
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default BroadcastMessage;
