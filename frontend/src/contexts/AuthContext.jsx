import { createContext, useContext, useState, useEffect } from "react";
import { authAPI } from "../services/api";

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

  removeToken: () => {
    try {
      localStorage.removeItem("token");
      localStorage.removeItem("tokenExpiry");
      localStorage.removeItem("user");
      sessionStorage.removeItem("token");
      sessionStorage.removeItem("tokenExpiry");
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
        const response = await authAPI.refreshToken();
        const { token: newToken } = response.data;
        tokenStorage.setToken(newToken, false); // Don't remember refresh tokens

        // Get user data
        const userData = tokenStorage.getUser();
        if (userData) {
          setUser(userData);
        }
      } catch (error) {
        console.error("Token refresh failed:", error);
        logout();
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
  }, [user]);

  const login = async (credentials, rememberMe = false) => {
    try {
      setError(null);
      setLoading(true);

      const response = await authAPI.login(credentials);
      const { token, user: userData } = response.data;

      // Validate token format (basic check)
      if (!token || typeof token !== "string" || token.length < 10) {
        throw new Error("Invalid token format received from server");
      }

      // Sanitize user data
      const sanitizedUser = {
        id: userData.id,
        username: userData.username?.trim() || "",
        email: userData.email?.trim() || "",
        last_login: userData.last_login,
      };

      tokenStorage.setToken(token, rememberMe);
      tokenStorage.setUser(sanitizedUser, rememberMe);
      setUser(sanitizedUser);

      return { success: true };
    } catch (error) {
      const errorMessage = error.response?.data?.error || "Login failed";
      setError(errorMessage);

      // Clear any existing tokens on login failure
      tokenStorage.removeToken();
      setUser(null);

      return {
        success: false,
        error: errorMessage,
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
        throw new Error("Username must be at least 3 characters long");
      }

      if (!userData.password || userData.password.length < 8) {
        throw new Error("Password must be at least 8 characters long");
      }

      const response = await authAPI.register(userData);
      const { token, user: newUser } = response.data;

      // Validate token format
      if (!token || typeof token !== "string" || token.length < 10) {
        throw new Error("Invalid token format received from server");
      }

      // Sanitize user data
      const sanitizedUser = {
        id: newUser.id,
        username: newUser.username?.trim() || "",
        email: newUser.email?.trim() || "",
        date_joined: newUser.date_joined,
      };

      tokenStorage.setToken(token, rememberMe);
      tokenStorage.setUser(sanitizedUser, rememberMe);
      setUser(sanitizedUser);

      return { success: true };
    } catch (error) {
      const errorMessage = error.response?.data?.error || "Registration failed";
      setError(errorMessage);

      return {
        success: false,
        error: errorMessage,
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
      await authAPI.logout();
    } catch (error) {
      console.error("Server logout failed:", error);
      // Continue with client-side logout even if server fails
    } finally {
      // Always clean up client-side state
      tokenStorage.removeToken();
      setUser(null);
      setError(null);
      setLoading(false);
    }
  };

  const refreshToken = async () => {
    try {
      const response = await authAPI.refreshToken();
      const { token } = response.data;

      tokenStorage.setToken(token, false);
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
      const response = await authAPI.updateProfile(profileData);
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
        error.response?.data?.error || "Profile update failed";
      setError(errorMessage);

      return {
        success: false,
        error: errorMessage,
        code: error.response?.data?.code || "PROFILE_UPDATE_ERROR",
      };
    }
  };

  const changePassword = async (passwordData) => {
    try {
      setError(null);
      const response = await authAPI.changePassword(passwordData);
      const { token } = response.data;

      // Update token since password change invalidates old tokens
      tokenStorage.setToken(
        token,
        tokenStorage.getToken() === localStorage.getItem("token")
      );

      return { success: true };
    } catch (error) {
      const errorMessage =
        error.response?.data?.error || "Password change failed";
      setError(errorMessage);

      return {
        success: false,
        error: errorMessage,
        code: error.response?.data?.code || "PASSWORD_CHANGE_ERROR",
        details: error.response?.data?.details || [],
      };
    }
  };

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
    changePassword,
    clearError,
    isAuthenticated: !!user && !tokenStorage.isTokenExpired(),
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
