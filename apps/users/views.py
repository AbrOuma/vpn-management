from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from django import forms
from .models import VPNUser, Department
from apps.accounts.decorators import staff_required, write_required
from apps.accounts.utils import log_action


class VPNUserForm(forms.ModelForm):
    class Meta:
        model  = VPNUser
        fields = ['full_name', 'email', 'department', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


@staff_required
def user_list(request):
    users = VPNUser.objects.exclude(status=VPNUser.Status.DELETED)

    q = request.GET.get('q')
    if q:
        users = users.filter(full_name__icontains=q) | \
                users.filter(email__icontains=q)

    return render(request, 'users/list.html', {'users': users})


@staff_required
@write_required
def user_add(request):
    form = VPNUserForm()

    if request.method == 'POST':
        form = VPNUserForm(request.POST)
        if form.is_valid():
            vpnuser = form.save()
            log_action(request, 'User Created', vpnuser.full_name, f'Email: {vpnuser.email}')
            messages.success(request, f'User "{vpnuser.full_name}" created.')
            return redirect('users:detail', pk=vpnuser.pk)

    return render(request, 'users/add.html', {'form': form})


@staff_required
def user_detail(request, pk):
    vpnuser = get_object_or_404(VPNUser, pk=pk)
    devices = vpnuser.devices.select_related('allocated_ip').all()

    return render(request, 'users/detail.html', {
        'vpnuser': vpnuser,
        'devices': devices,
    })


@staff_required
@write_required
def user_suspend(request, pk):
    vpnuser = get_object_or_404(VPNUser, pk=pk)
    if request.method == 'POST':
        vpnuser.status = VPNUser.Status.SUSPENDED
        vpnuser.save(update_fields=['status', 'updated_at'])
        log_action(request, 'User Suspended', vpnuser.full_name)
        messages.warning(request, f'{vpnuser.full_name} has been suspended.')
    return redirect('users:detail', pk=pk)


@staff_required
@write_required
def user_activate(request, pk):
    vpnuser = get_object_or_404(VPNUser, pk=pk)
    if request.method == 'POST':
        vpnuser.status = VPNUser.Status.ACTIVE
        vpnuser.save(update_fields=['status', 'updated_at'])
        log_action(request, 'User Activated', vpnuser.full_name)
        messages.success(request, f'{vpnuser.full_name} has been activated.')
    return redirect('users:detail', pk=pk)


@staff_required
@write_required
def user_delete(request, pk):
    user = get_object_or_404(VPNUser, pk=pk)
    if request.method == 'POST':
        name = user.full_name
        log_action(request, 'User Deleted', name)
        user.delete()
        messages.success(request, f'User "{name}" deleted.')
        return redirect('users:list')
    return redirect('users:detail', pk=pk)


@staff_required
def department_list(request):
    departments = Department.objects.annotate(
        user_count=models.Count('users')
    )
    return render(request, 'users/departments.html', {
        'departments': departments
    })


@staff_required
@write_required
def department_add(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            dept, created = Department.objects.get_or_create(name=name)
            if created:
                log_action(request, 'Department Created', name)
                messages.success(request, f'Department "{name}" added.')
            else:
                messages.warning(request, f'"{name}" already exists.')
    return redirect('users:departments')


@staff_required
@write_required
def department_delete(request, pk):
    if request.method == 'POST':
        dept = get_object_or_404(Department, pk=pk)
        name = dept.name
        log_action(request, 'Department Deleted', name)
        dept.delete()
        messages.success(request, f'Department "{name}" deleted.')
    return redirect('users:departments')