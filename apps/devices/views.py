from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Device
from .forms import DeviceForm, DeviceEditForm
from .services import create_device
from apps.accounts.decorators import staff_required, write_required
from apps.accounts.utils import log_action
from django.views.decorators.http import require_POST
from django.http import JsonResponse



@staff_required
def device_list(request):
    from apps.server.models import ServerConfig
    from wireguard.commands import ping_peers

    servers = ServerConfig.objects.prefetch_related(
        'devices__user',
        'devices__allocated_ip',
    ).order_by('name')

    online_ips = set()
    for server in servers:
        try:
            ip_list = [
                d.ip_address
                for d in server.devices.filter(status='active')
                if d.ip_address
            ]
            results    = ping_peers(server, ip_list)
            online_ips.update(ip for ip, up in results.items() if up)
        except Exception:
            pass

    total_devices  = Device.objects.count()
    active_count   = Device.objects.filter(status=Device.Status.ACTIVE).count()
    disabled_count = Device.objects.filter(status=Device.Status.DISABLED).count()
    online_count   = len(online_ips)

    return render(request, 'devices/list.html', {
        'servers':        servers,
        'online_ips':     online_ips,
        'total_devices':  total_devices,
        'online_count':   online_count,
        'active_count':   active_count,
        'disabled_count': disabled_count,
    })


@staff_required
@write_required
def device_add(request):
    form = DeviceForm()

    if request.method == 'POST':
        form = DeviceForm(request.POST)
        if form.is_valid():
            try:
                device = create_device(
                    name        = form.cleaned_data['name'],
                    device_type = form.cleaned_data['device_type'],
                    server      = form.cleaned_data['server'],
                    user        = form.cleaned_data['user'],
                    base_url    = request.build_absolute_uri('/').rstrip('/'),
                )
                log_action(request, 'Device Created', device.name, f'Server: {device.server.name}')
                messages.success(request, f'Device "{device.name}" created successfully.')
                if not form.cleaned_data.get('user'):
                    messages.warning(request, 'No user assigned - invite email was not sent. Assign a user to send the invite.')
                return redirect('devices:detail', pk=device.pk)
            except ValueError as e:
                messages.error(request, str(e))

    return render(request, 'devices/add.html', {'form': form})


@staff_required
def device_detail(request, pk):
    device = get_object_or_404(
        Device.objects.select_related('user', 'allocated_ip'),
        pk=pk
    )

    traffic = None
    try:
        from wireguard.commands import wg_show_dump, parse_wg_dump
        dump   = wg_show_dump(device.server, device.server.interface_name)
        peers  = parse_wg_dump(dump)
        traffic = peers.get(device.public_key)
    except Exception:
        pass

    return render(request, 'devices/detail.html', {
        'device':  device,
        'traffic': traffic,
    })

@staff_required
def device_traffic(request, pk):
    device = get_object_or_404(Device, pk=pk)
    try:
        from wireguard.commands import wg_show_dump, parse_wg_dump
        dump    = wg_show_dump(device.server, device.server.interface_name)
        peers   = parse_wg_dump(dump)
        data    = peers.get(device.public_key)
        if data:
            lh = data['last_handshake']
            return JsonResponse({
                'bytes_received':    data['bytes_received'],
                'bytes_sent':        data['bytes_sent'],
                'last_handshake_ts': int(lh.timestamp()) if lh else None,
                'endpoint':          data['endpoint'] or 'Not connected',
            })
    except Exception:
        pass
    return JsonResponse({'error': 'unavailable'})


