# Synology Infrastructure Manager

Complete Docker infrastructure management with **Portainer API integration** and **Synology reverse proxy automation**.

**Two ways to manage:**
- 🖥️ **Streamlit Web UI** - Beautiful visual interface
- 🔧 **CLI Scripts** - Command-line tools for automation

---

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Web UI](#web-ui-streamlit-app)
  - [CLI Scripts](#cli-scripts)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Troubleshooting](#troubleshooting)
- [Advanced Topics](#advanced-topics)

---

## Quick Start

### Option 1: Docker (Recommended for Production)

```bash
# 1. Clone and configure
git clone <repo>
cd synolog-config
cp .env.example .env
# Edit .env with your credentials

# 2. Deploy with Docker Compose
docker-compose up -d

# 3. Access at http://localhost:8501
```

### Option 2: Local Development

```bash
# 1. Setup
git clone <repo>
cd synolog-config
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure
cp .env.example .env
# Edit .env with your credentials

# 3. Run Web UI
streamlit run app/main.py

# OR use CLI
python scripts/portainer_sync.py scan
```

---

## Features

### ✅ Portainer Integration
- **Live container data** from Portainer API
- Automatic service discovery
- Container state tracking (running/stopped)
- Multi-port support (e.g., Portainer 8000+9000)
- Stack-aware organization

### ✅ Reverse Proxy Management
- Create/list/delete Synology proxy rules
- Real-time validation and duplicate detection
- Port conflict warnings
- HSTS and WebSocket support
- Domain availability checking

### ✅ Smart Sync
- Compare Portainer containers with proxy rules
- Identify missing proxies (containers without rules)
- Detect orphaned proxies (rules without containers)
- **Bulk auto-create** missing rules with one click

### ✅ Intelligent Detection
**Automatically excludes internal services:**
- Databases (postgres, mysql, mariadb, mongo)
- Cache (redis, memcached)
- Message queues (rabbitmq, kafka)

**Auto-detects WebSocket requirements:**
- Plex, Portainer, qBittorrent
- Immich, Jellyfin, Home Assistant
- Grafana, Netdata

### ✅ Multi-Port Handling
- Shows all published ports (e.g., `8000, 9000`)
- Intelligently selects correct port for proxy
- Example: Portainer `8000, 9000 (→9000)` uses 9000 for web UI

---

## Installation

### Prerequisites
- Python 3.8 or higher
- Portainer instance (running and accessible)
- Synology NAS with API enabled
- Network access to both systems

### Setup

```bash
# 1. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
nano .env  # Edit with your credentials
```

### Configuration File (`.env`)

```env
# Portainer Connection
PORTAINER_HOST=notmyproblemnas
PORTAINER_PORT=9000
PORTAINER_USERNAME=admin
PORTAINER_PASSWORD=your_password

# Synology Connection
SYNOLOGY_HOST=notmyproblemnas
SYNOLOGY_PORT=5000
SYNOLOGY_USERNAME=akib_admin
SYNOLOGY_PASSWORD=your_password
```

---

## Usage

## Web UI (Streamlit App)

### Starting the App

```bash
source .venv/bin/activate
streamlit run app/main.py
```

Opens at: http://localhost:8501

### Features

#### 📋 **Inventory Tab**
- View all containers from Portainer with live status
- See running vs stopped containers
- Filter by state (Running/Stopped) and proxy requirements
- Search for specific services or containers
- Check for port conflicts
- Export data to CSV

**Display format:**
```
Service: portainer
Container: portainer
Ports: 8000, 9000 (→9000)  ← Shows all ports, arrow points to proxy port
State: ✅ Running
```

#### 🌐 **Reverse Proxy Tab**

**Current Rules:**
- View all existing reverse proxy configurations
- Search and filter rules
- See port usage summary

**Add New Rule:**
- Real-time validation
- Duplicate detection (description and domain)
- Port conflict warnings
- Suggested next available port
- HSTS and WebSocket options

#### 🔄 **Sync Tab**
- Compare Portainer containers with actual proxy rules
- **Missing Proxies**: Running containers without proxy rules
- **Orphaned Proxies**: Proxy rules for stopped/missing containers
- **In Sync**: Services properly configured
- **One-click bulk create** all missing proxies

### Workflow Example

1. **Sidebar** → Portainer Settings → Enter credentials → Click "🔍 Scan Portainer"
2. **Sidebar** → Connection Settings → Enter Synology credentials → Click "🔐 Connect"
3. **Sync Tab** → View sync status
4. Click **"🚀 Auto-Create Missing Proxies"**
5. Done! All running containers now have proxy rules

---

## CLI Scripts

All scripts are in the `scripts/` directory.

### 1. `portainer_sync.py` - Portainer→Synology Sync

**Commands:**

```bash
# Scan Portainer and show inventory
python scripts/portainer_sync.py scan

# Compare with reverse proxy
python scripts/portainer_sync.py sync

# Check for port conflicts
python scripts/portainer_sync.py conflicts

# Auto-create missing proxy rules (interactive)
python scripts/portainer_sync.py create
```

**Example Output:**

```
📦 Stack: media
──────────────────────────────────────────────
  ✅ 🌐 sonarr           Port: 8989      linuxserver/sonarr:latest
  ✅ 🌐 radarr           Port: 7878      linuxserver/radarr:latest
  ✅ 🌐 portainer        Port: 8000,9000→9000  portainer/portainer-ce

📦 Stack: monitoring
──────────────────────────────────────────────
  ✅ 🌐 grafana          Port: 3000      grafana/grafana:latest
  ✅ 🔒 prometheus       Port: 9090      prom/prometheus:latest
```

**Sync Output:**

```
SYNC REPORT: Portainer vs Reverse Proxy
════════════════════════════════════════

❌ Missing Reverse Proxy Rules:
   - bazarr (port 6767) from stack 'media'
     Suggested: bazarr.akibrhast.synology.me

✅ In Sync: 15 services
   - portainer (port 9000) → portainer.akibrhast.synology.me
   - sonarr (port 8989) → sonarr.akibrhast.synology.me
```

### 2. `manage_reverse_proxy.py` - Direct Proxy Management

**Commands:**

```bash
# List all reverse proxy rules
python scripts/manage_reverse_proxy.py list

# Add new rule (interactive)
python scripts/manage_reverse_proxy.py add

# Show port usage
python scripts/manage_reverse_proxy.py ports
```

**Interactive Add Example:**

```bash
$ python scripts/manage_reverse_proxy.py add

Current rules:
─────────────────────────────────────────
 1. portainer
    Frontend: portainer.akibrhast.synology.me:443
    Backend:  notmyproblemnas:9000

📊 Ports in use: 9000, 8989, 7878 ...
💡 Next available port: 6767

New Rule Details:
─────────────────────────────────────────
Service name: bazarr
Frontend domain: bazarr.akibrhast.synology.me
Backend host [notmyproblemnas]:
Backend port [6767]:
Enable HSTS? (y/n) [y]:
Enable WebSocket? (y/n) [n]:

✅ Added: bazarr
   bazarr.akibrhast.synology.me:443 → notmyproblemnas:6767
```

### 3. `inventory.py` - Legacy File-Based Inventory

Scans docker-compose files (legacy):

```bash
# Scan docker-compose files
python scripts/inventory.py scan

# Generate PORT_MAP.md
python scripts/inventory.py generate

# Sync with proxy
python scripts/inventory.py sync
```

---

## Configuration

### Environment Variables

All configuration in single **`.env`** file at project root:

```env
# Portainer Connection
PORTAINER_HOST=notmyproblemnas      # Hostname or IP
PORTAINER_PORT=9000                  # Default: 9000
PORTAINER_USERNAME=admin             # Your username
PORTAINER_PASSWORD=your_password     # Your password

# Synology Connection
SYNOLOGY_HOST=notmyproblemnas        # Hostname or IP
SYNOLOGY_PORT=5000                   # DSM API port (usually 5000)
SYNOLOGY_USERNAME=akib_admin         # Admin username
SYNOLOGY_PASSWORD=your_password      # Admin password
```

### Portainer Setup

Your Portainer should be running and accessible. Example setup:

```bash
docker run -d --name=portainer \
  -p 8000:8000 \
  -p 9000:9000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /volume1/docker/portainer:/data \
  --restart=always \
  portainer/portainer-ce
```

Ports:
- **8000**: Edge agent communication
- **9000**: Web UI (HTTPS)

---

## Project Structure

```
synolog-config/
├── .venv/                          # Virtual environment
├── .env                            # Configuration (create from .env.example)
├── .env.example                    # Configuration template
├── .gitignore                      # Git ignore patterns
├── requirements.txt                # Python dependencies
├── README.md                       # This file
│
├── scripts/                        # CLI tools
│   ├── portainer_sync.py          # Portainer→Synology sync
│   ├── manage_reverse_proxy.py    # Reverse proxy management
│   └── inventory.py               # Legacy file-based inventory
│
├── app/                            # Streamlit web UI
│   ├── main.py                    # Main application
│   └── modules/
│       ├── inventory.py           # Portainer API integration
│       └── reverse_proxy.py       # Synology API integration
│
└── stacks/                         # Docker compose files (optional)
```

---

## How It Works

### Portainer API Flow

```
1. Authenticate with Portainer
   ↓
2. Get JWT token
   ↓
3. Fetch Endpoints (Docker hosts)
   ↓
4. For each endpoint:
   ├─ Get Stacks
   └─ Get Containers
       ↓
5. Parse container metadata:
   ├─ Extract ports from Ports array
   ├─ Get stack from 'com.docker.compose.project' label
   ├─ Get service from 'com.docker.compose.service' label
   └─ Determine running state
       ↓
6. Build service inventory
```

### Multi-Port Handling

For containers with multiple ports (e.g., Portainer):

```python
Container: portainer
Ports: [8000, 9000]

# Smart selection:
if 'portainer' in name:
    proxy_port = 9000  # Web UI
else:
    proxy_port = first_port

# Display:
"8000, 9000 (→9000)"
```

### Sync Logic

```
Portainer Containers ──┐
                       ├──> Compare by Port ──> Report
Synology Proxy Rules ──┘

Missing  = (Containers needing proxy) - (Proxy rules)
Orphaned = (Proxy rules) - (Running containers)
In Sync  = Matching on port number
```

### API Endpoints Used

**Portainer:**
- `POST /api/auth` - Get JWT token
- `GET /api/endpoints` - List Docker hosts
- `GET /api/stacks` - List compose stacks
- `GET /api/endpoints/{id}/docker/containers/json` - List containers

**Synology:**
- `POST /webapi/auth.cgi` - Login
- `POST /webapi/entry.cgi/SYNO.Core.AppPortal.ReverseProxy` - Manage rules

---

## Troubleshooting

### Connection Issues

**"Connection error" or "Connection refused"**

```bash
# Check Portainer is accessible
curl http://notmyproblemnas:9000

# Check Synology API is accessible
curl http://notmyproblemnas:5000/webapi/query.cgi?api=SYNO.API.Info&version=1&method=query
```

**Solutions:**
- Verify hostnames/IPs in `.env`
- Check firewalls allow access
- Ensure Portainer is running
- Verify Synology DSM is accessible

### Authentication Issues

**"Invalid credentials" (422 error)**

```bash
# Verify credentials work manually
# Login to Portainer web UI
# Login to Synology DSM
```

**Solutions:**
- Check passwords in `.env` (no quotes needed)
- Verify username is correct
- Check for special characters (they should work fine in .env)
- Try resetting password

### Module Not Found

**"ModuleNotFoundError: No module named 'streamlit'"**

```bash
# Make sure venv is activated
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Port Mismatch (Portainer Shows 8000 Instead of 9000)

**Issue:** Portainer shows as port 8000 but proxy is on 9000

**This is now fixed!** The code intelligently handles multi-port services:
- Shows all ports: `8000, 9000 (→9000)`
- Uses correct port (9000) for proxy matching

### Sync Shows Portainer as Missing

**Old behavior:** Compared first port (8000) with proxy (9000) → mismatch

**New behavior:** Smart port selection prefers 9000 for Portainer web UI → sync works!

---

## Advanced Topics

### Adding Custom Port Logic

To add custom port selection for other multi-port services:

```python
# app/modules/inventory.py (line ~231)
def _get_proxy_port(self, container_name, ports):
    if 'portainer' in container_name.lower():
        if 9000 in ports:
            return 9000

    # Add your custom logic:
    if 'myservice' in container_name.lower():
        if 8080 in ports:
            return 8080

    return ports[0]  # Default
```

### Excluding Services from Proxy

```python
# app/modules/inventory.py (line ~246)
def _needs_reverse_proxy(self, service_name, image):
    internal_keywords = [
        'database', 'postgres', 'redis',
        # Add your exclusions:
        'myinternal', 'backend-only'
    ]
    # ...
```

### Custom Domain Suffix

```python
# Change default from akibrhast.synology.me to your domain
inventory.generate_proxy_suggestions(domain_suffix="yourdomain.com")
```

### Automation with Cron

```bash
# Run sync daily at 2am
0 2 * * * /path/to/.venv/bin/python /path/to/scripts/portainer_sync.py sync > /tmp/sync.log 2>&1
```

### Deploying via Portainer

#### Step 1: Push to GitHub

```bash
cd /path/to/synolog-config
git init
git add .
git commit -m "Initial commit"
git remote add origin <your-repo-url>
git push -u origin main
```

#### Step 2: Deploy in Portainer

1. Navigate to **Stacks** → **Add stack**
2. **Name**: `synology-manager`
3. **Build method**: Repository
4. **Repository URL**: `https://github.com/yourusername/synolog-config`
5. **Repository reference**: `refs/heads/main`
6. **Compose path**: `docker-compose.yml`
7. **Authentication**: Add credentials if private repo

#### Step 3: Add Environment Variables

Click "Advanced mode" and paste:

```env
PORTAINER_HOST=notmyproblemnas
PORTAINER_PORT=9000
PORTAINER_USERNAME=admin
PORTAINER_PASSWORD=your_portainer_password

SYNOLOGY_HOST=notmyproblemnas
SYNOLOGY_PORT=5000
SYNOLOGY_USERNAME=akib_admin
SYNOLOGY_PASSWORD=your_synology_password
```

#### Step 4: Deploy

1. Click **Deploy the stack**
2. Wait for build to complete (first build may take 2-3 minutes)
3. Container will auto-start and connect to Portainer & Synology

#### Step 5: Access the App

- **Direct access**: `http://<nas-ip>:8501`
- **After creating reverse proxy**: `https://synology-manager.akibrhast.synology.me`

#### Step 6: Create Reverse Proxy Rule (Optional)

Use the app itself to create its own reverse proxy:

1. Access `http://<nas-ip>:8501`
2. Go to **Reverse Proxy** tab → **Add New Rule**
3. Fill in:
   - Service Name: `synology-manager`
   - Frontend Domain: `synology-manager.akibrhast.synology.me`
   - Frontend Port: `443`
   - Backend Host: `notmyproblemnas`
   - Backend Port: `8501`
   - Enable HSTS: ✅
   - **Enable WebSocket: ✅** (required for Streamlit)
4. Click **Create Rule**
5. Access via: `https://synology-manager.akibrhast.synology.me`

#### Updating the Deployment

1. Push changes to GitHub
2. In Portainer stack, click **Pull and redeploy**
3. Done!

#### Troubleshooting Deployment

**Container won't start:**
```bash
# Check logs in Portainer or via CLI
docker logs synology-infrastructure-manager

# Common issues:
# - Missing environment variables
# - Port 8501 already in use
# - Network conflicts
```

**Can't connect to Portainer/Synology:**
- Verify environment variables are correct
- Check container can reach services:
  ```bash
  docker exec synology-infrastructure-manager ping notmyproblemnas
  ```

**Streamlit shows "Unhealthy":**
- Wait 40 seconds for startup (healthcheck grace period)
- Verify Streamlit is running:
  ```bash
  docker exec synology-infrastructure-manager curl -f http://localhost:8501/_stcore/health
  ```

---

## Cross-Platform Support

Works on:
- ✅ **macOS** - Tested on macOS 14+
- ✅ **Windows** - Works with PowerShell/CMD
- ✅ **Linux** - Any modern distro

**Windows activation:**
```cmd
.venv\Scripts\activate
python scripts\portainer_sync.py scan
streamlit run app\main.py
```

---

## Comparison: File Scan vs Portainer API

| Feature | File Scan (`inventory.py`) | Portainer API (New) |
|---------|---------------------------|-------------------|
| **Data Source** | docker-compose.yml files | Live containers |
| **Accuracy** | Configuration | Reality |
| **Shows State** | No | Yes (running/stopped) |
| **Port Info** | Configured | Actually published |
| **Updates** | Manual rescan | Real-time |
| **Stack Info** | Directory name | Docker label |
| **Best For** | Planning | Operations |

**Recommendation:** Use Portainer API for operational sync, keep file scan for planning/documentation.

---

## Why This Project?

### Problem
- Managing dozens of Docker services across multiple stacks
- Each service needs a reverse proxy rule
- Manual creation is error-prone and tedious
- Hard to know what's missing or orphaned

### Solution
- **Portainer** as single source of truth
- **Automated sync** between containers and proxy
- **Intelligent detection** of service types
- **One-click bulk operations**

### Result
- ✅ Never manually create proxy rules again
- ✅ Always know sync status at a glance
- ✅ Detect and fix issues automatically
- ✅ Beautiful UI or powerful CLI - your choice

---

## License

MIT

## Contributing

Issues and pull requests welcome!

---

**Built with ❤️ using Streamlit, Portainer API, and Synology DSM API**
