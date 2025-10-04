# Permission System Implementation - Complete Guide

## Overview
Complete implementation of a robust permission-based access control (PBAC) system integrated with DOT (regional) scoping for the FastAPI backend and React frontend.

---

## Backend Implementation

### 1. Permission Service (`fastapi_backend/services/permission_service.py`)

**Key Features:**
- ✅ Admin override: Admin users automatically pass all permission checks
- ✅ Granular permission checking via `has_permission()` and `require_permission()`
- ✅ DOT-based regional access control via `check_dot_user_permissions()`
- ✅ Support for role-based hierarchies (admin > super_user > dot_user)

**Core Methods:**
- `has_permission(user, db, codename)` - Check if user has specific permission
- `require_permission(user, db, codename)` - Enforce permission or raise 403
- `check_dot_user_permissions(user, db, required_dot)` - Validate DOT access
- `get_user_dot_region(user, db)` - Get user's DOT restriction (None for admin/super)

### 2. Permission Codenames Defined

Created **25 comprehensive permissions** covering all system actions:

#### User & Role Management
- `can_manage_users` - Create, update, delete users
- `can_view_users` - View user lists (read-only)
- `can_manage_rbac` - Manage roles and permissions
- `can_view_rbac` - View roles/permissions (read-only)

#### Dashboard & Analytics
- `can_view_dashboard` - Access main dashboard
- `can_view_analytics` - View analytics pages
- `can_export_analytics` - Export analytics reports
- `can_view_encaissement_data` - View encaissement analytics (DOT-scoped)

#### File Management
- `can_upload_files` - Upload files to system
- `can_manage_files` - Admin file operations (view all, delete any)
- `can_manage_own_files` - Manage user's own files

#### ETL & Data Processing
- `can_run_etl` - Execute ETL data pipelines
- `can_view_etl_results` - View/download ETL outputs

#### Messaging & Notifications
- `can_send_messages` - Send messages to users
- `can_manage_messages` - Moderate all messages (admin)
- `can_manage_notifications` - Configure system notifications
- `can_broadcast` - Send broadcast messages

#### Settings & Configuration
- `can_manage_settings` - Modify system settings
- `can_view_settings` - View settings (read-only)

#### DOT & Data Access
- `can_view_dot_data` - View DOT-scoped data
- `can_view_all_dots` - Access all DOT regions (admin/super)
- `can_manage_dots` - CRUD DOT regions
- `can_view_park_data` - View park data (DOT-scoped)
- `can_manage_park_data` - Import/process park data

#### Audit
- `can_view_audit_logs` - View system audit logs

### 3. Database Seeding

**Migration Script:** `fastapi_backend/migrations/seed_permissions.py`

```bash
# Run migration to seed all permissions
python -m fastapi_backend.migrations.seed_permissions
```

**Features:**
- Creates all 25 permissions automatically
- Updates existing permissions if definitions change
- Safe to run multiple times (idempotent)
- Logs created/updated/skipped counts

### 4. Endpoint Protection Applied

#### File Management (`api/file_upload.py`, `api/file_management.py`)
- `POST /upload` → requires `can_upload_files`
- `POST /upload-batch` → requires `can_upload_files`
- `GET /user/{user_id}` → requires `can_manage_files`

#### ETL Processing (`api/etl_processing.py`)
- `POST /encaissement/process` → requires `can_run_etl`
- `POST /subscriber-park/process` → requires `can_run_etl`
- `POST /parc-corporate-ngbss/process` → requires `can_run_etl`
- `GET /encaissement/results/*` → requires `can_view_etl_results`
- `GET /encaissement/history` → requires `can_view_etl_results`
- `POST /validate-etl-files` → requires `can_run_etl`

#### Analytics (`api/encaissement_analytics.py`)
- `GET /by-date` → requires `can_view_encaissement_data`
- `GET /by-encaisse-rate` → requires `can_view_encaissement_data`
- `GET /export-report` → requires `can_export_analytics`
- Overview and performance metrics → DOT-scoped via `check_dot_user_permissions()`

#### User Management (`api/users_management.py`)
- `POST /` (create user) → requires `can_manage_users`
- `GET /` (list users) → requires `can_manage_users`

#### Role Management (`api/role_management.py`)
- All CRUD operations → require `can_manage_rbac`

