from functools import wraps

from django.core.exceptions import PermissionDenied

ACTIONS = {"view": "can_view", "create": "can_create", "edit": "can_edit", "delete": "can_delete",
           "approve": "can_approve", "export": "can_export"}


def user_can(user, module, action):
    """Does this user have this action on this module? Platform staff never touch client modules."""
    if not user.is_authenticated or not user.is_active:
        return False
    if user.is_platform_admin or not user.organization_id:
        return False
    if user.is_org_admin:
        return True
    cache = getattr(user, "_perm_cache", None)
    if cache is None:
        from apps.accounts.models import RolePermission

        cache = {}
        if user.role_id:
            for p in RolePermission.unscoped.filter(role_id=user.role_id, organization_id=user.organization_id):
                cache[p.module] = p
        user._perm_cache = cache
    perm = cache.get(module)
    return bool(perm and getattr(perm, ACTIONS[action]))


def permission_required(module, action="view"):
    def deco(view):
        @wraps(view)
        def wrapper(request, *a, **kw):
            if not user_can(request.user, module, action):
                raise PermissionDenied
            return view(request, *a, **kw)
        return wrapper
    return deco
