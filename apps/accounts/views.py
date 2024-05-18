from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django import forms


class LoginForm(forms.Form):
    email    = forms.EmailField(
                    widget=forms.EmailInput(
                        attrs={'placeholder': 'admin@example.com',
                               'autofocus': True}
                    )
                )
    password = forms.CharField(
                    widget=forms.PasswordInput(
                        attrs={'placeholder': 'Password'}
                    )
                )


def login_view(request):
    # If already logged in send to dashboard
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