import { Navigate } from "react-router-dom";
import { usePermission } from "../../hooks/usePermission";
import { useAuth } from "../../contexts/AuthContext";

/**
 * PermissionRoute - Wrapper component for routes requiring specific permissions
 *
 * @param {Object} props
 * @param {string} props.permission - Required permission codename (e.g., "can_view_dashboard")
 * @param {React.ReactNode} props.children - Content to render if permission is granted
 * @param {string} props.fallbackPath - Path to redirect if permission is denied (default: "/dashboard")
 * @param {React.ReactNode} props.fallbackComponent - Component to render instead of redirecting
 */
export function PermissionRoute({
  permission,
  children,
  fallbackPath = "/dashboard",
  fallbackComponent = null
}) {
  const { user, loading: authLoading } = useAuth();
  const { hasPermission, loading: permLoading } = usePermission(permission);

  // While loading, show loading spinner or null
  if (authLoading || permLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  // Not authenticated - redirect to login
  if (!user) {
    return <Navigate to="/login" replace />;
  }

  // Permission denied - show fallback or redirect
  if (!hasPermission) {
    if (fallbackComponent) {
      return fallbackComponent;
    }
    return <Navigate to={fallbackPath} replace />;
  }

  // Permission granted - render children
  return children;
}

/**
 * PermissionGate - Component to conditionally render content based on permission
 * Use this for UI elements (buttons, sections) rather than routes
 *
 * @param {Object} props
 * @param {string} props.permission - Required permission codename
 * @param {React.ReactNode} props.children - Content to render if permission is granted
 * @param {React.ReactNode} props.fallback - Content to render if permission is denied (optional)
 */
export function PermissionGate({ permission, children, fallback = null }) {
  const { hasPermission, loading } = usePermission(permission);

  if (loading) {
    return fallback; // Show fallback or null while loading
  }

  return hasPermission ? children : fallback;
}

/**
 * useRequirePermission - Hook to check permission and return boolean
 * Use this for conditional logic in components
 */
export { usePermission };
