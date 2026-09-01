from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User


class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("Clinic info", {"fields": ("role", "description", "shift_start", "shift_end")}),
    )
    list_display = ["username", "email", "role", "is_staff"]


admin.site.register(User, CustomUserAdmin)
