"""
Components specific to reverse proxy management
"""
import streamlit as st
import pandas as pd
from .ui_components import (
    section_header,
    confirmation_dialog,
    data_table,
    action_button,
    empty_state
)


def proxy_rules_table(manager):
    """
    Display reverse proxy rules table with selection and delete functionality

    Args:
        manager: SynologyReverseProxyManager instance

    Returns:
        None
    """
    # Initialize session state
    if 'selected_rule_ids' not in st.session_state:
        st.session_state.selected_rule_ids = []

    # Header with refresh button
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader("Current Reverse Proxy Rules")
    with col2:
        if action_button("Refresh", key="refresh_rules", icon="🔄", type="secondary"):
            manager.list_rules(refresh=True)
            st.session_state.selected_rule_ids = []
            st.rerun()

    # Get rules
    rules = manager.list_rules(refresh=False)

    if not rules:
        empty_state(
            "No reverse proxy rules found",
            icon="📭",
            action_label="Create New Rule",
            action_callback=None
        )
        return

    st.caption(f"Found {len(rules)} rules")

    # Debug expander
    with st.expander("🔍 Debug: API Response Structure", expanded=False):
        st.json(rules[0])
        st.caption("Available keys:")
        st.code(str(list(rules[0].keys())))

    # Convert to DataFrame
    rules_data = []
    for idx, rule in enumerate(rules):
        frontend = rule.get('frontend', {})
        backend = rule.get('backend', {})
        has_ws = len(rule.get('customize_headers', [])) > 0
        rule_uuid = rule.get('UUID', rule.get('uuid', f'rule_{idx}'))

        rules_data.append({
            'Select': False,
            'Description': rule.get('description'),
            'Domain': frontend.get('fqdn'),
            'Frontend Port': frontend.get('port'),
            'Backend Host': backend.get('fqdn'),
            'Backend Port': backend.get('port'),
            'HSTS': '✅' if frontend.get('https', {}).get('hsts') else '❌',
            'WebSocket': '✅' if has_ws else '❌',
            '_uuid': rule_uuid
        })

    df = pd.DataFrame(rules_data)

    # Search filter
    search = st.text_input("🔍 Search rules", placeholder="Search by description or domain...")
    if search:
        df = df[
            df['Description'].str.contains(search, case=False, na=False) |
            df['Domain'].str.contains(search, case=False, na=False)
        ]

    # Action buttons
    st.divider()
    col1, col2, col3 = st.columns(3)

    with col1:
        if action_button("Select All", key="select_all", icon="✅", type="secondary"):
            st.session_state.selected_rule_ids = df['_uuid'].tolist()
            st.rerun()

    with col2:
        if action_button("Deselect All", key="deselect_all", icon="❌", type="secondary"):
            st.session_state.selected_rule_ids = []
            st.rerun()

    with col3:
        selected_count = len(st.session_state.selected_rule_ids)
        delete_disabled = selected_count == 0

        if action_button(
            f"Delete Selected ({selected_count})",
            key="delete_selected",
            icon="🗑️",
            type="primary" if selected_count > 0 else "secondary",
            disabled=delete_disabled
        ):
            st.session_state.confirm_delete = True

    # Confirmation dialog
    if st.session_state.get('confirm_delete', False):
        selected_count = len(st.session_state.selected_rule_ids)
        confirm, cancel = confirmation_dialog(
            f"Are you sure you want to delete {selected_count} rule(s)?",
            confirm_label="Delete",
            cancel_label="Cancel"
        )

        if confirm:
            with st.spinner(f"Deleting {selected_count} rule(s)..."):
                success, message = manager.delete_rules_bulk(st.session_state.selected_rule_ids)

                if success:
                    st.success(f"✅ {message}")
                    st.session_state.selected_rule_ids = []
                    st.session_state.confirm_delete = False
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
                    st.session_state.confirm_delete = False

        if cancel:
            st.session_state.confirm_delete = False
            st.rerun()

    st.divider()

    # Data table
    edited_df = data_table(
        df,
        key="proxy_rules_table",
        column_config={
            "Select": st.column_config.CheckboxColumn(
                "Select",
                help="Select rules to delete",
                default=False,
            ),
            "Frontend Port": st.column_config.NumberColumn(format="%d"),
            "Backend Port": st.column_config.NumberColumn(format="%d"),
            "_uuid": None,
        },
        disabled_columns=["Description", "Domain", "Frontend Port", "Backend Host", "Backend Port", "HSTS", "WebSocket"]
    )

    # Update selection
    selected_rules = edited_df[edited_df['Select'] == True]['_uuid'].tolist()
    if selected_rules != st.session_state.selected_rule_ids:
        st.session_state.selected_rule_ids = selected_rules
        st.rerun()

    # Port usage summary
    st.divider()
    used_ports = manager.get_used_ports()
    st.caption(f"**Ports in use:** {', '.join(map(str, used_ports[:15]))}" +
               (f" ... ({len(used_ports)} total)" if len(used_ports) > 15 else ""))

    next_port = manager.suggest_next_port()
    st.caption(f"**Next available port:** {next_port}")
