"""
Synology Infrastructure Manager
Streamlit UI for managing docker-compose services and reverse proxy rules
"""
import streamlit as st
import pandas as pd
import os
from pathlib import Path
from dotenv import load_dotenv
from modules.inventory import InfrastructureInventory
from modules.reverse_proxy import SynologyReverseProxyManager

# Load environment variables from .env file
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Synology Infrastructure Manager",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    .warning-box {
        padding: 1rem;
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    if 'inventory' not in st.session_state:
        st.session_state.inventory = None
    if 'proxy_manager' not in st.session_state:
        st.session_state.proxy_manager = None
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'portainer_connected' not in st.session_state:
        st.session_state.portainer_connected = False


def sidebar_config():
    """Sidebar configuration and authentication"""
    st.sidebar.title("⚙️ Configuration")

    # Auto-connect to Portainer if credentials are available
    if not st.session_state.portainer_connected and 'portainer_auto_connect_attempted' not in st.session_state:
        portainer_password = os.getenv("PORTAINER_PASSWORD", "")
        if portainer_password:
            st.session_state.portainer_auto_connect_attempted = True
            with st.spinner("Auto-connecting to Portainer..."):
                try:
                    inventory = InfrastructureInventory(
                        os.getenv("PORTAINER_HOST", "notmyproblemnas"),
                        os.getenv("PORTAINER_PORT", "9000"),
                        os.getenv("PORTAINER_USERNAME", "admin"),
                        portainer_password
                    )
                    if inventory.is_authenticated():
                        inventory.scan_stacks()
                        st.session_state.inventory = inventory
                        st.session_state.portainer_connected = True
                        st.rerun()
                except Exception:
                    pass  # Silently fail auto-connect, user can manually connect

    # Portainer connection
    st.sidebar.subheader("Portainer Connection")

    with st.sidebar.expander("Portainer Settings", expanded=not st.session_state.portainer_connected):
        portainer_host = st.text_input("Portainer Host", value=os.getenv("PORTAINER_HOST", "notmyproblemnas"))
        portainer_port = st.text_input("Portainer Port", value=os.getenv("PORTAINER_PORT", "9000"))
        portainer_username = st.text_input("Portainer Username", value=os.getenv("PORTAINER_USERNAME", "admin"))
        portainer_password = st.text_input("Portainer Password", type="password", value=os.getenv("PORTAINER_PASSWORD", ""))

        if st.button("🔍 Scan Portainer", width="stretch"):
            if not portainer_password:
                st.error("Portainer password required")
            else:
                with st.spinner("Connecting to Portainer and scanning containers..."):
                    try:
                        inventory = InfrastructureInventory(
                            portainer_host,
                            portainer_port,
                            portainer_username,
                            portainer_password
                        )

                        if not inventory.is_authenticated():
                            st.error(f"Portainer connection failed: {inventory.get_error_message()}")
                        else:
                            inventory.scan_stacks()
                            st.session_state.inventory = inventory
                            st.session_state.portainer_connected = True
                            st.success(f"✅ Found {len(inventory.services)} services")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Scan failed: {str(e)}")

    if st.session_state.portainer_connected:
        st.sidebar.success("✅ Connected to Portainer")
        if st.sidebar.button("🔄 Refresh Inventory", width="stretch"):
            if st.session_state.inventory:
                with st.spinner("Refreshing..."):
                    st.session_state.inventory.scan_stacks()
                    st.success("Refreshed!")
                    st.rerun()

    st.sidebar.divider()

    # Auto-connect to Synology if credentials are available
    if not st.session_state.authenticated and 'synology_auto_connect_attempted' not in st.session_state:
        synology_password = os.getenv("SYNOLOGY_PASSWORD", "")
        if synology_password:
            st.session_state.synology_auto_connect_attempted = True
            with st.spinner("Auto-connecting to Synology..."):
                try:
                    manager = SynologyReverseProxyManager(
                        os.getenv("SYNOLOGY_HOST", "notmyproblemnas"),
                        os.getenv("SYNOLOGY_PORT", "5000"),
                        os.getenv("SYNOLOGY_USERNAME", "akib_admin"),
                        synology_password
                    )
                    if manager.authenticated:
                        st.session_state.proxy_manager = manager
                        st.session_state.authenticated = True
                        st.rerun()
                except Exception:
                    pass  # Silently fail auto-connect, user can manually connect

    # Synology connection
    st.sidebar.subheader("Synology Connection")

    with st.sidebar.expander("Connection Settings", expanded=not st.session_state.authenticated):
        host = st.text_input("Host", value=os.getenv("SYNOLOGY_HOST", "notmyproblemnas"))
        port = st.text_input("Port", value=os.getenv("SYNOLOGY_PORT", "5000"))
        username = st.text_input("Username", value=os.getenv("SYNOLOGY_USERNAME", "akib_admin"))
        password = st.text_input("Password", type="password", value=os.getenv("SYNOLOGY_PASSWORD", ""))

        if st.button("🔐 Connect", width="stretch"):
            if not password:
                st.error("Password required")
            else:
                with st.spinner("Connecting to Synology..."):
                    try:
                        manager = SynologyReverseProxyManager(host, port, username, password)
                        if manager.authenticated:
                            st.session_state.proxy_manager = manager
                            st.session_state.authenticated = True
                            st.success("Connected successfully!")
                            st.rerun()
                        else:
                            st.error(f"Authentication failed: {manager.error_message}")
                    except Exception as e:
                        st.error(f"Connection error: {str(e)}")

    if st.session_state.authenticated:
        st.sidebar.success("✅ Connected to Synology")
        if st.sidebar.button("🔓 Disconnect", width="stretch"):
            st.session_state.proxy_manager = None
            st.session_state.authenticated = False
            st.rerun()


