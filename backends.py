from django.contrib.auth.backends import ModelBackend

from apps.core.audit import record

from .models import User


class EmailBackend(ModelBackend):
    """Login by email with lockout (5 failures -> 15 minutes)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = (username or kwargs.get("email") or "").strip().lower()
        if not email or password is None:
            return None
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            User().set_password(password)  # constant-time-ish
            record("Login Failed", entity_type="user", entity_label=email, reason="unknown user")
            return None
        if user.is_locked:
            record("Login Failed", user=user, organization_id=user.organization_id, entity_type="user",
                   entity_id=user.pk, entity_label=email, reason="account locked")
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            user.register_success()
            return user
        user.register_failed_login()
        record("Login Failed", user=user, organization_id=user.organization_id, entity_type="user",
               entity_id=user.pk, entity_label=email, reason="bad password")
        return None
