import React from "react";
import { usersAPI } from "../../services/api";
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
import {
  Plus,
  Edit,
  Trash2,
  Users,
  Shield,
  Settings,
  Search,
  X,
  Eye,
  Copy,
  Filter,
  Download,
  Upload,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Info,
} from "lucide-react";
import { PermissionGate } from "../../components/auth/PermissionRoute";
import { useToast } from "../../hooks/use-toast";

const RolesPage = () => {
  const [roles, setRoles] = React.useState([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState("");
  const [isCreateOpen, setIsCreateOpen] = React.useState(false);
  const [isEditOpen, setIsEditOpen] = React.useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = React.useState(false);
  const [isViewOpen, setIsViewOpen] = React.useState(false);
  const [isBulkDeleteOpen, setIsBulkDeleteOpen] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);
  const [selectedRole, setSelectedRole] = React.useState(null);
  const [allPermissions, setAllPermissions] = React.useState([]);
  const [query, setQuery] = React.useState("");
  const [filterStatus, setFilterStatus] = React.useState("all");
  const [sortBy, setSortBy] = React.useState("name");
  const [sortOrder, setSortOrder] = React.useState("asc");
  const [selectedRoles, setSelectedRoles] = React.useState(new Set());
  const [viewingPermissions, setViewingPermissions] = React.useState([]);
  const { success, error: toastError } = useToast();

  const [createForm, setCreateForm] = React.useState({
    name: "",
    description: "",
    permissionIds: [],
  });

  const [editForm, setEditForm] = React.useState({
    id: null,
    name: "",
    description: "",
    permissionIds: [],
  });

  const [permQuery, setPermQuery] = React.useState("");
  const [permGroupFilter, setPermGroupFilter] = React.useState("all");

  const onCreateChange = (e) => {
    const { name, value } = e.target;
    setCreateForm((prev) => ({ ...prev, [name]: value }));
  };

  const onEditChange = (e) => {
    const { name, value } = e.target;
    setEditForm((prev) => ({ ...prev, [name]: value }));
  };

  const togglePermission = (permId, isCreate = false) => {
    const setFormFunc = isCreate ? setCreateForm : setEditForm;
    setFormFunc((prev) => {
      const setIds = new Set(prev.permissionIds);
      if (setIds.has(permId)) {
        setIds.delete(permId);
      } else {
        setIds.add(permId);
      }
      return { ...prev, permissionIds: Array.from(setIds) };
    });
  };

  const loadRoles = async () => {
    try {
      setLoading(true);
      setError("");
      const res = await usersAPI.getRoles();
      setRoles(res.data || []);
    } catch (e) {
      setError(e?.response?.data?.detail || "Failed to load roles");
      toastError("Failed to load roles");
    } finally {
      setLoading(false);
    }
  };

  const loadAllPermissions = async () => {
    try {
      const res = await usersAPI.getPermissions();
      setAllPermissions(res.data || []);
    } catch (e) {
      console.error("Failed to load permissions", e);
    }
  };

  React.useEffect(() => {
    loadRoles();
    loadAllPermissions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const getPermissionGroups = () => {
    const groups = new Set();
    allPermissions.forEach((p) => {
      const group = p.codename?.split("_")[0] || "other";
      groups.add(group);
    });
    return Array.from(groups).sort();
  };

  const filteredAndSortedRoles = React.useMemo(() => {
    let filtered = roles.filter((r) => {
      const matchesQuery = query.trim()
        ? r.name.toLowerCase().includes(query.toLowerCase()) ||
          (r.description || "").toLowerCase().includes(query.toLowerCase())
        : true;

      const matchesStatus =
        filterStatus === "all" ||
        (filterStatus === "with_users" && (r.users || 0) > 0) ||
        (filterStatus === "no_users" && (r.users || 0) === 0);

      return matchesQuery && matchesStatus;
    });

    filtered.sort((a, b) => {
      let aVal = a[sortBy];
      let bVal = b[sortBy];

      if (sortBy === "permission_count") {
        aVal = a.permission_count || 0;
        bVal = b.permission_count || 0;
      }

      if (typeof aVal === "string") {
        aVal = aVal.toLowerCase();
        bVal = (bVal || "").toLowerCase();
      }

      if (sortOrder === "asc") {
        return aVal > bVal ? 1 : -1;
      } else {
        return aVal < bVal ? 1 : -1;
      }
    });

    return filtered;
  }, [roles, query, filterStatus, sortBy, sortOrder]);

  const openCreate = () => {
    setCreateForm({ name: "", description: "", permissionIds: [] });
    setPermQuery("");
    setPermGroupFilter("all");
    setIsCreateOpen(true);
  };

  const handleCreate = async (e) => {
    e?.preventDefault();
    if (!createForm.name?.trim()) {
      toastError("Role name is required");
      return;
    }
    try {
      setSaving(true);
      const res = await usersAPI.createRole({
        name: createForm.name.trim(),
        description: createForm.description?.trim() || null,
      });

      // Assign permissions if any selected
      if (createForm.permissionIds.length > 0) {
        await usersAPI.updateRolePermissions(
          res.data.id,
          createForm.permissionIds
        );
      }

      setIsCreateOpen(false);
      success("Role created successfully");
      await loadRoles();
    } catch (e) {
      toastError(e?.response?.data?.detail || "Failed to create role");
    } finally {
      setSaving(false);
    }
  };

  const openEdit = async (role) => {
    setSelectedRole(role);
    setIsEditOpen(true);
    setPermQuery("");
    setPermGroupFilter("all");
    setEditForm({
      id: role.id,
      name: role.name,
      description: role.description || "",
      permissionIds: [],
    });
    try {
      const rp = await usersAPI.getRolePermissions(role.id);
      const ids = (rp.data?.permissions || []).map((p) => p.id);
      setEditForm((prev) => ({ ...prev, permissionIds: ids }));
    } catch (e) {
      console.error("Failed to load role permissions", e);
    }
  };

  const openView = async (role) => {
    setSelectedRole(role);
    setIsViewOpen(true);
    setViewingPermissions([]);
    try {
      const rp = await usersAPI.getRolePermissions(role.id);
      setViewingPermissions(rp.data?.permissions || []);
    } catch {
      toastError("Failed to load role permissions");
    }
  };

  const handleUpdate = async (e) => {
    e?.preventDefault();
    if (!editForm.id) return;
    if (!editForm.name?.trim()) {
      toastError("Role name is required");
      return;
    }
    try {
      setSaving(true);
      await usersAPI.updateRole(editForm.id, {
        name: editForm.name?.trim(),
        description: editForm.description?.trim() || null,
      });
      await usersAPI.updateRolePermissions(editForm.id, editForm.permissionIds);
      setIsEditOpen(false);
      setSelectedRole(null);
      success("Role updated successfully");
      await loadRoles();
    } catch (e) {
      toastError(e?.response?.data?.detail || "Failed to update role");
    } finally {
      setSaving(false);
    }
  };

  const openDelete = (role) => {
    setSelectedRole(role);
    setIsDeleteOpen(true);
  };

  const handleDelete = async () => {
    if (!selectedRole) return;
    try {
      setDeleting(true);
      await usersAPI.deleteRole(selectedRole.id);
      setIsDeleteOpen(false);
      setSelectedRole(null);
      success("Role deleted successfully");
      await loadRoles();
    } catch (e) {
      toastError(e?.response?.data?.detail || "Failed to delete role");
    } finally {
      setDeleting(false);
    }
  };

  const handleBulkDelete = async () => {
    try {
      setDeleting(true);
      await Promise.all(
        Array.from(selectedRoles).map((id) => usersAPI.deleteRole(id))
      );
      setIsBulkDeleteOpen(false);
      setSelectedRoles(new Set());
      success(`${selectedRoles.size} roles deleted successfully`);
      await loadRoles();
    } catch {
      toastError("Failed to delete some roles");
    } finally {
      setDeleting(false);
    }
  };

  const handleDuplicateRole = async (role) => {
    try {
      setSaving(true);
      const newRole = await usersAPI.createRole({
        name: `${role.name} (Copy)`,
        description: role.description,
      });

      // Copy permissions
      const rp = await usersAPI.getRolePermissions(role.id);
      const ids = (rp.data?.permissions || []).map((p) => p.id);
      if (ids.length > 0) {
        await usersAPI.updateRolePermissions(newRole.data.id, ids);
      }

      success("Role duplicated successfully");
      await loadRoles();
    } catch {
      toastError("Failed to duplicate role");
    } finally {
      setSaving(false);
    }
  };

  const toggleRoleSelection = (roleId) => {
    setSelectedRoles((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(roleId)) {
        newSet.delete(roleId);
      } else {
        newSet.add(roleId);
      }
      return newSet;
    });
  };

  const toggleSelectAll = () => {
    if (selectedRoles.size === filteredAndSortedRoles.length) {
      setSelectedRoles(new Set());
    } else {
      setSelectedRoles(new Set(filteredAndSortedRoles.map((r) => r.id)));
    }
  };

  const exportRoles = () => {
    const data = JSON.stringify(roles, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `roles_export_${new Date().toISOString()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    success("Roles exported successfully");
  };

  const getFilteredPermissions = () => {
    return allPermissions.filter((p) => {
      const matchesQuery = permQuery.trim()
        ? (p.name || "").toLowerCase().includes(permQuery.toLowerCase()) ||
          (p.codename || "").toLowerCase().includes(permQuery.toLowerCase())
        : true;

      const matchesGroup =
        permGroupFilter === "all" || p.codename?.startsWith(permGroupFilter);

      return matchesQuery && matchesGroup;
    });
  };

  const PermissionSelector = ({ isCreate = false }) => {
    const form = isCreate ? createForm : editForm;
    const filteredPerms = getFilteredPermissions();
    const selectedCount = form.permissionIds.length;
    const visibleCount = filteredPerms.length;

    return (
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Label className="m-0">Permissions</Label>
            <Badge variant="secondary" className="text-xs">
              {selectedCount} selected
            </Badge>
          </div>
          <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
            <Input
              placeholder="Search permissions..."
              value={permQuery}
              onChange={(e) => setPermQuery(e.target.value)}
              className="h-8 w-full sm:w-48"
            />
            <Select value={permGroupFilter} onValueChange={setPermGroupFilter}>
              <SelectTrigger className="h-8 w-full sm:w-32">
                <SelectValue placeholder="Group" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Groups</SelectItem>
                {getPermissionGroups().map((group) => (
                  <SelectItem key={group} value={group}>
                    {group}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => {
                const ids = filteredPerms.map((p) => p.id);
                const setIds = new Set(form.permissionIds);
                ids.forEach((id) => setIds.add(id));
                if (isCreate) {
                  setCreateForm((prev) => ({
                    ...prev,
                    permissionIds: Array.from(setIds),
                  }));
                } else {
                  setEditForm((prev) => ({
                    ...prev,
                    permissionIds: Array.from(setIds),
                  }));
                }
              }}
            >
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Select All
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8"
              onClick={() => {
                if (!permQuery.trim() && permGroupFilter === "all") {
                  if (isCreate) {
                    setCreateForm((prev) => ({ ...prev, permissionIds: [] }));
                  } else {
                    setEditForm((prev) => ({ ...prev, permissionIds: [] }));
                  }
                } else {
                  const setIds = new Set(form.permissionIds);
                  filteredPerms.forEach((p) => setIds.delete(p.id));
                  if (isCreate) {
                    setCreateForm((prev) => ({
                      ...prev,
                      permissionIds: Array.from(setIds),
                    }));
                  } else {
                    setEditForm((prev) => ({
                      ...prev,
                      permissionIds: Array.from(setIds),
                    }));
                  }
                }
              }}
            >
              <X className="h-3 w-3 mr-1" />
              Clear
            </Button>
          </div>
        </div>

        <div className="border rounded-md max-h-[50vh] overflow-auto">
          {filteredPerms.length === 0 ? (
            <div className="p-8 text-center text-sm text-gray-500">
              <Info className="h-8 w-8 mx-auto mb-2 text-gray-400" />
              No permissions found
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 p-3">
              {filteredPerms.map((p) => {
                const checked = form.permissionIds.includes(p.id);
                return (
                  <label
                    key={p.id}
                    className={`flex items-start gap-2 p-2 rounded border cursor-pointer transition-colors ${
                      checked
                        ? "bg-blue-50 border-blue-300"
                        : "hover:bg-gray-50 border-transparent"
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => togglePermission(p.id, isCreate)}
                      className="mt-0.5"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">
                        {p.name}
                      </div>
                      <div className="text-xs text-gray-500 truncate">
                        {p.codename}
                      </div>
                    </div>
                  </label>
                );
              })}
            </div>
          )}
        </div>
        <div className="text-xs text-gray-500">
          Showing {visibleCount} of {allPermissions.length} permissions
        </div>
      </div>
    );
  };

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Roles Management</h1>
        <p className="text-gray-600 mt-2">
          Manage user roles, permissions, and access control
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Roles</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{roles.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Active roles in the system
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Roles With Users
            </CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {roles.filter((r) => (r.users || 0) > 0).length}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Have at least one user
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Total Permissions
            </CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{allPermissions.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Available permissions
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Quick Actions</CardTitle>
            <Settings className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="flex flex-col gap-2">
              <PermissionGate permission="can_manage_rbac">
                <Button className="w-full" size="sm" onClick={openCreate}>
                  <Plus className="h-4 w-4 mr-2" />
                  Add Role
                </Button>
              </PermissionGate>
              <Button variant="outline" size="sm" onClick={() => loadRoles()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Roles Table */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <CardTitle>Roles List</CardTitle>
              <CardDescription>
                Manage and configure user roles and their permissions
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={exportRoles}
                disabled={roles.length === 0}
              >
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
              {selectedRoles.size > 0 && (
                <PermissionGate permission="can_manage_rbac">
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => setIsBulkDeleteOpen(true)}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete ({selectedRoles.size})
                  </Button>
                </PermissionGate>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters & Search */}
          <div className="flex flex-col sm:flex-row gap-3 mb-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search roles by name or description..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={filterStatus} onValueChange={setFilterStatus}>
              <SelectTrigger className="w-full sm:w-40">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Filter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Roles</SelectItem>
                <SelectItem value="with_users">With Users</SelectItem>
                <SelectItem value="no_users">No Users</SelectItem>
              </SelectContent>
            </Select>
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-full sm:w-40">
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="name">Name</SelectItem>
                <SelectItem value="permission_count">Permissions</SelectItem>
                <SelectItem value="users">Users</SelectItem>
              </SelectContent>
            </Select>
            <Button
              variant="outline"
              size="icon"
              onClick={() => setSortOrder(sortOrder === "asc" ? "desc" : "asc")}
            >
              {sortOrder === "asc" ? "↑" : "↓"}
            </Button>
          </div>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md flex items-center gap-2 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}

          {loading ? (
            <div className="py-12 text-center">
              <RefreshCw className="h-8 w-8 mx-auto mb-3 text-gray-400 animate-spin" />
              <p className="text-sm text-gray-600">Loading roles...</p>
            </div>
          ) : (
            <div className="rounded-md border overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <input
                        type="checkbox"
                        checked={
                          selectedRoles.size ===
                            filteredAndSortedRoles.length &&
                          filteredAndSortedRoles.length > 0
                        }
                        onChange={toggleSelectAll}
                        className="cursor-pointer"
                      />
                    </TableHead>
                    <TableHead>Role Name</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="text-center">Permissions</TableHead>
                    <TableHead className="text-center">Users</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredAndSortedRoles.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-12">
                        <Shield className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                        <p className="text-sm text-gray-500">
                          {query || filterStatus !== "all"
                            ? "No roles match your filters"
                            : "No roles found. Create your first role to get started."}
                        </p>
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredAndSortedRoles.map((role) => (
                      <TableRow key={role.id}>
                        <TableCell>
                          <input
                            type="checkbox"
                            checked={selectedRoles.has(role.id)}
                            onChange={() => toggleRoleSelection(role.id)}
                            className="cursor-pointer"
                          />
                        </TableCell>
                        <TableCell>
                          <div className="font-medium">{role.name}</div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm text-gray-600 max-w-xs truncate">
                            {role.description || "—"}
                          </div>
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant="outline" className="font-mono">
                            {role.permission_count ?? 0}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-center">
                          <Badge variant="secondary" className="font-mono">
                            {role.users ?? 0}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center justify-end gap-1">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => openView(role)}
                              title="View details"
                            >
                              <Eye className="h-4 w-4" />
                            </Button>
                            <PermissionGate permission="can_manage_rbac">
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => openEdit(role)}
                                title="Edit role"
                              >
                                <Edit className="h-4 w-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                onClick={() => handleDuplicateRole(role)}
                                title="Duplicate role"
                              >
                                <Copy className="h-4 w-4" />
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                                onClick={() => openDelete(role)}
                                title="Delete role"
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </PermissionGate>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>
          )}

          {!loading && filteredAndSortedRoles.length > 0 && (
            <div className="mt-4 text-sm text-gray-500">
              Showing {filteredAndSortedRoles.length} of {roles.length} roles
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Role Dialog */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Create New Role</DialogTitle>
            <DialogDescription>
              Define a new role with name, description, and permissions.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-6">
            <div className="grid grid-cols-1 gap-4">
              <div>
                <Label className="block mb-2">
                  Role Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  name="name"
                  value={createForm.name}
                  onChange={onCreateChange}
                  placeholder="e.g. Admin, Editor, Viewer"
                  required
                  autoFocus
                />
              </div>
              <div>
                <Label className="block mb-2">Description</Label>
                <Input
                  name="description"
                  value={createForm.description}
                  onChange={onCreateChange}
                  placeholder="Brief description of this role's purpose"
                />
              </div>
            </div>

            <PermissionSelector isCreate={true} />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsCreateOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Role
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Edit Role Dialog */}
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit Role</DialogTitle>
            <DialogDescription>
              Update role details and manage permissions.
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleUpdate} className="space-y-6">
            <div className="grid grid-cols-1 gap-4">
              <div>
                <Label className="block mb-2">
                  Role Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  name="name"
                  value={editForm.name}
                  onChange={onEditChange}
                  required
                />
              </div>
              <div>
                <Label className="block mb-2">Description</Label>
                <Input
                  name="description"
                  value={editForm.description}
                  onChange={onEditChange}
                />
              </div>
            </div>

            <PermissionSelector isCreate={false} />

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsEditOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <CheckCircle2 className="h-4 w-4 mr-2" />
                    Save Changes
                  </>
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* View Role Dialog */}
      <Dialog open={isViewOpen} onOpenChange={setIsViewOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Role Details</DialogTitle>
            <DialogDescription>
              View role information and assigned permissions
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-gray-500">Role Name</Label>
                <div className="text-lg font-semibold mt-1">
                  {selectedRole?.name}
                </div>
              </div>
              <div>
                <Label className="text-xs text-gray-500">Users Count</Label>
                <div className="text-lg font-semibold mt-1">
                  {selectedRole?.users || 0}
                </div>
              </div>
              <div className="col-span-2">
                <Label className="text-xs text-gray-500">Description</Label>
                <div className="text-sm mt-1">
                  {selectedRole?.description || "No description provided"}
                </div>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-3">
                <Label>Assigned Permissions</Label>
                <Badge variant="secondary">
                  {viewingPermissions.length} permissions
                </Badge>
              </div>
              <div className="border rounded-md max-h-96 overflow-y-auto">
                {viewingPermissions.length === 0 ? (
                  <div className="p-8 text-center text-sm text-gray-500">
                    <Shield className="h-8 w-8 mx-auto mb-2 text-gray-400" />
                    No permissions assigned
                  </div>
                ) : (
                  <div className="divide-y">
                    {viewingPermissions.map((perm) => (
                      <div
                        key={perm.id}
                        className="p-3 hover:bg-gray-50 transition-colors"
                      >
                        <div className="font-medium text-sm">{perm.name}</div>
                        <div className="text-xs text-gray-500">
                          {perm.codename}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsViewOpen(false)}>
              Close
            </Button>
            <PermissionGate permission="can_manage_rbac">
              <Button
                onClick={() => {
                  setIsViewOpen(false);
                  openEdit(selectedRole);
                }}
              >
                <Edit className="h-4 w-4 mr-2" />
                Edit Role
              </Button>
            </PermissionGate>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Role Confirmation */}
      <Dialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Role</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete the role {""}
              <strong>{selectedRole?.name}</strong>? This action cannot be
              undone.
              {(selectedRole?.users || 0) > 0 && (
                <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-md text-amber-800">
                  <AlertCircle className="h-4 w-4 inline mr-2" />
                  Warning: This role has {selectedRole.users} user(s) assigned.
                  They will lose these permissions.
                </div>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleDelete}
              disabled={deleting}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {deleting ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete Role
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Delete Confirmation */}
      <Dialog open={isBulkDeleteOpen} onOpenChange={setIsBulkDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Multiple Roles</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete {selectedRoles.size} selected
              roles? This action cannot be undone.
              <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-md text-amber-800">
                <AlertCircle className="h-4 w-4 inline mr-2" />
                Warning: Users assigned to these roles will lose their
                permissions.
              </div>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsBulkDeleteOpen(false)}
            >
              Cancel
            </Button>
            <Button
              onClick={handleBulkDelete}
              disabled={deleting}
              className="bg-red-600 hover:bg-red-700 text-white"
            >
              {deleting ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Deleting...
                </>
              ) : (
                <>
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete {selectedRoles.size} Roles
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default RolesPage;
