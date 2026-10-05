import secrets

from django.db import transaction
from django.utils import timezone

from apps.core import tenancy

from .defaults import seed_default_roles
from .models import Organization, User


@transaction.atomic
def create_organization(name_en="", name_ar="", admin_email="", admin_password=None, status="Trial",
                        admin_first_name="", admin_last_name="", language="en", **extra):
    """Onboard a client: company + default roles + the first Org Admin user."""
    org = Organization.objects.create(name_en=name_en, name_ar=name_ar, status=status,
                                      default_language=language, **extra)
    roles = seed_default_roles(org)
    generated = admin_password is None
    password = admin_password or secrets.token_urlsafe(12)
    with tenancy.tenant_context(org.pk):
        admin = User.objects.create_user(
            email=admin_email, password=password, organization=org, role=roles["org_admin"], is_org_admin=True,
            first_name=admin_first_name, last_name=admin_last_name, preferred_language=language,
            must_change_password=True, invited_at=timezone.now())
    return org, admin, (password if generated else None)
