from django.contrib.auth.models import User
from django.db import models

from .fields import EncryptedTextField


class StudentProfile(models.Model):
    class Gender(models.TextChoices):
        FEMALE = 'F', 'Female'
        MALE = 'M', 'Male'
        OTHER = 'O', 'Other'
        UNDISCLOSED = 'U', 'Prefer not to say'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile',
    )
    full_name = models.CharField(max_length=150)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices)
    matric_number = models.CharField(max_length=30, unique=True)
    department = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20)
    emergency_contact = models.CharField(
        max_length=150,
        help_text='Name and phone number of the emergency contact.',
    )
    # The counselor responsible for this student's caseload. Set by an
    # Administrator and expected to reference a user in the Counselor group.
    # SET_NULL keeps the student record if the counselor account is removed.
    assigned_counselor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_students',
    )

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.matric_number})'


class MentalHealthRecord(models.Model):
    class RecordType(models.TextChoices):
        ASSESSMENT = 'assessment', 'Assessment'
        SESSION = 'session', 'Session'
        NOTE = 'note', 'Note'

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name='records',
    )
    # The counselor who authored the record. Expected to be in the Counselor
    # group; PROTECT prevents deleting a counselor who still owns records.
    counselor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='authored_records',
    )
    record_type = models.CharField(max_length=20, choices=RecordType.choices)
    content = EncryptedTextField()
    date_assessed = models.DateField()
    # Soft-delete flag: records are hidden by setting this false, never removed.
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.get_record_type_display()} for {self.student.full_name} on {self.date_assessed}'
