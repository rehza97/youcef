import { useEffect, useState } from "react";
import { usersAPI } from "../services/api";

export function usePermission(codename) {
  const [hasPermission, setHasPermission] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    usersAPI
      .checkPermission(codename)
      .then((res) => {
        if (isMounted) setHasPermission(res.data.has_permission);
      })
      .catch(() => {
        if (isMounted) setHasPermission(false);
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [codename]);

  return { hasPermission, loading };
}
