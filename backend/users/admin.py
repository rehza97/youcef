from django.contrib import admin
from .models import Role, UserRole, Permission, Setting

admin.site.register(Role)
admin.site.register(UserRole)
admin.site.register(Permission)
admin.site.register(Setting)
