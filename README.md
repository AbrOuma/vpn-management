<div align="center">

# WireGuard Manager

A self-hosted, open-source VPN management platform built with Django.
Manage WireGuard VPN servers, devices, and users through a clean web interface without ever touching the terminal.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-4.2+-092E20?logo=django&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

</div>

---

## Overview

WireGuard Manager connects to your WireGuard VPN servers over SSH and manages them programmatically. You keep full ownership of your servers. This platform just gives you a dashboard to control them.

**Core workflow:**

```
Browser  ->  Django (self-hosted)  ->  SSH  ->  WireGuard Server (GCP / AWS / any VPS)
```

All server configuration is stored per-server in the database. There are no global environment variables for WireGuard. Each server carries its own SSH credentials, subnet, interface name, and keys.

---

## Features

### Server Management
- Register existing WireGuard servers or provision new ones from scratch
- **Three provisioning paths:**
  - Connect to an existing VM: SSH in, install WireGuard, generate keys, configure and start the service
  - Provision a new GCP VM: create the instance, wait for SSH, then run full setup
  - Provision a new AWS EC2 instance: launch Ubuntu 22.04, configure security groups, run full setup
- Real-time health checks and peer sync via SSH
- **Three deletion modes:** remove from database only, wipe all peers from the server, or fully destroy the cloud VM

### Device Management
- Add, edit, enable, disable, and revoke VPN devices
- IP addresses automatically allocated per-server from a configurable subnet pool
- Online/offline detection via SSH ping
- Download WireGuard client config files directly from the dashboard
- QR code generation for mobile clients

### User Management
- Manage VPN users with department groupings
- Assign devices to users
- Suspend and reactivate accounts
- Email notification on device creation (SendGrid)

### Invite & Self-Service Portal
- Generate magic-link invites for new users
- Users redeem their invite at a dedicated portal page with no password needed
- Self-service portal: view devices, download configs, show QR codes

### REST API
- Token-based authentication
- Role-based access control: `SUPER_ADMIN`, `NETWORK_ADMIN`, `READ_ONLY`
- Rate-limited endpoints
- Full CRUD for servers, devices, and users
- Suitable for CI/CD pipelines, onboarding automation, and third-party integrations

### Security
- SSH private keys encrypted at rest using Fernet symmetric encryption
- Keys written to a tempfile (chmod 600) only for the duration of the SSH connection, then deleted immediately
- CSRF protection on all forms
- Django's built-in authentication for the admin dashboard

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 4.2 |
| Database | PostgreSQL |
| API | Django REST Framework |
| SSH | Paramiko |
| Cloud (GCP) | `google-cloud-compute` |
| Cloud (AWS) | `boto3` |
| Email | SendGrid via `django-anymail` |
| Static files | Whitenoise |
| Web server | Gunicorn |
| Frontend | Bootstrap 5 |

---

## Project Structure

<details>
<summary>Click to expand</summary>

```
wireguard-manager/
├── apps/
│   ├── accounts/       # Admin authentication (login / logout)
│   ├── users/          # VPN user and department management
│   ├── server/         # Server registration, provisioning, health
│   ├── devices/        # Device CRUD, enable/disable/revoke
│   ├── invites/        # Magic-link invite generation and redemption
│   ├── portal/         # End-user self-service portal
│   └── api/            # DRF REST API
├── wireguard/
│   ├── ssh_client.py   # get_ssh_client, run_command, write_remote_script
│   ├── commands.py     # All wg commands (each takes server as first param)
│   ├── manager.py      # WireGuardManager(server) - high-level operations
│   └── key_manager.py  # Fernet encryption/decryption for SSH keys
├── config/
│   ├── settings/
│   │   ├── base.py
│   │   ├── development.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── templates/
│   └── wireguard/
│       └── client.conf  # WireGuard client config template
├── Procfile
├── railway.json
└── requirements.txt
```

</details>

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL database
- A WireGuard server (GCP, AWS, or any VPS) reachable over SSH
- SendGrid account for email

