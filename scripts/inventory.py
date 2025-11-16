#!/usr/bin/env python3
"""
Infrastructure Inventory Manager
Scans docker-compose files and syncs with reverse proxy
"""
import yaml
import json
import os
from pathlib import Path
from collections import defaultdict

class InfrastructureInventory:
    def __init__(self, stacks_dir):
        self.stacks_dir = Path(stacks_dir)
        self.services = {}
        self.scan_stacks()
    
    def scan_stacks(self):
        """Scan all docker-compose files"""
        for stack_dir in self.stacks_dir.iterdir():
            if not stack_dir.is_dir():
                continue
            
            compose_file = stack_dir / 'docker-compose.yml'
            if not compose_file.exists():
                continue
            
            with open(compose_file) as f:
                compose_data = yaml.safe_load(f)
            
            for service_name, config in compose_data.get('services', {}).items():
                # Extract port
                port = self._extract_port(config)
                
                # Determine if needs reverse proxy
                needs_proxy = self._needs_reverse_proxy(stack_dir, service_name)
                
                self.services[service_name] = {
                    'stack_dir': str(stack_dir),
                    'port': port,
                    'network_mode': config.get('network_mode'),
                    'needs_proxy': needs_proxy,
                    'image': config.get('image'),
                    'container_name': config.get('container_name', service_name)
                }
    
    def _extract_port(self, config):
        """Extract port from docker-compose config"""
        # Check network_mode: host first
        if config.get('network_mode') == 'host':
            # Try to extract from environment
            env = config.get('environment', {})
            if isinstance(env, dict):
                for key, value in env.items():
                    if 'PORT' in key.upper():
                        try:
                            return int(value)
                        except:
                            pass
            return None
        
        # Check ports mapping
        ports = config.get('ports', [])
        if ports:
            # Parse "8989:8989" format
            port_str = str(ports[0])
            external_port = port_str.split(':')[0]
            return int(external_port)
        
        return None
    
    def _needs_reverse_proxy(self, stack_dir, service_name):
        """Determine if service needs reverse proxy (has web UI)"""
        # Check for .proxy file or metadata
        proxy_file = stack_dir / '.proxy'
        if proxy_file.exists():
            with open(proxy_file) as f:
                data = yaml.safe_load(f)
                return data.get('enabled', True)
        
        # Default: assume services need proxy unless explicitly internal
        internal_services = ['database', 'redis', 'postgres', 'mysql', 'mariadb']
        return not any(internal in service_name.lower() for internal in internal_services)
    
    def check_port_conflicts(self):
        """Check for port conflicts"""
        port_usage = defaultdict(list)
        
        for service_name, info in self.services.items():
            port = info.get('port')
            if port:
                port_usage[port].append(service_name)
        
        conflicts = {port: names for port, names in port_usage.items() if len(names) > 1}
        return conflicts
    
    def generate_port_map(self):
        """Generate PORT_MAP.md"""
        lines = [
            "# Port Allocation Map",
            "",
            "Auto-generated from docker-compose files",
            f"Last updated: {os.popen('date').read().strip()}",
            "",
            "| Service | Port | Container | Needs Proxy | Image |",
            "|---------|------|-----------|-------------|-------|"
        ]
        
        for service_name in sorted(self.services.keys()):
            info = self.services[service_name]
            port = info.get('port', 'N/A')
            container = info.get('container_name', service_name)
            proxy = '✅' if info.get('needs_proxy') else '❌'
            image = info.get('image', 'N/A').split(':')[0]  # Remove tag
            
            lines.append(f"| {service_name} | {port} | {container} | {proxy} | {image} |")
        
        lines.extend([
            "",
            "## Port Conflicts",
            ""
        ])
        
        conflicts = self.check_port_conflicts()
        if conflicts:
            lines.append("⚠️ **CONFLICTS DETECTED:**")
            lines.append("")
            for port, services in conflicts.items():
                lines.append(f"- Port **{port}**: {', '.join(services)}")
        else:
            lines.append("✅ No port conflicts detected")
        
        lines.extend([
            "",
            "## Next Available Ports",
            ""
        ])
        
        used_ports = set(info['port'] for info in self.services.values() if info.get('port'))
        for start in [7000, 8000, 9000]:
            for port in range(start, start + 100):
                if port not in used_ports:
                    lines.append(f"- Starting from {start}00s: **{port}**")
                    break
        
        return '\n'.join(lines)
    
    def get_proxy_rules_needed(self):
        """Get list of services that need reverse proxy"""
        rules = []
        
        for service_name, info in self.services.items():
            if not info.get('needs_proxy'):
                continue
            
            port = info.get('port')
            if not port:
                continue
            
            rules.append({
                'service': service_name,
                'port': port,
                'suggested_domain': f"{service_name}.akibrhast.synology.me",
                'websocket': self._needs_websocket(service_name),
                'hsts': True
            })
        
        return rules
    
    def _needs_websocket(self, service_name):
        """Determine if service needs websocket"""
        websocket_services = ['plex', 'portainer', 'qbittorrent', 'immich', 'jellyfin']
        return any(ws in service_name.lower() for ws in websocket_services)
    
    def generate_sync_report(self, reverse_proxy_manager):
        """Compare inventory with actual reverse proxy rules"""
        # Get actual rules from Synology
        actual_rules = reverse_proxy_manager.list_rules(verbose=False)
        
        # Build lookup
        actual_by_port = {}
        for rule in actual_rules:
            port = rule.get('backend', {}).get('port')
            if port:
                actual_by_port[port] = rule
        
        # Compare
        report = {
            'missing_proxies': [],  # In compose but not in proxy
            'orphaned_proxies': [], # In proxy but not in compose
            'port_mismatches': [],  # Different ports
            'in_sync': []
        }
        
        # Check what's missing
        for service_name, info in self.services.items():
            if not info.get('needs_proxy'):
                continue
            
            port = info.get('port')
            if not port:
                continue
            
            if port not in actual_by_port:
                report['missing_proxies'].append({
                    'service': service_name,
                    'port': port,
                    'suggested_domain': f"{service_name}.akibrhast.synology.me"
                })
            else:
                report['in_sync'].append(service_name)
        
        # Check for orphaned rules
        known_ports = set(info['port'] for info in self.services.values() if info.get('port'))
        for rule in actual_rules:
            port = rule.get('backend', {}).get('port')
            if port and port not in known_ports:
                report['orphaned_proxies'].append({
                    'description': rule.get('description'),
                    'domain': rule.get('frontend', {}).get('fqdn'),
                    'port': port
                })
        
        return report


