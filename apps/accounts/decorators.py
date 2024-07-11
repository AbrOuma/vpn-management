from django.shortcuts import redirect
from functools import wraps


def staff_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_staff:
            return redirect('portal:login')
        return view_func(request, *args, **kwargs)
    return wrapper


def write_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.can_write:
            from django.contrib import messages
            messages.error(request, 'Your account is read-only.')
            return redirect(request.META.get('HTTP_REFERER', 'devices:list'))
        return view_func(request, *args, **kwargs)
    return wrapper


def superuser_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_superuser:
            from django.contrib import messages
            messages.error(request, 'Superuser access required.')
            return redirect('devices:list')
        return view_func(request, *args, **kwargs)
    return wrapper