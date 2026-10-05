from django.core.management.base import BaseCommand

from apps.accounts.defaults import ROLES
from apps.accounts.models import Organization, Role, User
from apps.accounts.provisioning import create_organization
from apps.core import tenancy

PASSWORD = "Demo-Pass-2026!"


class Command(BaseCommand):
    help = "Create two demo client companies with one user per role (development only)."

    def handle(self, *a, **o):
        for en, ar, slug in [("Demo Services Co.", "شركة الخدمات التجريبية", "alpha"),
                             ("Demo Real Estate Co.", "شركة العقارات التجريبية", "beta")]:
            if Organization.objects.filter(name_en=en).exists():
                continue
            org, admin, _ = create_organization(name_en=en, name_ar=ar, admin_email=f"admin@{slug}.test",
                                                admin_password=PASSWORD, status="Active")
            admin.must_change_password = False
            admin.save(update_fields=["must_change_password"])
            with tenancy.tenant_context(org.pk):
                for code, *_ in ROLES[1:]:
                    role = Role.objects.get(code=code)
                    User.objects.create_user(email=f"{code}@{slug}.test", password=PASSWORD, organization=org,
                                             role=role, first_name=role.name_en)
        self.stdout.write(self.style.SUCCESS(f"Demo data ready. Password for all demo users: {PASSWORD}"))
