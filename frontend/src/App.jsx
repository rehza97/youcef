import React from "react";
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

// Components
import Sidebar from "./components/layout/Sidebar";
import LoginForm from "./components/auth/LoginForm";
import RegisterForm from "./components/auth/RegisterForm";
import ErrorBoundary from "./components/ErrorBoundary";
import { PermissionRoute } from "./components/auth/PermissionRoute";

// Pages
import Dashboard from "./pages/Dashboard";
import UsersPage from "./pages/UsersPage";
import RolesPage from "./pages/RolesPage";
import ProtectedPage from "./pages/ProtectedPage";
import ProfilePage from "./pages/ProfilePage";
import NotificationsPage from "./pages/NotificationsPage";
import MessagingPage from "./pages/MessagingPage";
import ChangePasswordPage from "./pages/ChangePasswordPage";
import FilesPage from "./pages/FilesPage";
import FilePreviewPage from "./pages/FilePreviewPage";
import EncaissementPage from "./pages/EncaissementPage";

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
        <Routes>
          {/* Public Routes */}
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
            path="/permissions"
            element={<Navigate to="/dashboard" replace />}
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

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
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
            <Router>
              <AppContent />
              <Toaster />
            </Router>
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
