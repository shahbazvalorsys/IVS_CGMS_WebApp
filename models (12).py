from django.conf import settings
from django.db import models
from django.utils import timezone

from . import tenancy


class TenantQuerySet(models.QuerySet):
    def delete(self):  # no bulk hard delete of business data
        raise RuntimeError("Hard delete is not allowed. Use soft_delete().")


class TenantManager(models.Manager):
    """Default manager: only the current client's rows, excluding soft-deleted."""

    def get_queryset(self):
        org_id = tenancy.get_org_id()
        qs = TenantQuerySet(self.model, using=self._db)
        if org_id is None:
            return qs.none()  # fail closed
        return qs.filter(organization_id=org_id, is_deleted=False)


class TenantDeletedManager(models.Manager):
    """Soft-deleted rows of the current client only (for restore screens)."""

    def get_queryset(self):
        org_id = tenancy.get_org_id()
        qs = TenantQuerySet(self.model, using=self._db)
        if org_id is None:
            return qs.none()
        return qs.filter(organization_id=org_id, is_deleted=True)


class TenantModel(models.Model):
    """Base class of every client-owned table (see Data Schema, standard columns)."""

    organization = models.ForeignKey("accounts.Organization", on_delete=models.PROTECT, editable=False,
                                     related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
                                   on_delete=models.SET_NULL, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
                                   on_delete=models.SET_NULL, related_name="+")
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True, editable=False)
    deleted_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, editable=False,
                                   on_delete=models.SET_NULL, related_name="+")
    row_version = models.PositiveIntegerField(default=1, editable=False)

    objects = TenantManager()
    deleted_objects = TenantDeletedManager()
    unscoped = models.Manager()  # system use only: platform tasks, migrations, tests

    audit_mask = ()  # field names whose values must not appear in the audit log

    class Meta:
        abstract = True
        base_manager_name = "unscoped"

    # ---- audit snapshot -------------------------------------------------
    @classmethod
    def from_db(cls, db, field_names, values):
        obj = super().from_db(db, field_names, values)
        obj._audit_snapshot = obj._current_values()
        return obj

    def _current_values(self):
        skip = {"updated_at", "updated_by", "row_version"}
        return {f.attname: getattr(self, f.attname) for f in self._meta.concrete_fields if f.name not in skip}

    def _changes(self):
        before = getattr(self, "_audit_snapshot", None) or {}
        after = self._current_values()
        out = {}
        for k, new in after.items():
            old = before.get(k)
            if old != new:
                out[k] = ["***" if k in self.audit_mask else _jsonable(old),
                          "***" if k in self.audit_mask else _jsonable(new)]
        return out

    # ---- saving ----------------------------------------------------------
    def save(self, *args, **kwargs):
        from .audit import record  # local import avoids a circular import

        ctx_org = tenancy.get_org_id()
        creating = self._state.adding
        if self.organization_id is None:
            if ctx_org is None:
                raise RuntimeError("No client (organization) context; cannot save %s." % self.__class__.__name__)
            self.organization_id = ctx_org
        elif ctx_org is not None and self.organization_id != ctx_org:
            raise PermissionError("Cross-client write blocked.")
        uid = tenancy.get_user_id()
        if creating:
            self.created_by_id = self.created_by_id or uid
        self.updated_by_id = uid
        changes = {} if creating else self._changes()
        if not creating:
            self.row_version = (self.row_version or 1) + 1
        super().save(*args, **kwargs)
        if creating:
            record("Create", self, changes=None)
        elif changes:
            record("Update", self, changes=changes)
        self._audit_snapshot = self._current_values()

    def soft_delete(self):
        from .audit import record

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by_id = tenancy.get_user_id()
        super().save()
        record("Delete", self, changes=None)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Hard delete is not allowed. Use soft_delete().")

    def audit_label(self):
        return str(self)[:250]


def _jsonable(v):
    if v is None or isinstance(v, (int, float, bool, str)):
        return v
    return str(v)


class AuditLog(models.Model):
    """Append-only history of important actions (Data Schema, audit_log)."""

    ACTIONS = [(a, a) for a in (
        "Create", "Update", "Delete", "Restore", "Status Change", "Approve", "Reject", "Login", "Logout",
        "Login Failed", "Password Change", "Export", "Download", "Config Change", "Permission Change",
        "Support Access", "Import")]

    organization = models.ForeignKey("accounts.Organization", null=True, blank=True, on_delete=models.PROTECT,
                                     related_name="+")
    occurred_at = models.DateTimeField(default=timezone.now, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="+")
    user_email = models.CharField(max_length=254, blank=True)
    action = models.CharField(max_length=30, choices=ACTIONS)
    entity_type = models.CharField(max_length=60, blank=True)
    entity_id = models.BigIntegerField(null=True, blank=True)
    entity_label = models.CharField(max_length=250, blank=True)
    changes = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=300, blank=True)
    request_id = models.CharField(max_length=40, blank=True)
    reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "occurred_at"]),
            models.Index(fields=["organization", "entity_type", "entity_id"]),
        ]
        ordering = ["-occurred_at", "-id"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RuntimeError("Audit log entries cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Audit log entries cannot be deleted.")

    def __str__(self):
        return f"{self.occurred_at:%Y-%m-%d %H:%M} {self.action} {self.entity_type}#{self.entity_id}"
