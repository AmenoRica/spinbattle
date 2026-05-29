from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("username", "email", "is_staff", "is_active")
    fieldsets = UserAdmin.fieldsets + (
        (None, {"fields": ("bio",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {"fields": ("bio",)}),
    )


admin.site.register(CustomUser, CustomUserAdmin)
