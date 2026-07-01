from django import forms
from django.contrib.auth.models import Group, User

from .models import MentalHealthRecord, StudentProfile
from .permissions import is_administrator, is_counselor

FIELD_CLASSES = (
    'mt-1 w-full rounded-md border border-slate-300 px-3 py-2 '
    'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
)


class MentalHealthRecordForm(forms.ModelForm):
    class Meta:
        model = MentalHealthRecord
        fields = ['student', 'counselor', 'record_type', 'date_assessed', 'content']
        widgets = {
            'date_assessed': forms.DateInput(attrs={'type': 'date'}),
            'content': forms.Textarea(attrs={'rows': 6}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # The student and author choices are constrained by the current user's
        # role here in the form, not only in the template, so a hand-crafted POST
        # cannot reference a student or author the user is not allowed to use.
        if is_administrator(user):
            self.fields['student'].queryset = StudentProfile.objects.all()
            self.fields['counselor'].queryset = User.objects.filter(
                groups=Group.objects.get(name='Counselor')
            )
            self.fields['counselor'].label = 'Author (counselor)'
        elif is_counselor(user):
            self.fields['student'].queryset = StudentProfile.objects.filter(
                assigned_counselor=user
            )
            # The author is always the logged-in counselor, set in the view.
            del self.fields['counselor']
        else:
            self.fields['student'].queryset = StudentProfile.objects.none()
            del self.fields['counselor']

        for field in self.fields.values():
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = f'{existing} {FIELD_CLASSES}'.strip()