def inventory_tab():
    """Inventory management tab"""
    st.header("📋 Infrastructure Inventory")

    inventory = st.session_state.inventory

    if inventory is None:
        st.info("👈 Click 'Scan Portainer' in the sidebar to begin")
        return

    if len(inventory.services) == 0:
        st.warning("No services found in Portainer.")
        return

    # Statistics
    stats = inventory.get_statistics()
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Total Services", stats['total_services'])
    with col2:
        st.metric("Running", stats['running_services'])
    with col3:
        st.metric("With Ports", stats['services_with_ports'])
    with col4:
        st.metric("Need Proxy", stats['services_needing_proxy'])
    with col5:
        conflict_count = stats['port_conflicts']
        st.metric(
            "Port Conflicts",
            conflict_count,
            delta=None if conflict_count == 0 else "Action needed",
            delta_color="off" if conflict_count == 0 else "inverse"
        )

    st.divider()

    # Port conflicts section
    conflicts = inventory.check_port_conflicts()
    if conflicts:
        st.subheader("⚠️ Port Conflicts")
        for port, services in conflicts.items():
            st.error(f"**Port {port}** is used by: {', '.join(services)}")
        st.divider()

    # Services table
    st.subheader("Services Overview")

    # Convert to DataFrame
    services_data = []
    for name, info in inventory.services.items():
        state = info.get('state', 'unknown')
        state_icon = '✅' if state == 'running' else '⏸️' if state == 'exited' else '❓'

        # Get all ports and proxy port
        all_ports = info.get('ports', [])
        proxy_port = info.get('port')

        # Format ports display
        if all_ports:
            if len(all_ports) > 1:
                # Show all ports, highlight the proxy port
                ports_str = ', '.join(str(p) for p in all_ports)
                if proxy_port in all_ports:
                    ports_str = f"{ports_str} (→{proxy_port})"
            else:
                ports_str = str(all_ports[0])
        else:
            ports_str = 'N/A'

        services_data.append({
            'State': state_icon,
            'Service': info.get('service_name', name),
            'Container': info.get('container_name', name),
            'Stack': info.get('stack_dir', 'N/A'),
            'Ports': ports_str,
            'Image': info.get('image', 'N/A').split(':')[0] if info.get('image') else 'N/A',
            'Needs Proxy': '✅' if info.get('needs_proxy') else '❌'
        })

    df = pd.DataFrame(services_data)

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_state = st.selectbox(
            "Filter by State",
            options=["All", "Running", "Stopped"]
        )
    with col2:
        filter_proxy = st.selectbox(
            "Filter by Proxy Need",
            options=["All", "Needs Proxy", "No Proxy"]
        )
    with col3:
        search = st.text_input("Search services", "")

    # Apply filters
    if filter_state == "Running":
        df = df[df['State'] == '✅']
    elif filter_state == "Stopped":
        df = df[df['State'] != '✅']

    if filter_proxy == "Needs Proxy":
        df = df[df['Needs Proxy'] == '✅']
    elif filter_proxy == "No Proxy":
        df = df[df['Needs Proxy'] == '❌']

    if search:
        df = df[df['Service'].str.contains(search, case=False) | df['Container'].str.contains(search, case=False)]

    # Display table
    st.dataframe(
        df,
        width="stretch",
        hide_index=True
    )

    # Export options
    st.divider()
    col1, col2 = st.columns([3, 1])
    with col2:
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Export CSV",
            data=csv,
            file_name="infrastructure_inventory.csv",
            mime="text/csv",
            width="stretch"
        )


