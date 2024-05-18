from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone


class AccountManager(BaseUserManager):
    """
    Tells Django how to create users for our custom Account model.
    We use email as the username instead of a username field.
    """

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
    """
    Custom admin user model.
    Replaces Django's built-in User model.
    Uses email instead of username.
    """

    class Role(models.TextChoices):
        SUPER_ADMIN   = 'super_admin',   'Super Admin'    # Full access
        NETWORK_ADMIN = 'network_admin', 'Network Admin'  # Add/remove peers
        READ_ONLY     = 'read_only',     'Read Only'      # View only

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

    # Use email to log in instead of username
    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        verbose_name = 'Admin Account'
        ordering = ['full_name']

    def __str__(self):
        return f'{self.full_name} ({self.get_role_display()})'

    @property
    def can_write(self):
        """Returns True if this admin can make changes."""
        return self.role in (self.Role.SUPER_ADMIN, self.Role.NETWORK_ADMIN)


class AuditLog(models.Model):
    """
    An immutable record of every action taken on the platform.
    Who did what, and when.
    Never delete audit log entries.
    """

    class Action(models.TextChoices):
        PEER_ADDED    = 'peer_added',    'Peer Added'
        PEER_REMOVED  = 'peer_removed',  'Peer Removed'
        PEER_ENABLED  = 'peer_enabled',  'Peer Enabled'
        PEER_DISABLED = 'peer_disabled', 'Peer Disabled'
        PEER_REVOKED  = 'peer_revoked',  'Peer Revoked'
        USER_CREATED  = 'user_created',  'User Created'
        USER_DELETED  = 'user_deleted',  'User Deleted'
        INVITE_SENT   = 'invite_sent',   'Invite Sent'
        INVITE_USED   = 'invite_used',   'Invite Used'
        CONFIG_SYNCED = 'config_synced', 'Config Synced'
        IMPORT_RUN    = 'import_run',    'Import Run'
        LOGIN         = 'login',         'Login'

    account    = models.ForeignKey(
                    Account,
                    null=True,
                    on_delete=models.SET_NULL
                )
    action     = models.CharField(max_length=30, choices=Action.choices)
    target     = models.CharField(max_length=255, blank=True)
    detail     = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp  = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f'[{self.timestamp:%Y-%m-%d %H:%M}] {self.action} by {self.account}'