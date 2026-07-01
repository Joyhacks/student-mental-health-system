from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import MentalHealthRecord


def _in_group(user, name):
    return user.is_authenticated and user.groups.filter(name=name).exists()


def is_administrator(user):
    return _in_group(user, 'Administrator')


def is_counselor(user):
    return _in_group(user, 'Counselor')


def is_student(user):
    return _in_group(user, 'Student')


def scoped_records(user):
    """Return only the active records this user is allowed to see.

    Access control lives here at the queryset level so unauthorized rows are
    never loaded into memory and cannot be reached by guessing a URL. Every
    list and detail view must obtain records through this helper.
    """
    base = MentalHealthRecord.objects.filter(is_active=True).select_related(
        'student', 'student__user', 'counselor'
    )
    if is_administrator(user):
        return base
    if is_counselor(user):
        return base.filter(student__assigned_counselor=user)
    if is_student(user):
        return base.filter(student__user=user)
    return MentalHealthRecord.objects.none()


def role_required(*predicates):
    """Allow the view only if the user satisfies at least one role predicate,
    otherwise raise a genuine 403. Anonymous users are sent to login first."""
    def decorator(view):
        @login_required
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not any(predicate(request.user) for predicate in predicates):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return wrapper
    return decorator
