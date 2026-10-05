from django.apps import apps
from django.test import TestCase

from apps.accounts.models import Department, Organization
from apps.core import tenancy
from apps.core.models import AuditLog, TenantManager, TenantModel


def make_org(name):
    return Organization.objects.create(name_en=name)


class TenantIsolationTests(TestCase):
    def setUp(self):
        self.a, self.b = make_org("A Co"), make_org("B Co")
        with tenancy.tenant_context(self.a.pk):
            Department.objects.create(name_en="Finance A")
            Department.objects.create(name_en="Legal A")
        with tenancy.tenant_context(self.b.pk):
            Department.objects.create(name_en="Finance B")

    def test_every_client_table_is_protected(self):
        """Any new model built on TenantModel must be filtered by client automatically."""
        found = [m for m in apps.get_models() if issubclass(m, TenantModel)]
        self.assertTrue(found)
        for m in found:
            self.assertIsInstance(m._default_manager, TenantManager, m.__name__)
            self.assertEqual(m._default_manager.name, "objects", m.__name__)
            self.assertEqual(m._meta.base_manager_name, "unscoped", m.__name__)

    def test_no_context_returns_nothing(self):
        self.assertEqual(Department.objects.count(), 0)

    def test_each_client_sees_only_its_own_rows(self):
        with tenancy.tenant_context(self.a.pk):
            self.assertEqual(sorted(d.name_en for d in Department.objects.all()), ["Finance A", "Legal A"])
        with tenancy.tenant_context(self.b.pk):
            self.assertEqual([d.name_en for d in Department.objects.all()], ["Finance B"])

    def test_guessing_another_clients_id_finds_nothing(self):
        with tenancy.tenant_context(self.b.pk):
            other_id = Department.objects.get().pk
        with tenancy.tenant_context(self.a.pk):
            self.assertFalse(Department.objects.filter(pk=other_id).exists())
            with self.assertRaises(Department.DoesNotExist):
                Department.objects.get(pk=other_id)

    def test_cross_client_write_is_blocked(self):
        with tenancy.tenant_context(self.a.pk):
            with self.assertRaises(PermissionError):
                Department.objects.create(organization=self.b, name_en="Sneaky")

    def test_saving_without_context_is_blocked(self):
        with self.assertRaises(RuntimeError):
            Department.objects.create(name_en="Nobody")

    def test_context_is_cleared_after_block(self):
        with tenancy.tenant_context(self.a.pk):
            pass
        self.assertIsNone(tenancy.get_org_id())

    def test_soft_delete_hides_and_can_be_listed_separately(self):
        with tenancy.tenant_context(self.a.pk):
            d = Department.objects.get(name_en="Legal A")
            d.soft_delete()
            self.assertEqual(Department.objects.count(), 1)
            self.assertEqual(Department.deleted_objects.count(), 1)
        with tenancy.tenant_context(self.b.pk):
            self.assertEqual(Department.deleted_objects.count(), 0)

    def test_hard_delete_is_refused(self):
        with tenancy.tenant_context(self.a.pk):
            d = Department.objects.first()
            with self.assertRaises(RuntimeError):
                d.delete()
            with self.assertRaises(RuntimeError):
                Department.objects.all().delete()


class AuditTests(TestCase):
    def setUp(self):
        self.a = make_org("A Co")

    def test_create_and_update_are_audited_with_changes(self):
        with tenancy.tenant_context(self.a.pk):
            d = Department.objects.create(name_en="Ops")
            d.name_en = "Operations"
            d.save()
        logs = list(AuditLog.objects.filter(entity_type="department", entity_id=d.pk).order_by("id"))
        self.assertEqual([l.action for l in logs], ["Create", "Update"])
        self.assertEqual(logs[1].changes["name_en"], ["Ops", "Operations"])
        self.assertEqual(logs[1].organization_id, self.a.pk)

    def test_unchanged_save_writes_no_update_entry(self):
        with tenancy.tenant_context(self.a.pk):
            d = Department.objects.create(name_en="Ops")
            d.save()
        self.assertEqual(AuditLog.objects.filter(entity_type="department", action="Update").count(), 0)

    def test_audit_entries_cannot_be_changed_or_deleted(self):
        entry = AuditLog.objects.filter(entity_type="organization").first()
        self.assertIsNotNone(entry)
        entry.reason = "tampered"
        with self.assertRaises(RuntimeError):
            entry.save()
        with self.assertRaises(RuntimeError):
            entry.delete()

    def test_row_version_increments(self):
        with tenancy.tenant_context(self.a.pk):
            d = Department.objects.create(name_en="Ops")
            self.assertEqual(d.row_version, 1)
            d.name_en = "Ops 2"
            d.save()
            self.assertEqual(Department.objects.get(pk=d.pk).row_version, 2)
