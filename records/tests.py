import base64

from django.db import connection
from django.test import TestCase

from records.factories import PASSWORD, ScenarioMixin
from records.models import MentalHealthRecord

RECORD_TABLE = MentalHealthRecord._meta.db_table


def raw_content(record_id):
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT content FROM {RECORD_TABLE} WHERE id = %s', [record_id]
        )
        return cursor.fetchone()[0]


def is_base64(value):
    try:
        base64.b64decode(value, validate=True)
        return True
    except (ValueError, TypeError):
        return False


class AccessControlTests(ScenarioMixin, TestCase):
    def test_student_forbidden_from_create_get_and_post(self):
        self.login('student1')
        self.assertEqual(self.client.get('/records/new/').status_code, 403)
        self.assertEqual(self.client.post('/records/new/', {}).status_code, 403)

    def test_student_forbidden_from_edit_and_delete(self):
        self.login('student1')
        self.assertEqual(self.client.get(f'/records/{self.record1.id}/edit/').status_code, 403)
        self.assertEqual(self.client.get(f'/records/{self.record1.id}/delete/').status_code, 403)

    def test_counselor_list_shows_only_assigned_students(self):
        self.login('counselor1')
        response = self.client.get('/records/')
        self.assertContains(response, 'Ada Student')
        self.assertNotContains(response, 'Bola Student')

    def test_counselor_404_on_other_students_record(self):
        self.login('counselor1')
        self.assertEqual(self.client.get(f'/records/{self.record2.id}/').status_code, 404)
        self.assertEqual(self.client.get(f'/records/{self.record2.id}/edit/').status_code, 404)

    def test_counselor_forbidden_from_delete(self):
        self.login('counselor1')
        # Delete is administrator-only even for a counselor's own record.
        self.assertEqual(self.client.get(f'/records/{self.record1.id}/delete/').status_code, 403)

    def test_student_sees_only_own_records(self):
        self.login('student1')
        response = self.client.get('/records/')
        self.assertContains(response, 'Ada Student')
        self.assertNotContains(response, 'Bola Student')
        self.assertEqual(self.client.get(f'/records/{self.record2.id}/').status_code, 404)

    def test_administrator_full_lifecycle(self):
        self.login('admin')
        # List shows everyone.
        listing = self.client.get('/records/')
        self.assertContains(listing, 'Ada Student')
        self.assertContains(listing, 'Bola Student')
        # Create.
        created = self.client.post('/records/new/', {
            'student': self.profile1.id,
            'counselor': self.counselor1.id,
            'record_type': MentalHealthRecord.RecordType.SESSION,
            'date_assessed': '2026-02-01',
            'content': 'New session content.',
        })
        self.assertEqual(created.status_code, 302)
        new_id = int(created.url.rstrip('/').split('/')[-1])
        # Edit.
        edited = self.client.post(f'/records/{new_id}/edit/', {
            'student': self.profile1.id,
            'counselor': self.counselor1.id,
            'record_type': MentalHealthRecord.RecordType.SESSION,
            'date_assessed': '2026-02-02',
            'content': 'Edited session content.',
        })
        self.assertEqual(edited.status_code, 302)
        # Soft-delete.
        deleted = self.client.post(f'/records/{new_id}/delete/')
        self.assertRedirects(deleted, '/records/')
        self.assertFalse(MentalHealthRecord.objects.get(id=new_id).is_active)

    def test_audit_viewer_access_by_role(self):
        self.login('admin')
        self.assertEqual(self.client.get('/audit/').status_code, 200)
        self.client.logout()
        self.login('counselor1')
        self.assertEqual(self.client.get('/audit/').status_code, 403)
        self.client.logout()
        self.login('student1')
        self.assertEqual(self.client.get('/audit/').status_code, 403)

    def test_counselor_create_form_limits_student_choices(self):
        self.login('counselor1')
        response = self.client.get('/records/new/')
        students = response.context['form'].fields['student'].queryset
        self.assertIn(self.profile1, students)
        self.assertNotIn(self.profile2, students)
        # The rendered form exposes only the assigned student.
        self.assertContains(response, 'MHS/T/001')
        self.assertNotContains(response, 'MHS/T/002')


