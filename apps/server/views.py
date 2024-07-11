from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django import forms
from .models import ServerConfig, IPAllocation
from apps.accounts.decorators import staff_required, write_required


class ServerConfigForm(forms.ModelForm):
    ssh_key_file = forms.FileField(
        required=False,
        label='SSH Private Key',
        help_text='Upload your SSH private key file e.g. gcp_key'
    )
    private_key_input = forms.CharField(
        required=False,
        label='WireGuard Private Key',
        widget=forms.PasswordInput(
            attrs={'placeholder': 'Leave blank to keep existing key'}
        ),
        help_text='WireGuard server private key - will be encrypted'
    )

    class Meta:
        model  = ServerConfig
        fields = [
            'name', 'interface_name', 'public_ip', 'listen_port',
            'vpn_subnet', 'server_ip', 'address', 'public_key',
            'dns_servers', 'mtu', 'post_up', 'post_down',
            'ssh_host', 'ssh_user',
        ]
        labels = {
            'name':           'Server Name',
            'interface_name': 'Interface Name',
            'public_ip':      'Public IP',
            'listen_port':    'Listen Port',
            'vpn_subnet':     'VPN Subnet',
            'server_ip':      'Server VPN IP',
            'address':        'VPN Address',
            'public_key':     'Public Key',
            'dns_servers':    'DNS Servers',
            'mtu':            'MTU',
            'post_up':        'Post Up',
            'post_down':      'Post Down',
            'ssh_host':       'SSH Host',
            'ssh_user':       'SSH User',
        }
        widgets = {
            'public_key': forms.TextInput(),
            'post_up':    forms.Textarea(attrs={'rows': 2}),
            'post_down':  forms.Textarea(attrs={'rows': 2}),
        }
        help_texts = {
            'vpn_subnet':  'e.g. 10.0.0.0/24',
            'address':     'Server VPN address with mask e.g. 10.128.10.1/24',
            'server_ip':   'e.g. 10.0.0.1',
            'dns_servers': 'Comma separated e.g. 1.1.1.1,8.8.8.8',
            'mtu':         'Default is 1420',
        }


class ProvisionExistingForm(forms.Form):
    name           = forms.CharField(max_length=100, label='Server Name', help_text='A friendly name e.g. GCP Primary')
    ssh_host       = forms.CharField(max_length=255, label='VM IP Address', help_text='External IP of your VM')
    ssh_user       = forms.CharField(max_length=100, label='SSH User', initial='electrical', help_text='SSH user on the VM')
    ssh_key_file   = forms.FileField(label='SSH Private Key', help_text='Upload your SSH private key file')
    interface_name = forms.CharField(max_length=15, label='Interface Name', initial='wg0')
    listen_port    = forms.IntegerField(label='Listen Port', initial=51820)
    vpn_subnet     = forms.CharField(max_length=20, label='VPN Subnet', initial='10.0.0.0/24', help_text='e.g. 10.0.0.0/24')
    server_ip      = forms.CharField(max_length=20, label='Server IP', initial='10.0.0.1', help_text='e.g. 10.0.0.1')
    address        = forms.CharField(max_length=20, label='VPN Address', initial='10.0.0.1/24', help_text='e.g. 10.0.0.1/24')
    dns_servers    = forms.CharField(max_length=100, label='DNS Servers', initial='1.1.1.1,8.8.8.8', help_text='Comma separated e.g. 1.1.1.1,8.8.8.8')
    mtu            = forms.IntegerField(label='MTU', initial=1420)


GCP_ZONES = [
    ('us-central1-a',       'us-central1-a (Iowa)'),
    ('us-east1-b',          'us-east1-b (South Carolina)'),
    ('us-west1-a',          'us-west1-a (Oregon)'),
    ('europe-west1-b',      'europe-west1-b (Belgium)'),
    ('europe-west2-a',      'europe-west2-a (London)'),
    ('asia-east1-a',        'asia-east1-a (Taiwan)'),
    ('asia-southeast1-a',   'asia-southeast1-a (Singapore)'),
    ('africa-south1-a',     'africa-south1-a (Johannesburg)'),
    ('me-central1-a',       'me-central1-a (Doha)'),
]

GCP_MACHINE_TYPES = [
    ('e2-micro',      'e2-micro (free tier eligible, 1 vCPU, 1 GB)'),
    ('e2-small',      'e2-small (1 vCPU, 2 GB)'),
    ('e2-medium',     'e2-medium (1 vCPU, 4 GB)'),
    ('n1-standard-1', 'n1-standard-1 (1 vCPU, 3.75 GB)'),
]


