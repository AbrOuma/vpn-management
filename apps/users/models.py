from django.db import models
import uuid



class Department(models.Model):
    name       = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name



class VPNUser(models.Model):
    """
    A person who owns one or more VPN devices.
    This is NOT a Django auth user.
    They never log into the dashboard — only into the self-service portal
    via a magic link sent to their email.
    """

    class Status(models.TextChoices):
        ACTIVE    = 'active',    'Active'
        SUSPENDED = 'suspended', 'Suspended'  # All their devices stop working
        DELETED   = 'deleted',   'Deleted'    # Soft delete, data kept

    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email      = models.EmailField(unique=True)
    full_name  = models.CharField(max_length=150)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    notes      = models.TextField(blank=True)
    status     = models.CharField(
                    max_length=15,
                    choices=Status.choices,
                    default=Status.ACTIVE
                )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']
        verbose_name = 'VPN User'

    def __str__(self):
        return f'{self.full_name} <{self.email}>'

    @property
    def is_active(self):
        return self.status == self.Status.ACTIVE

    @property
    def active_device_count(self):
        """How many active devices this user has."""
        return self.devices.filter(status='active').count()


class MagicLinkToken(models.Model):
    """
    A one-time login token for the self-service portal.
    User enters their email, receives a link, clicks it, they are in.
    No password needed.
    """

    user       = models.ForeignKey(
                    VPNUser,
                    on_delete=models.CASCADE,
                    related_name='magic_tokens'
                )
    token      = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used       = models.BooleanField(default=False)
    used_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Magic link for {self.user.email}'