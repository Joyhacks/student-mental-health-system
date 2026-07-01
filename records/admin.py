from django.contrib import admin

from .models import MentalHealthRecord, StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'matric_number', 'department', 'assigned_counselor')
    list_filter = ('department', 'gender')
    search_fields = ('full_name', 'matric_number')
    raw_id_fields = ('user', 'assigned_counselor')


@admin.register(MentalHealthRecord)
class MentalHealthRecordAdmin(admin.ModelAdmin):
    list_display = ('student', 'record_type', 'counselor', 'date_assessed', 'is_active')
    list_filter = ('record_type', 'is_active')
    search_fields = ('student__full_name', 'student__matric_number')
    raw_id_fields = ('student', 'counselor')
    # created_at/updated_at are managed automatically; show them read-only.
    readonly_fields = ('created_at', 'updated_at')