class ProvisionGCPForm(forms.Form):
    name                 = forms.CharField(max_length=100, label='Server Name', help_text='A friendly name e.g. GCP US East')
    gcp_project_id       = forms.CharField(max_length=100, label='GCP Project ID', help_text='Found in GCP Console > Project Info')
    gcp_zone             = forms.ChoiceField(choices=GCP_ZONES, label='Zone')
    machine_type         = forms.ChoiceField(choices=GCP_MACHINE_TYPES, label='Machine Type')
    service_account_json = forms.FileField(label='Service Account JSON Key', help_text='Download from GCP > IAM > Service Accounts')
    ssh_user             = forms.CharField(max_length=100, label='SSH User', initial='wireguard', help_text='SSH user Django will create on the VM')
    interface_name       = forms.CharField(max_length=15, label='Interface Name', initial='wg0')
    listen_port          = forms.IntegerField(label='Listen Port', initial=51820)
    vpn_subnet           = forms.CharField(max_length=20, label='VPN Subnet', initial='10.0.0.0/24')
    server_ip            = forms.CharField(max_length=20, label='Server IP', initial='10.0.0.1')
    address              = forms.CharField(max_length=20, label='VPN Address', initial='10.0.0.1/24')
    dns_servers          = forms.CharField(max_length=100, label='DNS Servers', initial='1.1.1.1,8.8.8.8')
    mtu                  = forms.IntegerField(label='MTU', initial=1420)


# Standard server views

@staff_required
def server_list(request):
    servers = ServerConfig.objects.all().order_by('name')
    return render(request, 'server/list.html', {'servers': servers})


@staff_required
@write_required
def server_add(request):
    form = ServerConfigForm()
    if request.method == 'POST':
        form = ServerConfigForm(request.POST, request.FILES)
        if form.is_valid():
            server  = form.save(commit=False)
            raw_key = form.cleaned_data.get('private_key_input', '')
            if raw_key:
                from wireguard.key_manager import encrypt
                try:
                    server.private_key = encrypt(raw_key)
                except Exception:
                    server.private_key = raw_key
            ssh_key_file = form.cleaned_data.get('ssh_key_file')
            if ssh_key_file:
                from wireguard.key_manager import encrypt
                server.ssh_key_encrypted = encrypt(ssh_key_file.read().decode('utf-8'))
            server.save()
            messages.success(request, f'Server "{server.name}" added.')
            return redirect('server:list')
    return render(request, 'server/setup.html', {'form': form, 'title': 'Add Server'})


@staff_required
@write_required
def server_setup(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)
    form   = ServerConfigForm(instance=server)

    if request.method == 'POST':
        form = ServerConfigForm(request.POST, request.FILES, instance=server)
        if form.is_valid():
            server  = form.save(commit=False)
            raw_key = form.cleaned_data.get('private_key_input', '')
            if raw_key:
                from wireguard.key_manager import encrypt
                try:
                    server.private_key = encrypt(raw_key)
                except Exception:
                    server.private_key = raw_key
            ssh_key_file = form.cleaned_data.get('ssh_key_file')
            if ssh_key_file:
                from wireguard.key_manager import encrypt
                server.ssh_key_encrypted = encrypt(ssh_key_file.read().decode('utf-8'))
            server.save()
            messages.success(request, 'Server configuration saved.')
            return redirect('server:overview', pk=pk)

    return render(request, 'server/setup.html', {
        'form': form, 'server': server, 'title': 'Edit Server',
    })


@staff_required
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


@staff_required
def server_overview(request, pk):
    server           = get_object_or_404(ServerConfig, pk=pk)
    ip_free          = IPAllocation.objects.filter(server=server, status=IPAllocation.Status.FREE).count()
    ip_assigned      = IPAllocation.objects.filter(server=server, status=IPAllocation.Status.ASSIGNED).count()
    ip_total         = ip_free + ip_assigned
    ip_usage_percent = round((ip_assigned / ip_total) * 100) if ip_total > 0 else 0

    return render(request, 'server/overview.html', {
        'server':           server,
        'ip_free':          ip_free,
        'ip_assigned':      ip_assigned,
        'ip_total':         ip_total,
        'ip_usage_percent': ip_usage_percent,
    })


@staff_required
@write_required
def repopulate_ip_pool(request, pk):
    if request.method == 'POST':
        server    = get_object_or_404(ServerConfig, pk=pk)
        from wireguard.ip_allocator import IPAllocator
        deleted   = IPAllocation.objects.filter(server=server, status=IPAllocation.Status.FREE).delete()[0]
        allocator = IPAllocator(server)
        created   = allocator.populate_pool()
        messages.success(request, f'IP pool updated. {deleted} removed, {created} added.')
    return redirect('server:overview', pk=pk)


