# Default Roles Quick Reference

This document provides a quick overview of the 8 default roles automatically created in the system.

---

## Role Hierarchy

```
┌─────────────────────────────────────────────────┐
│  admin                                          │
│  └─ ALL PERMISSIONS (25 total)                 │
│     Full system access                          │
└─────────────────────────────────────────────────┘
          ▲
          │ Highest privileges
          │
┌─────────────────────────────────────────────────┐
│  SUPER_USER                                     │
│  └─ 15 permissions                              │
│     Cross-DOT access, most management features  │
└─────────────────────────────────────────────────┘
          ▲
          │
┌─────────────────────────────────────────────────┐
│  DOT_USER                                       │
│  └─ 7 permissions                               │
│     DOT-scoped regional access                  │
└─────────────────────────────────────────────────┘
          ▲
          │ Standard roles (parallel hierarchy)
          ├──────────────┬──────────────┬──────────────┐
┌─────────▼─────┐ ┌──────▼──────┐ ┌────▼────┐ ┌──────▼──────┐
│ Data Analyst  │ │ ETL Operator│ │File Mgr │ │  Moderator  │
│ 7 permissions │ │ 7 permissions│ │4 perms  │ │ 6 perms     │
└───────────────┘ └─────────────┘ └─────────┘ └─────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │      User       │
                   │  3 permissions  │
                   │  Basic access   │
                   └─────────────────┘
```

---

## Role Details

### 🔴 admin
**Full system administrator**

**Permissions:** ALL (25)
- Automatically receives ALL permissions in the system
- Bypasses all permission checks
- Can manage roles, permissions, and DOT assignments
- Sees all data across all DOT regions

**Typical Users:**
- System administrators
- IT managers
- Platform owners

**Access Level:** Unrestricted

---

### 🟠 SUPER_USER
**Cross-regional super user**

**Permissions:** 15
- `can_view_dashboard`
- `can_view_analytics`
- `can_export_analytics`
- `can_view_encaissement_data`
- `can_view_all_dots` ⭐
- `can_view_park_data`
- `can_manage_park_data`
- `can_run_etl`
- `can_view_etl_results`
- `can_upload_files`
- `can_manage_own_files`
- `can_send_messages`
- `can_view_settings`
- `can_view_audit_logs`

**Typical Users:**
- Senior managers
- Regional directors
- Data architects

**Access Level:** All DOT regions (no DOT restriction)

---

### 🟡 DOT_USER
**Regional user (DOT-scoped)**

**Permissions:** 7
- `can_view_dashboard`
- `can_view_analytics`
- `can_view_encaissement_data`
- `can_view_dot_data` ⭐
- `can_view_park_data`
- `can_manage_own_files`
- `can_send_messages`

**Typical Users:**
- Regional staff
- Local operators
- Branch managers

**Access Level:** Restricted to assigned DOT region

**Note:** Must be assigned a DOT via admin. Only sees data for their DOT.

---

### 🔵 Data Analyst
**Analytics and reporting specialist**

**Permissions:** 7
- `can_view_dashboard`
- `can_view_analytics`
- `can_export_analytics`
- `can_view_encaissement_data`
- `can_view_park_data`
- `can_view_etl_results`
- `can_view_settings`

**Typical Users:**
- Business analysts
- Data scientists
- Reporting specialists

**Access Level:** Read-only analytics access

---

### 🟢 ETL Operator
**Data processing specialist**

**Permissions:** 7
- `can_view_dashboard`
- `can_run_etl` ⭐
- `can_view_etl_results`
- `can_upload_files`
- `can_manage_own_files`
- `can_view_park_data`
- `can_manage_park_data`

**Typical Users:**
- Data engineers
- ETL developers
- Data pipeline operators

**Access Level:** ETL execution and file management

---

### 🟣 File Manager
**File and document administrator**

**Permissions:** 4
- `can_view_dashboard`
- `can_upload_files`
- `can_manage_files` ⭐ (admin-level file access)
- `can_manage_own_files`

**Typical Users:**
- Document administrators
- Content managers
- File system coordinators

