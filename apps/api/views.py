from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model, authenticate
from django.shortcuts import get_object_or_404

from apps.server.models import ServerConfig
from apps.devices.models import Device
from .serializers import ServerSerializer, DeviceSerializer, UserSerializer
from .permissions import IsAdminUser, IsAdminOrDeviceOwner
from wireguard.manager import WireGuardManager

User = get_user_model()


# Auth

class EmailTokenView(APIView):
    permission_classes = []

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        if not email or not password:
            return Response(
                {'error': 'Email and password required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(request, username=email, password=password)

        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})


# Servers

class ServerListView(generics.ListAPIView):
    serializer_class = ServerSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return ServerConfig.objects.all().order_by('name')


class ServerDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = ServerSerializer
    permission_classes = [IsAdminUser]
    queryset = ServerConfig.objects.all()


class ServerSyncView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        server = get_object_or_404(ServerConfig, pk=pk)
        try:
            manager = WireGuardManager(server)
            manager.sync_all()
            return Response({'status': 'synced'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class ServerHealthView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, pk):
        server = get_object_or_404(ServerConfig, pk=pk)
        try:
            manager = WireGuardManager(server)
            running = manager.is_running()
            updated = manager.refresh_stats() if running else 0
            return Response({
                'running': running,
                'stats_updated': updated,
            })
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


# Devices

class DeviceListView(generics.ListAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [IsAdminOrDeviceOwner]

    def get_queryset(self):
        if self.request.user.is_staff:
            return Device.objects.select_related('server', 'user').all().order_by('name')
        return Device.objects.select_related('server', 'user').filter(
            user=self.request.user
        ).order_by('name')


class DeviceDetailView(generics.RetrieveAPIView):
    serializer_class = DeviceSerializer
    permission_classes = [IsAdminOrDeviceOwner]

    def get_object(self):
        device = get_object_or_404(Device, pk=self.kwargs['pk'])
        if not self.request.user.is_staff and device.user != self.request.user:
            self.permission_denied(self.request)
        return device


class DeviceActionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk, action):
        device = get_object_or_404(Device, pk=pk)
        try:
            manager = WireGuardManager(device.server)
            if action == 'enable':
                device.status = Device.Status.ACTIVE
                device.save()
                manager.sync_all()
            elif action == 'disable':
                device.status = Device.Status.DISABLED
                device.save()
                manager.sync_all()
            elif action == 'revoke':
                device.status = Device.Status.REVOKED
                device.save()
                manager.remove_device(device)
            else:
                return Response({'error': 'Unknown action'}, status=status.HTTP_400_BAD_REQUEST)
            return Response({'status': device.status})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_502_BAD_GATEWAY)


class DeviceConfigView(APIView):
    permission_classes = [IsAdminOrDeviceOwner]

    def get(self, request, pk):
        device = get_object_or_404(Device, pk=pk)
        if not request.user.is_staff and device.user != request.user:
            return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)
        try:
            from apps.invites.services import generate_client_config
            config_text = generate_client_config(device)
            return Response({'config': config_text})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Users 

class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    queryset = User.objects.all().order_by('email')


class UserDetailView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    queryset = User.objects.all()


class UserActionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk, action):
        user = get_object_or_404(User, pk=pk)

        if user.pk == request.user.pk and action == 'suspend':
            return Response(
                {'error': 'You cannot suspend your own account.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if action == 'suspend':
            user.is_active = False
            user.save()
            return Response({'status': 'suspended'})
        elif action == 'activate':
            user.is_active = True
            user.save()
            return Response({'status': 'activated'})
        return Response({'error': 'Unknown action'}, status=status.HTTP_400_BAD_REQUEST)