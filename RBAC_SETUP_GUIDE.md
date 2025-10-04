# RBAC System Setup Guide

Quick start guide to get your permission system up and running.

---

## 🚀 Quick Start (Automatic)

**The system auto-initializes on first run!** Just start your backend:

```bash
# Start FastAPI backend
cd fastapi_backend
uvicorn main:app --reload
```

**Expected console output on FIRST RUN:**
```
INFO: Starting FastAPI application...
INFO: Database tables created successfully
🔧 RBAC system not initialized. Running auto-initialization...
📝 Seeding permissions...
INFO: Created permission: can_manage_users
INFO: Created permission: can_manage_rbac
...
👥 Creating default roles...
INFO: Created role: admin
INFO: Created role: SUPER_USER
...
✅ RBAC system initialized successfully!
======================================================================
✅ Default admin account created!
======================================================================
   Username: admin
   Email:    admin@company.local
   Password: Admin123!ChangeMeNow!
======================================================================
⚠️  IMPORTANT: Change the admin password immediately after first login!
======================================================================
```

**On subsequent runs:**
```
INFO: Starting FastAPI application...
INFO: Database tables created successfully
✓ RBAC system already initialized (25 permissions, 8 roles)
✓ Admin account already exists: admin
INFO: Application startup complete
```

**That's it!** Your system now has:
- ✅ 25 permissions
- ✅ 8 default roles with assigned permissions
- ✅ Default admin account ready to use
- ✅ No manual setup required!

---

## 📋 Initial Setup Steps

### Step 1: Start Backend (Everything Auto-initializes!)
```bash
cd fastapi_backend
uvicorn main:app --reload
```

### Step 2: Login with Default Admin
**Default admin credentials (auto-created):**
- Username: `admin`
- Email: `admin@company.local`
- Password: `Admin123!ChangeMeNow!`

### Step 3: Change Admin Password (IMPORTANT!)
1. Login with default credentials
2. Navigate to `/change-password`
3. Set a secure new password

**⚠️ Security Note:** The default password is intentionally obvious to remind you to change it!

### Step 4: (Optional) Custom Admin Credentials

If you want custom admin credentials on first run, set environment variables **before** starting:

```bash
# Linux/Mac
export DEFAULT_ADMIN_USERNAME="youradmin"
export DEFAULT_ADMIN_EMAIL="admin@yourcompany.com"
export DEFAULT_ADMIN_PASSWORD="YourSecurePassword123!"

# Windows
set DEFAULT_ADMIN_USERNAME=youradmin
set DEFAULT_ADMIN_EMAIL=admin@yourcompany.com
set DEFAULT_ADMIN_PASSWORD=YourSecurePassword123!

# Then start backend
uvicorn main:app --reload
```

### Step 5: Verify Installation
1. Start frontend: `cd frontend && npm run dev`
2. Navigate to http://localhost:5173/login
3. Login with admin credentials
4. Navigate to `/roles` - you should see 8 default roles
5. Navigate to `/permissions` - you should see 25 permissions

---

## 🔄 Manual Initialization (Optional)

If auto-init fails or you need to re-initialize:

### Option 1: Master Init Script
```bash
cd fastapi_backend
python -m migrations.init_rbac
```

### Option 2: Individual Scripts
```bash
# Step 1: Seed permissions
python -m migrations.seed_permissions

# Step 2: Create default roles
python -m migrations.seed_default_roles
```

### Option 3: Re-run Specific Parts
```bash
# Only seed permissions (safe to run multiple times)
python -m migrations.seed_permissions

# Only create roles (safe to run multiple times)
python -m migrations.seed_default_roles
```

All scripts are **idempotent** - safe to run multiple times without duplicates.

---

## ✅ Verification Checklist

After setup, verify everything works:

### Backend Verification
```bash
# Check permissions count
curl http://localhost:8000/api/permissions/ -H "Authorization: Bearer <token>"
# Should return 25 permissions

# Check roles count
curl http://localhost:8000/api/roles/ -H "Authorization: Bearer <token>"
# Should return 8 roles

# Check admin has all permissions
curl http://localhost:8000/api/roles/1/permissions -H "Authorization: Bearer <token>"
# Should return 25 permissions assigned to admin role
```

