"""
Reusable UI components for consistent styling
"""
import streamlit as st


def metric_card(label, value, delta=None, delta_color="normal", help_text=None):
    """
    Display a metric card with consistent styling

    Args:
        label: Metric label
        value: Metric value
        delta: Optional delta/change indicator
        delta_color: Color for delta ("normal", "inverse", "off")
        help_text: Optional tooltip text
    """
    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )


def info_box(message, type="info"):
    """
    Display an info box with consistent styling

    Args:
        message: Message to display
        type: Box type ("info", "success", "warning", "error")
    """
    if type == "info":
        st.info(message)
    elif type == "success":
        st.success(message)
    elif type == "warning":
        st.warning(message)
    elif type == "error":
        st.error(message)


def section_header(title, subtitle=None, icon=None):
    """
    Display a section header with optional subtitle and icon

    Args:
        title: Section title
        subtitle: Optional subtitle/description
        icon: Optional emoji icon
    """
    header_text = f"{icon} {title}" if icon else title
    st.header(header_text)

    if subtitle:
        st.caption(subtitle)

    st.divider()


def action_button(label, key=None, type="primary", disabled=False, help_text=None, icon=None, on_click=None):
    """
    Display a styled action button

    Args:
        label: Button label
        key: Unique key for the button
        type: Button type ("primary", "secondary")
        disabled: Whether button is disabled
        help_text: Optional tooltip
        icon: Optional emoji icon
        on_click: Optional callback function
    """
    button_label = f"{icon} {label}" if icon else label

    return st.button(
        button_label,
        key=key,
        type=type,
        disabled=disabled,
        help=help_text,
        use_container_width=True,
        on_click=on_click
    )


def confirmation_dialog(message, confirm_label="Yes", cancel_label="No", confirm_callback=None, cancel_callback=None):
    """
    Display a confirmation dialog with Yes/No buttons

    Args:
        message: Confirmation message
        confirm_label: Label for confirm button
        cancel_label: Label for cancel button
        confirm_callback: Function to call on confirm
        cancel_callback: Function to call on cancel

    Returns:
        Tuple of (confirm_clicked, cancel_clicked)
    """
    st.warning(f"⚠️ {message}")

    col1, col2 = st.columns(2)

    with col1:
        confirm = st.button(
            f"✅ {confirm_label}",
            type="primary",
            use_container_width=True,
            on_click=confirm_callback
        )

    with col2:
        cancel = st.button(
            f"❌ {cancel_label}",
            use_container_width=True,
            on_click=cancel_callback
        )

    return confirm, cancel


def data_table(df, key, column_config=None, disabled_columns=None, hide_index=True):
    """
    Display an editable data table with consistent styling

    Args:
        df: DataFrame to display
        key: Unique key for the table
        column_config: Column configuration dict
        disabled_columns: List of columns to disable editing
        hide_index: Whether to hide the index

    Returns:
        Edited DataFrame
    """
    return st.data_editor(
        df,
        hide_index=hide_index,
        use_container_width=True,
        column_config=column_config,
        disabled=disabled_columns,
        key=key
    )


def stats_row(stats_dict):
    """
    Display a row of statistics/metrics

    Args:
        stats_dict: Dictionary of {label: value} or {label: (value, delta)}
    """
    cols = st.columns(len(stats_dict))

    for col, (label, stat) in zip(cols, stats_dict.items()):
        with col:
            if isinstance(stat, tuple):
                value, delta = stat
                st.metric(label, value, delta=delta)
            else:
                st.metric(label, stat)


def filter_section(filters_config):
    """
    Display a filter section with multiple filter controls

    Args:
        filters_config: List of dicts with filter configurations
            Example: [
                {"type": "selectbox", "label": "Status", "options": ["All", "Active"]},
                {"type": "text_input", "label": "Search", "placeholder": "Enter text..."}
            ]

    Returns:
        Dictionary of filter values
    """
    cols = st.columns(len(filters_config))
    filter_values = {}

    for col, config in zip(cols, filters_config):
        with col:
            filter_type = config.get("type")
            label = config.get("label")
            key = config.get("key", label.lower().replace(" ", "_"))

            if filter_type == "selectbox":
                filter_values[key] = st.selectbox(
                    label,
                    options=config.get("options", []),
                    key=f"filter_{key}"
                )
            elif filter_type == "text_input":
                filter_values[key] = st.text_input(
                    label,
                    placeholder=config.get("placeholder", ""),
                    key=f"filter_{key}"
                )
            elif filter_type == "multiselect":
                filter_values[key] = st.multiselect(
                    label,
                    options=config.get("options", []),
                    key=f"filter_{key}"
                )

    return filter_values


def loading_spinner(message="Loading..."):
    """
    Context manager for loading spinner

    Usage:
        with loading_spinner("Fetching data..."):
            # do work
            pass
    """
    return st.spinner(message)


def empty_state(message, icon="📭", action_label=None, action_callback=None):
    """
    Display an empty state message

    Args:
        message: Empty state message
        icon: Emoji icon
        action_label: Optional action button label
        action_callback: Optional action button callback
    """
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 2rem;">
                <div style="font-size: 4rem;">{icon}</div>
                <p style="font-size: 1.2rem; color: #666;">{message}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if action_label and action_callback:
            if st.button(action_label, use_container_width=True, on_click=action_callback):
                pass


def card(title, content=None, icon=None, color=None):
    """
    Display a card component

    Args:
        title: Card title
        content: Card content (can be a function)
        icon: Optional emoji icon
        color: Optional background color
    """
    bg_color = color or "#f0f2f6"

    st.markdown(
        f"""
        <div style="background-color: {bg_color}; padding: 1rem; border-radius: 0.5rem; margin: 0.5rem 0;">
            <h4>{icon + ' ' if icon else ''}{title}</h4>
        </div>
        """,
        unsafe_allow_html=True
    )

    if callable(content):
        content()
    elif content:
        st.write(content)
