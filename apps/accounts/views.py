from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django import forms
from rest_framework.authtoken.models import Token

User = get_user_model()


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={'placeholder': 'admin@example.com', 'autofocus': True}
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={'placeholder': 'Password'}
        )
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect('devices:list')

    form = LoginForm()

    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            email    = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user     = authenticate(request, username=email, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.full_name}.')
                return redirect('devices:list')
            else:
                messages.error(request, 'Invalid email or password.')

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


@login_required
def settings_view(request):
    try:
        token = Token.objects.get(user=request.user)
    except Token.DoesNotExist:
        token = None

    user_tokens = None
    if request.user.is_staff:
        all_users = User.objects.order_by('email')
        token_map = {t.user_id: t for t in Token.objects.select_related('user').all()}
        user_tokens = [
            {'user': u, 'token': token_map.get(u.pk)}
            for u in all_users
            if u.pk != request.user.pk
        ]

    return render(request, 'accounts/settings.html', {
        'token': token,
        'user_tokens': user_tokens,
    })


@login_required
@require_POST
def token_generate(request):
    Token.objects.filter(user=request.user).delete()
    Token.objects.create(user=request.user)
    messages.success(request, 'API token generated successfully.')
    return redirect('accounts:settings')


@login_required
@require_POST
def token_revoke(request):
    Token.objects.filter(user=request.user).delete()
    messages.success(request, 'API token revoked.')
    return redirect('accounts:settings')


@login_required
@require_POST
def admin_token_revoke(request, user_id):
    if not request.user.is_staff:
        messages.error(request, 'Permission denied.')
        return redirect('accounts:settings')
    target_user = get_object_or_404(User, pk=user_id)
    Token.objects.filter(user=target_user).delete()
    messages.success(request, f'Token revoked for {target_user.email}.')
    return redirect('accounts:settings')