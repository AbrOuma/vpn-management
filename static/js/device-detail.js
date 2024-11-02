// TRAFFIC_URL is injected inline by the template via window.TRAFFIC_URL

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + units[i];
}

function formatHandshake(ts) {
    if (!ts) return 'Never';
    const date = new Date(ts * 1000);
    return date.toLocaleString(undefined, {
        day:          '2-digit',
        month:        'short',
        year:         'numeric',
        hour:         '2-digit',
        minute:       '2-digit',
        timeZoneName: 'short',
    });
}

function fetchTraffic() {
    fetch(window.TRAFFIC_URL)
        .then(r => r.json())
        .then(data => {
            if (data.error) {
                document.getElementById('traffic-status').textContent = 'Unavailable';
                document.getElementById('pulse').style.background = '#ef4444';
                return;
            }
            document.getElementById('stat-received').textContent  = formatBytes(data.bytes_received);
            document.getElementById('stat-sent').textContent      = formatBytes(data.bytes_sent);
            document.getElementById('stat-handshake').textContent = formatHandshake(data.last_handshake_ts);
            document.getElementById('stat-endpoint').textContent  = data.endpoint;
            document.getElementById('traffic-status').textContent = 'Live';
            document.getElementById('pulse').style.background     = '#10b981';
        })
        .catch(() => {
            document.getElementById('traffic-status').textContent = 'Unavailable';
            document.getElementById('pulse').style.background = '#ef4444';
        });
}

fetchTraffic();
setInterval(fetchTraffic, 10000);