@staff_required
def import_preview(request, pk):
    server       = get_object_or_404(ServerConfig, pk=pk)
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
            content      = read_server_config(server, server.interface_name)
            parser       = WireGuardConfigParser()
            config       = parser.parse_string(content)
            peers        = config.peers
            source_label = f'{server.name} - /etc/wireguard/{server.interface_name}.conf'
            request.session[f'import_config_{pk}'] = content
        except Exception as e:
            error = f'Could not connect to server: {e}'

    from apps.devices.models import Device
    existing_keys  = set(Device.objects.filter(server=server).values_list('public_key', flat=True))
    new_peers      = [p for p in peers if p.public_key not in existing_keys]
    existing_peers = [p for p in peers if p.public_key in existing_keys]

    return render(request, 'server/import.html', {
        'server':         server,
        'new_peers':      new_peers,
        'existing_peers': existing_peers,
        'source_label':   source_label,
        'error':          error,
    })


@staff_required
@write_required
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
            if Device.objects.filter(server=server, public_key=peer.public_key).exists():
                skipped += 1
                continue
            if peer.ip_address:
                allocation, _ = IPAllocation.objects.get_or_create(
                    server=server, ip_address=peer.ip_address,
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
                server=server,
                name=f'Imported ({peer.ip_address})',
                device_type=Device.DeviceType.OTHER,
                public_key=peer.public_key,
                private_key_encrypted='',
                preshared_key_encrypted='',
                allocated_ip=allocation,
                status=Device.Status.ACTIVE,
                imported=True,
            )
            imported += 1

    del request.session[f'import_config_{pk}']
    messages.success(request, f'Import complete - {imported} imported, {skipped} skipped.')
    return redirect('devices:list')


@staff_required
@write_required
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


@staff_required
@write_required
def server_health(request, pk):
    if request.method == 'POST':
        server = get_object_or_404(ServerConfig, pk=pk)
        try:
            from wireguard.commands import wg_is_running, wg_up
            if not wg_is_running(server, server.interface_name):
                wg_up(server, server.interface_name)
                messages.success(request, 'WireGuard was down - successfully restarted.')
            else:
                messages.info(request, 'WireGuard is already running.')
        except Exception as e:
            messages.error(request, f'Health check failed: {e}')
    return redirect('server:overview', pk=pk)


@staff_required
@write_required
def server_delete(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)
    if request.method == 'POST':
        from apps.devices.models import Device
        name = server.name
        Device.objects.filter(server=server).delete()
        IPAllocation.objects.filter(server=server).delete()
        server.delete()
        messages.success(request, f'Server "{name}" removed from database. GCP VM is untouched.')
        return redirect('server:list')
    return redirect('server:overview', pk=pk)


@staff_required
@write_required
def server_wipe_peers(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)
    if request.method == 'POST':
        from apps.devices.models import Device
        from wireguard.commands import wipe_all_peers
        name = server.name
        try:
            removed = wipe_all_peers(server, server.interface_name)
        except Exception as e:
            messages.error(request, f'Could not wipe peers from VM: {e}')
            return redirect('server:overview', pk=pk)
        Device.objects.filter(server=server).delete()
        IPAllocation.objects.filter(server=server).delete()
        server.delete()
        messages.success(request, f'Server "{name}" deleted. {removed} peers wiped from WireGuard on the VM.')
        return redirect('server:list')
    return redirect('server:overview', pk=pk)


@staff_required
@write_required
def server_destroy_vm(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)
    if request.method == 'POST':
        if not server.gcp_instance_name or not server.gcp_zone or not server.gcp_project_id:
            messages.error(request, 'This server has no GCP instance details. Use "Remove from Database" instead.')
            return redirect('server:overview', pk=pk)

        sa_json_file = request.FILES.get('sa_json_file')
        if not sa_json_file:
            messages.error(request, 'Service account JSON file is required to destroy the VM.')
            return redirect('server:overview', pk=pk)

        from apps.devices.models import Device
        from wireguard.provisioner import WireGuardProvisioner
        name        = server.name
        sa_json_str = sa_json_file.read().decode('utf-8')
        try:
            WireGuardProvisioner(server).destroy_gcp_vm(
                project_id=server.gcp_project_id,
                zone=server.gcp_zone,
                instance_name=server.gcp_instance_name,
                sa_json_str=sa_json_str,
            )
        except Exception as e:
            messages.error(request, f'Failed to destroy VM: {e}')
            return redirect('server:overview', pk=pk)

        Device.objects.filter(server=server).delete()
        IPAllocation.objects.filter(server=server).delete()
        server.delete()
        messages.success(request, f'Server "{name}" and its GCP VM have been permanently destroyed.')
        return redirect('server:list')
    return redirect('server:overview', pk=pk)


