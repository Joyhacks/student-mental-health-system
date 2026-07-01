from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.cache import cache
from django.shortcuts import render

# Roles are ordered by privilege so a user who happens to belong to more than
# one group lands on the most capable dashboard.
DASHBOARD_TEMPLATES = [
    ('Administrator', 'accounts/dashboard_admin.html'),
    ('Counselor', 'accounts/dashboard_counselor.html'),
    ('Student', 'accounts/dashboard_student.html'),
]

# Rate-limit thresholds. Ten failures per client within the window is generous
# enough for honest mistakes during a demo but still blunts brute-force attempts.
LOGIN_ATTEMPT_LIMIT = 10
LOGIN_ATTEMPT_WINDOW = 15 * 60


def _client_ip(request):
    # Deliberately use REMOTE_ADDR only. X-Forwarded-For is client-controlled and
    # would let an attacker sidestep the limit by rotating the header value.
    return request.META.get('REMOTE_ADDR', '')


class RateLimitedLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True

    def _attempt_key(self):
        return f'login-failures:{_client_ip(self.request)}'

    def _is_locked_out(self):
        return cache.get(self._attempt_key(), 0) >= LOGIN_ATTEMPT_LIMIT

    def post(self, request, *args, **kwargs):
        if self._is_locked_out():
            context = self.get_context_data(form=self.get_form(), locked_out=True)
            return self.render_to_response(context)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        # A successful sign-in clears the counter for this client.
        cache.delete(self._attempt_key())
        return super().form_valid(form)

    def form_invalid(self, form):
        key = self._attempt_key()
        cache.add(key, 0, LOGIN_ATTEMPT_WINDOW)
        try:
            cache.incr(key)
        except ValueError:
            # The entry expired between add and incr; restart the window.
            cache.set(key, 1, LOGIN_ATTEMPT_WINDOW)
        return super().form_invalid(form)


@login_required
def dashboard(request):
    """Route each user to the dashboard for their role. A user with no role
    group sees a plain informational page rather than an error."""
    roles = set(request.user.groups.values_list('name', flat=True))
    for role, template in DASHBOARD_TEMPLATES:
        if role in roles:
            return render(request, template)
    return render(request, 'accounts/dashboard_no_role.html')
