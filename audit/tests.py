from django.test import TestCase

from audit.models import AuditLog
from records.factories import PASSWORD, ScenarioMixin
from records.models import MentalHealthRecord


def count(action):
    return AuditLog.objects.filter(action_type=action).count()


def latest(action):
    return AuditLog.objects.filter(action_type=action).first()


class AuditLoggingTests(ScenarioMixin, TestCase):
    def test_successful_login_logs_one_entry(self):
        before = count(AuditLog.Action.LOGIN)
        self.client.post('/', {'username': 'admin', 'password': PASSWORD})
        self.assertEqual(count(AuditLog.Action.LOGIN), before + 1)
        self.assertEqual(latest(AuditLog.Action.LOGIN).user, self.admin)

    def test_detail_view_logs_once_and_list_logs_none(self):
        self.login('admin')
        before = count(AuditLog.Action.VIEW)

        self.client.get('/records/')
        self.assertEqual(count(AuditLog.Action.VIEW), before, 'list must not log a view')

        self.client.get(f'/records/{self.record1.id}/')
        self.assertEqual(count(AuditLog.Action.VIEW), before + 1, 'detail must log exactly one view')
        self.assertEqual(latest(AuditLog.Action.VIEW).resource, f'MentalHealthRecord #{self.record1.id}')

    def test_create_update_delete_each_logged_once(self):
        self.login('admin')

        before = count(AuditLog.Action.CREATE)
        created = self.client.post('/records/new/', {
            'student': self.profile1.id,
            'counselor': self.counselor1.id,
            'record_type': MentalHealthRecord.RecordType.SESSION,
            'date_assessed': '2026-03-01',
            'content': 'Audit create content.',
        })
        new_id = int(created.url.rstrip('/').split('/')[-1])
        self.assertEqual(count(AuditLog.Action.CREATE), before + 1, 'create must log exactly once')

        before = count(AuditLog.Action.UPDATE)
        self.client.post(f'/records/{new_id}/edit/', {
            'student': self.profile1.id,
            'counselor': self.counselor1.id,
            'record_type': MentalHealthRecord.RecordType.SESSION,
            'date_assessed': '2026-03-02',
            'content': 'Audit update content.',
        })
        self.assertEqual(count(AuditLog.Action.UPDATE), before + 1, 'update must log exactly once')

        before = count(AuditLog.Action.DELETE)
        self.client.post(f'/records/{new_id}/delete/')
        self.assertEqual(count(AuditLog.Action.DELETE), before + 1, 'soft-delete must log exactly once')

    def test_failed_login_logs_username_not_password(self):
        before = count(AuditLog.Action.LOGIN_FAILED)
        self.client.post('/', {'username': 'admin', 'password': 'super-secret-wrong'})
        self.assertEqual(count(AuditLog.Action.LOGIN_FAILED), before + 1)

        entry = latest(AuditLog.Action.LOGIN_FAILED)
        self.assertIn('admin', entry.details)
        self.assertNotIn('super-secret-wrong', entry.details)

    def test_audit_entries_are_immutable(self):
        entry = AuditLog.record(self.admin, AuditLog.Action.LOGIN, 'User #1')
        with self.assertRaises(ValueError):
            entry.save()
        with self.assertRaises(ValueError):
            entry.delete()