# Provisioning views

@staff_required
@write_required
def create_choice(request):
    return render(request, 'server/create_choice.html')


@staff_required
@write_required
def provision_existing(request):
    form = ProvisionExistingForm()
    if request.method == 'POST':
        form = ProvisionExistingForm(request.POST, request.FILES)
        if form.is_valid():
            from wireguard.key_manager import encrypt
            from wireguard.provisioner import WireGuardProvisioner
            data = form.cleaned_data

            server = ServerConfig.objects.create(
                name=data['name'],
                public_ip=data['ssh_host'],
                ssh_host=data['ssh_host'],
                ssh_user=data['ssh_user'],
                interface_name=data['interface_name'],
                listen_port=data['listen_port'],
                vpn_subnet=data['vpn_subnet'],
                server_ip=data['server_ip'],
                address=data['address'],
                dns_servers=data['dns_servers'],
                mtu=data['mtu'],
                provisioning_status='provisioning',
                provisioning_log='',
            )

            ssh_key_file = data.get('ssh_key_file')
            if ssh_key_file:
                server.ssh_key_encrypted = encrypt(ssh_key_file.read().decode('utf-8'))
                server.save(update_fields=['ssh_key_encrypted'])

            WireGuardProvisioner(server).start_provision_existing_vm()
            return redirect('server:provisioning_progress', pk=server.pk)

    return render(request, 'server/provision_existing.html', {'form': form})


@staff_required
@write_required
def provision_gcp(request):
    form = ProvisionGCPForm()
    if request.method == 'POST':
        form = ProvisionGCPForm(request.POST, request.FILES)
        if form.is_valid():
            from wireguard.provisioner import WireGuardProvisioner
            data = form.cleaned_data

            server = ServerConfig.objects.create(
                name=data['name'],
                ssh_user=data['ssh_user'],
                interface_name=data['interface_name'],
                listen_port=data['listen_port'],
                vpn_subnet=data['vpn_subnet'],
                server_ip=data['server_ip'],
                address=data['address'],
                dns_servers=data['dns_servers'],
                mtu=data['mtu'],
                gcp_project_id=data['gcp_project_id'],
                gcp_zone=data['gcp_zone'],
                provisioning_status='provisioning',
                provisioning_log='',
            )

            sa_json_str = data['service_account_json'].read().decode('utf-8')
            WireGuardProvisioner(server).start_provision_gcp_vm(
                project_id=data['gcp_project_id'],
                zone=data['gcp_zone'],
                machine_type=data['machine_type'],
                sa_json_str=sa_json_str,
            )
            return redirect('server:provisioning_progress', pk=server.pk)

    return render(request, 'server/provision_gcp.html', {'form': form})


@staff_required
def provisioning_progress(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)
    return render(request, 'server/provisioning_progress.html', {'server': server})


@staff_required
def ajax_provisioning_status(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)
    return JsonResponse({
        'status': server.provisioning_status,
        'log':    server.provisioning_log,
    })


# AJAX endpoints

@staff_required
@write_required
@require_POST
def ajax_sync(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)
    try:
        from wireguard.manager import WireGuardManager
        WireGuardManager(server).sync_all()
        return JsonResponse({'status': 'ok', 'message': 'All devices synced successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@staff_required
@write_required
@require_POST
def ajax_health(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)
    try:
        from wireguard.commands import wg_is_running, wg_up
        if not wg_is_running(server, server.interface_name):
            wg_up(server, server.interface_name)
            return JsonResponse({'status': 'ok', 'message': 'WireGuard was down - restarted successfully.'})
        return JsonResponse({'status': 'ok', 'message': 'WireGuard is already running.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


@staff_required
@write_required
@require_POST
def ajax_repopulate(request, pk):
    server = get_object_or_404(ServerConfig, pk=pk)
    try:
        from wireguard.ip_allocator import IPAllocator
        deleted     = IPAllocation.objects.filter(server=server, status=IPAllocation.Status.FREE).delete()[0]
        allocator   = IPAllocator(server)
        created     = allocator.populate_pool()
        ip_free     = IPAllocation.objects.filter(server=server, status=IPAllocation.Status.FREE).count()
        ip_assigned = IPAllocation.objects.filter(server=server, status=IPAllocation.Status.ASSIGNED).count()
        return JsonResponse({
            'status':      'ok',
            'message':     f'{deleted} old IPs removed, {created} new IPs added.',
            'ip_free':     ip_free,
            'ip_assigned': ip_assigned,
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)