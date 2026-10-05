"""Django admin is for IVS platform staff only. It shows platform data (clients, users).
Client business data is never registered here."""
from django.contrib import admin

from .models import Organization, User


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("name_en", "name_ar", "status", "industry_pack_code", "created_at")
    list_filter = ("status",)
    search_fields = ("name_en", "name_ar", "commercial_registration_no")


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "organization", "is_org_admin", "is_platform_admin", "is_active")
    list_filter = ("is_platform_admin", "is_org_admin", "is_active")
    search_fields = ("email",)
    exclude = ("password", "groups", "user_permissions")
