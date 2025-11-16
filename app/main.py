"""
Synology Infrastructure Manager
Streamlit UI for managing docker-compose services and reverse proxy rules
"""
import streamlit as st
import pandas as pd
import os
from pathlib import Path
from modules.inventory import InfrastructureInventory
from modules.reverse_proxy import SynologyReverseProxyManager

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

    # Portainer connection
    st.sidebar.subheader("Portainer Connection")

    with st.sidebar.expander("Portainer Settings", expanded=not st.session_state.portainer_connected):
        portainer_host = st.text_input("Portainer Host", value=os.getenv("PORTAINER_HOST", "notmyproblemnas"))
        portainer_port = st.text_input("Portainer Port", value=os.getenv("PORTAINER_PORT", "9000"))
        portainer_username = st.text_input("Portainer Username", value=os.getenv("PORTAINER_USERNAME", "admin"))
        portainer_password = st.text_input("Portainer Password", type="password", value=os.getenv("PORTAINER_PASSWORD", ""))

        if st.button("🔍 Scan Portainer", use_container_width=True):
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
        if st.sidebar.button("🔄 Refresh Inventory", use_container_width=True):
            if st.session_state.inventory:
                with st.spinner("Refreshing..."):
                    st.session_state.inventory.scan_stacks()
                    st.success("Refreshed!")
                    st.rerun()

    st.sidebar.divider()

    # Synology connection
    st.sidebar.subheader("Synology Connection")

    with st.sidebar.expander("Connection Settings", expanded=not st.session_state.authenticated):
        host = st.text_input("Host", value=os.getenv("SYNOLOGY_HOST", "notmyproblemnas"))
        port = st.text_input("Port", value=os.getenv("SYNOLOGY_PORT", "5000"))
        username = st.text_input("Username", value=os.getenv("SYNOLOGY_USERNAME", "akib_admin"))
        password = st.text_input("Password", type="password", value=os.getenv("SYNOLOGY_PASSWORD", ""))

        if st.button("🔐 Connect", use_container_width=True):
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
        if st.sidebar.button("🔓 Disconnect", use_container_width=True):
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
        use_container_width=True,
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
            use_container_width=True
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
        if st.button("🔄 Refresh", use_container_width=True):
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
        use_container_width=True,
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

    with st.form("add_rule_form", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            description = st.text_input(
                "Service Name *",
                placeholder="e.g., bazarr",
                help="Unique identifier for this rule"
            )

            frontend_domain = st.text_input(
                "Frontend Domain *",
                placeholder="e.g., bazarr.akibrhast.synology.me",
                help="Full domain name for HTTPS access"
            )

            backend_host = st.text_input(
                "Backend Host *",
                value="notmyproblemnas",
                help="Hostname or IP of the backend service"
            )

        with col2:
            suggested_port = manager.suggest_next_port()
            backend_port = st.number_input(
                "Backend Port *",
                min_value=1,
                max_value=65535,
                value=suggested_port,
                help="Port where the service is running"
            )

            hsts = st.checkbox("Enable HSTS", value=True, help="HTTP Strict Transport Security")
            websocket = st.checkbox("Enable WebSocket", value=False, help="For services requiring WebSocket support")

        # Validation warnings
        if description and manager.description_exists(description):
            st.warning(f"⚠️ Description '{description}' already exists")

        if frontend_domain and manager.domain_exists(frontend_domain):
            st.error(f"❌ Domain '{frontend_domain}' already exists")

        if backend_port:
            conflicts = manager.get_port_conflicts(backend_port)
            if conflicts:
                st.warning(f"⚠️ Port {backend_port} is already used by:")
                for conflict in conflicts:
                    st.caption(f"  • {conflict['description']} ({conflict['domain']})")

        submitted = st.form_submit_button("✅ Create Rule", use_container_width=True)

        if submitted:
            if not description or not frontend_domain or not backend_host:
                st.error("Please fill in all required fields")
            elif manager.description_exists(description):
                st.error(f"Description '{description}' already exists")
            elif manager.domain_exists(frontend_domain):
                st.error(f"Domain '{frontend_domain}' already exists")
            else:
                with st.spinner("Creating rule..."):
                    success, message = manager.add_rule(
                        description=description,
                        frontend_domain=frontend_domain,
                        backend_host=backend_host,
                        backend_port=backend_port,
                        hsts=hsts,
                        websocket=websocket
                    )

                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
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
        if st.button("🔄 Refresh Sync", use_container_width=True):
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
        st.dataframe(df_missing, use_container_width=True, hide_index=True)

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
        st.dataframe(df_orphaned, use_container_width=True, hide_index=True)

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
        st.dataframe(df_sync, use_container_width=True, hide_index=True)


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