def proxy_tab():
    """Reverse proxy management tab"""
    st.header("🌐 Reverse Proxy Manager")

    if not st.session_state.authenticated:
        st.info("👈 Connect to Synology in the sidebar to manage reverse proxy rules")
        return

    manager = st.session_state.proxy_manager

    # Tabs for different operations
    proxy_subtab1, proxy_subtab2 = st.tabs(["📋 Current Rules", "➕ Add New Rule"])

    with proxy_subtab1:
        show_current_rules(manager)

    with proxy_subtab2:
        add_new_rule_form(manager)


def show_current_rules(manager):
    """Display current reverse proxy rules"""
    col1, col2 = st.columns([4, 1])

    with col2:
        if st.button("🔄 Refresh", width="stretch"):
            manager.list_rules(refresh=True)
            st.rerun()

    rules = manager.list_rules(refresh=False)

    if not rules:
        st.info("No reverse proxy rules found")
        return

    st.subheader(f"Found {len(rules)} Rules")

    # Convert to DataFrame
    rules_data = []
    for rule in rules:
        frontend = rule.get('frontend', {})
        backend = rule.get('backend', {})
        has_ws = len(rule.get('customize_headers', [])) > 0

        rules_data.append({
            'ID': rule.get('id'),
            'Description': rule.get('description'),
            'Domain': frontend.get('fqdn'),
            'Frontend Port': frontend.get('port'),
            'Backend Host': backend.get('fqdn'),
            'Backend Port': backend.get('port'),
            'HSTS': '✅' if frontend.get('https', {}).get('hsts') else '❌',
            'WebSocket': '✅' if has_ws else '❌'
        })

    df = pd.DataFrame(rules_data)

    # Search
    search = st.text_input("Search rules", "")
    if search:
        df = df[
            df['Description'].str.contains(search, case=False) |
            df['Domain'].str.contains(search, case=False)
        ]

    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn(width="small"),
            "Frontend Port": st.column_config.NumberColumn(format="%d"),
            "Backend Port": st.column_config.NumberColumn(format="%d"),
        }
    )

    # Port usage summary
    st.divider()
    used_ports = manager.get_used_ports()
    st.caption(f"**Ports in use:** {', '.join(map(str, used_ports[:15]))}" +
               (f" ... ({len(used_ports)} total)" if len(used_ports) > 15 else ""))

    next_port = manager.suggest_next_port()
    st.caption(f"**Next available port:** {next_port}")


