from django.db import models
import ipaddress


class ServerConfig(models.Model):

    class ProvisioningStatus(models.TextChoices):
        MANUAL       = 'manual',       'Manually Configured'
        PROVISIONING = 'provisioning', 'Provisioning'
        PROVISIONED  = 'provisioned',  'Provisioned'
        FAILED       = 'failed',       'Failed'

    name           = models.CharField(
                        max_length=100,
                        default='Primary Server',
                        help_text='A friendly name e.g. GCP Primary'
                     )
    interface_name = models.CharField(max_length=15, default='wg0')
    public_ip      = models.GenericIPAddressField(
                        help_text='Your GCP external IP address',
                        blank=True,
                        null=True,
                     )
    listen_port    = models.PositiveIntegerField(default=51820)
    vpn_subnet     = models.CharField(max_length=20, default='10.0.0.0/24')
    server_ip      = models.GenericIPAddressField(default='10.0.0.1')
    address        = models.CharField(
                        max_length=20,
                        default='10.0.0.1/24',
                        help_text='Server VPN address with mask e.g. 10.0.0.1/24'
                     )
    public_key     = models.TextField(
                        help_text='WireGuard server public key',
                        blank=True,
                     )
    private_key    = models.TextField(
                        help_text='Encrypted WireGuard server private key',
                        blank=True
                     )
    dns_servers    = models.CharField(max_length=100, default='1.1.1.1,8.8.8.8')
    mtu            = models.PositiveIntegerField(default=1420)
    post_up        = models.TextField(
                        default=(
                            'iptables -A FORWARD -i wg0 -j ACCEPT; '
                            'iptables -A FORWARD -o wg0 -j ACCEPT; '
                            'iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE'
                        )
                     )
    post_down      = models.TextField(
                        default=(
                            'iptables -D FORWARD -i wg0 -j ACCEPT; '
                            'iptables -D FORWARD -o wg0 -j ACCEPT; '
                            'iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE'
                        )
                     )
    ssh_host       = models.CharField(
                        max_length=255,
                        blank=True,
                        help_text='GCP server external IP'
                     )
    ssh_user       = models.CharField(max_length=100, default='electrical')
    ssh_key_path   = models.CharField(max_length=500, default='gcp_key')
    ssh_key_encrypted = models.TextField(
                        blank=True,
                        help_text='Encrypted SSH private key content'
                     )

    # Provisioning
    provisioning_status = models.CharField(
                            max_length=15,
                            choices=ProvisioningStatus.choices,
                            default=ProvisioningStatus.MANUAL,
                          )
    provisioning_log    = models.TextField(blank=True, default='')
    gcp_instance_name   = models.CharField(max_length=100, blank=True)
    gcp_zone            = models.CharField(max_length=50, blank=True)
    gcp_project_id      = models.CharField(max_length=100, blank=True)
    aws_instance_id     = models.CharField(max_length=100, blank=True)
    aws_region          = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Server Configuration'

    def __str__(self):
        return f'{self.name} ({self.public_ip})'

    @property
    def network(self):
        return ipaddress.ip_network(self.vpn_subnet, strict=False)

    @property
    def total_ip_count(self):
        return self.network.num_addresses - 3


class IPAllocation(models.Model):

    class Status(models.TextChoices):
        FREE     = 'free',     'Free'
        ASSIGNED = 'assigned', 'Assigned'
        RESERVED = 'reserved', 'Reserved'

    server     = models.ForeignKey(
                    ServerConfig,
                    on_delete=models.CASCADE,
                    related_name='ip_allocations'
                 )
    ip_address = models.GenericIPAddressField()
    status     = models.CharField(
                    max_length=10,
                    choices=Status.choices,
                    default=Status.FREE
                 )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('server', 'ip_address')
        ordering        = ['ip_address']

    def __str__(self):
        return f'{self.ip_address} ({self.get_status_display()})'
    
class ServerHealthStatus(models.Model):
    server     = models.OneToOneField(ServerConfig, on_delete=models.CASCADE, related_name='health_status')
    is_up      = models.BooleanField(default=True)
    checked_at = models.DateTimeField(auto_now=True)
    alerted_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.server.name} - {"UP" if self.is_up else "DOWN"}'