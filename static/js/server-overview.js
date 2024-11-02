// CSRF and REPOPULATE_URL are injected inline by the template via window

(function () {
    const resultBanner         = document.getElementById('actionResult');
    const repopulateConfirmBtn = document.getElementById('repopulateConfirmBtn');

    function showResult(message, isError) {
        resultBanner.className   = 'alert mb-3 ' + (isError ? 'alert-danger' : 'alert-success');
        resultBanner.textContent = message;
        resultBanner.classList.remove('d-none');
        setTimeout(() => resultBanner.classList.add('d-none'), 6000);
    }

    function updatePool(data) {
        if (data.ip_free === undefined) return;
        const total   = data.ip_free + data.ip_assigned;
        const percent = total > 0 ? Math.round((data.ip_assigned / total) * 100) : 0;
        document.querySelector('.ip-free').textContent     = data.ip_free;
        document.querySelector('.ip-assigned').textContent = data.ip_assigned;
        document.querySelector('.ip-total').textContent    = total;
        document.querySelector('.ip-percent').textContent  = percent + '% of pool in use';
        const bar = document.querySelector('.progress-bar');
        if (bar) bar.style.width = percent + '%';
    }

    async function runAjax(url, btn) {
        const spinner = btn.querySelector('.spinner');
        const icon    = btn.querySelector('.btn-icon');
        if (spinner) spinner.classList.remove('d-none');
        if (icon)    icon.classList.add('d-none');
        btn.disabled = true;

        try {
            const response = await fetch(url, {
                method:  'POST',
                headers: {
                    'X-CSRFToken': window.CSRF,
                    'Content-Type': 'application/json',
                },
            });
            const data = await response.json();
            showResult(data.message, data.status !== 'ok');
            updatePool(data);
        } catch (err) {
            showResult('Request failed - ' + err.message, true);
        } finally {
            if (spinner) spinner.classList.add('d-none');
            if (icon)    icon.classList.remove('d-none');
            btn.disabled = false;
        }
    }

    document.querySelectorAll('.ajax-action').forEach(btn => {
        btn.addEventListener('click', function () {
            runAjax(this.dataset.url, this);
        });
    });

    repopulateConfirmBtn.addEventListener('click', function () {
        const modal = bootstrap.Modal.getInstance(
            document.getElementById('repopulateConfirmModal')
        );
        if (modal) modal.hide();
        runAjax(window.REPOPULATE_URL, this);
    });

    document.querySelectorAll('.modal form').forEach(function (form) {
        form.addEventListener('submit', function () {
            const btn = form.querySelector('button[type="submit"]');
            if (!btn) return;
            btn.disabled  = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Working...';
        });
    });

    const destroyForm = document.getElementById('destroyVmForm');
    if (destroyForm) {
        destroyForm.addEventListener('submit', function () {
            const btn     = destroyForm.querySelector('.submit-btn');
            const spinner = btn.querySelector('.spinner');
            const label   = btn.querySelector('.btn-label');
            spinner.classList.remove('d-none');
            label.classList.add('d-none');
            btn.disabled = true;
        });
    }

    const deleteInput   = document.getElementById('deleteConfirmInput');
    const confirmedBtns = document.querySelectorAll('.confirmed-btn');

    if (deleteInput) {
        deleteInput.addEventListener('input', function () {
            const confirmed = this.value === 'DELETE';
            confirmedBtns.forEach(btn => btn.disabled = !confirmed);
        });

        document.getElementById('deleteServerModal').addEventListener('hidden.bs.modal', function () {
            deleteInput.value = '';
            confirmedBtns.forEach(btn => btn.disabled = true);
        });
    }
})();