import { createContext, useContext, useState, useEffect } from "react";
import {
  login as apiLogin,
  register as apiRegister,
  logout as apiLogout,
  refreshToken as apiRefreshToken,
  getCurrentUser,
  updateProfile as apiUpdateProfile,
} from "../services/api";
import { handleApiError } from "../lib/error-handler";
import { clearPermissionCache } from "../hooks/usePermission";

const AuthContext = createContext();

// Token storage utility with security improvements
const tokenStorage = {
  // Use sessionStorage as first preference (cleared on tab close)
  getToken: () => {
    try {
      return sessionStorage.getItem("token") || localStorage.getItem("token");
    } catch (error) {
      console.error("Error accessing token storage:", error);
      return null;
    }
  },

  setToken: (token, rememberMe = false) => {
    try {
      if (rememberMe) {
        localStorage.setItem("token", token);
        // Set expiration time (24 hours)
        localStorage.setItem("tokenExpiry", Date.now() + 24 * 60 * 60 * 1000);
      } else {
        sessionStorage.setItem("token", token);
        sessionStorage.setItem("tokenExpiry", Date.now() + 8 * 60 * 60 * 1000);
      }
    } catch (error) {
      console.error("Error setting token:", error);
    }
  },

  setRefreshToken: (refreshToken, rememberMe = false) => {
    try {
      if (rememberMe) {
        localStorage.setItem("refreshToken", refreshToken);
      } else {
        sessionStorage.setItem("refreshToken", refreshToken);
      }
    } catch (error) {
      console.error("Error setting refresh token:", error);
    }
  },

  getRefreshToken: () => {
    try {
      return (
        sessionStorage.getItem("refreshToken") ||
        localStorage.getItem("refreshToken")
      );
    } catch (error) {
      console.error("Error accessing refresh token storage:", error);
      return null;
    }
  },

  removeToken: () => {
    try {
      localStorage.removeItem("token");
      localStorage.removeItem("tokenExpiry");
      localStorage.removeItem("refreshToken");
      localStorage.removeItem("user");
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("tokenExpiry");
      sessionStorage.removeItem("refreshToken");
      sessionStorage.removeItem("user");
    } catch (error) {
      console.error("Error removing token:", error);
    }
  },

  isTokenExpired: () => {
    try {
      const expiry =
        sessionStorage.getItem("tokenExpiry") ||
        localStorage.getItem("tokenExpiry");
      if (!expiry) return true;
      return Date.now() > parseInt(expiry);
    } catch (error) {
      console.error("Error checking token expiry:", error);
      return true;
    }
  },

  getUser: () => {
    try {
      const userData =
        sessionStorage.getItem("user") || localStorage.getItem("user");
      return userData ? JSON.parse(userData) : null;
    } catch (error) {
      console.error("Error parsing user data:", error);
      return null;
    }
  },

  setUser: (user, rememberMe = false) => {
    try {
      const storage = rememberMe ? localStorage : sessionStorage;
      storage.setItem("user", JSON.stringify(user));
    } catch (error) {
      console.error("Error setting user data:", error);
    }
  },
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Check token validity and refresh if needed
  const checkTokenValidity = async () => {
    const token = tokenStorage.getToken();
    if (!token) {
      setLoading(false);
      return;
    }

    if (tokenStorage.isTokenExpired()) {
      console.warn("Token expired, attempting refresh...");
      try {
        const refreshToken = tokenStorage.getRefreshToken();
        if (refreshToken) {
          const response = await apiRefreshToken(refreshToken);
          const { access_token: newToken, refresh_token: newRefreshToken } =
            response.data;
          tokenStorage.setToken(newToken, false);
          tokenStorage.setRefreshToken(newRefreshToken, false);

          // Get user data
          const userData = tokenStorage.getUser();
          if (userData) {
            setUser(userData);
          }
        } else {
          // No refresh token, clear everything
          tokenStorage.removeToken();
          setUser(null);
        }
      } catch (error) {
        console.error("Token refresh failed:", error);
        // Clear tokens on refresh failure
        tokenStorage.removeToken();
        setUser(null);
      }
    } else {
      const userData = tokenStorage.getUser();
      if (userData) {
        setUser(userData);
      }
    }
    setLoading(false);
  };

  useEffect(() => {
    checkTokenValidity();

    // Set up token expiry check interval
    const interval = setInterval(() => {
      if (tokenStorage.isTokenExpired() && user) {
        console.warn("Token expired, logging out...");
        logout();
      }
    }, 60000); // Check every minute

    return () => clearInterval(interval);
  }, []); // Remove user dependency to prevent infinite loop

  const login = async (credentials, rememberMe = false) => {
    try {
      setError(null);
      setLoading(true);

      const response = await apiLogin(credentials);
      const { access_token, refresh_token, user: userData } = response.data;

      // Validate token format (basic check)
      if (
        !access_token ||
        typeof access_token !== "string" ||
        access_token.length < 10
      ) {
        throw new Error("Format de token invalide reçu du serveur");
      }

      // Sanitize user data - if user data is not in response, we'll need to get it separately
      const sanitizedUser = {
        id: userData?.id || null,
        username: userData?.username?.trim() || credentials.username,
        email: userData?.email?.trim() || "",
        last_login: userData?.last_login || null,
      };

      tokenStorage.setToken(access_token, rememberMe);
      tokenStorage.setRefreshToken(refresh_token, rememberMe);
      tokenStorage.setUser(sanitizedUser, rememberMe);
      setUser(sanitizedUser);

      return { success: true };
    } catch (error) {
      // Use improved error handling
      const { message } = handleApiError(error, {
        showToast: false, // Don't show toast here, let component handle it
        logError: true,
      });

      setError(message);

      // Clear any existing tokens on login failure
      tokenStorage.removeToken();
      setUser(null);

      return {
        success: false,
        error: message,
        code: error.response?.data?.code || "LOGIN_ERROR",
      };
    } finally {
      setLoading(false);
    }
  };

  const register = async (userData, rememberMe = false) => {
    try {
      setError(null);
      setLoading(true);

      // Client-side validation
      if (!userData.username || userData.username.length < 3) {
        throw new Error(
          "Le nom d'utilisateur doit contenir au moins 3 caractères"
        );
      }

      if (!userData.password || userData.password.length < 8) {
        throw new Error("Le mot de passe doit contenir au moins 8 caractères");
      }

      const response = await apiRegister(userData);
      const { success, message, data } = response.data;

      if (!success) {
        throw new Error(message || "Échec de l'inscription");
      }

      // Registration successful, but no tokens returned
      // User needs to login separately after registration
      return {
        success: true,
        message:
          "Inscription réussie. Veuillez vous connecter avec vos identifiants.",
      };
    } catch (error) {
      // Use improved error handling
      const { message } = handleApiError(error, {
        showToast: false, // Don't show toast here, let component handle it
        logError: true,
      });

      setError(message);

      return {
        success: false,
        error: message,
        code: error.response?.data?.code || "REGISTER_ERROR",
        details: error.response?.data?.details || [],
      };
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      setLoading(true);

      // Call server logout endpoint to invalidate token
      await apiLogout();
    } catch (error) {
      console.error("Server logout failed:", error);
      // Continue with client-side logout even if server fails
    } finally {
      // Always clean up client-side state
      tokenStorage.removeToken();
      setUser(null);
      setError(null);
      setLoading(false);
      // Clear permission cache
      clearPermissionCache();
    }
  };

  const refreshToken = async () => {
    try {
      const refreshToken = tokenStorage.getRefreshToken();
      if (!refreshToken) {
        throw new Error("Aucun token de rafraîchissement disponible");
      }

      const response = await apiRefreshToken(refreshToken);
      const { access_token, refresh_token: newRefreshToken } = response.data;

      tokenStorage.setToken(access_token, false);
      tokenStorage.setRefreshToken(newRefreshToken, false);
      return { success: true };
    } catch (error) {
      console.error("Token refresh failed:", error);
      logout();
      return { success: false };
    }
  };

  const updateProfile = async (profileData) => {
    try {
      setError(null);
      const response = await apiUpdateProfile(profileData);
      const updatedUser = response.data.user;

      // Update user state
      setUser(updatedUser);
      tokenStorage.setUser(
        updatedUser,
        tokenStorage.getToken() === localStorage.getItem("token")
      );

      return { success: true };
    } catch (error) {
      const errorMessage =
        error.response?.data?.error || "Échec de la mise à jour du profil";
      setError(errorMessage);

      return {
        success: false,
        error: errorMessage,
        code: error.response?.data?.code || "PROFILE_UPDATE_ERROR",
      };
    }
  };

  // const changePassword = async (passwordData) => {
  //   try {
  //     setError(null);
  //     const response = await authAPI.changePassword(passwordData);
  //     const { success, message } = response.data;

  //     if (!success) {
  //       throw new Error(message || "Password change failed");
  //     }

  //     // Password change successful, but no new token returned
  //     // User may need to login again
  //     return { success: true, message: "Password changed successfully" };
  //   } catch (error) {
  //     const errorMessage =
  //       error.response?.data?.error || "Password change failed";
  //     setError(errorMessage);

  //     return {
  //       success: false,
  //       error: errorMessage,
  //       code: error.response?.data?.code || "PASSWORD_CHANGE_ERROR",
  //       details: error.response?.data?.details || [],
  //     };
  //   }
  // };

  const clearError = () => {
    setError(null);
  };

  const value = {
    user,
    loading,
    error,
    login,
    register,
    logout,
    refreshToken,
    updateProfile,
    // changePassword,
    clearError,
    isAuthenticated: !!user && !tokenStorage.isTokenExpired(),
    token: tokenStorage.getToken(), // Add token to context
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
