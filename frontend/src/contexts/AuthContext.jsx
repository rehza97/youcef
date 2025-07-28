import { createContext, useContext, useState, useEffect } from "react";
import { authAPI } from "../services/api";

const AuthContext = createContext();

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

  useEffect(() => {
    // Check if user is logged in on app start
    const token = localStorage.getItem("token");
    const savedUser = localStorage.getItem("user");

    if (token && savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const login = async (credentials) => {
    try {
      const response = await authAPI.login(credentials);
      const { token } = response.data;

      localStorage.setItem("token", token);

      // Get user info from token or make a request
      const userInfo = { username: credentials.username };
      localStorage.setItem("user", JSON.stringify(userInfo));
      setUser(userInfo);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || "Échec de la connexion",
      };
    }
  };

  const register = async (userData) => {
    try {
      const response = await authAPI.register(userData);
      const { token } = response.data;

      localStorage.setItem("token", token);

      const userInfo = { username: userData.username };
      localStorage.setItem("user", JSON.stringify(userInfo));
      setUser(userInfo);

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || "Échec de l'inscription",
      };
    }
  };

  const logout = () => {
    authAPI.logout();
    setUser(null);
  };

  const value = {
    user,
    login,
    register,
    logout,
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
