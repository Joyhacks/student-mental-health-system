from datetime import date

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction

from records.models import MentalHealthRecord, StudentProfile

# Shared password for the role accounts. This is demo-only convenience; real
# accounts would set individual passwords through the user-management flow.
DEMO_PASSWORD = 'DemoPass123!'  # nosec B105 - demo seed credential, not a production secret

DEMO_USERS = [
    ('admin_demo', 'Administrator', 'Amara', 'Okafor'),
    ('counselor_demo', 'Counselor', 'Daniel', 'Mensah'),
    ('counselor_two', 'Counselor', 'Grace', 'Adeyemi'),
    ('student_demo', 'Student', 'Zainab', 'Yusuf'),
    ('student_two', 'Student', 'Emeka', 'Nwosu'),
]

# Student profiles keyed by the student's username. assigned_counselor is given
# as a username that belongs to the Counselor group.
STUDENT_PROFILES = {
    'student_demo': {
        'full_name': 'Zainab Yusuf',
        'date_of_birth': date(2002, 3, 14),
        'gender': StudentProfile.Gender.FEMALE,
        'matric_number': 'MHS/2021/001',
        'department': 'Computer Science',
        'phone_number': '08030000001',
        'emergency_contact': 'Fatima Yusuf, 08030000010',
        'assigned_counselor': 'counselor_demo',
    },
    'student_two': {
        'full_name': 'Emeka Nwosu',
        'date_of_birth': date(2001, 11, 2),
        'gender': StudentProfile.Gender.MALE,
        'matric_number': 'MHS/2020/045',
        'department': 'Economics',
        'phone_number': '08030000002',
        'emergency_contact': 'Chidi Nwosu, 08030000020',
        'assigned_counselor': 'counselor_two',
    },
}

# Sample records. Each is authored by the student's assigned counselor. The
# (student, record_type, date_assessed) triple is used as the idempotency key.
SAMPLE_RECORDS = [
    {
        'student': 'student_demo',
        'record_type': MentalHealthRecord.RecordType.ASSESSMENT,
        'date_assessed': date(2026, 5, 10),
        'content': (
            'Initial intake assessment. Student reports mild exam-related stress '
            'and asked for guidance on time management. No risk indicators noted.'
        ),
    },
    {
        'student': 'student_demo',
        'record_type': MentalHealthRecord.RecordType.SESSION,
        'date_assessed': date(2026, 6, 2),
        'content': (
            'Follow-up session. Reviewed study schedule and sleep routine. Student '
            'is engaging well and applying the agreed strategies.'
        ),
    },
    {
        'student': 'student_two',
        'record_type': MentalHealthRecord.RecordType.NOTE,
        'date_assessed': date(2026, 6, 18),
        'content': (
            'Brief check-in note. Student is settling into the new department and '
            'was encouraged to join a peer study group.'
        ),
    },
]

SUPERUSER_NAME = 'superadmin'
SUPERUSER_PASSWORD = 'SuperDemo123!'  # nosec B105 - demo seed credential, not a production secret
SUPERUSER_EMAIL = 'superadmin@example.com'


class Command(BaseCommand):
    help = 'Create demo users, student profiles, and sample records for the live demo.'

    @transaction.atomic
    def handle(self, *args, **options):
        users = {}
        for username, role, first_name, last_name in DEMO_USERS:
            group = Group.objects.get(name=role)
            user, _ = User.objects.get_or_create(username=username)
            user.first_name = first_name
            user.last_name = last_name
            user.is_active = True
            user.set_password(DEMO_PASSWORD)
            user.save()
            user.groups.set([group])
            users[username] = user

        for student_username, data in STUDENT_PROFILES.items():
            fields = dict(data)
            fields['assigned_counselor'] = users[fields.pop('assigned_counselor')]
            StudentProfile.objects.update_or_create(
                user=users[student_username],
                defaults=fields,
            )

        for record in SAMPLE_RECORDS:
            profile = StudentProfile.objects.get(user=users[record['student']])
            MentalHealthRecord.objects.get_or_create(
                student=profile,
                record_type=record['record_type'],
                date_assessed=record['date_assessed'],
                defaults={
                    'counselor': profile.assigned_counselor,
                    'content': record['content'],
                },
            )

        superuser, _ = User.objects.get_or_create(
            username=SUPERUSER_NAME,
            defaults={'email': SUPERUSER_EMAIL},
        )
        superuser.is_staff = True
        superuser.is_superuser = True
        superuser.is_active = True
        superuser.set_password(SUPERUSER_PASSWORD)
        superuser.save()

        self._print_summary()

    def _print_summary(self):
        student_count = StudentProfile.objects.count()
        record_count = MentalHealthRecord.objects.count()

        self.stdout.write(self.style.SUCCESS('Demo data ready.'))
        self.stdout.write(f'  Student profiles: {student_count}')
        self.stdout.write(f'  Mental health records: {record_count}')
        self.stdout.write('')
        self.stdout.write('Application logins (password is the same for all):')
        self.stdout.write(f'  Password: {DEMO_PASSWORD}')
        for username, role, _, _ in DEMO_USERS:
            self.stdout.write(f'  {role:<14} {username}')
        self.stdout.write('')
        self.stdout.write('Django admin superuser:')
        self.stdout.write(f'  Username: {SUPERUSER_NAME}')
        self.stdout.write(f'  Password: {SUPERUSER_PASSWORD}')
