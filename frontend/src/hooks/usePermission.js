import { useEffect, useState } from "react";
import { checkPermission } from "../services/api";

// In-memory cache for permission checks
const permissionCache = new Map();
const pendingRequests = new Map();

export function usePermission(codename) {
  const [hasPermission, setHasPermission] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;

    // Check cache first
    if (permissionCache.has(codename)) {
      setHasPermission(permissionCache.get(codename));
      setLoading(false);
      return;
    }

    // Check if there's already a pending request for this permission
    if (pendingRequests.has(codename)) {
      // Wait for the existing request to complete
      pendingRequests.get(codename).then((result) => {
        if (isMounted) {
          setHasPermission(result);
          setLoading(false);
        }
      });
      return;
    }

    // Make a new request
    setLoading(true);
    const requestPromise = checkPermission(codename)
      .then((res) => {
        const result = res.data.has_permission;
        // Cache the result
        permissionCache.set(codename, result);
        // Remove from pending requests
        pendingRequests.delete(codename);
        if (isMounted) setHasPermission(result);
        return result;
      })
      .catch(() => {
        // Cache false on error
        permissionCache.set(codename, false);
        pendingRequests.delete(codename);
        if (isMounted) setHasPermission(false);
        return false;
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    // Store the pending request
    pendingRequests.set(codename, requestPromise);

    return () => {
      isMounted = false;
    };
  }, [codename]);

  return { hasPermission, loading };
}

// Export function to clear cache (useful for logout or permission updates)
export function clearPermissionCache() {
  permissionCache.clear();
  pendingRequests.clear();
}