def add_new_rule_form(manager):
    """Form to add new reverse proxy rule"""
    st.subheader("Create New Proxy Rule")

    # Ensure we have fresh rules for validation
    if 'last_rules_refresh' not in st.session_state or st.session_state.last_rules_refresh is None:
        manager.list_rules(refresh=True)
        st.session_state.last_rules_refresh = True

    # Use columns for side-by-side layout
    col1, col2 = st.columns(2)

    with col1:
        description = st.text_input(
            "Service Name *",
            placeholder="e.g., bazarr",
            help="Unique identifier for this rule",
            key="new_rule_description"
        )

        frontend_domain = st.text_input(
            "Frontend Domain *",
            placeholder="e.g., bazarr.akibrhast.synology.me",
            help="Full domain name for HTTPS access",
            key="new_rule_domain"
        )

        backend_host = st.text_input(
            "Backend Host *",
            value="notmyproblemnas",
            help="Hostname or IP of the backend service",
            key="new_rule_host"
        )

    with col2:
        frontend_port = st.number_input(
            "Frontend Port (Source) *",
            min_value=1,
            max_value=65535,
            value=443,
            help="HTTPS port that users connect to (usually 443)",
            key="new_rule_frontend_port"
        )

        suggested_port = manager.suggest_next_port()
        backend_port = st.number_input(
            "Backend Port (Destination) *",
            min_value=1,
            max_value=65535,
            value=suggested_port,
            help="Port where the service is running",
            key="new_rule_backend_port"
        )

        hsts = st.checkbox("Enable HSTS", value=True, help="HTTP Strict Transport Security", key="new_rule_hsts")
        websocket = st.checkbox("Enable WebSocket", value=False, help="For services requiring WebSocket support", key="new_rule_ws")

    # Real-time validation (shows as user types)
    has_errors = False
    is_valid = True

    # Check required fields
    if not description or not frontend_domain or not backend_host:
        is_valid = False

    # Check domain:port conflict (BLOCKER - same domain CAN be used with different ports)
    if frontend_domain and frontend_port:
        # Get all rules and check for conflicts
        rules = manager.list_rules()

        # Debug: Show total rules loaded
        st.caption(f"🔍 Debug: Total rules loaded: {len(rules)}")

        matching_domain_rules = [r for r in rules if r.get("frontend", {}).get("fqdn") == frontend_domain]

        # Debug output - always show for debugging
        if matching_domain_rules:
            st.warning(f"🔍 Debug: Found {len(matching_domain_rules)} existing rules for domain '{frontend_domain}'")
            for rule in matching_domain_rules:
                existing_port = rule.get("frontend", {}).get("port")
                st.caption(f"  - Existing: {rule.get('description')} on port {existing_port} (type: {type(existing_port).__name__})")
            st.caption(f"  - Checking: port {frontend_port} (type: {type(frontend_port).__name__})")
        else:
            st.caption(f"🔍 Debug: No existing rules found for domain '{frontend_domain}'")

        # Check if exact domain:port exists
        conflict_exists = manager.domain_port_exists(frontend_domain, frontend_port)
        st.caption(f"🔍 Debug: domain_port_exists() returned: {conflict_exists}")

        if conflict_exists:
            st.error(f"❌ Domain '{frontend_domain}:{frontend_port}' already exists")
            has_errors = True
            is_valid = False
        elif matching_domain_rules:
            # Same domain exists on different port - show info with details
            existing_ports = [r.get("frontend", {}).get("port") for r in matching_domain_rules]
            st.info(f"ℹ️ Domain '{frontend_domain}' is already used on port(s): {', '.join(map(str, existing_ports))}")

    # Check description conflict (WARNING only - descriptions can be similar)
    if description and manager.description_exists(description):
        st.warning(f"⚠️ Description '{description}' already exists")

    # Check backend port conflict (INFO only - same port can be used for different domains)
    if backend_port:
        conflicts = manager.get_port_conflicts(backend_port)
        if conflicts:
            st.info(f"ℹ️ Backend port {backend_port} is already used by:")
            for conflict in conflicts:
                st.caption(f"  • {conflict['description']} ({conflict['domain']})")

    st.divider()

    # Create button - disabled until all fields valid and no errors
    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 2])
    with col_btn2:
        create_clicked = st.button(
            "✅ Create Rule",
            width="stretch",
            disabled=not is_valid,
            type="primary"
        )

    if create_clicked:
        # Validate required fields
        if not description or not frontend_domain or not backend_host:
            st.error("❌ Please fill in all required fields")
        elif manager.domain_port_exists(frontend_domain, frontend_port):
            st.error(f"❌ Domain '{frontend_domain}:{frontend_port}' already exists")
        else:
            with st.spinner("Creating rule..."):
                success, message = manager.add_rule(
                    description=description,
                    frontend_domain=frontend_domain,
                    backend_host=backend_host,
                    backend_port=backend_port,
                    frontend_port=frontend_port,
                    hsts=hsts,
                    websocket=websocket
                )

                if success:
                    st.success(f"✅ {message}")
                    st.balloons()
                    # Clear the form by resetting session state
                    for key in ['new_rule_description', 'new_rule_domain', 'new_rule_host',
                                'new_rule_frontend_port', 'new_rule_backend_port', 'new_rule_hsts', 'new_rule_ws']:
                        if key in st.session_state:
                            del st.session_state[key]
                    st.rerun()
                else:
                    st.error(f"❌ {message}")


