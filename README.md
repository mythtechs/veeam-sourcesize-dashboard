# Veeam Backup Sizes Dashboard (Adept Networks)

Real-time dashboard showing:
- VM source sizes grouped by company
- Workstation backup sizes grouped by job name prefix (the only reliable method on this VSPC)

Tested and working 100% on `veeam.adeptnetworks.com:1280`

## Quick Start

```bash
git clone https://github.com/yourusername/veeam-dashboard.git
cd veeam-dashboard

# Edit docker-compose.yml and replace YOUR_TOKEN_HERE_REPLACE_ME with your real API token

docker compose up --build -d
