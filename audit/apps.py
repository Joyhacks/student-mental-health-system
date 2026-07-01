from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit'

    def ready(self):
        # Importing connects the signal receivers to their senders.
        from . import signals  # noqa: F401
