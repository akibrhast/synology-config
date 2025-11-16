"""
Synology Reverse Proxy Manager
Manages reverse proxy rules via Synology API
"""
import requests
import json
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SynologyReverseProxyManager:
    """Manages Synology reverse proxy rules via API"""

    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.session = None
        self.syno_token = None
        self.base_url = f"http://{host}:{port}"
        self.api_url = f"{self.base_url}/webapi/entry.cgi/SYNO.Core.AppPortal.ReverseProxy"
        self.rules_cache = None
        self.authenticated = False
        self.error_message = None

        # Attempt login
        self.login(username, password)

    def login(self, username, password):
        """Login and get session token"""
        try:
            url = f"{self.base_url}/webapi/auth.cgi"
            params = {
                "api": "SYNO.API.Auth",
                "version": "7",
                "method": "login",
                "account": username,
                "passwd": password,
                "session": "ReverseProxy",
                "format": "cookie"
            }

            self.session = requests.Session()
            response = self.session.get(url, params=params, verify=False, timeout=10)
            data = response.json()

            if not data.get("success"):
                error_code = data.get('error', {}).get('code')
                self.error_message = f"Login failed. Error code: {error_code}"
                self.authenticated = False
                return False

            self.syno_token = data.get("data", {}).get("synotoken")
            self.authenticated = True
            self.error_message = None
            return True

        except requests.exceptions.RequestException as e:
            self.error_message = f"Connection error: {str(e)}"
            self.authenticated = False
            return False
        except Exception as e:
            self.error_message = f"Unexpected error: {str(e)}"
            self.authenticated = False
            return False

    def list_rules(self, refresh=False):
        """List all reverse proxy rules"""
        if not self.authenticated:
            return []

        if self.rules_cache and not refresh:
            return self.rules_cache

        try:
            data = {
                "api": "SYNO.Core.AppPortal.ReverseProxy",
                "version": "1",
                "method": "list"
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
            if self.syno_token:
                headers["X-SYNO-TOKEN"] = self.syno_token

            response = self.session.post(self.api_url, data=data, headers=headers, verify=False, timeout=10)
            result = response.json()

            if not result.get("success"):
                self.error_message = "Failed to list rules"
                return []

            rules = result.get("data", {}).get("entries", [])
            self.rules_cache = rules
            return rules

        except Exception as e:
            self.error_message = f"Error listing rules: {str(e)}"
            return []

    def description_exists(self, description):
        """Check if description already exists"""
        rules = self.list_rules()
        return any(rule.get("description") == description for rule in rules)

    def domain_exists(self, domain):
        """Check if frontend domain already exists (deprecated - use domain_port_exists instead)"""
        rules = self.list_rules()
        return any(rule.get("frontend", {}).get("fqdn") == domain for rule in rules)

    def domain_port_exists(self, domain, port):
        """Check if frontend domain:port combination already exists"""
        rules = self.list_rules()
        for rule in rules:
            frontend = rule.get("frontend", {})
            # Convert both to int for comparison to handle type mismatches
            existing_port = frontend.get("port")
            if existing_port is not None:
                try:
                    if frontend.get("fqdn") == domain and int(existing_port) == int(port):
                        return True
                except (ValueError, TypeError):
                    # If conversion fails, do string comparison
                    if frontend.get("fqdn") == domain and str(existing_port) == str(port):
                        return True
        return False

    def get_port_conflicts(self, backend_port):
        """Get rules using the same backend port"""
        rules = self.list_rules()
        conflicts = []

        for rule in rules:
            if rule.get("backend", {}).get("port") == backend_port:
                conflicts.append({
                    'description': rule.get("description"),
                    'domain': rule.get("frontend", {}).get("fqdn"),
                    'host': rule.get("backend", {}).get("fqdn"),
                    'port': backend_port
                })

        return conflicts

    def get_used_ports(self):
        """Get all ports currently in use by reverse proxy rules"""
        rules = self.list_rules()
        used_ports = set()

        for rule in rules:
            port = rule.get("backend", {}).get("port")
            if port:
                used_ports.add(port)

        return sorted(used_ports)

    def suggest_next_port(self, start_range=8000):
        """Suggest next available port"""
        used_ports = self.get_used_ports()

        for port in range(start_range, 65536):
            if port not in used_ports:
                return port
        return None

    def add_rule(self, description, frontend_domain, backend_host, backend_port,
                 frontend_port=443, hsts=True, websocket=False):
        """Add a new reverse proxy rule"""
        if not self.authenticated:
            return False, "Not authenticated"

        # Build rule entry
        entry = {
            "description": description,
            "proxy_connect_timeout": 60,
            "proxy_read_timeout": 60,
            "proxy_send_timeout": 60,
            "proxy_http_version": 1,
            "proxy_intercept_errors": False,
            "frontend": {
                "acl": None,
                "fqdn": frontend_domain,
                "port": frontend_port,
                "protocol": 1,
                "https": {"hsts": hsts}
            },
            "backend": {
                "fqdn": backend_host,
                "port": backend_port,
                "protocol": 0
            },
            "customize_headers": []
        }

        # Add websocket headers if needed
        if websocket:
            entry["customize_headers"] = [
                {"name": "Upgrade", "value": "$http_upgrade"},
                {"name": "Connection", "value": "$connection_upgrade"}
            ]

        try:
            data = {
                "api": "SYNO.Core.AppPortal.ReverseProxy",
                "version": "1",
                "method": "create",
                "entry": json.dumps(entry, separators=(',', ':'))
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
            if self.syno_token:
                headers["X-SYNO-TOKEN"] = self.syno_token

            response = self.session.post(self.api_url, data=data, headers=headers, verify=False, timeout=10)
            result = response.json()

            if result.get("success"):
                self.rules_cache = None  # Invalidate cache
                return True, "Rule added successfully"
            else:
                error = result.get('error', {})
                error_code = error.get('code')

                if error_code == 4154:
                    return False, "Domain may already exist, be invalid, or not under your Synology account"
                elif error_code == 101:
                    return False, "Invalid parameter format"
                else:
                    return False, f"Error code: {error_code}"

        except Exception as e:
            return False, f"Exception: {str(e)}"

    def delete_rule(self, rule_id):
        """Delete a reverse proxy rule by ID"""
        if not self.authenticated:
            return False, "Not authenticated"

        try:
            data = {
                "api": "SYNO.Core.AppPortal.ReverseProxy",
                "version": "1",
                "method": "delete",
                "id": json.dumps([rule_id])
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
            if self.syno_token:
                headers["X-SYNO-TOKEN"] = self.syno_token

            response = self.session.post(self.api_url, data=data, headers=headers, verify=False, timeout=10)
            result = response.json()

            if result.get("success"):
                self.rules_cache = None  # Invalidate cache
                return True, "Rule deleted successfully"
            else:
                error_code = result.get('error', {}).get('code')
                return False, f"Delete failed. Error code: {error_code}"

        except Exception as e:
            return False, f"Exception: {str(e)}"

    def delete_rules_bulk(self, rule_uuids):
        """Delete multiple reverse proxy rules by UUIDs"""
        if not self.authenticated:
            return False, "Not authenticated"

        if not rule_uuids:
            return False, "No rule UUIDs provided"

        try:
            data = {
                "api": "SYNO.Core.AppPortal.ReverseProxy",
                "version": "1",
                "method": "delete",
                "uuids": json.dumps(rule_uuids)
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
            if self.syno_token:
                headers["X-SYNO-TOKEN"] = self.syno_token

            response = self.session.post(self.api_url, data=data, headers=headers, verify=False, timeout=10)
            result = response.json()

            if result.get("success"):
                self.rules_cache = None  # Invalidate cache
                count = len(rule_uuids)
                return True, f"{count} rule{'s' if count > 1 else ''} deleted successfully"
            else:
                error_code = result.get('error', {}).get('code')
                return False, f"Delete failed. Error code: {error_code}"

        except Exception as e:
            return False, f"Exception: {str(e)}"

    def generate_sync_report(self, inventory_services):
        """Compare inventory with actual reverse proxy rules"""
        actual_rules = self.list_rules(refresh=True)

        # Build lookup by port
        actual_by_port = {}
        for rule in actual_rules:
            port = rule.get('backend', {}).get('port')
            if port:
                actual_by_port[port] = rule

        # Compare
        report = {
            'missing_proxies': [],  # In inventory but not in proxy
            'orphaned_proxies': [],  # In proxy but not in inventory
            'in_sync': []
        }

        # Check what's missing from proxy
        for service_name, info in inventory_services.items():
            if not info.get('needs_proxy'):
                continue

            port = info.get('port')
            if not port:
                continue

            if port not in actual_by_port:
                report['missing_proxies'].append({
                    'service': service_name,
                    'port': port,
                    'stack': info.get('stack_dir')
                })
            else:
                report['in_sync'].append({
                    'service': service_name,
                    'port': port,
                    'domain': actual_by_port[port].get('frontend', {}).get('fqdn')
                })

        # Check for orphaned rules
        known_ports = set(
            info['port']
            for info in inventory_services.values()
            if info.get('port')
        )

        for rule in actual_rules:
            port = rule.get('backend', {}).get('port')
            if port and port not in known_ports:
                report['orphaned_proxies'].append({
                    'description': rule.get('description'),
                    'domain': rule.get('frontend', {}).get('fqdn'),
                    'port': port,
                    'id': rule.get('id')
                })

        return report
