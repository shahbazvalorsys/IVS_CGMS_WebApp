import getpass

from django.core.management.base import BaseCommand

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Create an IVS platform administrator (super user)."

    def add_arguments(self, p):
        p.add_argument("--email", required=True)
        p.add_argument("--password")

    def handle(self, *a, **o):
        password = o["password"] or getpass.getpass("Password (min 10 characters): ")
        User.objects.create_superuser(email=o["email"], password=password, must_change_password=False)
        self.stdout.write(self.style.SUCCESS("Platform admin created."))
