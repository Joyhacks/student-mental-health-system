def user_role(request):
    """Expose the current user's role name to every template so the nav bar
    can display it without each view having to pass it in."""
    user = getattr(request, 'user', None)
    if user is None or not user.is_authenticated:
        return {}
    role = user.groups.values_list('name', flat=True).first()
    return {'user_role': role or 'No role assigned'}
