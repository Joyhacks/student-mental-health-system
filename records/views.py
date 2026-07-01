from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import MentalHealthRecordForm
from .permissions import (
    is_administrator,
    is_counselor,
    role_required,
    scoped_records,
)


@login_required
def record_list(request):
    records = scoped_records(request.user)
    can_create = is_administrator(request.user) or is_counselor(request.user)
    return render(request, 'records/list.html', {
        'records': records,
        'can_create': can_create,
    })


@login_required
def record_detail(request, pk):
    # Pulling from the scoped queryset means an out-of-scope id is a genuine 404
    # for this user, not a redirect that would hint the record exists.
    record = get_object_or_404(scoped_records(request.user), pk=pk)
    return render(request, 'records/detail.html', {
        'record': record,
        'can_edit': is_administrator(request.user) or is_counselor(request.user),
        'can_delete': is_administrator(request.user),
    })


@role_required(is_administrator, is_counselor)
def record_create(request):
    if request.method == 'POST':
        form = MentalHealthRecordForm(request.POST, user=request.user)
        if form.is_valid():
            record = form.save(commit=False)
            if is_counselor(request.user) and not is_administrator(request.user):
                record.counselor = request.user
            record.save()
            return redirect('records:detail', pk=record.pk)
    else:
        form = MentalHealthRecordForm(user=request.user)
    return render(request, 'records/form.html', {'form': form, 'heading': 'New record'})


@role_required(is_administrator, is_counselor)
def record_update(request, pk):
    record = get_object_or_404(scoped_records(request.user), pk=pk)
    if request.method == 'POST':
        form = MentalHealthRecordForm(request.POST, instance=record, user=request.user)
        if form.is_valid():
            record = form.save(commit=False)
            if is_counselor(request.user) and not is_administrator(request.user):
                record.counselor = request.user
            record.save()
            return redirect('records:detail', pk=record.pk)
    else:
        form = MentalHealthRecordForm(instance=record, user=request.user)
    return render(request, 'records/form.html', {'form': form, 'heading': 'Edit record'})


@role_required(is_administrator)
def record_delete(request, pk):
    record = get_object_or_404(scoped_records(request.user), pk=pk)
    if request.method == 'POST':
        # Soft delete: hide the record everywhere but keep the row in the database.
        record.is_active = False
        record.save(update_fields=['is_active', 'updated_at'])
        return redirect('records:list')
    return render(request, 'records/delete_confirm.html', {'record': record})