class EncryptionTests(ScenarioMixin, TestCase):
    def test_stored_value_is_ciphertext_not_plaintext(self):
        stored = raw_content(self.record1.id)
        self.assertNotEqual(stored, 'Assessment content for Ada.')
        self.assertTrue(is_base64(stored))

    def test_read_returns_plaintext(self):
        record = MentalHealthRecord.objects.get(id=self.record1.id)
        self.assertEqual(record.content, 'Assessment content for Ada.')

    def test_same_plaintext_produces_different_ciphertext(self):
        a = MentalHealthRecord.objects.create(
            student=self.profile1, counselor=self.counselor1,
            record_type=MentalHealthRecord.RecordType.NOTE,
            date_assessed=self.record1.date_assessed, content='identical text',
        )
        b = MentalHealthRecord.objects.create(
            student=self.profile1, counselor=self.counselor1,
            record_type=MentalHealthRecord.RecordType.NOTE,
            date_assessed=self.record1.date_assessed, content='identical text',
        )
        self.assertNotEqual(raw_content(a.id), raw_content(b.id))
        self.assertEqual(a.content, b.content)

    def test_blank_content_round_trips(self):
        record = MentalHealthRecord.objects.create(
            student=self.profile1, counselor=self.counselor1,
            record_type=MentalHealthRecord.RecordType.NOTE,
            date_assessed=self.record1.date_assessed, content='',
        )
        self.assertEqual(MentalHealthRecord.objects.get(id=record.id).content, '')


class InjectionAndXSSTests(ScenarioMixin, TestCase):
    def test_sql_injection_input_is_handled_safely(self):
        # Django's ORM parameterises every query, so this payload is treated as
        # literal data, never executed. The record saves and the table survives.
        payload = "'; DROP TABLE records_mentalhealthrecord; --"
        self.login('admin')
        response = self.client.post('/records/new/', {
            'student': self.profile1.id,
            'counselor': self.counselor1.id,
            'record_type': MentalHealthRecord.RecordType.NOTE,
            'date_assessed': '2026-04-01',
            'content': payload,
        })
        self.assertEqual(response.status_code, 302)
        new_id = int(response.url.rstrip('/').split('/')[-1])

        # The table still exists and both the original rows and the new one remain.
        self.assertEqual(MentalHealthRecord.objects.count(), 3)
        # The payload was stored verbatim as data, not interpreted.
        self.assertEqual(MentalHealthRecord.objects.get(id=new_id).content, payload)

        # The same holds for a free-text search filter on the audit viewer.
        search = self.client.get('/audit/', {'q': payload})
        self.assertEqual(search.status_code, 200)
        self.assertEqual(MentalHealthRecord.objects.count(), 3)

    def test_script_tag_in_content_is_escaped_not_executed(self):
        # Django templates auto-escape variables, so a script payload is rendered
        # as inert text rather than an executable element.
        payload = '<script>alert("xss")</script>'
        record = MentalHealthRecord.objects.create(
            student=self.profile1, counselor=self.counselor1,
            record_type=MentalHealthRecord.RecordType.NOTE,
            date_assessed=self.record1.date_assessed, content=payload,
        )
        self.login('admin')
        response = self.client.get(f'/records/{record.id}/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertNotIn('<script>alert("xss")</script>', html)
        self.assertIn('&lt;script&gt;', html)


class SoftDeleteTests(ScenarioMixin, TestCase):
    def test_soft_delete_hides_record_but_keeps_row(self):
        total_before = MentalHealthRecord.objects.count()
        self.login('admin')
        self.client.post(f'/records/{self.record1.id}/delete/')

        self.record1.refresh_from_db()
        self.assertFalse(self.record1.is_active)
        # Row is still present in the database.
        self.assertEqual(MentalHealthRecord.objects.count(), total_before)

        # Gone from every role's list and detail.
        for username in ('admin', 'counselor1', 'student1'):
            self.client.logout()
            self.login(username)
            self.assertNotContains(self.client.get('/records/'), 'Ada Student')
            self.assertEqual(self.client.get(f'/records/{self.record1.id}/').status_code, 404)
