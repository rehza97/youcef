import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Badge } from "../../components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import { Plus, Edit, Trash2, Users, Shield, Settings } from "lucide-react";

const RolesPage = () => {
  const [roles, setRoles] = React.useState([
    {
      id: 1,
      name: "Administrator",
      description: "Full system access and control",
      users: 5,
      permissions: ["read", "write", "delete", "admin"],
      status: "active",
    },
    {
      id: 2,
      name: "Manager",
      description: "Department management and oversight",
      users: 12,
      permissions: ["read", "write"],
      status: "active",
    },
    {
      id: 3,
      name: "User",
      description: "Basic user access",
      users: 45,
      permissions: ["read"],
      status: "active",
    },
    {
      id: 4,
      name: "Guest",
      description: "Limited access for visitors",
      users: 8,
      permissions: ["read"],
      status: "inactive",
    },
  ]);

  const getStatusColor = (status) => {
    return status === "active"
      ? "bg-green-100 text-green-800"
      : "bg-gray-100 text-gray-800";
  };

  const getPermissionBadges = (permissions) => {
    return permissions.map((permission, index) => (
      <Badge key={index} variant="outline" className="mr-1 mb-1">
        {permission}
      </Badge>
    ));
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Roles Management</h1>
        <p className="text-gray-600 mt-2">Manage user roles and permissions</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Overview Cards */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Roles</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{roles.length}</div>
            <p className="text-xs text-muted-foreground">
              Active roles in the system
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Roles</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {roles.filter((role) => role.status === "active").length}
            </div>
            <p className="text-xs text-muted-foreground">
              Currently active roles
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Users</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {roles.reduce((total, role) => total + role.users, 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Users across all roles
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Actions</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <Button className="w-full" size="sm">
              <Plus className="h-4 w-4 mr-2" />
              Add Role
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Roles Table */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Roles List</CardTitle>
          <CardDescription>
            Manage and configure user roles and their permissions
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Role Name</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Users</TableHead>
                <TableHead>Permissions</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {roles.map((role) => (
                <TableRow key={role.id}>
                  <TableCell className="font-medium">{role.name}</TableCell>
                  <TableCell>{role.description}</TableCell>
                  <TableCell>{role.users}</TableCell>
                  <TableCell>
                    <div className="flex flex-wrap">
                      {getPermissionBadges(role.permissions)}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge className={getStatusColor(role.status)}>
                      {role.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <div className="flex space-x-2">
                      <Button size="sm" variant="outline">
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="text-red-600"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

export default RolesPage;
