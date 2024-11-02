function toggleToken() {
    const field = document.getElementById('tokenField');
    const icon  = document.getElementById('toggleIcon');
    if (field.type === 'password') {
        field.type    = 'text';
        icon.className = 'bi bi-eye-slash';
    } else {
        field.type    = 'password';
        icon.className = 'bi bi-eye';
    }
}

function copyToken(token) {
    navigator.clipboard.writeText(token).then(() => {
        const icon     = document.getElementById('copyIcon');
        icon.className = 'bi bi-clipboard-check';
        setTimeout(() => icon.className = 'bi bi-clipboard', 2000);
    });
}