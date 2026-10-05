from . import tenancy


def record(action, obj=None, changes=None, reason="", organization_id=None, user=None, entity_type=None,
           entity_id=None, entity_label=None):
    """Write one audit entry. Safe to call from anywhere."""
    from .models import AuditLog

    meta = tenancy.get_request_meta()
    org_id = organization_id or tenancy.get_org_id()
    uid = user.pk if user is not None else tenancy.get_user_id()
    email = getattr(user, "email", "") if user is not None else meta.get("user_email", "")
    if obj is not None:
        entity_type = entity_type or obj.__class__.__name__.lower()
        entity_id = entity_id or obj.pk
        if entity_label is None:
            entity_label = obj.audit_label() if hasattr(obj, "audit_label") else str(obj)[:250]
        org_id = org_id or getattr(obj, "organization_id", None)
    return AuditLog.objects.create(
        organization_id=org_id, user_id=uid, user_email=email or "", action=action,
        entity_type=entity_type or "", entity_id=entity_id, entity_label=entity_label or "",
        changes=changes, reason=reason, ip_address=meta.get("ip"), user_agent=meta.get("ua", "")[:300],
        request_id=meta.get("request_id", ""))
