import uuid

from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import translation

from . import tenancy

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
ALWAYS_ALLOWED = ("/accounts/logout/", "/i18n/", "/static/", "/accounts/password/")


def _ip(request):
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    return (fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")) or None


class TenantContextMiddleware:
    """Sets the client company and user for the request, enforces subscription state,
    and clears everything afterwards. Place AFTER AuthenticationMiddleware."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        authed = bool(user and user.is_authenticated)
        meta = {"ip": _ip(request), "ua": request.META.get("HTTP_USER_AGENT", ""),
                "request_id": uuid.uuid4().hex, "user_email": user.email if authed else ""}
        org_id = user.organization_id if authed and not user.is_platform_admin else None
        tokens = tenancy.set_context(org_id, user.pk if authed else None, meta)
        try:
            if authed and org_id:
                blocked = self._check_org(request, user)
                if blocked is not None:
                    return blocked
            return self.get_response(request)
        finally:
            tenancy.reset_context(tokens)

    def _check_org(self, request, user):
        path = request.path
        if path.startswith(ALWAYS_ALLOWED):
            return None
        org = user.organization
        if org.status in ("Suspended", "Closed", "Expired"):
            return render(request, "blocked.html", {"org": org, "state": org.status}, status=403)
        if org.status == "Grace" and request.method not in SAFE_METHODS:
            return render(request, "blocked.html", {"org": org, "state": "Grace"}, status=403)
        if user.must_change_password and not path.startswith(reverse("password_change")):
            return redirect("password_change")
        return None


class UserLanguageMiddleware:
    """The signed-in user's saved language wins. Place AFTER LocaleMiddleware."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.preferred_language:
            translation.activate(user.preferred_language)
            request.LANGUAGE_CODE = user.preferred_language
        return self.get_response(request)
