from datetime import timedelta

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase
from django.utils import timezone

from apps.accounts.defaults import MODULES, ROLES
from apps.accounts.models import Department, Organization, Role, RolePermission, User
from apps.accounts.provisioning import create_organization
from apps.core import tenancy
from apps.core.models import AuditLog
from apps.core.permissions import user_can

PW = "Correct-Horse-2026"


def org_with_users(slug, status="Active"):
    org, admin, _ = create_organization(name_en=f"{slug} Co", name_ar=f"شركة {slug}",
                                        admin_email=f"admin@{slug}.test", admin_password=PW, status=status)
    admin.must_change_password = False
    admin.save(update_fields=["must_change_password"])
    users = {"org_admin": admin}
    with tenancy.tenant_context(org.pk):
        for code, *_ in ROLES[1:]:
            users[code] = User.objects.create_user(email=f"{code}@{slug}.test", password=PW, organization=org,
                                                   role=Role.objects.get(code=code))
    return org, users


class ProvisioningAndRoleTests(TestCase):
    def test_new_client_gets_seven_roles_and_full_permission_rows(self):
        org, users = org_with_users("alpha")
        with tenancy.tenant_context(org.pk):
            self.assertEqual(Role.objects.count(), 7)
            self.assertEqual(RolePermission.objects.count(), 7 * len(MODULES))

    def test_first_admin_must_change_password(self):
        org, admin, _ = create_organization(name_en="Zed", admin_email="a@zed.test", admin_password=PW)
        self.assertTrue(admin.must_change_password)
        self.assertTrue(admin.is_org_admin)

    def test_roles_of_two_clients_are_separate(self):
        a, _ = org_with_users("alpha")
        b, _ = org_with_users("beta")
        with tenancy.tenant_context(a.pk):
            ids_a = set(Role.objects.values_list("id", flat=True))
        with tenancy.tenant_context(b.pk):
            ids_b = set(Role.objects.values_list("id", flat=True))
        self.assertFalse(ids_a & ids_b)

    def test_client_user_must_belong_to_a_company(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(email="orphan@x.test", password=PW)

    def test_seat_type_follows_role(self):
        _, users = org_with_users("alpha")
        self.assertEqual(users["viewer"].seat_type, "Viewer")
        self.assertEqual(users["officer"].seat_type, "Full")


class PermissionMatrixTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org, cls.u = org_with_users("alpha")

    def test_matrix_spot_checks(self):
        u = self.u
        self.assertTrue(user_can(u["officer"], "contract", "create"))
        self.assertFalse(user_can(u["officer"], "contract", "delete"))
        self.assertFalse(user_can(u["officer"], "contract", "approve"))
        self.assertTrue(user_can(u["manager"], "contract", "approve"))
        self.assertFalse(user_can(u["manager"], "contract", "delete"))
        self.assertTrue(user_can(u["finance"], "guarantee", "create"))
        self.assertFalse(user_can(u["finance"], "contract", "create"))
        self.assertTrue(user_can(u["legal"], "contract", "edit"))
        self.assertFalse(user_can(u["viewer"], "contract", "create"))
        self.assertTrue(user_can(u["viewer"], "contract", "view"))
        self.assertFalse(user_can(u["viewer"], "audit", "view"))
        self.assertTrue(user_can(u["auditor"], "audit", "view"))
        self.assertTrue(user_can(u["auditor"], "audit", "export"))
        self.assertFalse(user_can(u["auditor"], "contract", "edit"))
        self.assertTrue(user_can(u["org_admin"], "configuration", "delete"))

    def test_platform_admin_has_no_client_module_access(self):
        p = User.objects.create_superuser(email="root@ivs.test", password=PW)
        for m in MODULES:
            self.assertFalse(user_can(p, m, "view"), m)

    def test_inactive_user_has_no_access(self):
        v = self.u["officer"]
        v.is_active = False
        v.save()
        self.assertFalse(user_can(v, "contract", "view"))


class PasswordTests(TestCase):
    def test_minimum_length_and_common_passwords(self):
        for bad in ["short1!", "password123", "1234567890"]:
            with self.assertRaises(ValidationError, msg=bad):
                validate_password(bad)
        validate_password("Tr4ffic-Light-Blue")


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org, cls.u = org_with_users("alpha")

    def test_login_success_and_audit(self):
        c = Client()
        self.assertTrue(c.login(username="admin@alpha.test", password=PW))
        self.assertEqual(AuditLog.objects.filter(action="Login", user_email="admin@alpha.test").count(), 1)

    def test_wrong_password_is_audited(self):
        c = Client()
        self.assertFalse(c.login(username="admin@alpha.test", password="nope"))
        self.assertEqual(AuditLog.objects.filter(action="Login Failed").count(), 1)

    def test_lockout_after_five_failures_even_with_correct_password(self):
        c = Client()
        for _ in range(5):
            c.login(username="viewer@alpha.test", password="wrong")
        self.assertFalse(c.login(username="viewer@alpha.test", password=PW))
        user = User.objects.get(email="viewer@alpha.test")
        self.assertTrue(user.is_locked)

    def test_lock_expires(self):
        c = Client()
        for _ in range(5):
            c.login(username="viewer@alpha.test", password="wrong")
        User.objects.filter(email="viewer@alpha.test").update(locked_until=timezone.now() - timedelta(minutes=1))
        self.assertTrue(c.login(username="viewer@alpha.test", password=PW))

    def test_login_email_is_case_insensitive(self):
        self.assertTrue(Client().login(username="ADMIN@Alpha.Test", password=PW))

    def test_session_context_is_cleared_between_requests(self):
        c = Client()
        c.login(username="admin@alpha.test", password=PW)
        c.get("/")
        self.assertIsNone(tenancy.get_org_id())
        self.assertIsNone(tenancy.get_user_id())


class ViewAccessTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.a, cls.ua = org_with_users("alpha")
        cls.b, cls.ub = org_with_users("beta")
        with tenancy.tenant_context(cls.b.pk):
            Department.objects.create(name_en="Secret Beta Department")

    def client_for(self, email):
        c = Client()
        self.assertTrue(c.login(username=email, password=PW))
        return c

    def test_login_required(self):
        r = Client().get("/audit/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/login/", r["Location"])

    def test_dashboard(self):
        r = self.client_for("viewer@alpha.test").get("/")
        self.assertContains(r, "alpha Co")

    def test_audit_screen_permissions(self):
        self.assertEqual(self.client_for("viewer@alpha.test").get("/audit/").status_code, 403)
        self.assertEqual(self.client_for("officer@alpha.test").get("/audit/").status_code, 403)
        self.assertEqual(self.client_for("auditor@alpha.test").get("/audit/").status_code, 200)
        self.assertEqual(self.client_for("admin@alpha.test").get("/audit/").status_code, 200)

    def test_audit_screen_never_shows_another_clients_entries(self):
        c = self.client_for("admin@alpha.test")
        r = c.get("/audit/", {"q": "Secret Beta"})
        self.assertNotContains(r, "Secret Beta Department")
        r = c.get("/audit/")
        self.assertNotContains(r, "beta Co")
        self.assertNotContains(r, "admin@beta.test")

    def test_platform_admin_sees_clients_but_not_client_data(self):
        User.objects.create_superuser(email="root@ivs.test", password=PW)
        c = self.client_for("root@ivs.test")
        r = c.get("/")
        self.assertContains(r, "alpha Co")
        self.assertContains(r, "beta Co")
        self.assertEqual(c.get("/audit/").status_code, 403)

    def test_django_admin_is_for_platform_staff_only(self):
        self.assertEqual(self.client_for("admin@alpha.test").get("/platform-admin/").status_code, 302)

    def test_client_models_are_not_in_django_admin(self):
        from django.contrib import admin
        registered = {m.__name__ for m in admin.site._registry}
        for name in ("Department", "Role", "RolePermission", "AuditLog"):
            self.assertNotIn(name, registered)


class SubscriptionStateTests(TestCase):
    def test_suspended_company_is_blocked(self):
        org, u = org_with_users("alpha", status="Suspended")
        c = Client()
        c.login(username="admin@alpha.test", password=PW)
        self.assertEqual(c.get("/").status_code, 403)

    def test_grace_company_is_read_only(self):
        org, u = org_with_users("alpha", status="Grace")
        c = Client()
        c.login(username="admin@alpha.test", password=PW)
        self.assertEqual(c.get("/").status_code, 200)
        self.assertEqual(c.post("/audit/").status_code, 403)

    def test_blocked_company_can_still_sign_out(self):
        org, u = org_with_users("alpha", status="Closed")
        c = Client()
        c.login(username="admin@alpha.test", password=PW)
        self.assertEqual(c.post("/accounts/logout/").status_code, 302)


class MustChangePasswordTests(TestCase):
    def test_redirect_then_change(self):
        org, admin, _ = create_organization(name_en="Zed", admin_email="a@zed.test", admin_password=PW,
                                            status="Active")
        c = Client()
        c.login(username="a@zed.test", password=PW)
        r = c.get("/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/accounts/password/", r["Location"])
        r = c.post("/accounts/password/", {"old_password": PW, "new_password1": "Brand-New-Pass-77",
                                           "new_password2": "Brand-New-Pass-77"})
        self.assertEqual(r.status_code, 302)
        admin.refresh_from_db()
        self.assertFalse(admin.must_change_password)
        self.assertEqual(c.get("/").status_code, 200)
        self.assertTrue(AuditLog.objects.filter(action="Password Change", entity_label="a@zed.test").exists())

    def test_weak_new_password_rejected(self):
        org, admin, _ = create_organization(name_en="Zed", admin_email="a@zed.test", admin_password=PW)
        c = Client()
        c.login(username="a@zed.test", password=PW)
        r = c.post("/accounts/password/", {"old_password": PW, "new_password1": "short1",
                                           "new_password2": "short1"})
        self.assertEqual(r.status_code, 200)
        admin.refresh_from_db()
        self.assertTrue(admin.must_change_password)


class LanguageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org, cls.u = org_with_users("alpha")

    def test_english_is_left_to_right(self):
        c = Client()
        c.login(username="viewer@alpha.test", password=PW)
        r = c.get("/")
        self.assertContains(r, 'dir="ltr"')
        self.assertContains(r, "Dashboard")

    def test_switching_to_arabic_is_saved_and_right_to_left(self):
        c = Client()
        c.login(username="viewer@alpha.test", password=PW)
        c.post("/i18n/setlang/", {"language": "ar", "next": "/"})
        self.assertEqual(User.objects.get(email="viewer@alpha.test").preferred_language, "ar")
        r = c.get("/")
        self.assertContains(r, 'dir="rtl"')
        self.assertContains(r, 'lang="ar"')
        self.assertContains(r, "لوحة المعلومات")
        self.assertContains(r, "bootstrap.rtl.min.css")
        self.assertContains(r, "شركة alpha")

    def test_login_page_in_arabic_for_anonymous_cookie(self):
        c = Client()
        c.cookies["django_language"] = "ar"
        r = c.get("/accounts/login/")
        self.assertContains(r, 'dir="rtl"')
        self.assertContains(r, "تسجيل الدخول")

    def test_open_redirect_is_blocked(self):
        c = Client()
        r = c.post("/i18n/setlang/", {"language": "ar", "next": "https://evil.example/"})
        self.assertEqual(r["Location"], "/")
