import { useEffect, useState } from "react";
import { Loader2, CheckCircle, XCircle, AlertTriangle } from "lucide-react";
import axios from "axios";

export default function SystemStatusWidget() {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchStatus() {
      setLoading(true);
      setError(null);
      try {
        // Try /api/health/ first, fallback to /api/info/
        let res;
        try {
          res = await axios.get("/api/health/");
        } catch {
          res = await axios.get("/api/info/");
        }
        setStatus(res.data);
      } catch (err) {
        setError("Impossible d'atteindre l'API du backend.");
      } finally {
        setLoading(false);
      }
    }
    fetchStatus();
  }, []);

  return (
    <div className="bg-gray-50 rounded-lg p-4 shadow flex flex-col gap-2 w-full max-w-md">
      <div className="flex items-center gap-2 mb-2">
        <span className="font-semibold text-lg">État du système</span>
        {loading && <Loader2 className="animate-spin text-gray-400" />}
        {!loading && !error && status && (
          <CheckCircle className="text-green-500" />
        )}
        {error && <XCircle className="text-red-500" />}
      </div>
      {loading && (
        <div className="text-gray-500">
          Vérification de l'état du système...
        </div>
      )}
      {error && (
        <div className="text-red-600 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" /> {error}
        </div>
      )}
      {!loading && status && (
        <div className="space-y-1">
          {status.version && (
            <div>
              <span className="font-medium">Version :</span> {status.version}
            </div>
          )}
          {status.uptime && (
            <div>
              <span className="font-medium">Temps de fonctionnement :</span>{" "}
              {status.uptime}
            </div>
          )}
          {status.db_status && (
            <div>
              <span className="font-medium">Base de données :</span>{" "}
              {status.db_status}
            </div>
          )}
          {status.message && (
            <div>
              <span className="font-medium">Message :</span> {status.message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