### 1. Clone the repository

```bash
git clone https://github.com/AbrOuma/vpn-management.git
cd vpn-management
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows (PowerShell)
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root. See [Environment Variables](#environment-variables) below for the full list.

### 5. Run migrations

```bash
python manage.py migrate
```

### 6. Create a superuser

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000` and log in with your superuser credentials.

---

## Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for development, `False` for production |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames |
| `DATABASE_URL` | PostgreSQL connection string |
| `ENCRYPTION_KEY` | Fernet key for encrypting SSH private keys at rest |
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` or `config.settings.development` |
| `SENDGRID_API_KEY` | Required only if sending invite emails |
| `DEFAULT_FROM_EMAIL` | Sender address for outgoing email |

**Generating an encryption key:**

```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

---

## Connecting a WireGuard Server

### Option A - Register an existing server

Navigate to **Servers -> Add Server** and fill in your SSH credentials, interface name, VPN subnet, and listen port. Then click **Provision Existing VM** to install WireGuard and generate server keys automatically.

### Option B - Provision a new GCP instance

From **Servers -> Add Server -> Provision GCP VM**, supply your GCP project ID, zone, and instance name. The platform will:

1. Generate an SSH keypair in memory
2. Create the GCP instance
3. Wait for SSH to become available
4. Install WireGuard, generate keys, write config, and start the service

> A service account JSON with Compute Engine permissions is required.

### Option C - Provision a new AWS EC2 instance

From **Servers -> Add Server -> Provision AWS VM**, supply your AWS region and credentials. The platform will:

1. Create a security group with the WireGuard UDP port open
2. Generate and import an SSH keypair
3. Launch an Ubuntu 22.04 instance
4. Wait for SSH, then run the full WireGuard setup

---

## API

The REST API is available at `/api/v1/`.

### Authentication

```http
POST /api/v1/auth/token/
Content-Type: application/json

{
  "email": "admin@example.com",
  "password": "yourpassword"
}
```

Use the token in subsequent requests:

```http
Authorization: Token <your-token>
```

### Roles

| Role | Permissions |
|---|---|
| `SUPER_ADMIN` | Full access including admin management |
| `NETWORK_ADMIN` | Read and write access to servers, devices, users |
| `READ_ONLY` | Read-only access to all resources |

### Key Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/servers/` | List all servers |
| `POST` | `/api/v1/servers/` | Register a new server |
| `GET` | `/api/v1/servers/{id}/health/` | Server health check |
| `GET` | `/api/v1/devices/` | List all devices |
| `POST` | `/api/v1/devices/` | Create a device |
| `PATCH` | `/api/v1/devices/{id}/revoke/` | Revoke a device |
| `GET` | `/api/v1/users/` | List all VPN users |
| `POST` | `/api/v1/users/` | Create a VPN user |
| `PATCH` | `/api/v1/users/{id}/suspend/` | Suspend a user |

Token management is available under **Dashboard -> Settings -> API Tokens**.

---

## WireGuard Server Requirements

Add the following to `/etc/sudoers.d/wireguard-manager` on your server, then validate with `visudo -c`:

```
your-ssh-user ALL=(root) NOPASSWD: /usr/bin/wg show wg0
your-ssh-user ALL=(root) NOPASSWD: /usr/bin/wg show wg0 dump
your-ssh-user ALL=(root) NOPASSWD: /usr/bin/wg set wg0 *
your-ssh-user ALL=(root) NOPASSWD: /bin/cat /etc/wireguard/wg0.conf
your-ssh-user ALL=(root) NOPASSWD: /usr/bin/wg showconf wg0
your-ssh-user ALL=(root) NOPASSWD: /bin/systemctl restart wg-quick@wg0
```

---

## Contributing

Contributions are welcome. Please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "Add your feature"`
4. Push to your fork: `git push origin feature/your-feature`
5. Open a pull request

---

## License

MIT License. See [LICENSE](LICENSE) for details.
