import React, { Suspense, lazy } from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { Toaster } from "sonner";

// Context
import { AuthProvider } from "./contexts/AuthContext";
import { ProcessingProvider } from "./contexts/ProcessingContext";

// Components (not lazy-loaded as they're used globally)
import Sidebar from "./components/layout/Sidebar";
import LoginForm from "./components/auth/LoginForm";
import RegisterForm from "./components/auth/RegisterForm";
import ErrorBoundary from "./components/ErrorBoundary";
import { PermissionRoute } from "./components/auth/PermissionRoute";
import GlobalProcessingIndicator from "./components/GlobalProcessingIndicator";

// Lazy-loaded Pages for code splitting
const Dashboard = lazy(() => import("./pages/Dashboard"));
const AdminDashboard = lazy(() => import("./pages/AdminDashboard"));
const UsersPage = lazy(() => import("./pages/UsersPage"));
const RolesPage = lazy(() => import("./pages/RolesPage"));
const ProtectedPage = lazy(() => import("./pages/ProtectedPage"));
const ProfilePage = lazy(() => import("./pages/ProfilePage"));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage"));
const MessagingPage = lazy(() => import("./pages/MessagingPage"));
const SecureMessagingPage = lazy(() => import("./pages/SecureMessagingPage"));
const ChangePasswordPage = lazy(() => import("./pages/ChangePasswordPage"));
const FilesPage = lazy(() => import("./pages/FilesPage"));
const FilePreviewPage = lazy(() => import("./pages/FilePreviewPage"));
const EncaissementPage = lazy(() => import("./pages/EncaissementPage"));
const RevenuePage = lazy(() => import("./pages/RevenuePage"));
const EncaissementARDotPage = lazy(() => import("./pages/EncaissementARDotPage"));
const CreancePeriodiqueDotPage = lazy(() => import("./pages/CreancePeriodiqueDotPage"));
const DOTManagementPage = lazy(() => import("./pages/DOTManagement/DOTManagementPage"));

// Hooks
import { useAuth } from "./contexts/AuthContext";

// Create a new QueryClient instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Loading fallback component for lazy-loaded pages
const PageLoadingFallback = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p className="text-gray-600">Loading...</p>
    </div>
  </div>
);

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return isAuthenticated ? children : <Navigate to="/login" replace />;
};

// Public Route Component (redirects to dashboard if already authenticated)
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return isAuthenticated ? <Navigate to="/dashboard" replace /> : children;
};

// Main App Content
const AppContent = () => {
  const { isAuthenticated } = useAuth();

  return (
    <div className="flex h-screen bg-gray-100">
      {isAuthenticated && <Sidebar />}
      <div className="flex-1 overflow-auto">
        {/* Global Processing Indicator */}
        {isAuthenticated && <GlobalProcessingIndicator />}
        <Suspense fallback={<PageLoadingFallback />}>
          <Routes>
          {/* Public Routes */}
          <Route
            path="/revenue"
            element={
              <ProtectedRoute>
                <PermissionRoute permission="can_view_analytics">
                  <RevenuePage />
                </PermissionRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/login"
            element={
              <PublicRoute>
                <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-800 py-12 px-4 sm:px-6 lg:px-8">
                  <LoginForm />
                </div>
              </PublicRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicRoute>
                <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-800 py-12 px-4 sm:px-6 lg:px-8">
                  <RegisterForm />
                </div>
              </PublicRoute>
            }
          />

          {/* Protected Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <PermissionRoute permission="can_manage_rbac">
                  <AdminDashboard />
                </PermissionRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/users"
            element={
              <ProtectedRoute>
                <PermissionRoute permission="can_manage_users">
                  <UsersPage />
                </PermissionRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/settings"
            element={<Navigate to="/dashboard" replace />}
          />
          <Route
            path="/roles"
            element={
              <ProtectedRoute>
                <PermissionRoute permission="can_manage_rbac">
                  <RolesPage />
                </PermissionRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/protected"
            element={
              <ProtectedRoute>
                <ProtectedPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/notifications"
            element={
              <ProtectedRoute>
                <NotificationsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/messaging"
            element={
              <ProtectedRoute>
                <MessagingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/secure-messaging"
            element={
              <ProtectedRoute>
                <SecureMessagingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/files"
            element={
              <ProtectedRoute>
                <PermissionRoute permission="can_upload_files">
                  <FilesPage />
                </PermissionRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/files/:fileId/preview"
            element={
              <ProtectedRoute>
                <PermissionRoute permission="can_upload_files">
                  <FilePreviewPage />
                </PermissionRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/health"
            element={<Navigate to="/dashboard" replace />}
          />
          <Route
            path="/change-password"
            element={
              <ProtectedRoute>
                <ChangePasswordPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/api-info"
            element={<Navigate to="/dashboard" replace />}
          />
          <Route
            path="/encaissement"
            element={
              <ProtectedRoute>
                <PermissionRoute permission="can_view_encaissement_data">
                  <EncaissementPage />
                </PermissionRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/encaissement-ar-dot"
            element={
              <ProtectedRoute>
                <PermissionRoute permission="can_view_kpi_data">
                  <EncaissementARDotPage />
                </PermissionRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/creance-periodique-dot"
            element={
              <ProtectedRoute>
                <PermissionRoute permission="can_view_kpi_data">
                  <CreancePeriodiqueDotPage />
                </PermissionRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/dot-management"
            element={
              <ProtectedRoute>
                <PermissionRoute permission="can_manage_rbac">
                  <DOTManagementPage />
                </PermissionRoute>
              </ProtectedRoute>
            }
          />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </div>
    </div>
  );
};

// Main App Component
function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
          <AuthProvider>
            <ProcessingProvider>
              <Router>
                <AppContent />
                <Toaster />
              </Router>
            </ProcessingProvider>
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
