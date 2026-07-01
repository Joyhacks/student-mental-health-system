"""Shared test data builders. Not a test module itself; imported by the test
suites so each TestCase can build its own world in setUp without relying on
seed_demo. Groups come from the accounts migration, which the test runner
applies to the test database."""

from datetime import date

from django.contrib.auth.models import Group, User

from records.models import MentalHealthRecord, StudentProfile

PASSWORD = 'test-pass-123'


def make_user(username, group_name):
    user = User.objects.create_user(username=username, password=PASSWORD)
    user.groups.add(Group.objects.get(name=group_name))
    return user


class ScenarioMixin:
    """Builds two counselors, two students (one assigned to each counselor),
    and one record per student. counselor1 owns student1/record1; counselor2
    owns student2/record2."""

    def setUp(self):
        super().setUp()
        self.admin = make_user('admin', 'Administrator')
        self.counselor1 = make_user('counselor1', 'Counselor')
        self.counselor2 = make_user('counselor2', 'Counselor')
        self.student1_user = make_user('student1', 'Student')
        self.student2_user = make_user('student2', 'Student')

        self.profile1 = StudentProfile.objects.create(
            user=self.student1_user,
            full_name='Ada Student',
            date_of_birth=date(2000, 1, 1),
            gender=StudentProfile.Gender.FEMALE,
            matric_number='MHS/T/001',
            department='Computer Science',
            phone_number='08000000001',
            emergency_contact='Kin One, 08000000010',
            assigned_counselor=self.counselor1,
        )
        self.profile2 = StudentProfile.objects.create(
            user=self.student2_user,
            full_name='Bola Student',
            date_of_birth=date(1999, 6, 15),
            gender=StudentProfile.Gender.MALE,
            matric_number='MHS/T/002',
            department='Economics',
            phone_number='08000000002',
            emergency_contact='Kin Two, 08000000020',
            assigned_counselor=self.counselor2,
        )

        self.record1 = MentalHealthRecord.objects.create(
            student=self.profile1,
            counselor=self.counselor1,
            record_type=MentalHealthRecord.RecordType.ASSESSMENT,
            date_assessed=date(2026, 1, 1),
            content='Assessment content for Ada.',
        )
        self.record2 = MentalHealthRecord.objects.create(
            student=self.profile2,
            counselor=self.counselor2,
            record_type=MentalHealthRecord.RecordType.NOTE,
            date_assessed=date(2026, 1, 2),
            content='Note content for Bola.',
        )

    def login(self, username):
        self.client.login(username=username, password=PASSWORD)
