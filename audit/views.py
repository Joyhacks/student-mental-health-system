from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.shortcuts import render
from django.utils.dateparse import parse_date

from records.permissions import is_administrator, role_required

from .models import AuditLog


@role_required(is_administrator)
def audit_log(request):
    logs = AuditLog.objects.select_related('user')

    user_id = request.GET.get('user', '')
    action = request.GET.get('action_type', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    query = request.GET.get('q', '').strip()

    # Filters combine: each supplied value narrows the result set further.
    if user_id:
        logs = logs.filter(user_id=user_id)
    if action:
        logs = logs.filter(action_type=action)
    if parse_date(date_from):
        logs = logs.filter(timestamp__date__gte=date_from)
    if parse_date(date_to):
        logs = logs.filter(timestamp__date__lte=date_to)
    if query:
        logs = logs.filter(resource__icontains=query)

    paginator = Paginator(logs, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    # Preserve the active filters (but not the page number) across pagination.
    active_filters = {
        'user': user_id,
        'action_type': action,
        'date_from': date_from,
        'date_to': date_to,
        'q': query,
    }
    querystring = urlencode({k: v for k, v in active_filters.items() if v})

    return render(request, 'audit/log_list.html', {
        'page_obj': page_obj,
        'users': User.objects.order_by('username'),
        'action_choices': AuditLog.Action.choices,
        'filters': active_filters,
        'querystring': querystring,
    })
