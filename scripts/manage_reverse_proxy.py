#!/usr/bin/env python3
"""
Synology Reverse Proxy Manager
List, create, and validate reverse proxy rules with real-time validation
"""
import requests
import json
import os
import sys
import urllib3
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

class SynologyReverseProxyManager:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.session = None
        self.syno_token = None
        self.base_url = f"http://{host}:{port}"
        self.api_url = f"{self.base_url}/webapi/entry.cgi/SYNO.Core.AppPortal.ReverseProxy"
        self.rules_cache = None  # Cache rules for validation
        
        if not self.login(username, password):
            raise Exception("Login failed")
    
    def login(self, username, password):
        """Login and get session token"""
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
        response = self.session.get(url, params=params, verify=False)
        data = response.json()
        
        if not data.get("success"):
            print(f"❌ Login failed. Error: {data.get('error', {}).get('code')}")
            return False
        
        self.syno_token = data.get("data", {}).get("synotoken")
        print("✅ Logged in successfully\n")
        return True
    
    def list_rules(self, verbose=True, refresh=False):
        """List all reverse proxy rules"""
        if self.rules_cache and not refresh:
            rules = self.rules_cache
        else:
            data = {
                "api": "SYNO.Core.AppPortal.ReverseProxy",
                "version": "1",
                "method": "list"
            }
            
            headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
            if self.syno_token:
                headers["X-SYNO-TOKEN"] = self.syno_token
            
            response = self.session.post(self.api_url, data=data, headers=headers, verify=False)
            result = response.json()
            
            if not result.get("success"):
                print(f"❌ Failed to list rules")
                return []
            
            rules = result.get("data", {}).get("entries", [])
            self.rules_cache = rules  # Cache for validation
        
        if verbose:
            print(f"📋 Found {len(rules)} reverse proxy rules:\n")
            for i, rule in enumerate(rules, 1):
                desc = rule.get("description")
                frontend = rule.get("frontend", {})
                backend = rule.get("backend", {})
                ws = len(rule.get("customize_headers", [])) > 0
                
                print(f"{i:2d}. {desc}")
                print(f"    Frontend: {frontend.get('fqdn')}:{frontend.get('port')}")
                print(f"    Backend:  {backend.get('fqdn')}:{backend.get('port')}")
                print(f"    HSTS: {frontend.get('https', {}).get('hsts')}, WebSocket: {ws}")
                print()
        
        return rules
    
    def description_exists(self, description):
        """Check if description already exists"""
        rules = self.list_rules(verbose=False)
        return any(rule.get("description") == description for rule in rules)
    
    def domain_exists(self, domain):
        """Check if frontend domain already exists"""
        rules = self.list_rules(verbose=False)
        return any(rule.get("frontend", {}).get("fqdn") == domain for rule in rules)
    
    def get_port_conflicts(self, backend_port):
        """Get rules using the same backend port"""
        rules = self.list_rules(verbose=False)
        conflicts = []
        
        for rule in rules:
            if rule.get("backend", {}).get("port") == backend_port:
                conflicts.append({
                    'description': rule.get("description"),
                    'host': rule.get("backend", {}).get("fqdn"),
                    'port': backend_port
                })
        
        return conflicts
    
    def add_rule(self, description, frontend_domain, backend_host, backend_port, 
                 hsts=True, websocket=False):
        """Add a new reverse proxy rule"""
        
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
                "port": 443,
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
        
        if websocket:
            entry["customize_headers"] = [
                {"name": "Upgrade", "value": "$http_upgrade"},
                {"name": "Connection", "value": "$connection_upgrade"}
            ]
        
        data = {
            "api": "SYNO.Core.AppPortal.ReverseProxy",
            "version": "1",
            "method": "create",
            "entry": json.dumps(entry, separators=(',', ':'))
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
        if self.syno_token:
            headers["X-SYNO-TOKEN"] = self.syno_token
        
        response = self.session.post(self.api_url, data=data, headers=headers, verify=False)
        result = response.json()
        
        if result.get("success"):
            print(f"✅ Added: {description}")
            print(f"   {frontend_domain}:443 → {backend_host}:{backend_port}")
            self.rules_cache = None  # Invalidate cache
            return True
        else:
            error = result.get('error', {})
            error_code = error.get('code')
            print(f"❌ Failed to add rule. Error: {error_code}")
            
            if error_code == 4154:
                print("   Hint: Domain may already exist, be invalid, or not under your Synology account")
            elif error_code == 101:
                print("   Hint: Invalid parameter format")
            
            return False
    
    def get_available_ports(self):
        """Show which ports are already in use"""
        rules = self.list_rules(verbose=False)
        used_ports = set()
        
        for rule in rules:
            port = rule.get("backend", {}).get("port")
            if port:
                used_ports.add(port)
        
        return sorted(used_ports)
    
    def suggest_port(self, start_range=8000):
        """Suggest an available port"""
        used_ports = self.get_available_ports()
        
        for port in range(start_range, 65536):
            if port not in used_ports:
                return port
        return None


def get_validated_input(prompt, validator=None, error_msg="Invalid input"):
    """Get input with validation"""
    while True:
        value = input(prompt).strip()
        if not value:
            return None
        
        if validator is None or validator(value):
            return value
        
        print(f"❌ {error_msg}")


def interactive_add(manager):
    """Interactive mode to add a new rule with real-time validation"""
    print("=" * 60)
    print("Add New Reverse Proxy Rule")
    print("=" * 60)
    print()
    
    # Show current rules first
    print("Current rules:")
    print("-" * 60)
    manager.list_rules()
    
    # Show port usage
    used_ports = manager.get_available_ports()
    print(f"📊 Ports in use: {', '.join(map(str, used_ports[:10]))}" + 
          (f" ... ({len(used_ports)} total)" if len(used_ports) > 10 else ""))
    suggested_port = manager.suggest_port()
    print(f"💡 Next available port: {suggested_port}")
    print()
    
    print("=" * 60)
    print("New Rule Details:")
    print("=" * 60)
    
    # Get description with validation
    while True:
        description = input("Service name (e.g., 'bazarr'): ").strip()
        if not description:
            print("❌ Description is required")
            continue
        
        if manager.description_exists(description):
            print(f"❌ Description '{description}' already exists. Choose a different name.")
            continue
        
        break
    
    # Get frontend domain with validation
    while True:
        frontend_domain = input("Frontend domain (e.g., 'bazarr.akibrhast.synology.me'): ").strip()
        if not frontend_domain:
            print("❌ Frontend domain is required")
            continue
        
        if manager.domain_exists(frontend_domain):
            print(f"❌ Domain '{frontend_domain}' already exists. Choose a different domain.")
            # Show which rule is using it
            rules = manager.list_rules(verbose=False)
            for rule in rules:
                if rule.get("frontend", {}).get("fqdn") == frontend_domain:
                    existing_desc = rule.get("description")
                    print(f"   Currently used by: {existing_desc}")
            continue
        
        break
    
    backend_host = input("Backend host [notmyproblemnas]: ").strip() or "notmyproblemnas"
    
    # Get backend port with validation
    while True:
        backend_port_str = input(f"Backend port [{suggested_port}]: ").strip()
        backend_port = int(backend_port_str) if backend_port_str else suggested_port
        
        if backend_port < 1 or backend_port > 65535:
            print(f"❌ Invalid port: {backend_port}. Must be between 1-65535")
            continue
        
        # Check for port conflicts (warning only)
        conflicts = manager.get_port_conflicts(backend_port)
        if conflicts:
            print(f"⚠️  Port {backend_port} is already in use:")
            for conflict in conflicts:
                print(f"   - {conflict['description']} ({conflict['host']}:{conflict['port']})")
            
            confirm = input("Continue with this port anyway? (y/n): ").strip().lower()
            if confirm != 'y':
                continue
        
        break
    
    hsts = input("Enable HSTS? (y/n) [y]: ").strip().lower() != "n"
    websocket = input("Enable WebSocket? (y/n) [n]: ").strip().lower() == "y"
    
    print()
    print("=" * 60)
    print("Summary:")
    print("=" * 60)
    print(f"Description:  {description}")
    print(f"Frontend:     https://{frontend_domain}:443")
    print(f"Backend:      http://{backend_host}:{backend_port}")
    print(f"HSTS:         {hsts}")
    print(f"WebSocket:    {websocket}")
    print()
    
    confirm = input("Create this rule? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Aborted")
        return False
    
    print()
    return manager.add_rule(description, frontend_domain, backend_host, 
                           backend_port, hsts, websocket)


def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("""
Synology Reverse Proxy Manager

Usage:
  python manage-reverse-proxy.py [command]

Commands:
  (none)    Interactive mode - list rules and optionally add new one
  list      List all rules and exit
  add       Add a new rule interactively
  ports     Show port usage

Environment variables (from .env):
  SYNOLOGY_HOST        Synology hostname
  SYNOLOGY_PORT        API port (default: 5000)
  SYNOLOGY_USERNAME    Username
  SYNOLOGY_PASSWORD    Password
        """)
        return 0
    
    # Get credentials
    host = os.getenv("SYNOLOGY_HOST", "notmyproblemnas")
    port = os.getenv("SYNOLOGY_PORT", "5000")
    username = os.getenv("SYNOLOGY_USERNAME", "akib_admin")
    password = os.getenv("SYNOLOGY_PASSWORD")
    
    if not password:
        import getpass
        password = getpass.getpass("Password: ")
    
    # Create manager
    try:
        manager = SynologyReverseProxyManager(host, port, username, password)
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return 1
    
    # Handle commands
    command = sys.argv[1] if len(sys.argv) > 1 else None
    
    if command == "list":
        manager.list_rules()
        return 0
    
    elif command == "ports":
        used_ports = manager.get_available_ports()
        print(f"📊 Ports in use ({len(used_ports)} total):\n")
        for port in used_ports:
            print(f"  {port}")
        print()
        suggested = manager.suggest_port()
        print(f"💡 Next available port: {suggested}")
        return 0
    
    elif command == "add" or command is None:
        # Interactive mode
        if command is None:
            print("Current Configuration:")
            print("=" * 60)
            manager.list_rules()
            print()
            
            add_new = input("Add a new rule? (y/n): ").strip().lower()
            if add_new != 'y':
                return 0
            print()
        
        success = interactive_add(manager)
        return 0 if success else 1
    
    else:
        print(f"Unknown command: {command}")
        print("Run with --help for usage")
        return 1


if __name__ == "__main__":
    exit(main())
