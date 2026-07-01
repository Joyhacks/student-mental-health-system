from django.contrib.auth.models import User
from django.db import models


class AuditLog(models.Model):
    class Action(models.TextChoices):
        LOGIN = 'login', 'Login'
        LOGOUT = 'logout', 'Logout'
        LOGIN_FAILED = 'login_failed', 'Failed login'
        VIEW = 'view', 'View'
        CREATE = 'create', 'Create'
        UPDATE = 'update', 'Update'
        DELETE = 'delete', 'Delete'
        ADMIN = 'admin', 'Admin'

    # SET_NULL so a system action, or the later removal of a user account, still
    # leaves the historical log entry intact.
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_entries',
    )
    action_type = models.CharField(max_length=20, choices=Action.choices)
    resource = models.CharField(max_length=100, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    # Non-sensitive context only. Record content and passwords must never land here.
    details = models.TextField(blank=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        actor = self.user.username if self.user else 'system'
        return f'{self.timestamp:%Y-%m-%d %H:%M:%S} {actor} {self.action_type} {self.resource}'.strip()

    def save(self, *args, **kwargs):
        # The audit trail is append-only: entries may be created but never edited.
        if self.pk is not None:
            raise ValueError('Audit log entries are immutable and cannot be modified.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Audit log entries cannot be deleted.')

    @classmethod
    def record(cls, user, action_type, resource, ip_address=None, details=''):
        """Single entry point for writing to the audit trail."""
        return cls.objects.create(
            user=user,
            action_type=action_type,
            resource=resource,
            ip_address=ip_address,
            details=details,
        )
