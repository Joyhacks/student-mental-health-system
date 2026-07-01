from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action_type', 'resource', 'ip_address')
    list_filter = ('action_type', 'user', 'timestamp')
    search_fields = ('resource', 'details')
    # Every field is read-only; the log is never authored through the admin.
    readonly_fields = ('user', 'action_type', 'resource', 'timestamp', 'ip_address', 'details')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
