import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getUsers, sendMultiMessage } from "../../services/api";
import Select from "react-select";

export default function MessageInput({ conversation, onSend }) {
  const [value, setValue] = useState("");
  const [file, setFile] = useState(null);
  const [users, setUsers] = useState([]);
  const [selectedUsers, setSelectedUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [results, setResults] = useState([]);

  useEffect(() => {
    getUsers().then((res) => setUsers(res.data));
  }, []);

  const userOptions = users.map((user) => ({
    value: user.id,
    label: user.username,
    email: user.email,
    avatar: user.avatar_url || null, // If you have avatar URLs
  }));

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setResults([]);
    if (conversation) {
      // Real-time send via WebSocket
      if (!value.trim()) return;
      onSend && onSend(value);
      setValue("");
      return;
    }
    // Multi-user/file upload logic
    setLoading(true);
    if (!selectedUsers.length) {
      setError("Veuillez sélectionner au moins un utilisateur.");
      setLoading(false);
      return;
    }
    const formData = new FormData();
    selectedUsers.forEach((opt) => formData.append("recipient_ids", opt.value));
    formData.append("content", value);
    if (file) formData.append("file", file);
    try {
      const response = await sendMultiMessage(formData);
      setSuccess("Message envoyé !");
      setResults(response.data.results || []);
      setValue("");
      setFile(null);
      setSelectedUsers([]);
    } catch (err) {
      setError("Erreur lors de l'envoi du message.");
    }
    setLoading(false);
  };

  if (conversation) {
    // Real-time chat input
    return (
      <form
        className="flex gap-2 items-center p-2 border-t bg-white"
        onSubmit={handleSubmit}
      >
        <Input
          className="flex-1"
          placeholder="Écrire un message..."
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <Button type="submit" disabled={!value.trim()}>
          Envoyer
        </Button>
      </form>
    );
  }

  // Multi-user/file upload input
  return (
    <form
      className="flex flex-col gap-2 p-2 border-t bg-white"
      onSubmit={handleSubmit}
    >
      <div className="flex gap-2 items-center">
        <div className="min-w-[250px] flex-1">
          <Select
            isMulti
            options={userOptions}
            value={selectedUsers}
            onChange={setSelectedUsers}
            placeholder="Sélectionner des utilisateurs..."
            isClearable
            isSearchable
            getOptionLabel={(opt) => (
              <div className="flex items-center gap-2">
                {opt.avatar && (
                  <img
                    src={opt.avatar}
                    alt="avatar"
                    className="w-5 h-5 rounded-full"
                  />
                )}
                <span>{opt.label}</span>
                {opt.email && (
                  <span className="text-xs text-gray-400 ml-2">
                    {opt.email}
                  </span>
                )}
              </div>
            )}
            getOptionValue={(opt) => opt.value}
            styles={{ menu: (base) => ({ ...base, zIndex: 9999 }) }}
          />
        </div>
        <Input type="file" onChange={handleFileChange} className="w-auto" />
      </div>
      <div className="flex gap-2 items-center">
        <Input
          className="flex-1"
          placeholder="Écrire un message..."
          value={value}
          onChange={(e) => setValue(e.target.value)}
        />
        <Button
          type="submit"
          disabled={loading || !selectedUsers.length || (!value && !file)}
        >
          {loading ? "Envoi..." : "Envoyer"}
        </Button>
      </div>
      {error && <div className="text-red-500 text-sm">{error}</div>}
      {success && <div className="text-green-600 text-sm">{success}</div>}
      {results.length > 0 && (
        <div className="text-sm mt-2">
          <b>Résumé de l'envoi :</b>
          <ul className="list-disc ml-6">
            {results.map((r) => (
              <li
                key={r.recipient_id}
                className={
                  r.status === "sent" ? "text-green-700" : "text-red-600"
                }
              >
                Utilisateur ID {r.recipient_id}:{" "}
                {r.status === "sent" ? "Message envoyé" : "Erreur"}
              </li>
            ))}
          </ul>
        </div>
      )}
    </form>
  );
}
