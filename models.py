from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantModel

GOVERNORATES = [("Capital", "Capital"), ("Hawalli", "Hawalli"), ("Farwaniya", "Farwaniya"), ("Ahmadi", "Ahmadi"),
                ("Jahra", "Jahra"), ("Mubarak Al-Kabeer", "Mubarak Al-Kabeer"), ("Other", "Other")]


class Organization(models.Model):
    """A client company (tenant). This table IS the tenant, so it has no organization_id."""

    class Status(models.TextChoices):
        TRIAL = "Trial", _("Trial")
        ACTIVE = "Active", _("Active")
        GRACE = "Grace", _("Grace")
        EXPIRED = "Expired", _("Expired")
        SUSPENDED = "Suspended", _("Suspended")
        CLOSED = "Closed", _("Closed")

    name_en = models.CharField(max_length=200, blank=True)
    name_ar = models.CharField(max_length=200, blank=True)
    legal_form = models.CharField(max_length=50, blank=True)
    commercial_registration_no = models.CharField(max_length=50, null=True, blank=True, unique=True)
    commercial_licence_no = models.CharField(max_length=50, blank=True)
    industry_pack_code = models.CharField(max_length=40, blank=True)
    contact_name = models.CharField(max_length=150, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=30, blank=True)
    address_en = models.TextField(blank=True)
    address_ar = models.TextField(blank=True)
    governorate = models.CharField(max_length=30, choices=GOVERNORATES, blank=True)
    default_language = models.CharField(max_length=2, choices=[("en", "English"), ("ar", "العربية")], default="en")
    time_zone = models.CharField(max_length=50, default="Asia/Kuwait")
    weekend_days = models.JSONField(default=list)  # ISO weekdays; default Friday, Saturday = [5, 6]
    fiscal_year_start_month = models.PositiveSmallIntegerField(default=1)
    hijri_display_default = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.TRIAL)
    trial_ends_on = models.DateField(null=True, blank=True)
    closed_on = models.DateField(null=True, blank=True)
    deletion_scheduled_on = models.DateField(null=True, blank=True)
    internal_notes = models.TextField(blank=True)  # visible to IVS only
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name_en", "name_ar"]
        constraints = [models.CheckConstraint(condition=~models.Q(name_en="", name_ar=""), name="org_has_a_name")]

    def save(self, *args, **kwargs):
        from apps.core.audit import record

        if not self.weekend_days:
            self.weekend_days = [5, 6]
        creating = self._state.adding
        super().save(*args, **kwargs)
        record("Create" if creating else "Update", self, organization_id=self.pk)

    def __str__(self):
        return self.name_en or self.name_ar

    @property
    def display_name(self):
        return str(self)


class Department(TenantModel):
    name_en = models.CharField(max_length=150, blank=True)
    name_ar = models.CharField(max_length=150, blank=True)

    class Meta(TenantModel.Meta):
        constraints = [models.UniqueConstraint(fields=["organization", "name_en"],
                                               condition=models.Q(is_deleted=False) & ~models.Q(name_en=""),
                                               name="uniq_department_name_en_per_org")]

    def __str__(self):
        return self.name_en or self.name_ar


class Role(TenantModel):
    class SeatType(models.TextChoices):
        FULL = "Full", _("Full")
        VIEWER = "Viewer", _("Viewer")

    code = models.CharField(max_length=40)
    name_en = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    seat_type = models.CharField(max_length=10, choices=SeatType.choices, default=SeatType.FULL)
    can_view_financial_values = models.BooleanField(default=True)
    can_view_sensitive_fields = models.BooleanField(default=False)
    is_system = models.BooleanField(default=False)

    class Meta(TenantModel.Meta):
        constraints = [models.UniqueConstraint(fields=["organization", "code"],
                                               condition=models.Q(is_deleted=False),
                                               name="uniq_role_code_per_org")]

    def __str__(self):
        return self.name_en


class RolePermission(TenantModel):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    module = models.CharField(max_length=50)
    can_view = models.BooleanField(default=False)
    can_create = models.BooleanField(default=False)
    can_edit = models.BooleanField(default=False)
    can_delete = models.BooleanField(default=False)
    can_approve = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)

    class Meta(TenantModel.Meta):
        constraints = [models.UniqueConstraint(fields=["role", "module"], name="uniq_permission_per_role_module")]

    def __str__(self):
        return f"{self.role_id}:{self.module}"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _make(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.password_changed_at = timezone.now()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        return self._make(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_platform_admin", True)
        extra.setdefault("is_superuser", True)
        return self._make(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    """Everyone who can log in: client users and IVS platform staff."""

    LOCK_AFTER = 5
    LOCK_MINUTES = 15

    organization = models.ForeignKey(Organization, null=True, blank=True, on_delete=models.PROTECT,
                                     related_name="users")  # null = IVS platform staff
    email = models.EmailField(max_length=254, unique=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    full_name_ar = models.CharField(max_length=150, blank=True)
    mobile = models.CharField(max_length=30, blank=True)
    designation = models.CharField(max_length=100, blank=True)
    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    role = models.ForeignKey(Role, null=True, blank=True, on_delete=models.PROTECT, related_name="users")
    seat_type = models.CharField(max_length=10, choices=Role.SeatType.choices, blank=True)
    preferred_language = models.CharField(max_length=2, choices=[("en", "English"), ("ar", "العربية")],
                                          default="en")
    show_hijri = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_org_admin = models.BooleanField(default=False)
    is_platform_admin = models.BooleanField(default=False)
    mfa_enabled = models.BooleanField(default=False)
    failed_login_count = models.PositiveIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    password_changed_at = models.DateTimeField(null=True, blank=True)
    must_change_password = models.BooleanField(default=False)
    invited_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        ordering = ["email"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(is_platform_admin=True) | models.Q(organization__isnull=False),
                name="client_user_needs_organization"),
        ]

    def save(self, *args, **kwargs):
        self.email = (self.email or "").lower()
        if self.role_id:
            self.seat_type = self.role.seat_type
        elif self.is_org_admin:
            self.seat_type = Role.SeatType.FULL
        super().save(*args, **kwargs)

    # Django admin is for IVS platform staff only
    @property
    def is_staff(self):
        return self.is_platform_admin

    @property
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    def register_failed_login(self):
        self.failed_login_count += 1
        if self.failed_login_count >= self.LOCK_AFTER:
            self.locked_until = timezone.now() + timedelta(minutes=self.LOCK_MINUTES)
            self.failed_login_count = 0
        self.save(update_fields=["failed_login_count", "locked_until"])

    def register_success(self):
        self.failed_login_count = 0
        self.locked_until = None
        self.save(update_fields=["failed_login_count", "locked_until"])

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip() or self.email

    def display_name(self, lang=None):
        if lang == "ar" and self.full_name_ar:
            return self.full_name_ar
        return self.full_name

    def __str__(self):
        return self.email
