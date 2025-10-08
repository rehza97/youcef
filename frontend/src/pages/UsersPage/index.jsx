import React from "react";
import {
  getUsers,
  getUser,
  createUser,
  updateUser,
  deleteUser,
  getRoles,
  createRole,
  updateRole,
  deleteRole,
  getPermissions,
  createPermission,
  updatePermission,
  deletePermission,
  assignRole,
  removeUserRole,
  getUserRoles,
  getRolePermissions,
  updateRolePermissions,
} from "../../services/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Badge } from "../../components/ui/badge";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "../../components/ui/avatar";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  Plus,
  Edit,
  Trash2,
  Users,
  UserPlus,
  Search,
  Filter,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogTrigger,
} from "../../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { useToast } from "../../hooks/use-toast";
import { PermissionGate } from "../../components/auth/PermissionRoute";

const UsersPage = () => {
  const [users, setUsers] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");
  const [isCreateOpen, setIsCreateOpen] = React.useState(false);
  const [isEditOpen, setIsEditOpen] = React.useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = React.useState(false);
  const [creating, setCreating] = React.useState(false);
  const [editing, setEditing] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);
  const { success, error: toastError } = useToast();
  const [roles, setRoles] = React.useState([]);
  const [rolesLoading, setRolesLoading] = React.useState(false);
  const [selectedUser, setSelectedUser] = React.useState(null);

  const [form, setForm] = React.useState({
    username: "",
    email: "",
    password: "",
    first_name: "",
    last_name: "",
    is_active: true,
    role_id: "",
  });

  const [editForm, setEditForm] = React.useState({
    username: "",
    email: "",
    first_name: "",
    last_name: "",
    is_active: true,
    role_id: "",
    current_role_id: "",
  });

  const onChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  const onEditChange = (e) => {
    const { name, value, type, checked } = e.target;
    setEditForm((prev) => ({
      ...prev,
      [name]: type === "checkbox" ? checked : value,
    }));
  };

  React.useEffect(() => {
    const fetchUsers = async () => {
      try {
        setLoading(true);
        setError("");
        const res = await getUsers();
        const baseUsers = (res.data || []).map((u) => ({
          id: u.id,
          name:
            u.first_name && u.last_name
              ? `${u.first_name} ${u.last_name}`
              : u.username,
          email: u.email,
          status: u.is_active ? "active" : "inactive",
          lastLogin: u.last_login
            ? new Date(u.last_login).toLocaleString()
            : "-",
          avatar: u.avatar_url || "/api/placeholder/40/40",
        }));
        const withRoles = await Promise.all(
          baseUsers.map(async (bu) => {
            try {
              const rolesRes = await getUserRoles(bu.id);
              const roleNames = (rolesRes.data?.roles || []).map((r) => r.name);
              return { ...bu, roles: roleNames };
            } catch {
              return { ...bu, roles: [] };
            }
          })
        );
        setUsers(withRoles);
      } catch (e) {
        setError(e?.response?.data?.detail || "Failed to load users");
      } finally {
        setLoading(false);
      }
    };
    fetchUsers();
    const fetchRoles = async () => {
      try {
        setRolesLoading(true);
        const res = await getRoles();
        setRoles(res.data || []);
      } finally {
        setRolesLoading(false);
      }
    };
    fetchRoles();
  }, []);

  const handleCreateUser = async (e) => {
    e?.preventDefault();
    if (!form.username?.trim() || !form.email?.trim() || !form.password) {
      toastError("Username, email and password are required");
      return;
    }
    try {
      setCreating(true);
      await createUser({
        username: form.username.trim(),
        email: form.email.trim(),
        password: form.password,
        first_name: form.first_name?.trim() || undefined,
        last_name: form.last_name?.trim() || undefined,
        is_active: !!form.is_active,
      });
      // fetch newly created user id by reloading users then assign role
      const newest = await getUsers();
      const created = (newest.data || []).find(
        (u) => u.username === form.username
      );
      if (created && form.role_id) {
        await assignRole({
          user_id: created.id,
          role_id: Number(form.role_id),
        });
      }
      success("User created successfully");
      setIsCreateOpen(false);
      setForm({
        username: "",
        email: "",
        password: "",
        first_name: "",
        last_name: "",
        is_active: true,
        role_id: "",
      });
      // reload users
      setLoading(true);
      const res = await getUsers();
      const baseUsers = (res.data || []).map((u) => ({
        id: u.id,
        name:
          u.first_name && u.last_name
            ? `${u.first_name} ${u.last_name}`
            : u.username,
        email: u.email,
        status: u.is_active ? "active" : "inactive",
        lastLogin: u.last_login ? new Date(u.last_login).toLocaleString() : "-",
        avatar: u.avatar_url || "/api/placeholder/40/40",
      }));
      const withRoles = await Promise.all(
        baseUsers.map(async (bu) => {
          try {
            const rolesRes = await getUserRoles(bu.id);
            const roleNames = (rolesRes.data?.roles || []).map((r) => r.name);
            return { ...bu, roles: roleNames };
          } catch {
            return { ...bu, roles: [] };
          }
        })
      );
      setUsers(withRoles);
    } catch (err) {
      toastError(err?.response?.data?.detail || "Failed to create user");
    } finally {
      setCreating(false);
      setLoading(false);
    }
  };

  const openEdit = async (user) => {
    try {
      setSelectedUser(user);
      setIsEditOpen(true);
      // load user roles
      const res = await getUserRoles(user.id);
      const rolesArr = res.data?.roles || [];
      const primaryRoleId = rolesArr.length ? String(rolesArr[0].id) : "";
      setEditForm({
        username: user.name || user.username,
        email: user.email,
        first_name: user.name?.split(" ")[0] || "",
        last_name: user.name?.split(" ").slice(1).join(" ") || "",
        is_active: user.status === "active",
        role_id: primaryRoleId,
        current_role_id: primaryRoleId,
      });
    } catch (err) {
      console.error(err);
      // even if roles fail, keep dialog open for basic edits
      setEditForm((prev) => ({ ...prev, role_id: "", current_role_id: "" }));
    }
  };

  const handleUpdateUser = async (e) => {
    e?.preventDefault();
    if (!selectedUser) return;
    try {
      setEditing(true);
      await updateUser(selectedUser.id, {
        email: editForm.email?.trim(),
        first_name: editForm.first_name?.trim() || null,
        last_name: editForm.last_name?.trim() || null,
        is_active: !!editForm.is_active,
      });

      // handle role change
      const prevId = editForm.current_role_id
        ? Number(editForm.current_role_id)
        : null;
      const nextId = editForm.role_id ? Number(editForm.role_id) : null;
      if (prevId !== nextId) {
        if (prevId) {
          try {
            await removeUserRole(selectedUser.id, prevId);
          } catch (err) {
            console.warn(err);
          }
        }
        if (nextId) {
          await assignRole({
            user_id: selectedUser.id,
            role_id: nextId,
          });
        }
      }

      success("User updated");
      setIsEditOpen(false);
      setSelectedUser(null);
      // refresh users
      setLoading(true);
      const res = await getUsers();
      const baseUsers = (res.data || []).map((u) => ({
        id: u.id,
        name:
          u.first_name && u.last_name
            ? `${u.first_name} ${u.last_name}`
            : u.username,
        email: u.email,
        status: u.is_active ? "active" : "inactive",
        lastLogin: u.last_login ? new Date(u.last_login).toLocaleString() : "-",
        avatar: u.avatar_url || "/api/placeholder/40/40",
      }));
      const withRoles = await Promise.all(
        baseUsers.map(async (bu) => {
          try {
            const rolesRes = await getUserRoles(bu.id);
            const roleNames = (rolesRes.data?.roles || []).map((r) => r.name);
            return { ...bu, roles: roleNames };
          } catch {
            return { ...bu, roles: [] };
          }
        })
      );
      setUsers(withRoles);
    } catch (err) {
      toastError(err?.response?.data?.detail || "Failed to update user");
    } finally {
      setEditing(false);
      setLoading(false);
    }
  };

  const openDelete = (user) => {
    setSelectedUser(user);
    setIsDeleteOpen(true);
  };

  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    try {
      setDeleting(true);
      await deleteUser(selectedUser.id);
      success("User deleted");
      setIsDeleteOpen(false);
      setSelectedUser(null);
      // refresh list
      setLoading(true);
      const res = await getUsers();
      const baseUsers = (res.data || []).map((u) => ({
        id: u.id,
        name:
          u.first_name && u.last_name
            ? `${u.first_name} ${u.last_name}`
            : u.username,
        email: u.email,
        status: u.is_active ? "active" : "inactive",
        lastLogin: u.last_login ? new Date(u.last_login).toLocaleString() : "-",
        avatar: u.avatar_url || "/api/placeholder/40/40",
      }));
      const withRoles = await Promise.all(
        baseUsers.map(async (bu) => {
          try {
            const rolesRes = await getUserRoles(bu.id);
            const roleNames = (rolesRes.data?.roles || []).map((r) => r.name);
            return { ...bu, roles: roleNames };
          } catch {
            return { ...bu, roles: [] };
          }
        })
      );
      setUsers(withRoles);
    } catch (err) {
      toastError(err?.response?.data?.detail || "Failed to delete user");
    } finally {
      setDeleting(false);
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    return status === "active"
      ? "bg-green-100 text-green-800"
      : "bg-gray-100 text-gray-800";
  };

  const getRoleColor = (role) => {
    switch (role?.toLowerCase()) {
      case "admin":
      case "administrator":
        return "bg-red-100 text-red-800";
      case "manager":
      case "moderator":
        return "bg-blue-100 text-blue-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Users Management</h1>
        <p className="text-gray-600 mt-2">
          Manage system users and their permissions
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Overview Cards */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Utilisateurs
            </CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{users.length}</div>
            <p className="text-xs text-muted-foreground">
              Utilisateurs dans le système
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Utilisateurs Actifs
            </CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {users.filter((user) => user.status === "active").length}
            </div>
            <p className="text-xs text-muted-foreground">
              Utilisateurs actuellement actifs
            </p>
          </CardContent>
        </Card>

        {/* Online Users card removed as presence is not tracked */}

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Actions</CardTitle>
            <UserPlus className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <PermissionGate permission="can_manage_users">
              <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                <DialogTrigger asChild>
                  <Button className="w-full" size="sm">
                    <Plus className="h-4 w-4 mr-2" />
                    Add User
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Create User</DialogTitle>
                    <DialogDescription>
                      Enter the new user details. Required fields are marked
                      with *.
                    </DialogDescription>
                  </DialogHeader>
                  <form onSubmit={handleCreateUser} className="space-y-4">
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm mb-1">Username *</label>
                        <Input
                          name="username"
                          value={form.username}
                          onChange={onChange}
                          placeholder="johndoe"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm mb-1">Email *</label>
                        <Input
                          name="email"
                          type="email"
                          value={form.email}
                          onChange={onChange}
                          placeholder="john@example.com"
                          required
                        />
                      </div>
                      <div>
                        <label className="block text-sm mb-1">First name</label>
                        <Input
                          name="first_name"
                          value={form.first_name}
                          onChange={onChange}
                          placeholder="John"
                        />
                      </div>
                      <div>
                        <label className="block text-sm mb-1">Last name</label>
                        <Input
                          name="last_name"
                          value={form.last_name}
                          onChange={onChange}
                          placeholder="Doe"
                        />
                      </div>
                      <div>
                        <label className="block text-sm mb-1">Role</label>
                        <Select
                          value={form.role_id}
                          onValueChange={(v) =>
                            setForm((p) => ({ ...p, role_id: v }))
                          }
                        >
                          <SelectTrigger className="w-full">
                            <SelectValue
                              placeholder={
                                rolesLoading
                                  ? "Loading..."
                                  : "Select role (optional)"
                              }
                            />
                          </SelectTrigger>
                          <SelectContent>
                            {roles.map((r) => (
                              <SelectItem key={r.id} value={String(r.id)}>
                                {r.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="sm:col-span-2">
                        <label className="block text-sm mb-1">Password *</label>
                        <Input
                          name="password"
                          type="password"
                          value={form.password}
                          onChange={onChange}
                          placeholder="Strong password"
                          required
                        />
                      </div>
                    </div>
                    <DialogFooter>
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setIsCreateOpen(false)}
                      >
                        Cancel
                      </Button>
                      <Button type="submit" disabled={creating}>
                        {creating ? "Creating..." : "Create"}
                      </Button>
                    </DialogFooter>
                  </form>
                </DialogContent>
              </Dialog>
            </PermissionGate>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filters */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle>Users List</CardTitle>
          <CardDescription>Search and manage system users</CardDescription>
        </CardHeader>
        <CardContent>
          {error && <div className="mb-4 text-sm text-red-600">{error}</div>}
          {loading && (
            <div className="mb-4 text-sm text-gray-600">Loading users...</div>
          )}
          <div className="flex flex-col sm:flex-row gap-4 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <Input placeholder="Search users..." className="pl-10" />
            </div>
            <Button variant="outline">
              <Filter className="h-4 w-4 mr-2" />
              Filter
            </Button>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>User</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Roles</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Last Login</TableHead>
                <TableHead>Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.length === 0 && !loading ? (
                <TableRow>
                  <TableCell
                    colSpan={6}
                    className="text-center text-sm text-gray-500"
                  >
                    No users found.
                  </TableCell>
                </TableRow>
              ) : (
                users.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell>
                      <div className="flex items-center space-x-3">
                        <Avatar className="h-8 w-8">
                          <AvatarImage src={user.avatar} alt={user.name} />
                          <AvatarFallback>
                            {user.name
                              .split(" ")
                              .map((n) => n[0])
                              .join("")}
                          </AvatarFallback>
                        </Avatar>
                        <span className="font-medium">{user.name}</span>
                      </div>
                    </TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <div className="flex gap-1 flex-wrap">
                        {(user.roles && user.roles.length > 0
                          ? user.roles
                          : ["User"]
                        ).map((r) => (
                          <Badge key={r} className={getRoleColor(r)}>
                            {r}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(user.status)}>
                        {user.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{user.lastLogin}</TableCell>
                    <TableCell>
                      <PermissionGate permission="can_manage_users">
                        <div className="flex space-x-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => openEdit(user)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-red-600"
                            onClick={() => openDelete(user)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </PermissionGate>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
      {/* Edit User Dialog */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit User</DialogTitle>
            <DialogDescription>Update user details and role.</DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUpdateUser} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm mb-1">Email</label>
                <Input
                  name="email"
                  type="email"
                  value={editForm.email}
                  onChange={onEditChange}
                />
              </div>
              <div>
                <label className="block text-sm mb-1">First name</label>
                <Input
                  name="first_name"
                  value={editForm.first_name}
                  onChange={onEditChange}
                />
              </div>
              <div>
                <label className="block text-sm mb-1">Last name</label>
                <Input
                  name="last_name"
                  value={editForm.last_name}
                  onChange={onEditChange}
                />
              </div>
              <div>
                <label className="block text-sm mb-1">Role</label>
                <Select
                  value={editForm.role_id}
                  onValueChange={(v) =>
                    setEditForm((p) => ({ ...p, role_id: v }))
                  }
                >
                  <SelectTrigger className="w-full">
                    <SelectValue
                      placeholder={rolesLoading ? "Loading..." : "Select role"}
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {roles.map((r) => (
                      <SelectItem key={r.id} value={String(r.id)}>
                        {r.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsEditOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={editing}>
                {editing ? "Saving..." : "Save"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete User</DialogTitle>
            <DialogDescription>
              This action cannot be undone. Are you sure you want to delete this
              user?
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsDeleteOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleDeleteUser}
              disabled={deleting}
              className="text-red-600"
            >
              {deleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default UsersPage;
