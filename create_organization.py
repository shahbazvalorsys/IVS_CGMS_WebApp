from django.core.management.base import BaseCommand, CommandError

from apps.accounts.provisioning import create_organization


class Command(BaseCommand):
    help = "Create a client company with default roles and its first Org Admin."

    def add_arguments(self, p):
        p.add_argument("--name-en", default="")
        p.add_argument("--name-ar", default="")
        p.add_argument("--admin-email", required=True)
        p.add_argument("--admin-password")
        p.add_argument("--status", default="Trial")
        p.add_argument("--language", default="en", choices=["en", "ar"])

    def handle(self, *a, **o):
        if not (o["name_en"] or o["name_ar"]):
            raise CommandError("Give --name-en or --name-ar")
        org, admin, generated = create_organization(
            name_en=o["name_en"], name_ar=o["name_ar"], admin_email=o["admin_email"],
            admin_password=o["admin_password"], status=o["status"], language=o["language"])
        self.stdout.write(self.style.SUCCESS(f"Created {org} (id {org.pk}); Org Admin {admin.email}"))
        if generated:
            self.stdout.write(f"Temporary password (must be changed at first login): {generated}")
