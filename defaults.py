"""Default roles and permission matrix (FSD Section 3.1)."""
from apps.core import tenancy

# V view, C create, E edit, D delete (soft), A approve, X export
ROLES = [
    # code, name_en, name_ar, seat, sensitive
    ("org_admin", "Org Admin", "مدير النظام", "Full", True),
    ("manager", "Manager", "مدير", "Full", False),
    ("officer", "Contracts Officer", "مسؤول العقود", "Full", False),
    ("finance", "Finance", "المالية", "Full", False),
    ("legal", "Legal", "الشؤون القانونية", "Full", True),
    ("viewer", "Viewer", "مشاهد", "Viewer", False),
    ("auditor", "Auditor", "مدقق", "Viewer", False),
]

MODULES = ["party", "contract", "amendment", "guarantee", "cheque", "payment", "obligation", "asset", "document",
           "alert_rule", "alert_centre", "report", "user", "configuration", "approval", "audit"]

# order of columns: org_admin, manager, officer, finance, legal, viewer, auditor
MATRIX = {
    "party":         ["VCEDX", "VCEX", "VCEX", "V", "VCE", "V", "VX"],
    "contract":      ["VCEDAX", "VCEAX", "VCEX", "VX", "VCEX", "V", "VX"],
    "amendment":     ["VCEDAX", "VCEAX", "VCE", "V", "VCE", "V", "V"],
    "guarantee":     ["VCEDX", "VCEX", "VCE", "VCEX", "V", "V", "VX"],
    "cheque":        ["VCEDX", "VCEX", "V", "VCEX", "V", "V", "VX"],
    "payment":       ["VCEDX", "VCEX", "VCE", "VCEX", "V", "V", "VX"],
    "obligation":    ["VCEDX", "VCEX", "VCE", "V", "VCEX", "V", "V"],
    "asset":         ["VCEDX", "VCEX", "VCE", "V", "V", "V", "V"],
    "document":      ["VCEDX", "VCEX", "VCE", "VCE", "VCEX", "V", "VX"],
    "alert_rule":    ["VCED", "VCE", "V", "V", "V", "", "V"],
    "alert_centre":  ["V", "V", "V", "V", "V", "V", "V"],
    "report":        ["VX", "VX", "VX", "VX", "VX", "V", "VX"],
    "user":          ["VCED", "V", "", "", "", "", "V"],
    "configuration": ["VCED", "V", "", "", "", "", "V"],
    "approval":      ["VA", "VA", "V", "V", "V", "", "V"],
    "audit":         ["VX", "", "", "", "", "", "VX"],
}

ACTION_FIELD = {"V": "can_view", "C": "can_create", "E": "can_edit", "D": "can_delete", "A": "can_approve",
                "X": "can_export"}


def seed_default_roles(organization):
    """Create the seven default roles and their permissions for a new client."""
    from .models import Role, RolePermission

    created = {}
    with tenancy.tenant_context(organization.pk):
        for idx, (code, en, ar, seat, sensitive) in enumerate(ROLES):
            role, _ = Role.unscoped.get_or_create(
                organization=organization, code=code, is_deleted=False,
                defaults=dict(name_en=en, name_ar=ar, seat_type=seat, can_view_sensitive_fields=sensitive,
                              can_view_financial_values=True, is_system=True))
            created[code] = role
            perms = []
            for module in MODULES:
                letters = MATRIX[module][idx]
                flags = {field: (letter in letters) for letter, field in ACTION_FIELD.items()}
                perms.append(RolePermission(organization=organization, role=role, module=module, **flags))
            RolePermission.unscoped.bulk_create(perms, ignore_conflicts=True)
    return created
