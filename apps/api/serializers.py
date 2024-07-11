from rest_framework import serializers
from apps.server.models import ServerConfig
from apps.devices.models import Device
from django.contrib.auth import get_user_model

User = get_user_model()


class ServerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServerConfig
        fields = [
            'id', 'name', 'interface_name', 'public_ip', 'listen_port',
            'vpn_subnet', 'server_ip', 'dns_servers', 'mtu',
            'provisioning_status', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'provisioning_status', 'created_at', 'updated_at']


class DeviceSerializer(serializers.ModelSerializer):
    server_name = serializers.CharField(source='server.name', read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Device
        fields = [
            'id', 'name', 'status', 'server', 'server_name',
            'user', 'user_email', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'full_name', 'email', 'is_active', 'is_staff', 'created_at']
        read_only_fields = ['id', 'created_at']