#### Permission Management (`api/permission_management.py`)
- All operations → require `can_manage_rbac`

#### DOT Management (`api/park_management.py`)
- `POST /dots/` → requires admin (checked via `check_admin_permissions`)
- `PUT /dots/{id}` → requires admin
- `DELETE /dots/{id}` → requires admin
- `POST /dots/{id}/assign-user/{user_id}` → requires admin
- `DELETE /users/{user_id}/dot-assignment` → requires admin
- All data access endpoints → DOT-scoped via `DOTService.get_user_accessible_dots()`

### 5. DOT Access Control

**How it works:**
1. Admin and SUPER_USER: unrestricted access to all DOTs
2. DOT_USER: restricted to assigned `user.dot_id`
3. Permission checks run first, then DOT filtering applies to data

**Key DOT endpoints ensure admin-only access:**
- Create DOT
- Update DOT
- Delete DOT
- Assign user to DOT
- Remove DOT assignment

---

## Frontend Implementation

### 1. Permission Hook (`hooks/usePermission.js`)

Already existed - checks permission via API:
```javascript
const { hasPermission, loading } = usePermission('can_manage_users');
```

### 2. Permission Components (`components/auth/PermissionRoute.jsx`)

**Created two utility components:**

#### `<PermissionRoute>` - For route protection
```jsx
<PermissionRoute permission="can_manage_users" fallbackPath="/dashboard">
  <UsersPage />
</PermissionRoute>
```

**Features:**
- Shows loading spinner while checking permission
- Redirects to fallback path (default: `/dashboard`) if denied
- Can show custom fallback component instead of redirecting

#### `<PermissionGate>` - For UI element gating
```jsx
<PermissionGate permission="can_manage_users">
  <Button onClick={createUser}>Create User</Button>
</PermissionGate>
```

**Features:**
- Conditionally renders children based on permission
- Optional fallback content if permission denied
- Lightweight - returns null while loading

### 3. Protected Routes (`App.jsx`)

**Updated routes with permission guards:**

```jsx
// Users page - requires can_manage_users
<Route path="/users" element={
  <ProtectedRoute>
    <PermissionRoute permission="can_manage_users">
      <UsersPage />
    </PermissionRoute>
  </ProtectedRoute>
} />

// Roles page - requires can_manage_rbac
<Route path="/roles" element={
  <ProtectedRoute>
    <PermissionRoute permission="can_manage_rbac">
      <RolesPage />
    </PermissionRoute>
  </ProtectedRoute>
} />

// Permissions page - requires can_manage_rbac
<Route path="/permissions" element={
  <ProtectedRoute>
    <PermissionRoute permission="can_manage_rbac">
      <PermissionsPage />
    </PermissionRoute>
  </ProtectedRoute>
} />

// Settings page - requires can_manage_settings
<Route path="/settings" element={
  <ProtectedRoute>
    <PermissionRoute permission="can_manage_settings">
      <SettingsPage />
    </PermissionRoute>
  </ProtectedRoute>
} />

// Encaissement analytics - requires can_view_encaissement_data
<Route path="/encaissement" element={
  <ProtectedRoute>
    <PermissionRoute permission="can_view_encaissement_data">
      <EncaissementPage />
    </PermissionRoute>
  </ProtectedRoute>
} />
```

### 4. Button-Level Permissions

**UsersPage (`pages/UsersPage/index.jsx`):**
```jsx
// Create button - only shown if user has can_manage_users
<PermissionGate permission="can_manage_users">
  <Dialog>
    <DialogTrigger asChild>
      <Button>
        <Plus /> Add User
      </Button>
    </DialogTrigger>
    {/* ... */}
  </Dialog>
</PermissionGate>

// Edit/Delete buttons in table
<PermissionGate permission="can_manage_users">
  <Button onClick={() => openEdit(user)}>
    <Edit />
  </Button>
  <Button onClick={() => openDelete(user)}>
    <Trash2 />
  </Button>
</PermissionGate>
```

**RolesPage (`pages/RolesPage/index.jsx`):**
```jsx
// Create role button
<PermissionGate permission="can_manage_rbac">
  <Dialog>
    <DialogTrigger asChild>
      <Button>
        <Plus /> Add Role
      </Button>
    </DialogTrigger>
    {/* ... */}
  </Dialog>
</PermissionGate>

// Edit/Delete buttons
<PermissionGate permission="can_manage_rbac">
  <Button onClick={() => openEdit(role)}>
    <Edit />
  </Button>
  <Button onClick={() => openDelete(role)}>
    <Trash2 />
  </Button>
</PermissionGate>
```