### Frontend Verification
1. ✅ Login as admin
2. ✅ Can access `/users` page
3. ✅ Can access `/roles` page
4. ✅ Can access `/permissions` page
5. ✅ Can see "Add User" button on Users page
6. ✅ Can see "Add Role" button on Roles page
7. ✅ Can edit role and see all 25 permissions in checkboxes

### Permission Enforcement Verification
1. Create a test user with "User" role (3 permissions)
2. Login as test user
3. Try to access `/users` → Should redirect to `/dashboard`
4. Try to access `/roles` → Should redirect to `/dashboard`
5. Verify no "Add User" buttons visible on any page
6. Test user can only access `/dashboard`, `/profile`, `/messages`, `/files`

---

## 🎯 Next Steps

### 1. Configure DOT Regions (if using regional access)
```bash
# Create DOT regions
POST http://localhost:8000/api/parks/dots/
{
  "name": "ALGER",
  "description": "Algiers region"
}

# Assign user to DOT
POST http://localhost:8000/api/parks/dots/1/assign-user/123
```

### 2. Create Additional Users
Navigate to `/users` as admin and click "Add User"

### 3. Customize Roles
- Edit default roles via `/roles` page
- Create custom roles for your organization
- Assign permissions based on job functions

### 4. Test Permission Scoping
- Create test users with different roles
- Login as each and verify page access
- Test button visibility with different permissions

---

## 🔧 Troubleshooting

### Auto-initialization didn't run
**Symptom:** No permissions or roles in database

**Solution:**
```bash
# Manually run init
cd fastapi_backend
python -m migrations.init_rbac
```

### "admin" role has no permissions
**Symptom:** Admin role shows 0 permissions

**Cause:** Role-permission mapping didn't complete

**Solution:**
```bash
# Re-run role seeding
python -m migrations.seed_default_roles
```

### User has role but no permissions work
**Symptom:** 403 errors despite having role

**Cause:** Role-permission mapping missing

**Solution:**
```bash
# Re-seed roles to fix mappings
python -m migrations.seed_default_roles
```

### Permission check API returns false for admin
**Symptom:** Admin can't access protected pages

**Cause:** UserRole mapping missing

**Solution:**
```python
# Via Python shell
>>> from database.connection import SessionLocal
>>> from models.role import UserRole, Role
>>> from models.user import User
>>>
>>> db = SessionLocal()
>>> admin_user = db.query(User).filter(User.username == "admin").first()
>>> admin_role = db.query(Role).filter(Role.name == "admin").first()
>>>
>>> # Check if mapping exists
>>> existing = db.query(UserRole).filter(
...     UserRole.user_id == admin_user.id,
...     UserRole.role_id == admin_role.id
... ).first()
>>>
>>> if not existing:
...     user_role = UserRole(user_id=admin_user.id, role_id=admin_role.id)
...     db.add(user_role)
...     db.commit()
...     print("Admin role assigned!")
```

### Backend crashes on startup
**Symptom:** FastAPI fails to start with RBAC error

**Cause:** Database tables not created or migration failed

**Solution:**
```bash
# 1. Check database exists
# 2. Restart backend (tables auto-create)
# 3. If still failing, run migrations manually:
python -m migrations.init_rbac
```

---

## 📚 Additional Resources

- **Full Implementation Guide:** `PERMISSION_SYSTEM_IMPLEMENTATION.md`
- **Default Roles Reference:** `DEFAULT_ROLES_REFERENCE.md`
- **Permission List:** See `fastapi_backend/migrations/seed_permissions.py`

---

## 🆘 Need Help?

1. Check backend logs: `debug.log` in `fastapi_backend/`
2. Check browser console for frontend errors
3. Verify database has `permissions`, `roles`, `role_permissions`, `user_roles` tables
4. Test permission check API: `GET /api/users/check-permission/{permission_codename}`

---

## 🔒 Security Notes

⚠️ **Important:**
- Change default admin password immediately after setup
- Limit admin role to 1-2 trusted users
- Use `DOT_USER` role for regional restrictions
- Regularly audit role assignments
- Test permission enforcement before production deployment

---

**Setup Complete!** Your RBAC system is ready to use. 🎉
