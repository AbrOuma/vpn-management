from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django import forms
from .models import ServerConfig, IPAllocation


class ServerConfigForm(forms.ModelForm):
    ssh_key_file = forms.FileField(
        required=False,
        help_text='Upload your SSH private key file (e.g. gcp_key). '
                  'Leave blank to keep existing key.'
    )

    class Meta:
        model  = ServerConfig
        fields = [
            'name',
            'interface_name',
            'public_ip',
            'listen_port',
            'vpn_subnet',
            'server_ip',
            'address',
            'public_key',
            'private_key',
            'dns_servers',
            'mtu',
            'post_up',
            'post_down',
            'ssh_host',
            'ssh_user',
            'ssh_key_path',
        ]
        widgets = {
            'public_key':  forms.TextInput(),
            'private_key': forms.PasswordInput(render_value=True),
            'post_up':     forms.Textarea(attrs={'rows': 2}),
            'post_down':   forms.Textarea(attrs={'rows': 2}),
        }
        help_texts = {
            'vpn_subnet':   'e.g. 10.0.0.0/24',
            'address':      'Server VPN address with mask e.g. 10.128.10.1/24',
            'server_ip':    'e.g. 10.0.0.1',
            'dns_servers':  'Comma separated e.g. 1.1.1.1,8.8.8.8',
            'private_key':  'WireGuard server private key — will be encrypted',
            'ssh_key_path': 'Fallback path if no key uploaded e.g. gcp_key',
        }


@login_required
def server_list(request):
    servers = ServerConfig.objects.all().order_by('name')
    return render(request, 'server/list.html', {'servers': servers})


@login_required
def server_add(request):
    form = ServerConfigForm()
    if request.method == 'POST':
        form = ServerConfigForm(request.POST, request.FILES)
        if form.is_valid():
            server  = form.save(commit=False)

            # Encrypt WireGuard private key
            raw_key = form.cleaned_data.get('private_key', '')
            if raw_key:
                from wireguard.key_manager import encrypt
                try:
                    server.private_key = encrypt(raw_key)
                except Exception:
                    server.private_key = raw_key

            # Encrypt SSH key if uploaded
            ssh_key_file = form.cleaned_data.get('ssh_key_file')
            if ssh_key_file:
                from wireguard.key_manager import encrypt
                key_content = ssh_key_file.read().decode('utf-8')
                server.ssh_key_encrypted = encrypt(key_content)

            server.save()
            messages.success(request, f'Server "{server.name}" added.')
            return redirect('server:list')
    return render(request, 'server/setup.html', {
        'form':  form,
        'title': 'Add Server',
    })


@login_required
def server_setup(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)
    form   = ServerConfigForm(instance=server)

    if request.method == 'POST':
        form = ServerConfigForm(request.POST, request.FILES, instance=server)
        if form.is_valid():
            server  = form.save(commit=False)

            # Encrypt WireGuard private key
            raw_key = form.cleaned_data.get('private_key', '')
            if raw_key:
                from wireguard.key_manager import encrypt
                try:
                    server.private_key = encrypt(raw_key)
                except Exception:
                    server.private_key = raw_key

            # Encrypt SSH key if uploaded
            ssh_key_file = form.cleaned_data.get('ssh_key_file')
            if ssh_key_file:
                from wireguard.key_manager import encrypt
                key_content = ssh_key_file.read().decode('utf-8')
                server.ssh_key_encrypted = encrypt(key_content)

            server.save()
            messages.success(request, 'Server configuration saved.')
            return redirect('server:overview', pk=pk)

    return render(request, 'server/setup.html', {
        'form':   form,
        'server': server,
        'title':  'Edit Server',
    })