def sync_tab():
    """Sync inventory with reverse proxy"""
    st.header("🔄 Sync Inventory with Proxy")

    if not st.session_state.authenticated:
        st.info("👈 Connect to Synology in the sidebar")
        return

    if st.session_state.inventory is None:
        st.info("👈 Scan infrastructure first")
        return

    inventory = st.session_state.inventory
    manager = st.session_state.proxy_manager

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Refresh Sync", width="stretch"):
            manager.list_rules(refresh=True)
            st.rerun()

    # Generate sync report
    with st.spinner("Analyzing sync status..."):
        report = manager.generate_sync_report(inventory.services)

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ In Sync", len(report['in_sync']))
    with col2:
        st.metric("❌ Missing Proxies", len(report['missing_proxies']))
    with col3:
        st.metric("⚠️ Orphaned Proxies", len(report['orphaned_proxies']))

    st.divider()

    # Missing proxies
    if report['missing_proxies']:
        st.subheader("❌ Missing Reverse Proxy Rules")
        st.caption("Services defined in docker-compose but not in reverse proxy")

        missing_data = []
        for item in report['missing_proxies']:
            missing_data.append({
                'Service': item['service'],
                'Port': item['port'],
                'Stack': item['stack'],
                'Suggested Domain': f"{item['service']}.akibrhast.synology.me"
            })

        df_missing = pd.DataFrame(missing_data)
        st.dataframe(df_missing, width="stretch", hide_index=True)

        # Auto-create option
        if st.button("🚀 Auto-Create Missing Proxies", type="primary"):
            with st.spinner("Creating proxy rules..."):
                created = 0
                failed = 0

                progress_bar = st.progress(0)
                status_text = st.empty()

                for idx, item in enumerate(report['missing_proxies']):
                    status_text.text(f"Creating proxy for {item['service']}...")

                    success, message = manager.add_rule(
                        description=item['service'],
                        frontend_domain=f"{item['service']}.akibrhast.synology.me",
                        backend_host='notmyproblemnas',
                        backend_port=item['port'],
                        hsts=True,
                        websocket=False
                    )

                    if success:
                        created += 1
                    else:
                        failed += 1

                    progress_bar.progress((idx + 1) / len(report['missing_proxies']))

                status_text.empty()
                progress_bar.empty()

                if created > 0:
                    st.success(f"✅ Created {created} proxy rules")
                if failed > 0:
                    st.warning(f"⚠️ Failed to create {failed} rules")

                st.rerun()

    # Orphaned proxies
    if report['orphaned_proxies']:
        st.divider()
        st.subheader("⚠️ Orphaned Reverse Proxy Rules")
        st.caption("Rules in reverse proxy but no matching docker-compose service")

        orphaned_data = []
        for item in report['orphaned_proxies']:
            orphaned_data.append({
                'ID': item['id'],
                'Description': item['description'],
                'Domain': item['domain'],
                'Port': item['port']
            })

        df_orphaned = pd.DataFrame(orphaned_data)
        st.dataframe(df_orphaned, width="stretch", hide_index=True)

        st.caption("💡 These may be legacy rules or external services not managed by docker-compose")

    # In sync
    if report['in_sync']:
        st.divider()
        st.subheader("✅ Services In Sync")

        sync_data = []
        for item in report['in_sync']:
            sync_data.append({
                'Service': item['service'],
                'Port': item['port'],
                'Domain': item['domain']
            })

        df_sync = pd.DataFrame(sync_data)
        st.dataframe(df_sync, width="stretch", hide_index=True)


def main():
    """Main application"""
    init_session_state()

    # Header
    st.markdown('<p class="main-header">🖥️ Synology Infrastructure Manager</p>', unsafe_allow_html=True)

    # Sidebar
    sidebar_config()

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📋 Inventory", "🌐 Reverse Proxy", "🔄 Sync"])

    with tab1:
        inventory_tab()

    with tab2:
        proxy_tab()

    with tab3:
        sync_tab()


if __name__ == "__main__":
    main()
