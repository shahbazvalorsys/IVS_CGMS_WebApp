from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from apps.core.audit import record


@receiver(user_logged_in)
def _login(sender, request, user, **kw):
    record("Login", user=user, organization_id=user.organization_id, entity_type="user", entity_id=user.pk,
           entity_label=user.email)


@receiver(user_logged_out)
def _logout(sender, request, user, **kw):
    if user is not None:
        record("Logout", user=user, organization_id=user.organization_id, entity_type="user", entity_id=user.pk,
               entity_label=user.email)
