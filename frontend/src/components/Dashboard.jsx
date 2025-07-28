import { useEffect, useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { generalAPI } from "../services/api";
import PageHeader from "../components/PageHeader";
import { Button } from "@/components/ui/button";

export default function Dashboard() {
  const { user } = useAuth();
  const [protectedMessage, setProtectedMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    setError("");
    try {
      const protectedRes = await generalAPI.protected();
      setProtectedMessage(protectedRes.data.message);
    } catch {
      setError(
        "Échec de la récupération des données. Veuillez vérifier votre authentification."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full p-4 sm:p-8 flex flex-col items-center">
      <div className="w-full max-w-3xl">
        <PageHeader
          title="Tableau de bord"
          subtitle={`Bon retour, ${user?.username} !`}
        />
        <div className="bg-white p-6 rounded-xl shadow-md">
          {loading ? (
            <div className="animate-pulse h-8 bg-gray-100 rounded mb-2 w-1/2" />
          ) : error ? (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6">
              {error}
            </div>
          ) : (
            <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-6">
              {protectedMessage || "Bienvenue sur votre tableau de bord !"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
