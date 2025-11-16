#!/usr/bin/env python3
"""
Portainer-Synology Sync
Uses Portainer API as source of truth to sync with Synology reverse proxy
"""
import requests
import json
import os
import sys
import urllib3
from pathlib import Path
from dotenv import load_dotenv
from collections import defaultdict

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()


class PortainerClient:
    """Client for Portainer API"""

    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()

        # Authenticate
        if not self.authenticate():
            raise Exception("Failed to authenticate with Portainer")

    def authenticate(self):
        """Authenticate with Portainer and get JWT token"""
        url = f"{self.base_url}/api/auth"

        payload = {
            "username": self.username,
            "password": self.password
        }

        try:
            response = self.session.post(url, json=payload, verify=False, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.token = data.get('jwt')

                # Set authorization header for future requests
                self.session.headers.update({
                    'Authorization': f'Bearer {self.token}'
                })

                print("✅ Authenticated with Portainer\n")
                return True
            else:
                print(f"❌ Authentication failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"   Error details: {error_data}")
                except:
                    print(f"   Response: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False

    def get_endpoints(self):
        """Get all endpoints (Docker environments)"""
        url = f"{self.base_url}/api/endpoints"

        try:
            response = self.session.get(url, verify=False, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get endpoints: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Error getting endpoints: {e}")
            return []

    def get_stacks(self, endpoint_id):
        """Get all stacks for an endpoint"""
        url = f"{self.base_url}/api/stacks"

        try:
            response = self.session.get(url, verify=False, timeout=10)

            if response.status_code == 200:
                stacks = response.json()
                # Filter by endpoint
                return [s for s in stacks if s.get('EndpointId') == endpoint_id]
            else:
                print(f"❌ Failed to get stacks: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Error getting stacks: {e}")
            return []

    def get_containers(self, endpoint_id):
        """Get all containers for an endpoint"""
        url = f"{self.base_url}/api/endpoints/{endpoint_id}/docker/containers/json"
        params = {'all': 'true'}  # Include stopped containers

        try:
            response = self.session.get(url, params=params, verify=False, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Failed to get containers: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ Error getting containers: {e}")
            return []


class PortainerInventory:
    """Build service inventory from Portainer"""

    def __init__(self, portainer_client):
        self.client = portainer_client
        self.services = {}
        self.endpoints = []
        self.stacks = []
        self.containers = []

    def scan(self):
        """Scan Portainer for all services"""
        print("🔍 Scanning Portainer for services...")

        # Get endpoints
        self.endpoints = self.client.get_endpoints()
        print(f"Found {len(self.endpoints)} endpoint(s)")

        # For each endpoint, get stacks and containers
        for endpoint in self.endpoints:
            endpoint_id = endpoint.get('Id')
            endpoint_name = endpoint.get('Name', 'unknown')

            print(f"\n📍 Scanning endpoint: {endpoint_name} (ID: {endpoint_id})")

            # Get stacks
            stacks = self.client.get_stacks(endpoint_id)
            self.stacks.extend(stacks)
            print(f"   Found {len(stacks)} stack(s)")

            # Get containers
            containers = self.client.get_containers(endpoint_id)
            self.containers.extend(containers)
            print(f"   Found {len(containers)} container(s)")

        # Build service inventory from containers
        self._build_inventory()

        print(f"\n✅ Total services discovered: {len(self.services)}")

    def _build_inventory(self):
        """Build service inventory from containers"""
        for container in self.containers:
            # Extract container info
            names = container.get('Names', [])
            if not names:
                continue

            # Remove leading slash from name
            container_name = names[0].lstrip('/')

            # Get image
            image = container.get('Image', 'unknown')

            # Get state
            state = container.get('State', 'unknown')

            # Get labels
            labels = container.get('Labels', {})

            # Extract stack name from labels
            stack_name = labels.get('com.docker.compose.project', 'standalone')

            # Extract service name from labels or use container name
            service_name = labels.get('com.docker.compose.service', container_name)

            # Extract ports
            ports = self._extract_ports(container)

            # Determine if needs reverse proxy
            needs_proxy = self._needs_reverse_proxy(service_name, image)

            # Determine proxy port (port to use for reverse proxy matching)
            proxy_port = self._get_proxy_port(container_name, ports)

            # Store service info
            self.services[container_name] = {
                'service_name': service_name,
                'container_name': container_name,
                'stack': stack_name,
                'image': image,
                'state': state,
                'ports': ports,  # All published ports
                'published_port': proxy_port,  # Port used for reverse proxy (for sync)
                'needs_proxy': needs_proxy,
                'labels': labels
            }

    def _extract_ports(self, container):
        """Extract all published ports from container"""
        ports_config = container.get('Ports', [])
        published_ports = []

        for port_mapping in ports_config:
            public_port = port_mapping.get('PublicPort')
            if public_port:
                published_ports.append(public_port)

        return sorted(published_ports)

    def _get_proxy_port(self, container_name, ports):
        """Determine which port should be used for reverse proxy matching"""
        if not ports:
            return None

        # For most services, use the first (lowest) port
        # Special cases for services with multiple ports
        if 'portainer' in container_name.lower():
            # Portainer: prefer 9000 (web UI) over 8000 (edge agent)
            if 9000 in ports:
                return 9000

        # Default: return first port
        return ports[0]

    def _needs_reverse_proxy(self, service_name, image):
        """Determine if service needs reverse proxy"""
        # Internal services that don't need proxy
        internal_keywords = [
            'database', 'db', 'postgres', 'mysql', 'mariadb', 'mongo',
            'redis', 'cache', 'rabbitmq', 'kafka', 'zookeeper',
            'elasticsearch', 'logstash'
        ]

        service_lower = service_name.lower()
        image_lower = image.lower()

        # Check if it's an internal service
        for keyword in internal_keywords:
            if keyword in service_lower or keyword in image_lower:
                return False

        return True

    def check_port_conflicts(self):
        """Check for port conflicts"""
        port_usage = defaultdict(list)

        for container_name, info in self.services.items():
            port = info.get('published_port')
            if port:
                port_usage[port].append(container_name)

        conflicts = {
            port: names
            for port, names in port_usage.items()
            if len(names) > 1
        }
        return conflicts

    def get_services_needing_proxy(self):
        """Get services that need reverse proxy"""
        return {
            name: info
            for name, info in self.services.items()
            if info.get('needs_proxy') and info.get('published_port') and info.get('state') == 'running'
        }

    def generate_proxy_suggestions(self, domain_suffix="akibrhast.synology.me"):
        """Generate suggested reverse proxy rules"""
        suggestions = []

        for container_name, info in self.services.items():
            if not info.get('needs_proxy'):
                continue

            if info.get('state') != 'running':
                continue

            port = info.get('published_port')
            if not port:
                continue

            # Use service name for domain (cleaner than container name)
            service_name = info.get('service_name', container_name)

            suggestions.append({
                'service': service_name,
                'container': container_name,
                'port': port,
                'suggested_domain': f"{service_name}.{domain_suffix}",
                'websocket': self._needs_websocket(service_name, info.get('image', '')),
                'hsts': True,
                'stack': info.get('stack')
            })

        return suggestions

    def _needs_websocket(self, service_name, image):
        """Determine if service needs websocket"""
        websocket_keywords = [
            'plex', 'portainer', 'qbittorrent', 'immich',
            'jellyfin', 'home-assistant', 'grafana', 'netdata'
        ]

        service_lower = service_name.lower()
        image_lower = image.lower()

        return any(
            keyword in service_lower or keyword in image_lower
            for keyword in websocket_keywords
        )


def print_inventory(inventory):
    """Pretty print the inventory"""
    print("\n" + "=" * 80)
    print("PORTAINER SERVICE INVENTORY")
    print("=" * 80)

    # Group by stack
    by_stack = defaultdict(list)
    for container_name, info in inventory.services.items():
        stack = info.get('stack', 'standalone')
        by_stack[stack].append((container_name, info))

    for stack_name in sorted(by_stack.keys()):
        print(f"\n📦 Stack: {stack_name}")
        print("-" * 80)

        for container_name, info in sorted(by_stack[stack_name]):
            service_name = info.get('service_name', container_name)
            all_ports = info.get('ports', [])
            proxy_port = info.get('published_port')
            state = info.get('state', 'unknown')
            proxy = '🌐' if info.get('needs_proxy') else '🔒'
            state_icon = '✅' if state == 'running' else '⏸️'

            # Format ports display
            if all_ports:
                if len(all_ports) > 1:
                    ports_str = f"{','.join(map(str, all_ports))}→{proxy_port}"
                else:
                    ports_str = str(all_ports[0])
            else:
                ports_str = 'N/A'

            print(f"  {state_icon} {proxy} {service_name:25s} Port: {ports_str:12s} {info.get('image', '')[:40]}")


def generate_sync_report(inventory, reverse_proxy_manager):
    """Compare Portainer inventory with reverse proxy"""
    print("\n" + "=" * 80)
    print("SYNC REPORT: Portainer vs Reverse Proxy")
    print("=" * 80)

    # Get actual proxy rules
    actual_rules = reverse_proxy_manager.list_rules(verbose=False)

    # Build lookup by port
    actual_by_port = {}
    for rule in actual_rules:
        port = rule.get('backend', {}).get('port')
        if port:
            actual_by_port[port] = rule

    # Compare
    missing_proxies = []
    in_sync = []

    for container_name, info in inventory.services.items():
        if not info.get('needs_proxy'):
            continue

        if info.get('state') != 'running':
            continue

        port = info.get('published_port')
        if not port:
            continue

        service_name = info.get('service_name', container_name)

        if port not in actual_by_port:
            missing_proxies.append({
                'service': service_name,
                'container': container_name,
                'port': port,
                'stack': info.get('stack'),
                'suggested_domain': f"{service_name}.akibrhast.synology.me"
            })
        else:
            in_sync.append({
                'service': service_name,
                'port': port,
                'domain': actual_by_port[port].get('frontend', {}).get('fqdn')
            })

    # Check for orphaned rules
    known_ports = set(
        info['published_port']
        for info in inventory.services.values()
        if info.get('published_port') and info.get('state') == 'running'
    )

    orphaned_proxies = []
    for rule in actual_rules:
        port = rule.get('backend', {}).get('port')
        if port and port not in known_ports:
            orphaned_proxies.append({
                'description': rule.get('description'),
                'domain': rule.get('frontend', {}).get('fqdn'),
                'port': port
            })

    # Print report
    if missing_proxies:
        print("\n❌ Missing Reverse Proxy Rules:")
        print("   (Running in Portainer but not in proxy)")
        for item in missing_proxies:
            print(f"   - {item['service']} (port {item['port']}) from stack '{item['stack']}'")
            print(f"     Suggested: {item['suggested_domain']}")

    if orphaned_proxies:
        print("\n⚠️  Orphaned Reverse Proxy Rules:")
        print("   (In proxy but no running container)")
        for item in orphaned_proxies:
            print(f"   - {item['description']} ({item['domain']}) port {item['port']}")

    if in_sync:
        print(f"\n✅ In Sync: {len(in_sync)} services")
        for item in in_sync:
            print(f"   - {item['service']} (port {item['port']}) → {item['domain']}")

    print()

    return {
        'missing_proxies': missing_proxies,
        'orphaned_proxies': orphaned_proxies,
        'in_sync': in_sync
    }


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("""
Portainer-Synology Sync

Uses Portainer API as source of truth to sync with Synology reverse proxy.

Usage:
  python portainer_sync.py [command]

Commands:
  scan          Scan Portainer and show inventory
  sync          Compare Portainer with reverse proxy
  conflicts     Check for port conflicts
  create        Scan and offer to create missing proxy rules

Environment variables (from .env):
  PORTAINER_HOST        Portainer hostname (default: notmyproblemnas)
  PORTAINER_PORT        Portainer port (default: 9000)
  PORTAINER_USERNAME    Portainer username
  PORTAINER_PASSWORD    Portainer password
  SYNOLOGY_HOST         Synology hostname
  SYNOLOGY_PORT         Synology API port (default: 5000)
  SYNOLOGY_USERNAME     Synology username
  SYNOLOGY_PASSWORD     Synology password
        """)
        return 0

    # Get Portainer credentials
    portainer_host = os.getenv("PORTAINER_HOST", "notmyproblemnas")
    portainer_port = os.getenv("PORTAINER_PORT", "9000")
    portainer_username = os.getenv("PORTAINER_USERNAME", "admin")
    portainer_password = os.getenv("PORTAINER_PASSWORD")

    if not portainer_password:
        import getpass
        portainer_password = getpass.getpass("Portainer Password: ")

    # Build Portainer URL
    portainer_url = f"http://{portainer_host}:{portainer_port}"

    # Create Portainer client
    try:
        portainer = PortainerClient(portainer_url, portainer_username, portainer_password)
    except Exception as e:
        print(f"❌ Failed to connect to Portainer: {e}")
        return 1

    # Build inventory
    inventory = PortainerInventory(portainer)
    inventory.scan()

    command = sys.argv[1] if len(sys.argv) > 1 else 'scan'

    if command == 'scan':
        print_inventory(inventory)

        # Show port conflicts
        conflicts = inventory.check_port_conflicts()
        if conflicts:
            print("\n⚠️  PORT CONFLICTS:")
            for port, containers in conflicts.items():
                print(f"   Port {port}: {', '.join(containers)}")

    elif command == 'conflicts':
        conflicts = inventory.check_port_conflicts()
        if conflicts:
            print("\n⚠️  PORT CONFLICTS:")
            for port, containers in conflicts.items():
                print(f"   Port {port}: {', '.join(containers)}")
        else:
            print("✅ No port conflicts")

    elif command in ['sync', 'create']:
        # Get Synology credentials
        synology_host = os.getenv("SYNOLOGY_HOST", "notmyproblemnas")
        synology_port = os.getenv("SYNOLOGY_PORT", "5000")
        synology_username = os.getenv("SYNOLOGY_USERNAME", "akib_admin")
        synology_password = os.getenv("SYNOLOGY_PASSWORD")

        if not synology_password:
            import getpass
            synology_password = getpass.getpass("Synology Password: ")

        # Import reverse proxy manager
        from manage_reverse_proxy import SynologyReverseProxyManager

        try:
            manager = SynologyReverseProxyManager(
                synology_host, synology_port,
                synology_username, synology_password
            )
        except Exception as e:
            print(f"❌ Failed to connect to Synology: {e}")
            return 1

        # Generate sync report
        report = generate_sync_report(inventory, manager)

        # Offer to create missing rules
        if command == 'create' and report['missing_proxies']:
            print("\nWould you like to create the missing proxy rules? (y/n): ", end='')
            if input().strip().lower() == 'y':
                for item in report['missing_proxies']:
                    service_name = item['service']

                    # Check if service needs websocket
                    container_info = next(
                        (info for name, info in inventory.services.items() if info['service_name'] == service_name),
                        None
                    )

                    websocket = False
                    if container_info:
                        websocket = inventory._needs_websocket(
                            service_name,
                            container_info.get('image', '')
                        )

                    print(f"\nCreating proxy for {service_name}...")
                    success = manager.add_rule(
                        description=service_name,
                        frontend_domain=item['suggested_domain'],
                        backend_host='notmyproblemnas',
                        backend_port=item['port'],
                        hsts=True,
                        websocket=websocket
                    )

                    if not success:
                        print(f"   ⚠️  Failed to create rule for {service_name}")

    else:
        print(f"Unknown command: {command}")
        print("Run with --help for usage")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
