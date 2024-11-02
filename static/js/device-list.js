(function () {
    // BULK_URL, POLL_URL, and CSRF are injected inline by the template
    const input      = document.getElementById('deviceSearch');
    const countEl    = document.getElementById('searchCount');
    const noResults  = document.getElementById('noResults');
    const toolbar    = document.getElementById('bulkToolbar');
    const countLabel = document.getElementById('selectedCount');
    const clearBtn   = document.getElementById('clearSelection');
    const pollDot    = document.getElementById('poll-dot');
    const pollLabel  = document.getElementById('poll-label');

    // Status badge helper
    function statusBadge(status) {
        if (status === 'online')   return '<span class="badge bg-success">Online</span>';
        if (status === 'active')   return '<span class="badge bg-secondary">Active</span>';
        if (status === 'disabled') return '<span class="badge bg-warning text-dark">Disabled</span>';
        if (status === 'revoked')  return '<span class="badge bg-danger">Revoked</span>';
        return '';
    }

    // Live polling
    function poll() {
        fetch(window.POLL_URL)
            .then(r => r.json())
            .then(data => {
                document.getElementById('stat-total').textContent    = data.total;
                document.getElementById('stat-online').textContent   = data.online;
                document.getElementById('stat-active').textContent   = data.active;
                document.getElementById('stat-disabled').textContent = data.disabled;

                Object.entries(data.devices).forEach(([pk, status]) => {
                    const row = document.querySelector(`.device-row[data-id="${pk}"]`);
                    if (row) row.querySelector('.status-cell').innerHTML = statusBadge(status);
                });

                pollDot.style.background = '#10b981';
                pollLabel.textContent    = 'Live';
            })
            .catch(() => {
                pollDot.style.background = '#ef4444';
                pollLabel.textContent    = 'Offline';
            });
    }

    poll();
    setInterval(poll, 20000);

    // Search
    input.addEventListener('input', function () {
        const q = this.value.trim().toLowerCase();
        if (!q) {
            document.querySelectorAll('.device-row').forEach(r => r.style.display = '');
            document.querySelectorAll('.server-section').forEach(s => s.style.display = '');
            countEl.classList.add('d-none');
            noResults.classList.add('d-none');
            return;
        }
        let totalVisible = 0;
        document.querySelectorAll('.server-section').forEach(section => {
            const rows     = section.querySelectorAll('.device-row');
            const collapse = section.querySelector('.collapse');
            const badge    = section.querySelector('[id^="badge-"]');
            let sectionVisible = 0;
            rows.forEach(row => {
                const match =
                    (row.dataset.name || '').includes(q) ||
                    (row.dataset.user || '').includes(q) ||
                    (row.dataset.ip   || '').includes(q) ||
                    (row.dataset.type || '').includes(q);
                row.style.display = match ? '' : 'none';
                if (match) sectionVisible++;
            });
            if (sectionVisible > 0) {
                section.style.display = '';
                collapse.classList.add('show');
                totalVisible += sectionVisible;
            } else {
                section.style.display = 'none';
            }
            if (badge) badge.textContent = sectionVisible;
        });
        countEl.textContent = `${totalVisible} device${totalVisible !== 1 ? 's' : ''} found`;
        countEl.classList.remove('d-none');
        noResults.classList.toggle('d-none', totalVisible > 0);
    });

    // Selection
    function getChecked() {
        return document.querySelectorAll('.device-checkbox:checked');
    }

    function updateToolbar() {
        const count = getChecked().length;
        if (count > 0) {
            toolbar.classList.remove('d-none');
            countLabel.textContent = `${count} selected`;
        } else {
            toolbar.classList.add('d-none');
        }
    }

    document.querySelectorAll('.device-checkbox').forEach(cb => {
        cb.addEventListener('change', updateToolbar);
    });

    document.querySelectorAll('.select-all-server').forEach(selectAll => {
        selectAll.addEventListener('change', function () {
            const serverPk = this.dataset.server;
            document.querySelectorAll(`.device-checkbox[data-server="${serverPk}"]`)
                .forEach(cb => {
                    const row = cb.closest('tr');
                    if (!row || row.style.display !== 'none') cb.checked = this.checked;
                });
            updateToolbar();
        });
    });

    clearBtn.addEventListener('click', function () {
        document.querySelectorAll('.device-checkbox, .select-all-server')
            .forEach(cb => cb.checked = false);
        updateToolbar();
    });

    // Bulk modal
    let pendingAction = null;
    let pendingIds    = [];

    window.openBulkModal = function (action) {
        const checked = getChecked();
        const count   = checked.length;
        pendingAction = action;
        pendingIds    = Array.from(checked).map(cb => cb.value);

        const config = {
            enable: {
                title:    'Enable Devices',
                body:     `Enable <strong>${count} device(s)</strong>? They will be re-added to the VPN server and users will regain access.`,
                btnClass: 'btn-success',
                btnText:  '<i class="bi bi-play-circle me-1"></i>Enable',
            },
            disable: {
                title:    'Disable Devices',
                body:     `Disable <strong>${count} device(s)</strong>? Users will lose VPN access immediately. You can re-enable them at any time.`,
                btnClass: 'btn-warning',
                btnText:  '<i class="bi bi-pause-circle me-1"></i>Disable',
            },
            revoke: {
                title:    'Revoke Devices',
                body:     `Revoke <strong>${count} device(s)</strong>?<div class="alert alert-danger mt-3 mb-0"><i class="bi bi-exclamation-triangle me-2"></i>Revoking is permanent. Devices will be blocked and cannot be re-enabled.</div>`,
                btnClass: 'btn-danger',
                btnText:  '<i class="bi bi-x-circle me-1"></i>Revoke',
            },
        };

        const c = config[action];
        document.getElementById('bulkModalTitle').textContent = c.title;
        document.getElementById('bulkModalBody').innerHTML    = c.body;
        const confirmBtn     = document.getElementById('bulkConfirmBtn');
        confirmBtn.className = `btn ${c.btnClass}`;
        confirmBtn.innerHTML = c.btnText;

        new bootstrap.Modal(document.getElementById('bulkModal')).show();
    };

    document.getElementById('bulkConfirmBtn').addEventListener('click', function () {
        if (!pendingAction || pendingIds.length === 0) return;

        const btn          = this;
        const originalHTML = btn.innerHTML;
        btn.disabled  = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Processing...';

        const formData = new FormData();
        formData.append('csrfmiddlewaretoken', window.CSRF);
        formData.append('action', pendingAction);
        pendingIds.forEach(id => formData.append('device_ids', id));

        fetch(window.BULK_URL, { method: 'POST', body: formData })
            .then(r => r.json())
            .then(data => {
                if (data.error) { alert(data.error); return; }

                Object.entries(data.updated).forEach(([pk, status]) => {
                    const row = document.querySelector(`.device-row[data-id="${pk}"]`);
                    if (row) {
                        row.querySelector('.status-cell').innerHTML = statusBadge(status.toLowerCase());
                        row.querySelector('.device-checkbox').checked = false;
                    }
                });

                bootstrap.Modal.getInstance(document.getElementById('bulkModal')).hide();
                document.querySelectorAll('.select-all-server').forEach(cb => cb.checked = false);
                updateToolbar();
                poll();

                pendingAction = null;
                pendingIds    = [];
            })
            .catch(() => alert('Something went wrong. Please try again.'))
            .finally(() => {
                btn.disabled  = false;
                btn.innerHTML = originalHTML;
            });
    });
})();