def print_sync_report(report):
    """Pretty print the sync report"""
    print("\n" + "=" * 60)
    print("INFRASTRUCTURE SYNC REPORT")
    print("=" * 60)
    
    if report['missing_proxies']:
        print("\n❌ Missing Reverse Proxy Rules:")
        print("   (Defined in docker-compose but not in proxy)")
        for item in report['missing_proxies']:
            print(f"   - {item['service']} (port {item['port']})")
            print(f"     Suggested: {item['suggested_domain']}")
    
    if report['orphaned_proxies']:
        print("\n⚠️  Orphaned Reverse Proxy Rules:")
        print("   (Defined in proxy but no matching docker-compose)")
        for item in report['orphaned_proxies']:
            print(f"   - {item['description']} ({item['domain']}) port {item['port']}")
    
    if report['in_sync']:
        print(f"\n✅ In Sync: {len(report['in_sync'])} services")
    
    print()


def main():
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--help':
        print("""
Infrastructure Inventory Manager

Commands:
  scan          Scan docker-compose files and show inventory
  sync          Compare with reverse proxy and show what's missing
  generate      Generate PORT_MAP.md
  conflicts     Check for port conflicts
        """)
        return
    
    # Scan infrastructure
    base_dir = Path(__file__).parent.parent
    stacks_dir = base_dir / 'stacks'
    
    print("🔍 Scanning docker-compose files...")
    inventory = InfrastructureInventory(stacks_dir)
    
    print(f"✅ Found {len(inventory.services)} services")
    print()
    
    command = sys.argv[1] if len(sys.argv) > 1 else 'scan'
    
    if command == 'scan':
        print("📋 Service Inventory:")
        print()
        for service, info in sorted(inventory.services.items()):
            port = info.get('port', 'N/A')
            proxy = '🌐' if info.get('needs_proxy') else '🔒'
            print(f"{proxy} {service:20s} Port: {str(port):5s}  {info.get('image', '')[:40]}")
    
    elif command == 'conflicts':
        conflicts = inventory.check_port_conflicts()
        if conflicts:
            print("⚠️  PORT CONFLICTS:")
            for port, services in conflicts.items():
                print(f"   Port {port}: {', '.join(services)}")
        else:
            print("✅ No port conflicts")
    
    elif command == 'generate':
        port_map = inventory.generate_port_map()
        output_file = base_dir / 'docs' / 'PORT_MAP.md'
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            f.write(port_map)
        
        print(f"✅ Generated: {output_file}")
    
    elif command == 'sync':
        # Load reverse proxy manager
        from dotenv import load_dotenv
        load_dotenv()
        
        # Import the manager (assuming it's in the same directory)
        sys.path.insert(0, str(Path(__file__).parent))
        from manage_reverse_proxy import SynologyReverseProxyManager
        
        host = os.getenv("SYNOLOGY_HOST", "notmyproblemnas")
        port = os.getenv("SYNOLOGY_PORT", "5000")
        username = os.getenv("SYNOLOGY_USERNAME", "akib_admin")
        password = os.getenv("SYNOLOGY_PASSWORD")
        
        if not password:
            import getpass
            password = getpass.getpass("Password: ")
        
        try:
            manager = SynologyReverseProxyManager(host, port, username, password)
            report = inventory.generate_sync_report(manager)
            print_sync_report(report)
            
            # Offer to create missing rules
            if report['missing_proxies']:
                print("Would you like to create the missing proxy rules? (y/n): ", end='')
                if input().strip().lower() == 'y':
                    for item in report['missing_proxies']:
                        print(f"\nCreating proxy for {item['service']}...")
                        manager.add_rule(
                            description=item['service'],
                            frontend_domain=item['suggested_domain'],
                            backend_host='notmyproblemnas',
                            backend_port=item['port'],
                            hsts=True,
                            websocket=False
                        )
        except Exception as e:
            print(f"❌ Failed to connect to Synology: {e}")
            return 1


if __name__ == '__main__':
    main()