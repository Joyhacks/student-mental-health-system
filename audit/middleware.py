import threading

from .models import AuditLog

# Per-thread handle on the request in flight so signal receivers (which have no
# direct access to the request) can attribute the acting user and client IP.
_request_context = threading.local()

# Only these resolved view names produce a "view" audit entry, and each maps to
# the URL keyword argument holding the record id. Keeping this explicit avoids
# logging every page load as noise.
VIEWABLE_RESOURCES = {
    'records:detail': ('pk', 'MentalHealthRecord'),
}


def get_current_request():
    return getattr(_request_context, 'request', None)


def get_current_user():
    request = get_current_request()
    if request is None:
        return None
    user = getattr(request, 'user', None)
    return user if (user is not None and user.is_authenticated) else None


def get_current_ip():
    request = get_current_request()
    if request is None:
        return None
    return client_ip(request)


def client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _request_context.request = request
        try:
            response = self.get_response(request)
            self._log_record_view(request, response)
            return response
        finally:
            # Always clear so nothing leaks into the next request on this thread.
            _request_context.request = None

    def _log_record_view(self, request, response):
        # Access logging covers reads only. Create/update/delete are captured by
        # model signals, so logging POSTs here would double-count them.
        if request.method != 'GET':
            return
        # Only a successful read counts; a 404 for an out-of-scope id is not a view.
        if response.status_code != 200:
            return
        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return
        match = request.resolver_match
        if match is None:
            return
        mapping = VIEWABLE_RESOURCES.get(match.view_name)
        if mapping is None:
            return
        kwarg, model_name = mapping
        object_id = match.kwargs.get(kwarg)
        AuditLog.record(
            user=user,
            action_type=AuditLog.Action.VIEW,
            resource=f'{model_name} #{object_id}',
            ip_address=client_ip(request),
        )
