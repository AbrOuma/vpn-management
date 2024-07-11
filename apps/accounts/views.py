from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django import forms
from rest_framework.authtoken.models import Token
from .decorators import staff_required, superuser_required
from .models import Account

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


class AdminForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password'}),
        required=False,
        help_text='Leave blank to keep existing password.'
    )

    class Meta:
        model = Account
        fields = ['full_name', 'email', 'role', 'is_active']

    def __init__(self, *args, **kwargs):
        self.is_create = kwargs.pop('is_create', False)
        super().__init__(*args, **kwargs)
        if self.is_create:
            self.fields['password'].required = True
            self.fields['password'].help_text = ''
        for field_name, field in self.fields.items():
            if field_name == 'is_active':
                field.widget.attrs['class'] = 'form-check-input'
            else:
                field.widget.attrs['class'] = 'form-control'

    def save(self, commit=True):
        account = super().save(commit=False)
        password = self.cleaned_data.get('password')
        if password:
            account.set_password(password)
        if commit:
            account.save()
        return account


def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('devices:list')
        return redirect('portal:index')

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
                if user.is_staff:
                    return redirect('devices:list')
                return redirect('portal:index')
            else:
                messages.error(request, 'Invalid email or password.')

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')


@staff_required
def settings_view(request):
    try:
        token = Token.objects.get(user=request.user)
    except Token.DoesNotExist:
        token = None

    user_tokens = None
    if request.user.is_superuser:
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


@staff_required
@require_POST
def token_generate(request):
    Token.objects.filter(user=request.user).delete()
    Token.objects.create(user=request.user)
    messages.success(request, 'API token generated successfully.')
    return redirect('accounts:settings')


@staff_required
@require_POST
def token_revoke(request):
    Token.objects.filter(user=request.user).delete()
    messages.success(request, 'API token revoked.')
    return redirect('accounts:settings')


@staff_required
@require_POST
def admin_token_revoke(request, user_id):
    if not request.user.is_superuser:
        messages.error(request, 'Permission denied.')
        return redirect('accounts:settings')
    target_user = get_object_or_404(User, pk=user_id)
    Token.objects.filter(user=target_user).delete()
    messages.success(request, f'Token revoked for {target_user.email}.')
    return redirect('accounts:settings')


@superuser_required
def admin_list(request):
    admins = Account.objects.exclude(pk=request.user.pk).order_by('full_name')
    return render(request, 'accounts/admins.html', {'admins': admins})


@superuser_required
def admin_add(request):
    form = AdminForm(is_create=True)
    if request.method == 'POST':
        form = AdminForm(request.POST, is_create=True)
        if form.is_valid():
            account = form.save(commit=False)
            account.is_staff = True
            account.is_superuser = account.role == Account.Role.SUPER_ADMIN
            account.save()
            messages.success(request, f'Admin "{account.full_name}" created.')
            return redirect('accounts:admin_list')
    return render(request, 'accounts/admin_form.html', {'form': form, 'action': 'Add'})


@superuser_required
def admin_edit(request, pk):
    account = get_object_or_404(Account, pk=pk)
    form = AdminForm(instance=account)
    if request.method == 'POST':
        form = AdminForm(request.POST, instance=account)
        if form.is_valid():
            account = form.save(commit=False)
            account.is_staff = True
            account.is_superuser = account.role == Account.Role.SUPER_ADMIN
            account.save()
            messages.success(request, f'Admin "{account.full_name}" updated.')
            return redirect('accounts:admin_list')
    return render(request, 'accounts/admin_form.html', {'form': form, 'action': 'Edit'})


@superuser_required
@require_POST
def admin_deactivate(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if account.pk == request.user.pk:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('accounts:admin_list')
    account.is_active = False
    account.save(update_fields=['is_active'])
    messages.warning(request, f'{account.full_name} has been deactivated.')
    return redirect('accounts:admin_list')


@superuser_required
@require_POST
def admin_activate(request, pk):
    account = get_object_or_404(Account, pk=pk)
    account.is_active = True
    account.save(update_fields=['is_active'])
    messages.success(request, f'{account.full_name} has been activated.')
    return redirect('accounts:admin_list')


@superuser_required
@require_POST
def admin_delete(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if account.pk == request.user.pk:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('accounts:admin_list')
    if account.is_superuser:
        messages.error(request, 'Superuser accounts cannot be deleted.')
        return redirect('accounts:admin_list')
    name = account.full_name
    account.delete()
    messages.success(request, f'Admin "{name}" deleted.')
    return redirect('accounts:admin_list')


