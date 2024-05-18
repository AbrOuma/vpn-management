from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Device
from .forms import DeviceForm, DeviceEditForm
from .services import create_device


@login_required
def device_list(request):
    from apps.server.models import ServerConfig
    from wireguard.commands import ping_peers

    servers = ServerConfig.objects.prefetch_related(
        'devices__user',
        'devices__allocated_ip',
    ).order_by('name')

    # Ping all active devices per server in parallel - ~1 second total
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
            pass  # SSH failure never blocks the page

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


@login_required
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
                messages.success(
                    request,
                    f'Device "{device.name}" created successfully.'
                )
                return redirect('devices:detail', pk=device.pk)
            except ValueError as e:
                messages.error(request, str(e))

    return render(request, 'devices/add.html', {'form': form})


@login_required
def device_detail(request, pk):
    device = get_object_or_404(
        Device.objects.select_related('user', 'allocated_ip'),
        pk=pk
    )
    return render(request, 'devices/detail.html', {'device': device})


@login_required
def device_enable(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        device.status = Device.Status.ACTIVE
        device.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'{device.name} has been enabled.')
    return redirect('devices:detail', pk=pk)


@login_required
def device_disable(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        device.status = Device.Status.DISABLED
        device.save(update_fields=['status', 'updated_at'])
        messages.warning(request, f'{device.name} has been disabled.')
    return redirect('devices:detail', pk=pk)


@login_required
def device_revoke(request, pk):
    device = get_object_or_404(Device, pk=pk)
    if request.method == 'POST':
        device.status = Device.Status.REVOKED
        device.save(update_fields=['status', 'updated_at'])
        messages.error(request, f'{device.name} has been revoked.')
    return redirect('devices:detail', pk=pk)




@login_required
def device_edit(request, pk):
    device = get_object_or_404(Device, pk=pk)
    form   = DeviceEditForm(instance=device)

    if request.method == 'POST':
        form = DeviceEditForm(request.POST, instance=device)
        if form.is_valid():
            form.save()
            messages.success(request, f'{device.name} updated successfully.')
            return redirect('devices:detail', pk=pk)

    return render(request, 'devices/edit.html', {
        'form':   form,
        'device': device,
    })


@login_required
def device_delete(request, pk):
    device = get_object_or_404(Device, pk=pk)

    if request.method == 'POST':
        # Save info before deletion
        device_name       = device.name
        device_public_key = device.public_key
        allocation        = device.allocated_ip

        # Step 1 — Free the IP back to the pool immediately
        from wireguard.ip_allocator import IPAllocator
        from apps.server.models import ServerConfig
        server    = ServerConfig.objects.first()
        allocator = IPAllocator(server)
        allocator.release(allocation)

        # Step 2 — Delete from database immediately
        device.delete()

        # Step 3 — Remove from WireGuard server in background
        # Page returns immediately, this runs behind the scenes
        from .tasks import run_in_background, remove_device_from_server
        from django.conf import settings
        run_in_background(
            remove_device_from_server,
            device_public_key,
            device_name,
            settings.WIREGUARD_INTERFACE,
        )

        messages.success(
            request,
            f'Device "{device_name}" deleted. '
            f'Server is updating in the background.'
        )
        return redirect('devices:list')

    return redirect('devices:detail', pk=pk)