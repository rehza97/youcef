# RBAC System - Quick Start Card

## 🚀 In 30 Seconds

### 1. Start Backend
```bash
cd fastapi_backend
uvicorn main:app --reload
```

**That's it!** 🎉 Auto-initialization runs and creates:
- ✅ 25 permissions
- ✅ 8 default roles
- ✅ Default admin account

**Console output:**
```
✅ RBAC system initialized successfully!
✅ Default admin account created!
   Username: admin
   Email:    admin@company.local
   Password: Admin123!ChangeMeNow!
⚠️  IMPORTANT: Change the admin password immediately after first login!
```

### 2. Login & Verify
- Frontend: http://localhost:5173/login
- Login with:
  - Username: `admin`
  - Password: `Admin123!ChangeMeNow!`
- Navigate to `/roles` → See 8 roles
- Navigate to `/permissions` → See 25 permissions
- **Change password at `/change-password`**

**Done!** 🎉

---

## 🔐 Default Admin Credentials

**Auto-created on first run:**
- **Username:** `admin`
- **Email:** `admin@company.local`
- **Password:** `Admin123!ChangeMeNow!`

**⚠️ Change immediately after first login!**

### Custom Admin Credentials (Optional)

Set via environment variables before starting backend:
```bash
export DEFAULT_ADMIN_USERNAME="youradmin"
export DEFAULT_ADMIN_EMAIL="admin@yourcompany.com"
export DEFAULT_ADMIN_PASSWORD="YourSecurePassword123!"

uvicorn main:app --reload
```

---

## 📊 Default Roles At-A-Glance

| Role | Permissions | DOT Access | Best For |
|------|------------|------------|----------|
| **admin** | 25 (ALL) | All | System admin |
| **SUPER_USER** | 15 | All | Senior management |
| **DOT_USER** | 7 | 1 region | Regional staff |
| **Data Analyst** | 7 | Standard | Analysts |
| **ETL Operator** | 7 | Standard | Data engineers |
| **File Manager** | 4 | Standard | Doc managers |
| **Moderator** | 6 | Standard | Support staff |
| **User** | 3 | Standard | Basic users |

---

## 🎯 Common Tasks

### Assign Role to User
```python
# Via Python
from models.role import UserRole
user_role = UserRole(user_id=123, role_id=2)  # role_id=2 is SUPER_USER
db.add(user_role)
db.commit()
```

Or via UI: Navigate to `/users` → Edit user → Select role

### Create Custom Role
1. Login as admin
2. Go to `/roles`
3. Click "Add Role"
4. Enter name and description
5. Select permissions (multi-select)
6. Save

### Assign User to DOT
```bash
# Only admins can do this
POST /api/parks/dots/{dot_id}/assign-user/{user_id}
```

### Check Permission
```javascript
// Frontend
const { hasPermission } = usePermission('can_manage_users');
if (hasPermission) {
  // Show button
}
```

```python
# Backend
from services.permission_service import PermissionService
PermissionService.require_permission(current_user, db, "can_manage_users")
```

---

## 🔒 25 Permission Checklist

### User & Role Management (4)
- [ ] can_manage_users
- [ ] can_view_users
- [ ] can_manage_rbac
- [ ] can_view_rbac

### Dashboard & Analytics (4)
- [ ] can_view_dashboard
- [ ] can_view_analytics
- [ ] can_export_analytics
- [ ] can_view_encaissement_data

### Files (3)
- [ ] can_upload_files
- [ ] can_manage_files
- [ ] can_manage_own_files

### ETL (2)
- [ ] can_run_etl
- [ ] can_view_etl_results

### Messaging (4)
- [ ] can_send_messages
- [ ] can_manage_messages
- [ ] can_manage_notifications
- [ ] can_broadcast

### Settings (2)
- [ ] can_manage_settings
- [ ] can_view_settings

### DOT & Data (5)
- [ ] can_view_dot_data
- [ ] can_view_all_dots
- [ ] can_manage_dots
- [ ] can_view_park_data
- [ ] can_manage_park_data

### Audit (1)
- [ ] can_view_audit_logs

---

## 🛠️ Troubleshooting

### "No permissions/roles found"
```bash
python -m migrations.init_rbac
```

### "User can't access page"
1. Check user has role assigned
2. Verify role has required permission
3. Check backend logs for 403 errors

### "DOT_USER sees no data"
```python
# Assign DOT to user
POST /api/parks/dots/1/assign-user/123
```

### "Admin can't do anything"
```python
# Verify admin role assignment
db.query(UserRole).filter(UserRole.user_id == admin_id).all()
```

---

## 📚 Full Documentation

- **Setup Guide:** `RBAC_SETUP_GUIDE.md`
- **Full Docs:** `PERMISSION_SYSTEM_IMPLEMENTATION.md`
- **Role Details:** `DEFAULT_ROLES_REFERENCE.md`
- **Summary:** `RBAC_SYSTEM_SUMMARY.md`

---

## 🎓 Cheat Sheet

### Backend Permission Check
```python
# Method 1: Decorator-style (if available)
@require_permission("can_manage_users")
def my_endpoint():
    pass

# Method 2: Manual check
PermissionService.require_permission(user, db, "can_manage_users")

# Method 3: Boolean check
if PermissionService.has_permission(user, db, "can_manage_users"):
    # do something
```

### Frontend Permission Gate
```jsx
// Hide button if no permission
<PermissionGate permission="can_manage_users">
  <Button onClick={createUser}>Create User</Button>
</PermissionGate>

// Protect entire route
<PermissionRoute permission="can_manage_users">
  <UsersPage />
</PermissionRoute>

// Hook for conditional logic
const { hasPermission, loading } = usePermission('can_manage_users');
```

### DOT Access Check
```python
# Backend
accessible_dots = DOTService.get_user_accessible_dots(db, user.id)
query = query.filter(Model.dot_id.in_(accessible_dots))

# Admin sees all DOTs
if PermissionService.is_admin(user, db):
    # No DOT filtering
```

---

## ✅ Quick Verification

Run this checklist after setup:

```bash
# Backend running?
curl http://localhost:8000/api/health

# Permissions seeded?
curl http://localhost:8000/api/permissions/ -H "Authorization: Bearer <token>"
# Should return 25 items

# Roles seeded?
curl http://localhost:8000/api/roles/ -H "Authorization: Bearer <token>"
# Should return 8 items

# Admin has all permissions?
curl http://localhost:8000/api/roles/1/permissions -H "Authorization: Bearer <token>"
# Should return 25 items

# Can login?
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'
# Should return access token
```

All passing? **You're good to go!** 🚀

---

**Need Help?** See full docs or check backend logs at `fastapi_backend/debug.log`
