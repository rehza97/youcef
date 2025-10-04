import React from "react";
import { Outlet } from "react-router-dom";
import {
  Sidebar,
  SidebarContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuItem,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenuButton,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
} from "@/components/ui/sidebar";
import { useAuth } from "../contexts/AuthContext";
import { usePermission } from "../hooks/usePermission";
import NotificationBell from "./notifications/NotificationBell";
import {
  LayoutDashboard,
  Users,
  Shield,
  LogOut,
  UserPlus,
  BarChart3,
  Bell,
  MessageSquare,
} from "lucide-react";
import { Link, useLocation } from "react-router-dom";

export default function SidebarLayout() {
  const { logout } = useAuth();
  const location = useLocation();

  // Permission checks for menu visibility
  const { hasPermission: canViewDashboard } =
    usePermission("can_view_dashboard");
  const { hasPermission: canManageUsers } = usePermission("can_manage_users");
  const { hasPermission: canViewAnalytics } =
    usePermission("can_view_analytics");
  const { hasPermission: canManageSettings } = usePermission(
    "can_manage_settings"
  );
  const { hasPermission: canManageRBAC } = usePermission("can_manage_rbac");

  return (
    <div className="flex min-h-screen w-screen">
      {/* Sidebar: fixed width */}
      <div className="w-64 flex-shrink-0">
        <Sidebar>
          <SidebarHeader>
            <div className="flex items-center gap-2 px-4 py-2">
              <Shield className="h-6 w-6" />
              <span className="font-semibold">Panneau d'administration</span>
            </div>
          </SidebarHeader>
          <SidebarContent>
            <SidebarMenu>
              {/* Dashboard Section */}
              {canViewDashboard && (
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={location.pathname === "/"}
                  >
                    <Link to="/">
                      <LayoutDashboard className="h-4 w-4" />
                      <span>Tableau de bord</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )}

              {/* User Management Section */}
              {canManageUsers && (
                <SidebarGroup>
                  <SidebarGroupLabel>
                    Gestion des utilisateurs
                  </SidebarGroupLabel>
                  <SidebarGroupContent>
                    <SidebarMenuSub>
                      <SidebarMenuSubItem>
                        <SidebarMenuSubButton
                          asChild
                          isActive={location.pathname === "/users"}
                        >
                          <Link to="/users">
                            <Users className="h-4 w-4" />
                            <span>Utilisateurs</span>
                          </Link>
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                      <SidebarMenuSubItem>
                        <SidebarMenuSubButton
                          asChild
                          isActive={location.pathname === "/roles"}
                        >
                          <Link to="/roles">
                            <Shield className="h-4 w-4" />
                            <span>Rôles</span>
                          </Link>
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                    </SidebarMenuSub>
                  </SidebarGroupContent>
                </SidebarGroup>
              )}

              {/* RBAC Management Section (permissions link removed) */}
              {canManageRBAC && (
                <SidebarGroup>
                  <SidebarGroupLabel>Gestion RBAC</SidebarGroupLabel>
                  <SidebarGroupContent>
                    <SidebarMenuSub>
                      <SidebarMenuSubItem>
                        <SidebarMenuSubButton
                          asChild
                          isActive={location.pathname === "/assign-role"}
                        >
                          <Link to="/assign-role">
                            <UserPlus className="h-4 w-4" />
                            <span>Attribuer des rôles</span>
                          </Link>
                        </SidebarMenuSubButton>
                      </SidebarMenuSubItem>
                    </SidebarMenuSub>
                  </SidebarGroupContent>
                </SidebarGroup>
              )}

              {/* Analytics Section */}
              {canViewAnalytics && (
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={location.pathname === "/analytics"}
                  >
                    <Link to="/analytics">
                      <BarChart3 className="h-4 w-4" />
                      <span>Analyses</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )}

              {/* Communication Section */}
              <SidebarGroup>
                <SidebarGroupLabel>Communication</SidebarGroupLabel>
                <SidebarGroupContent>
                  <SidebarMenuSub>
                    <SidebarMenuSubItem>
                      <SidebarMenuSubButton
                        asChild
                        isActive={location.pathname === "/notifications"}
                      >
                        <Link to="/notifications">
                          <Bell className="h-4 w-4" />
                          <span>Notifications</span>
                        </Link>
                      </SidebarMenuSubButton>
                    </SidebarMenuSubItem>
                    <SidebarMenuSubItem>
                      <SidebarMenuSubButton
                        asChild
                        isActive={location.pathname === "/messaging"}
                      >
                        <Link to="/messaging">
                          <MessageSquare className="h-4 w-4" />
                          <span>Messagerie</span>
                        </Link>
                      </SidebarMenuSubButton>
                    </SidebarMenuSubItem>
                  </SidebarMenuSub>
                </SidebarGroupContent>
              </SidebarGroup>

              {/* Settings Section removed */}

              {/* Logout */}
              <SidebarMenuItem>
                <SidebarMenuButton onClick={logout}>
                  <LogOut className="h-4 w-4" />
                  <span>Déconnexion</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarContent>
        </Sidebar>
      </div>
      {/* Main content: fills all available space */}
      <main className="flex flex-1 flex-col justify-start items-center p-8 bg-white min-h-screen w-full">
        {/* Header with notification bell */}
        <div className="w-full max-w-7xl mb-6">
          <div className="flex justify-between items-center">
            <div></div> {/* Spacer */}
            <div className="flex items-center gap-4">
              <NotificationBell unreadCount={0} />
            </div>
          </div>
        </div>
        <Outlet />
      </main>
    </div>
  );
}