@staff_required
@write_required
def device_enable(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        device.status = Device.Status.ACTIVE
        device.save(update_fields=['status', 'updated_at'])
        log_action(request, 'Device Enabled', device.name)
        messages.success(request, f'{device.name} has been enabled.')
    return redirect('devices:detail', pk=pk)


@staff_required
@write_required
def device_disable(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        device.status = Device.Status.DISABLED
        device.save(update_fields=['status', 'updated_at'])
        log_action(request, 'Device Disabled', device.name)
        messages.warning(request, f'{device.name} has been disabled.')
    return redirect('devices:detail', pk=pk)


@staff_required
@write_required
def device_revoke(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        device.status = Device.Status.REVOKED
        device.save(update_fields=['status', 'updated_at'])
        log_action(request, 'Device Revoked', device.name)
        messages.error(request, f'{device.name} has been revoked.')
    return redirect('devices:detail', pk=pk)


@staff_required
@write_required
def device_edit(request, pk):
    device = get_object_or_404(Device, pk=pk)
    form   = DeviceEditForm(instance=device)

    if request.method == 'POST':
        form = DeviceEditForm(request.POST, instance=device)
        if form.is_valid():
            form.save()
            log_action(request, 'Device Updated', device.name)
            messages.success(request, f'{device.name} updated successfully.')
            return redirect('devices:detail', pk=pk)

    return render(request, 'devices/edit.html', {
        'form':   form,
        'device': device,
    })


@staff_required
@write_required
def device_delete(request, pk):
    device = get_object_or_404(Device, pk=pk)

    if request.method == 'POST':
        device_name = device.name
        allocation  = device.allocated_ip
        server      = device.server

        from wireguard.ip_allocator import IPAllocator
        IPAllocator(server).release(allocation)

        log_action(request, 'Device Deleted', device_name, f'Server: {server.name}')
        device.delete()

        try:
            from wireguard.manager import WireGuardManager
            WireGuardManager(server).sync_all()
        except Exception as e:
            messages.warning(request, f'Device deleted but server sync failed: {e}')
            return redirect('devices:list')

        messages.success(request, f'Device "{device_name}" deleted.')
        return redirect('devices:list')

    return redirect('devices:detail', pk=pk)


@staff_required
@write_required
@require_POST
def device_bulk_action(request):
    import json
    action     = request.POST.get('action')
    device_ids = request.POST.getlist('device_ids')

    if not action or not device_ids:
        return JsonResponse({'error': 'No action or devices selected.'}, status=400)

    valid_actions = ['enable', 'disable', 'revoke']
    if action not in valid_actions:
        return JsonResponse({'error': 'Invalid action.'}, status=400)

    devices = Device.objects.filter(pk__in=device_ids)
    count   = devices.count()

    if action == 'enable':
        devices.update(status=Device.Status.ACTIVE)
        log_action(request, 'Bulk Enable', f'{count} devices')
    elif action == 'disable':
        devices.update(status=Device.Status.DISABLED)
        log_action(request, 'Bulk Disable', f'{count} devices')
    elif action == 'revoke':
        devices.update(status=Device.Status.REVOKED)
        log_action(request, 'Bulk Revoke', f'{count} devices')

    # Return updated statuses so the page can update badges in place
    updated = {
        str(d.pk): d.status
        for d in Device.objects.filter(pk__in=device_ids)
    }

    return JsonResponse({'status': 'ok', 'count': count, 'action': action, 'updated': updated})


@staff_required
def device_status_poll(request):
    from apps.server.models import ServerConfig
    from wireguard.commands import ping_peers

    servers = ServerConfig.objects.prefetch_related('devices__allocated_ip').all()

    online_ips = set()
    for server in servers:
        try:
            ip_list = [
                d.ip_address
                for d in server.devices.filter(status='active')
                if d.ip_address
            ]
            results = ping_peers(server, ip_list)
            online_ips.update(ip for ip, up in results.items() if up)
        except Exception:
            pass

    devices_data = {}
    for server in servers:
        for device in server.devices.all():
            status = device.status
            if status == 'active' and device.ip_address in online_ips:
                display = 'online'
            else:
                display = status
            devices_data[str(device.pk)] = display

    total    = sum(len(list(s.devices.all())) for s in servers)
    active   = sum(1 for v in devices_data.values() if v in ('active', 'online'))
    disabled = sum(1 for v in devices_data.values() if v == 'disabled')
    online   = sum(1 for v in devices_data.values() if v == 'online')

    return JsonResponse({
        'devices':  devices_data,
        'total':    total,
        'active':   active,
        'disabled': disabled,
        'online':   online,
    })