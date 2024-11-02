// Modal submit spinner - prevents double submission and shows loading state
document.querySelectorAll('.modal form').forEach(function (form) {
    form.addEventListener('submit', function () {
        const btn = form.querySelector('.modal-submit-btn');
        if (!btn) return;
        btn.querySelector('.spinner').classList.remove('d-none');
        btn.querySelector('.btn-label').classList.add('d-none');
        btn.disabled = true;
    });
});