**Access Level:** Full file management (can view/delete all users' files)

---

### 🟤 Moderator
**Community and messaging manager**

**Permissions:** 6
- `can_view_dashboard`
- `can_send_messages`
- `can_manage_messages` ⭐
- `can_manage_notifications`
- `can_broadcast` ⭐
- `can_view_users`

**Typical Users:**
- Community managers
- Support staff
- Communications coordinators

**Access Level:** Messaging and notification management

---

### ⚪ User
**Standard end user**

**Permissions:** 3
- `can_view_dashboard`
- `can_send_messages`
- `can_manage_own_files`

**Typical Users:**
- Standard end users
- Basic staff
- Limited access personnel

**Access Level:** Minimal - basic application access

---

## Role Assignment Guide

### Who assigns roles?
- **admin** can assign any role to any user
- Users with `can_manage_users` can assign roles

### How to assign?
1. Login as admin
2. Navigate to `/users`
3. Create or edit user
4. Select role from dropdown
5. Save

### Multiple roles?
Yes! Users can have multiple roles. Their effective permissions are the **union** of all assigned roles.

### Default role for new users?
New users have **no role** by default. Assign "User" role for basic access.

---

## DOT Assignment (for DOT_USER)

DOT_USER role requires DOT assignment to function properly:

```python
# Via API
POST /api/parks/dots/{dot_id}/assign-user/{user_id}

# Example: Assign user 123 to DOT "ALGER" (dot_id=1)
POST /api/parks/dots/1/assign-user/123
```

**Admin can:**
- Create DOT regions
- Assign users to DOTs
- Remove DOT assignments
- View DOT statistics

**DOT_USER sees:**
- Only data for their assigned DOT
- Analytics filtered to their region
- Park data scoped to their DOT

---

## Permission Reference

Quick lookup of what each permission allows:

| Permission | Description |
|-----------|-------------|
| `can_manage_users` | Create, update, delete users |
| `can_view_users` | View user lists (read-only) |
| `can_manage_rbac` | Manage roles and permissions |
| `can_view_rbac` | View roles/permissions (read-only) |
| `can_view_dashboard` | Access main dashboard |
| `can_view_analytics` | View analytics pages |
| `can_export_analytics` | Export analytics reports |
| `can_view_encaissement_data` | View encaissement analytics (DOT-scoped) |
| `can_upload_files` | Upload files |
| `can_manage_files` | Admin file management (all files) |
| `can_manage_own_files` | Manage user's own files |
| `can_run_etl` | Execute ETL processes |
| `can_view_etl_results` | View/download ETL results |
| `can_send_messages` | Send messages |
| `can_manage_messages` | Moderate all messages (admin) |
| `can_manage_notifications` | Configure notifications |
| `can_broadcast` | Send broadcast messages |
| `can_manage_settings` | Modify system settings |
| `can_view_settings` | View settings (read-only) |
| `can_view_dot_data` | View DOT-scoped data |
| `can_view_all_dots` | Access all DOT regions |
| `can_manage_dots` | CRUD DOT regions |
| `can_view_park_data` | View park data (DOT-scoped) |
| `can_manage_park_data` | Import/process park data |
| `can_view_audit_logs` | View system audit logs |

---

## Common Use Cases

### Setup 1: Small Team
- **1 admin:** You
- **2-3 Users:** Basic staff
- DOT not used

### Setup 2: Multi-Regional Organization
- **1 admin:** IT manager
- **5 DOT_USERs:** Regional managers (each assigned to their DOT)
- **2 Data Analysts:** Corporate analytics team
- **3 Users:** Support staff

### Setup 3: Complex Enterprise
- **2 admins:** IT team
- **1 SUPER_USER:** CEO/CTO
- **10 DOT_USERs:** Regional directors
- **5 ETL Operators:** Data engineering team
- **3 Data Analysts:** BI team
- **2 Moderators:** Support/community team
- **50 Users:** General staff

---

## Customization

### Create Custom Role
1. Login as admin
2. Navigate to `/roles`
3. Click "Add Role"
4. Enter name and description
5. Click "Edit" on the new role
6. Select desired permissions
7. Save

### Modify Default Role
Default roles can be edited! Their permissions are not locked.

1. Navigate to `/roles`
2. Click "Edit" on any default role
3. Add/remove permissions
4. Save

**Tip:** Don't modify "admin" role - it auto-receives all permissions.

---

## Security Best Practices

1. **Principle of Least Privilege:** Assign minimal permissions needed
2. **Regular Audits:** Review role assignments quarterly
3. **Admin Accounts:** Limit to 1-2 trusted administrators
4. **DOT Boundaries:** Ensure DOT_USERs are properly scoped
5. **Test Roles:** Create test users to verify permission enforcement
6. **Document Changes:** Keep log of custom role modifications

---

## Troubleshooting

### User can't access page
- ✅ Check user has required role assigned
- ✅ Verify role has necessary permission
- ✅ Confirm backend permission check matches frontend route

### DOT_USER sees no data
- ✅ Ensure user is assigned to a DOT
- ✅ Verify DOT has data
- ✅ Check DOT ID matches data records

### Permission not working
- ✅ Restart backend after permission changes
- ✅ Clear browser cache / hard refresh
- ✅ Check backend logs for permission denials

### Can't modify role
- ✅ Ensure you have `can_manage_rbac` permission
- ✅ Login as admin for full access

---

**Last Updated:** [Auto-generated on RBAC initialization]

**Need Help?** Check the full implementation guide in `PERMISSION_SYSTEM_IMPLEMENTATION.md`