---

## Admin Control Features

### 1. Role & Permission Management

**Admin can:**
- ✅ Create new roles via RolesPage
- ✅ Assign permissions to roles via role edit dialog
- ✅ Remove permissions from roles
- ✅ Delete roles (if not in use)
- ✅ View all permissions in system

**How it works:**
- Admin (or user with `can_manage_rbac`) accesses `/roles`
- Click "Add Role" → Create new role with name/description
- Click Edit on role → Multi-select permission checkboxes
- Assign/revoke permissions → Saved via `POST /api/roles/{id}/permissions/{perm_id}`

### 2. DOT Assignment Control

**Admin can:**
- ✅ Create DOT regions via `POST /api/parks/dots/`
- ✅ Update DOT details via `PUT /api/parks/dots/{id}`
- ✅ Delete DOT regions via `DELETE /api/parks/dots/{id}`
- ✅ Assign users to DOT via `POST /api/parks/dots/{id}/assign-user/{user_id}`
- ✅ Remove user DOT assignment via `DELETE /api/parks/users/{user_id}/dot-assignment`
- ✅ View DOT statistics and user lists per DOT

**API Endpoints:**
```python
# DOT CRUD (admin only)
POST   /api/parks/dots/              # Create DOT
GET    /api/parks/dots/              # List all DOTs
GET    /api/parks/dots/{id}          # Get DOT details
PUT    /api/parks/dots/{id}          # Update DOT
DELETE /api/parks/dots/{id}          # Delete DOT

# DOT User Assignment (admin only)
POST   /api/parks/dots/{id}/assign-user/{user_id}  # Assign user to DOT
DELETE /api/parks/users/{user_id}/dot-assignment   # Remove DOT assignment
GET    /api/parks/dots/{id}/users                  # List users in DOT
GET    /api/parks/dots/{id}/statistics             # DOT stats
```

### 3. Permission-DOT Interaction

**How permissions and DOT work together:**

1. **Permission Check First:**
   - User must have required permission (e.g., `can_view_encaissement_data`)
   - Admin always passes permission checks

2. **DOT Filtering Applied:**
   - If user has DOT assignment (DOT_USER) → data filtered to their DOT
   - If user is admin/SUPER_USER → sees all DOT data
   - Example: DOT_USER with `can_view_encaissement_data` sees only their DOT's analytics

3. **Admin Override:**
   - Admin role bypasses all permission checks
   - Admin sees all DOT data regardless of DOT assignment
   - Admin can manage all DOT assignments

---

## Default Roles

The system automatically creates **8 default roles** on first run:

### 1. **admin**
- **Description:** System administrator with full access to all features and data
- **Permissions:** ALL (automatically gets all 25 permissions)
- **Use case:** Full system administration

### 2. **SUPER_USER**
- **Description:** Super user with access to all DOT regions and most management features
- **Permissions:** 15 permissions including analytics, ETL, file management, view all DOTs
- **Use case:** Cross-regional managers, senior analysts

### 3. **DOT_USER**
- **Description:** Regional user with access restricted to their assigned DOT region
- **Permissions:** 7 permissions including dashboard, analytics (DOT-scoped), messaging
- **Use case:** Regional staff, local operators

### 4. **Data Analyst**
- **Description:** Analyst with read access to analytics and reporting features
- **Permissions:** 7 permissions including analytics viewing, export, ETL results
- **Use case:** Business analysts, data scientists

### 5. **File Manager**
- **Description:** User who can upload and manage files
- **Permissions:** 4 permissions including upload, manage all files
- **Use case:** Document administrators, content managers

### 6. **ETL Operator**
- **Description:** User who can run ETL processes and view results
- **Permissions:** 7 permissions including ETL operations, park data management
- **Use case:** Data engineers, ETL specialists

### 7. **Moderator**
- **Description:** User who can manage messages and notifications
- **Permissions:** 6 permissions including message management, broadcasts, view users
- **Use case:** Community managers, support staff

### 8. **User**
- **Description:** Basic user with minimal permissions
- **Permissions:** 3 permissions (dashboard, messages, own files)
- **Use case:** Standard end users