@login_required
def download_ssh_key(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)

    if not server.ssh_key_encrypted:
        messages.error(request, 'No SSH key stored for this server.')
        return redirect('server:overview', pk=pk)

    from wireguard.key_manager import decrypt
    from django.http import HttpResponse

    key_content = decrypt(server.ssh_key_encrypted)
    filename    = f'{server.name.replace(" ", "_")}_ssh_key'
    response    = HttpResponse(key_content, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response



@login_required
def server_overview(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)

    ip_free     = IPAllocation.objects.filter(
                    server=server,
                    status=IPAllocation.Status.FREE
                  ).count()
    ip_assigned = IPAllocation.objects.filter(
                    server=server,
                    status=IPAllocation.Status.ASSIGNED
                  ).count()
    ip_total         = ip_free + ip_assigned
    ip_usage_percent = round((ip_assigned / ip_total) * 100) if ip_total > 0 else 0

    return render(request, 'server/overview.html', {
        'server':           server,
        'ip_free':          ip_free,
        'ip_assigned':      ip_assigned,
        'ip_total':         ip_total,
        'ip_usage_percent': ip_usage_percent,
    })


@login_required
def repopulate_ip_pool(request, pk):
    if request.method == 'POST':
        server = get_object_or_404(ServerConfig, pk=pk)
        from wireguard.ip_allocator import IPAllocator

        deleted = IPAllocation.objects.filter(
            server=server,
            status=IPAllocation.Status.FREE
        ).delete()[0]

        allocator = IPAllocator(server)
        created   = allocator.populate_pool()

        messages.success(
            request,
            f'IP pool updated for {server.vpn_subnet}. '
            f'{deleted} old IPs removed, {created} new IPs added.'
        )

    return redirect('server:overview', pk=pk)


@login_required
def import_preview(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)

    from wireguard.parser import WireGuardConfigParser

    peers        = []
    error        = None
    source_label = None

    if request.FILES.get('config_file'):
        try:
            content      = request.FILES['config_file'].read().decode('utf-8')
            parser       = WireGuardConfigParser()
            config       = parser.parse_string(content)
            peers        = config.peers
            source_label = 'Uploaded file'
            request.session[f'import_config_{pk}'] = content
        except Exception as e:
            error = f'Could not parse file: {e}'

    elif request.GET.get('from_server'):
        try:
            from wireguard.commands import read_server_config
            content      = read_server_config(server.interface_name)
            parser       = WireGuardConfigParser()
            config       = parser.parse_string(content)
            peers        = config.peers
            source_label = f'{server.name} — /etc/wireguard/{server.interface_name}.conf'
            request.session[f'import_config_{pk}'] = content
        except Exception as e:
            error = f'Could not connect to server: {e}'

    from apps.devices.models import Device
    existing_keys = set(
        Device.objects.filter(server=server).values_list('public_key', flat=True)
    )

    new_peers      = [p for p in peers if p.public_key not in existing_keys]
    existing_peers = [p for p in peers if p.public_key in existing_keys]

    return render(request, 'server/import.html', {
        'server':         server,
        'new_peers':      new_peers,
        'existing_peers': existing_peers,
        'source_label':   source_label,
        'error':          error,
    })


@login_required
def import_commit(request, pk):
    if request.method != 'POST':
        return redirect('server:import', pk=pk)

    server  = get_object_or_404(ServerConfig, pk=pk)
    content = request.session.get(f'import_config_{pk}')

    if not content:
        messages.error(request, 'No config found. Please upload the file again.')
        return redirect('server:import', pk=pk)

    from wireguard.parser import WireGuardConfigParser
    from wireguard.ip_allocator import IPAllocator
    from apps.devices.models import Device
    from django.db import transaction

    parser    = WireGuardConfigParser()
    config    = parser.parse_string(content)
    peers     = config.peers
    allocator = IPAllocator(server)

    allocator.populate_pool()

    imported = 0
    skipped  = 0

    with transaction.atomic():
        for peer in peers:
            if not peer.public_key:
                skipped += 1
                continue

            if Device.objects.filter(
                server=server,
                public_key=peer.public_key
            ).exists():
                skipped += 1
                continue

            if peer.ip_address:
                allocation, _ = IPAllocation.objects.get_or_create(
                    server=server,
                    ip_address=peer.ip_address,
                    defaults={'status': IPAllocation.Status.ASSIGNED}
                )
                allocation.status = IPAllocation.Status.ASSIGNED
                allocation.save(update_fields=['status'])
            else:
                try:
                    allocation = allocator.allocate()
                except ValueError:
                    messages.error(request, 'IP pool exhausted.')
                    break

            Device.objects.create(
                server                  = server,
                name                    = f'Imported ({peer.ip_address})',
                device_type             = Device.DeviceType.OTHER,
                public_key              = peer.public_key,
                private_key_encrypted   = '',
                preshared_key_encrypted = '',
                allocated_ip            = allocation,
                status                  = Device.Status.ACTIVE,
                imported                = True,
            )
            imported += 1

    del request.session[f'import_config_{pk}']

    messages.success(
        request,
        f'Import complete — {imported} imported, {skipped} skipped.'
    )
    return redirect('devices:list')


@login_required
def sync_server(request, pk):
    if request.method == 'POST':
        server = get_object_or_404(ServerConfig, pk=pk)
        try:
            from wireguard.manager import WireGuardManager
            WireGuardManager(server).sync_all()
            messages.success(request, 'All devices synced to WireGuard server.')
        except Exception as e:
            messages.error(request, f'Sync failed: {e}')
    return redirect('server:overview', pk=pk)


@login_required
def server_health(request, pk):
    if request.method == 'POST':
        server = get_object_or_404(ServerConfig, pk=pk)
        try:
            from wireguard.commands import wg_is_running, wg_up
            if not wg_is_running(server.interface_name):
                wg_up(server.interface_name)
                messages.success(request, 'WireGuard was down - successfully restarted.')
            else:
                messages.info(request, 'WireGuard is already running.')
        except Exception as e:
            messages.error(request, f'Health check failed: {e}')
    return redirect('server:overview', pk=pk)


@login_required
def server_delete(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)
    if request.method == 'POST':
        name = server.name
        server.delete()
        messages.success(request, f'Server "{name}" deleted.')
        return redirect('server:list')
    return redirect('server:overview', pk=pk)