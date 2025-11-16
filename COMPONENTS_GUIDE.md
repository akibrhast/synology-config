# Components Guide

This guide explains the new componentized UI structure for the Synology Infrastructure Manager.

## 📁 Structure

```
app/
├── components/
│   ├── __init__.py
│   ├── ui_components.py       # Reusable UI components
│   ├── theme.py               # Theme and styling
│   └── proxy_components.py    # Domain-specific components
├── modules/
│   ├── inventory.py
│   └── reverse_proxy.py
└── main.py                    # Main application (now much cleaner!)
```

## 🎨 Available Components

### From `ui_components.py`:

#### 1. **section_header(title, subtitle, icon)**
Creates consistent section headers with optional subtitle and icon.

```python
section_header("Reverse Proxy Manager", "Manage your proxy rules", icon="🌐")
```

#### 2. **stats_row(stats_dict)**
Display a row of metrics/statistics.

```python
stats_row({
    "Total Services": 15,
    "Running": (12, "+2"),  # With delta
    "Stopped": 3
})
```

#### 3. **action_button(label, key, type, icon, ...)**
Styled action button with consistent appearance.

```python
action_button("Refresh", key="refresh_btn", icon="🔄", type="secondary")
```

#### 4. **empty_state(message, icon, action_label, action_callback)**
Display empty state messages with optional action button.

```python
empty_state(
    "No rules found",
    icon="📭",
    action_label="Create First Rule",
    action_callback=create_rule_fn
)
```

#### 5. **confirmation_dialog(message, confirm_label, cancel_label)**
Reusable confirmation dialog.

```python
confirm, cancel = confirmation_dialog(
    "Are you sure?",
    confirm_label="Delete",
    cancel_label="Cancel"
)
```

#### 6. **data_table(df, key, column_config, disabled_columns)**
Consistent table styling with edit capabilities.

```python
edited_df = data_table(
    df,
    key="my_table",
    column_config={"Select": st.column_config.CheckboxColumn(...)},
    disabled_columns=["Name", "Domain"]
)
```

#### 7. **filter_section(filters_config)**
Create filter controls easily.

```python
filters = filter_section([
    {"type": "selectbox", "label": "Status", "options": ["All", "Active"]},
    {"type": "text_input", "label": "Search", "placeholder": "Search..."}
])
```

### From `theme.py`:

#### 1. **apply_custom_theme()**
Apply global theme (already called in main.py).

#### 2. **COLORS dictionary**
Access color palette:
```python
from components.theme import COLORS
st.markdown(f"<div style='color: {COLORS['primary']}'>Text</div>")
```

#### 3. **get_status_icon(status)** and **get_status_color(status)**
Get consistent icons and colors for statuses:
```python
icon = get_status_icon("running")  # Returns "✅"
color = get_status_color("error")  # Returns "#d62728"
```

### From `proxy_components.py`:

#### 1. **proxy_rules_table(manager)**
Complete proxy rules table with selection, deletion, and filtering.

```python
proxy_rules_table(manager)
```

## 🎯 Benefits

### Before (Old Code):
```python
def show_current_rules(manager):
    # 150+ lines of table logic, selection, deletion, etc.
    if 'selected_rule_ids' not in st.session_state:
        st.session_state.selected_rule_ids = []

    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 Refresh", width="stretch"):
            # ...
    # ... 140 more lines
```

### After (New Code):
```python
def show_current_rules(manager):
    """Display current reverse proxy rules using componentized version"""
    proxy_rules_table(manager)
```

## 🚀 Creating New Components

### Example: Create a new metrics component

```python
# In components/ui_components.py
def service_health_card(service_name, status, uptime, memory_usage):
    """Display service health information"""
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.markdown(f"### {service_name}")
            status_icon = get_status_icon(status)
            st.markdown(f"{status_icon} {status.title()}")

        with col2:
            st.metric("Uptime", uptime)

        with col3:
            st.metric("Memory", memory_usage)
```

### Usage:
```python
from components.ui_components import service_health_card

service_health_card("Portainer", "running", "5d 3h", "128MB")
```

## 📊 What Was Refactored

### main.py Changes:

1. **Imports** - Added component imports
2. **Theme** - Replaced inline CSS with `apply_custom_theme()`
3. **Headers** - All headers now use `section_header()`
4. **Empty States** - All info messages now use `empty_state()`
5. **Metrics** - All metrics now use `stats_row()`
6. **Buttons** - Action buttons now use `action_button()`
7. **Proxy Table** - Complete table moved to `proxy_rules_table()`

### Lines of Code Reduction:
- **Before**: ~785 lines in main.py
- **After**: ~650 lines in main.py (+ reusable components)
- **Benefit**: 135+ lines moved to reusable components that can be used anywhere

## 🎨 Customizing Styles

### Global Theme Colors

Edit `components/theme.py`:

```python
COLORS = {
    "primary": "#1f77b4",      # Change this
    "secondary": "#ff7f0e",    # And this
    "success": "#2ca02c",
    # ...
}
```

### Custom CSS Styles

Add to `CUSTOM_CSS` in `components/theme.py`:

```python
CUSTOM_CSS = """
<style>
    /* Your custom styles */
    .my-custom-class {
        background-color: #f0f2f6;
        border-radius: 8px;
    }
</style>
"""
```

## 💡 Best Practices

1. **Consistency** - Always use components instead of raw Streamlit calls
2. **Reusability** - If you write the same UI code twice, make it a component
3. **Single Responsibility** - Each component should do one thing well
4. **Documentation** - Add docstrings to all components
5. **Type Hints** - Use type hints for component parameters

## 🔧 Next Steps

To further componentize:

1. Create `inventory_components.py` for inventory-specific UI
2. Create `sync_components.py` for sync-specific UI
3. Add more theme variants (dark mode, light mode)
4. Create a component library documentation page
5. Add component unit tests

## 📝 Example: Full Component Usage

```python
from components.ui_components import (
    section_header,
    stats_row,
    action_button,
    empty_state,
    confirmation_dialog
)
from components.theme import COLORS, get_status_icon
from components.proxy_components import proxy_rules_table

def my_custom_tab():
    # Header
    section_header("My Feature", "Description here", icon="🎯")

    # Stats
    stats_row({
        "Total": 100,
        "Active": (75, "+5"),
        "Inactive": 25
    })

    # Empty state check
    if no_data:
        empty_state("No data found", icon="📭")
        return

    # Action button
    if action_button("Do Something", key="my_btn", icon="✨", type="primary"):
        # Handle action
        pass

    # Confirmation
    if st.session_state.get('needs_confirm'):
        confirm, cancel = confirmation_dialog("Are you sure?")
        if confirm:
            # Do action
            pass
```

---

**Built with ❤️ for better code organization and maintainability**