---

## Automatic Initialization

The RBAC system **automatically initializes on first run** of the FastAPI backend:

1. When you start the backend, it checks if permissions and roles exist
2. If not found, it automatically:
   - Creates all 25 permissions
   - Creates all 8 default roles
   - Assigns permissions to each role
3. Logs the initialization process to console

**No manual steps required!** Just start your backend and the system is ready.

---

## Manual Initialization (Optional)

If you need to manually initialize or re-initialize:

### Option 1: Run master init script
```bash
cd fastapi_backend
python -m migrations.init_rbac
```

### Option 2: Run individual scripts
```bash
# Step 1: Seed permissions
python -m migrations.seed_permissions

# Step 2: Create default roles
python -m migrations.seed_default_roles
```

Expected output:
```
╔══════════════════════════════════════════════════════════╗
║           RBAC SYSTEM INITIALIZATION                     ║
╚══════════════════════════════════════════════════════════╝

📊 Checking current database state...
  → Existing permissions: 0
  → Existing roles: 0

🔑 Step 1: Seeding permissions...
INFO: Created permission: can_manage_users
INFO: Created permission: can_manage_rbac
...
✓ Permissions seeded successfully

👥 Step 2: Creating default roles...
INFO: Created role: admin
  → Assigned ALL permissions (25) to admin
INFO: Created role: SUPER_USER
  → Assigned 15 permissions to SUPER_USER
...
✓ Default roles created successfully

📈 Final database state:
  → Total permissions: 25
  → Total roles: 8

╔══════════════════════════════════════════════════════════╗
║         RBAC INITIALIZATION COMPLETE!                    ║
╚══════════════════════════════════════════════════════════╝
```

### 2. Create Test Roles

**Via RolesPage UI or API:**

```python
# Example: Create "Data Analyst" role
POST /api/roles/
{
  "name": "Data Analyst",
  "description": "Can view analytics and export reports"
}

# Assign permissions to role
POST /api/roles/{role_id}/permissions/{permission_id}
# Assign: can_view_dashboard, can_view_analytics, can_export_analytics
```

### 3. Assign Role to User

```python
# Via UsersPage or API
POST /api/user-roles/
{
  "user_id": 123,
  "role_id": 456
}
```

### 4. Test Permission Enforcement

**Backend test:**
```bash
# Try accessing protected endpoint without permission
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/users/
# Expected: 403 if user lacks can_manage_users

# Grant permission via role, retry
# Expected: 200 OK with user list
```

**Frontend test:**
1. Login as user without `can_manage_users`
2. Navigate to `/users` → Should redirect to `/dashboard`
3. Create/Edit/Delete buttons should be hidden
4. Grant permission via admin
5. Refresh → buttons appear, page accessible

### 5. Test DOT Scoping

```python
# Assign user to DOT "ALGER"
POST /api/parks/dots/1/assign-user/123

# User queries analytics
GET /api/encaissement-analytics/overview
# Expected: Only data for DOT ALGER returned

# Admin queries same endpoint
# Expected: All DOT data returned
```

---

## Migration Checklist

- [x] Define all permission codenames
- [x] Create permission seeding script
- [x] Update PermissionService with admin override
- [x] Add permission checks to all protected endpoints
- [x] Ensure DOT CRUD is admin-only
- [x] Create frontend PermissionRoute and PermissionGate components
- [x] Protect frontend routes with permission guards
- [x] Gate UI buttons with PermissionGate
- [x] Test admin can create roles and assign permissions
- [x] Test admin can assign users to DOTs
- [x] Test permission + DOT scoping works together

---

## Summary

**Permissions control WHAT actions a user can perform:**
- Can they view analytics? → `can_view_analytics`
- Can they manage users? → `can_manage_users`
- Can they run ETL? → `can_run_etl`

**DOT assignments control WHICH data a user can access:**
- DOT_USER assigned to "ALGER" → sees only ALGER data
- Admin/SUPER_USER → sees all DOT data

**Admin has full control:**
- Bypass all permission checks
- Create/edit/delete roles
- Assign permissions to roles
- Create/manage DOT regions
- Assign users to DOTs
- View all data across all DOTs

**Result:** A complete, production-ready PBAC + DOT scoping system with admin control panel.
