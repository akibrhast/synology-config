"""
Infrastructure Inventory Manager - Portainer Edition
Uses Portainer API as source of truth for infrastructure inventory
"""
import requests
import urllib3
from collections import defaultdict

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PortainerClient:
    """Client for Portainer API"""

    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.token = None
        self.session = requests.Session()
        self.authenticated = False
        self.error_message = None

        # Authenticate
        self.authenticate()

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

                self.authenticated = True
                self.error_message = None
                return True
            else:
                self.authenticated = False
                try:
                    error_data = response.json()
                    self.error_message = f"Authentication failed ({response.status_code}): {error_data.get('message', 'Unknown error')}"
                except:
                    self.error_message = f"Authentication failed ({response.status_code})"
                return False

        except Exception as e:
            self.authenticated = False
            self.error_message = f"Connection error: {str(e)}"
            return False

    def get_endpoints(self):
        """Get all endpoints (Docker environments)"""
        if not self.authenticated:
            return []

        url = f"{self.base_url}/api/endpoints"

        try:
            response = self.session.get(url, verify=False, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                self.error_message = f"Failed to get endpoints: {response.status_code}"
                return []

        except Exception as e:
            self.error_message = f"Error getting endpoints: {str(e)}"
            return []

    def get_stacks(self, endpoint_id):
        """Get all stacks for an endpoint"""
        if not self.authenticated:
            return []

        url = f"{self.base_url}/api/stacks"

        try:
            response = self.session.get(url, verify=False, timeout=10)

            if response.status_code == 200:
                stacks = response.json()
                # Filter by endpoint
                return [s for s in stacks if s.get('EndpointId') == endpoint_id]
            else:
                return []

        except Exception as e:
            return []

    def get_containers(self, endpoint_id):
        """Get all containers for an endpoint"""
        if not self.authenticated:
            return []

        url = f"{self.base_url}/api/endpoints/{endpoint_id}/docker/containers/json"
        params = {'all': 'true'}  # Include stopped containers

        try:
            response = self.session.get(url, params=params, verify=False, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                return []

        except Exception as e:
            return []


class InfrastructureInventory:
    """Manages infrastructure inventory from Portainer API"""

    def __init__(self, portainer_host, portainer_port, username, password):
        # Build Portainer URL
        portainer_url = f"http://{portainer_host}:{portainer_port}"

        self.client = PortainerClient(portainer_url, username, password)
        self.services = {}
        self.endpoints = []
        self.stacks = []
        self.containers = []

    def is_authenticated(self):
        """Check if Portainer connection is authenticated"""
        return self.client.authenticated

    def get_error_message(self):
        """Get last error message"""
        return self.client.error_message

    def scan_stacks(self):
        """Scan Portainer for all services"""
        if not self.client.authenticated:
            return

        # Get endpoints
        self.endpoints = self.client.get_endpoints()

        # For each endpoint, get stacks and containers
        for endpoint in self.endpoints:
            endpoint_id = endpoint.get('Id')

            # Get stacks
            stacks = self.client.get_stacks(endpoint_id)
            self.stacks.extend(stacks)

            # Get containers
            containers = self.client.get_containers(endpoint_id)
            self.containers.extend(containers)

        # Build service inventory from containers
        self._build_inventory()

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
                'stack_dir': stack_name,  # Use stack name instead of directory
                'image': image,
                'state': state,
                'ports': ports,  # All published ports
                'port': proxy_port,  # Port used for reverse proxy (for sync)
                'needs_proxy': needs_proxy,
                'labels': labels,
                'network_mode': labels.get('com.docker.compose.network_mode', 'default')
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
        """Check for port conflicts across services"""
        port_usage = defaultdict(list)

        for container_name, info in self.services.items():
            port = info.get('port')
            if port:
                port_usage[port].append(container_name)

        conflicts = {
            port: names
            for port, names in port_usage.items()
            if len(names) > 1
        }
        return conflicts

    def get_services_needing_proxy(self):
        """Get list of services that need reverse proxy"""
        return {
            name: info
            for name, info in self.services.items()
            if info.get('needs_proxy') and info.get('port') and info.get('state') == 'running'
        }

    def get_next_available_port(self, start=8000, end=9000):
        """Find next available port in range"""
        used_ports = set(
            info['port']
            for info in self.services.values()
            if info.get('port')
        )

        for port in range(start, end):
            if port not in used_ports:
                return port
        return None

    def _needs_websocket(self, service_name, image):
        """Determine if service likely needs websocket support"""
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

    def generate_proxy_suggestions(self, domain_suffix="akibrhast.synology.me"):
        """Generate suggested reverse proxy rules for services"""
        suggestions = []

        for container_name, info in self.services.items():
            if not info.get('needs_proxy'):
                continue

            if info.get('state') != 'running':
                continue

            port = info.get('port')
            if not port:
                continue

            # Use service name for domain (cleaner than container name)
            service_name = info.get('service_name', container_name)

            suggestions.append({
                'service': service_name,
                'port': port,
                'suggested_domain': f"{service_name}.{domain_suffix}",
                'websocket': self._needs_websocket(service_name, info.get('image', '')),
                'hsts': True,
                'stack': info.get('stack_dir')
            })

        return suggestions

    def get_statistics(self):
        """Get inventory statistics"""
        total_services = len(self.services)
        running_services = sum(1 for s in self.services.values() if s.get('state') == 'running')
        services_with_ports = sum(1 for s in self.services.values() if s.get('port'))
        services_needing_proxy = sum(
            1 for s in self.services.values()
            if s.get('needs_proxy') and s.get('state') == 'running'
        )
        conflicts = len(self.check_port_conflicts())

        return {
            'total_services': total_services,
            'running_services': running_services,
            'services_with_ports': services_with_ports,
            'services_needing_proxy': services_needing_proxy,
            'port_conflicts': conflicts
        }
