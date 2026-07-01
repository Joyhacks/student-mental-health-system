from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from records.models import MentalHealthRecord

from .middleware import client_ip, get_current_ip, get_current_user
from .models import AuditLog


def _record_resource(instance):
    # Identify the record by id and the student it belongs to, without exposing
    # any of the encrypted content.
    return f'MentalHealthRecord #{instance.pk} (student: {instance.student.full_name})'


@receiver(post_save, sender=MentalHealthRecord)
def log_record_saved(sender, instance, created, **kwargs):
    if created:
        action = AuditLog.Action.CREATE
    elif not instance.is_active:
        # is_active flipped to False is our soft-delete.
        action = AuditLog.Action.DELETE
    else:
        action = AuditLog.Action.UPDATE

    user = get_current_user()
    # No request context (seed, shell) means a system action, not an error.
    details = '' if user is not None else 'system action'
    AuditLog.record(
        user=user,
        action_type=action,
        resource=_record_resource(instance),
        ip_address=get_current_ip(),
        details=details,
    )


@receiver(post_delete, sender=MentalHealthRecord)
def log_record_deleted(sender, instance, **kwargs):
    # Covers a genuine row deletion for completeness; soft-delete is handled above.
    user = get_current_user()
    details = '' if user is not None else 'system action'
    AuditLog.record(
        user=user,
        action_type=AuditLog.Action.DELETE,
        resource=_record_resource(instance),
        ip_address=get_current_ip(),
        details=details,
    )


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    AuditLog.record(
        user=user,
        action_type=AuditLog.Action.LOGIN,
        resource=f'User #{user.pk}',
        ip_address=client_ip(request) if request else None,
    )


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    AuditLog.record(
        user=user,
        action_type=AuditLog.Action.LOGOUT,
        resource=f'User #{user.pk}' if user else '',
        ip_address=client_ip(request) if request else None,
    )


@receiver(user_login_failed)
def log_login_failed(sender, credentials, request=None, **kwargs):
    # Store only the attempted username; the password is never logged.
    username = credentials.get('username', '')
    AuditLog.record(
        user=None,
        action_type=AuditLog.Action.LOGIN_FAILED,
        resource='',
        ip_address=client_ip(request) if request else None,
        details=f'attempted username: {username}',
    )
