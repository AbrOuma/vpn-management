from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class AccountManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', Account.Role.SUPER_ADMIN)
        return self.create_user(email, password, **extra_fields)


class Account(AbstractBaseUser, PermissionsMixin):
    class Role(models.TextChoices):
        SUPER_ADMIN   = 'super_admin',   'Super Admin'
        NETWORK_ADMIN = 'network_admin', 'Network Admin'
        READ_ONLY     = 'read_only',     'Read Only'

    email      = models.EmailField(unique=True)
    full_name  = models.CharField(max_length=150)
    role       = models.CharField(
                    max_length=20,
                    choices=Role.choices,
                    default=Role.NETWORK_ADMIN
                )
    is_active  = models.BooleanField(default=True)
    is_staff   = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AccountManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        verbose_name = 'Admin Account'
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'

    @property
    def can_write(self):
        return self.role in (self.Role.SUPER_ADMIN, self.Role.NETWORK_ADMIN)


class AuditLog(models.Model):
    actor     = models.ForeignKey(Account, on_delete=models.SET_NULL, null=True)
    action    = models.CharField(max_length=100)
    target    = models.CharField(max_length=255)
    detail    = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.actor} - {self.action} - {self.timestamp}'