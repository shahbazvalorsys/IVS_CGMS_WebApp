from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils import timezone, translation
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.core.audit import record
from apps.core.models import AuditLog
from apps.core.permissions import permission_required

from .models import Organization


class LoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True


class PasswordChangeView(auth_views.PasswordChangeView):
    template_name = "registration/password_change.html"
    success_url = reverse_lazy("home")

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        user.must_change_password = False
        user.password_changed_at = timezone.now()
        user.save(update_fields=["must_change_password", "password_changed_at"])
        record("Password Change", user=user, organization_id=user.organization_id, entity_type="user",
               entity_id=user.pk, entity_label=user.email)
        return response


@login_required
def home(request):
    if request.user.is_platform_admin:
        orgs = Organization.objects.order_by("name_en")
        return render(request, "platform_home.html", {"orgs": orgs})
    return render(request, "dashboard.html", {"org": request.user.organization})


@login_required
@permission_required("audit", "view")
def audit_list(request):
    qs = AuditLog.objects.filter(organization_id=request.user.organization_id)
    action = request.GET.get("action", "")
    if action:
        qs = qs.filter(action=action)
    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(entity_label__icontains=q)
    page = Paginator(qs.select_related("user"), 50).get_page(request.GET.get("page"))
    return render(request, "audit_list.html", {"page": page, "actions": [a for a, _ in AuditLog.ACTIONS],
                                               "action": action, "q": q})


@require_POST
def set_language(request):
    lang = request.POST.get("language", "en")
    if lang not in ("en", "ar"):
        lang = "en"
    nxt = request.POST.get("next", "/")
    if not url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        nxt = "/"
    response = HttpResponseRedirect(nxt)
    response.set_cookie("django_language", lang, max_age=365 * 24 * 3600, samesite="Lax")
    if request.user.is_authenticated:
        request.user.preferred_language = lang
        request.user.save(update_fields=["preferred_language"])
    translation.activate(lang)
    return response
