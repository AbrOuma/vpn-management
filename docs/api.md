# API Reference

The WireGuard Manager REST API allows you to manage servers, devices, and users programmatically. All endpoints are available at `/api/v1/`.

---

## Authentication

The API uses token-based authentication. Include the token in every request header:

```http
Authorization: Token <your-token>
```

### Obtain a token

```http
POST /api/v1/auth/token/
```

**Request body:**

```json
{
  "email": "admin@example.com",
  "password": "yourpassword"
}
```

**Response:**

```json
{
  "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
}
```

**Error responses:**

| Status | Meaning |
|---|---|
| `400` | Email or password missing |
| `401` | Invalid credentials |

Tokens can also be generated and revoked from the dashboard under **Settings -> API Tokens**.

---

## Roles and permissions

| Role | Access |
|---|---|
| `SUPER_ADMIN` | Full access to all endpoints |
| `NETWORK_ADMIN` | Full access to all endpoints |
| `READ_ONLY` | Read-only — `GET` requests only |

All endpoints require authentication. Unauthenticated requests return `401`.

---

## Servers

### List servers

```http
GET /api/v1/servers/
```

Returns all registered servers ordered by name.

**Response:**

```json
[
  {
    "id": 1,
    "name": "GCP Primary",
    "public_ip": "34.123.45.67",
    "ssh_host": "34.123.45.67",
    "ssh_user": "user",
    "interface_name": "wg0",
    "listen_port": 51820,
    "vpn_subnet": "10.128.10.1/24",
    "server_ip": "10.128.10.1",
    "address": "10.128.10.1/24",
    "public_key": "abc123...",
    "dns_servers": "1.1.1.1,8.8.8.8",
    "mtu": 1420,
    "provisioning_status": "provisioned"
  }
]
```

---

### Get server

```http
GET /api/v1/servers/<id>/
```

Returns a single server by ID.

---

### Delete server

```http
DELETE /api/v1/servers/<id>/
```

Removes the server from the database only. The VM is not affected.

**Response:** `204 No Content`

---

### Sync server

```http
POST /api/v1/servers/<id>/sync/
```

Pushes all active device peers to the live WireGuard process on the server via SSH.

**Response:**

```json
{
  "status": "synced"
}
```

**Error response (`502`):**

```json
{
  "error": "Connection refused"
}
```

---

### Server health check

```http
GET /api/v1/servers/<id>/health/
```

Checks whether WireGuard is running on the server and refreshes peer stats.

**Response:**

```json
{
  "running": true,
  "stats_updated": 12
}
```

**Error response (`502`):**

```json
{
  "error": "SSH timeout"
}
```

---

## Devices

### List devices

```http
GET /api/v1/devices/
```

Staff users receive all devices. Non-staff users receive only their own devices.

**Response:**

```json
[
  {
    "id": "0d137bae-4f6c-4f07-a471-94a5ac58828e",
    "name": "John's Laptop",
    "device_type": "laptop",
    "status": "ACTIVE",
    "ip_address": "10.128.10.5",
    "public_key": "xyz789...",
    "server": 1,
    "user": 3,
    "created_at": "2025-01-15T10:30:00Z"
  }
]
```

---

### Get device

```http
GET /api/v1/devices/<uuid>/
```

Returns a single device. Staff can access any device. Non-staff can only access their own.

---

### Enable device

```http
POST /api/v1/devices/<uuid>/enable/
```

Sets the device status to `ACTIVE` and syncs the server.

**Response:**

```json
{
  "status": "ACTIVE"
}
```

---

### Disable device

```http
POST /api/v1/devices/<uuid>/disable/
```

Sets the device status to `DISABLED` and syncs the server.

**Response:**

```json
{
  "status": "DISABLED"
}
```

---

### Revoke device

```http
POST /api/v1/devices/<uuid>/revoke/
```

Sets the device status to `REVOKED` and removes the peer from the WireGuard server immediately.

**Response:**

```json
{
  "status": "REVOKED"
}
```

---

### Download device config

```http
GET /api/v1/devices/<uuid>/config/
```

Returns the WireGuard client configuration file content for the device. Staff can access any device config. Non-staff can only access their own.

**Response:**

```json
{
  "config": "[Interface]\nPrivateKey = ...\nAddress = 10.128.10.5/32\n\n[Peer]\n..."
}
```

---

## Users

### List users

```http
GET /api/v1/users/
```

Returns all VPN users ordered by email. Staff only.

**Response:**

```json
[
  {
    "id": 3,
    "full_name": "John Doe",
    "email": "john@example.com",
    "department": 1,
    "status": "ACTIVE",
    "created_at": "2025-01-10T08:00:00Z"
  }
]
```

---

### Get user

```http
GET /api/v1/users/<id>/
```

Returns a single VPN user by ID. Staff only.

---

### Suspend user

```http
POST /api/v1/users/<id>/suspend/
```

Deactivates the user account. Cannot be used on your own account.

**Response:**

```json
{
  "status": "suspended"
}
```

**Error response (`400`):**

```json
{
  "error": "You cannot suspend your own account."
}
```

---

### Activate user

```http
POST /api/v1/users/<id>/activate/
```

Reactivates a suspended user account.

**Response:**

```json
{
  "status": "activated"
}
```

---

## Error responses

All endpoints follow a consistent error format:

```json
{
  "error": "Description of what went wrong"
}
```

Common status codes:

| Status | Meaning |
|---|---|
| `400` | Bad request — missing or invalid input |
| `401` | Unauthenticated — token missing or invalid |
| `403` | Forbidden — insufficient permissions |
| `404` | Resource not found |
| `502` | SSH or WireGuard server unreachable |

---

## Rate limiting

The token endpoint is rate limited to prevent brute force. Repeated failed attempts will result in temporary blocking.

---

## Example: full onboarding flow

The following sequence creates a user, creates a device, and retrieves the config — suitable for an automated onboarding script.

**1. Obtain a token:**

```bash
curl -X POST https://yourdomain.com/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "yourpassword"}'
```

**2. List available servers to get the server ID:**

```bash
curl https://yourdomain.com/api/v1/servers/ \
  -H "Authorization: Token <your-token>"
```

**3. Retrieve the new device config:**

```bash
curl https://yourdomain.com/api/v1/devices/<uuid>/config/ \
  -H "Authorization: Token <your-token>"
```

**4. Revoke access when the user leaves:**

```bash
curl -X POST https://yourdomain.com/api/v1/devices/<uuid>/revoke/ \
  -H "Authorization: Token <your-token>"
```