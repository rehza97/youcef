import React from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { Button } from "../ui/button";
import {
  LayoutDashboard,
  Users,
  Shield,
  User,
  Bell,
  MessageSquare,
  LogOut,
  Menu,
  X,
  FileText,
  BarChart3,
} from "lucide-react";

const Sidebar = () => {
  const { logout } = useAuth();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = React.useState(false);

  const navigation = [
    { name: "Tableau de bord", href: "/dashboard", icon: LayoutDashboard },
    { name: "Parc Corporate NGBSS", href: "/encaissement", icon: BarChart3 },
    { name: "Chiffre d'Affaires", href: "/revenue", icon: BarChart3 },
    { name: "Encaissement AR DOT", href: "/encaissement-ar-dot", icon: BarChart3 },
    { name: "Créance Périodique DOT", href: "/creance-periodique-dot", icon: BarChart3 },
    { name: "Utilisateurs", href: "/users", icon: Users },
    { name: "Rôles", href: "/roles", icon: Shield },
    { name: "Profil", href: "/profile", icon: User },
    { name: "Notifications", href: "/notifications", icon: Bell },
    { name: "Messagerie", href: "/messaging", icon: MessageSquare },
    { name: "Fichiers", href: "/files", icon: FileText },
  ];

  const handleLogout = () => {
    logout();
  };

  return (
    <>
      {/* Mobile menu button */}
      <div className="lg:hidden fixed top-4 left-4 z-50">
        <Button
          variant="outline"
          size="sm"
          onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
        >
          {isMobileMenuOpen ? (
            <X className="h-4 w-4" />
          ) : (
            <Menu className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* Sidebar */}
      <div
        className={`fixed inset-y-0 left-0 z-40 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${
          isMobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        } lg:relative lg:translate-x-0`}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-center gap-3 h-16 px-4 border-b border-gray-200">
            <img 
              src="/Algerie_Telecom.svg" 
              alt="Algerie Telecom" 
              className="h-12 w-auto object-contain"
            />
            <h6 className="font-bold text-gray-900 text-sm">
              Big Data Automated Analytics
            </h6>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-2">
            {navigation.map((item) => {
              const isActive = location.pathname === item.href;
              return (
                <Link
                  key={item.name}
                  to={item.href}
                  className={`flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    isActive
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-700 hover:bg-gray-100"
                  }`}
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.name}
                </Link>
              );
            })}
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200">
            <Button
              variant="outline"
              className="w-full justify-start"
              onClick={handleLogout}
            >
              <LogOut className="mr-3 h-5 w-5" />
              Déconnexion
            </Button>
          </div>
        </div>
      </div>

      {/* Mobile overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 z-30 lg:hidden"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}
    </>
  );
};

export default Sidebar;
