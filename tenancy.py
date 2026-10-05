"""Per-request tenant (client company) context.

The middleware sets the current organization and user for each request.
TenantManager reads it so that every query is filtered automatically.
If no organization is set, tenant queries return NOTHING (fail closed).
"""
from contextlib import contextmanager
from contextvars import ContextVar

_org_id = ContextVar("cgms_org_id", default=None)
_user_id = ContextVar("cgms_user_id", default=None)
_request_meta = ContextVar("cgms_request_meta", default=None)


def get_org_id():
    return _org_id.get()


def get_user_id():
    return _user_id.get()


def get_request_meta():
    return _request_meta.get() or {}


def set_context(org_id=None, user_id=None, meta=None):
    return (_org_id.set(org_id), _user_id.set(user_id), _request_meta.set(meta))


def reset_context(tokens):
    _org_id.reset(tokens[0])
    _user_id.reset(tokens[1])
    _request_meta.reset(tokens[2])


@contextmanager
def tenant_context(org_id, user_id=None):
    """Use in background jobs, commands and tests to work inside one client."""
    tokens = set_context(org_id, user_id, None)
    try:
        yield
    finally:
        reset_context(tokens)
