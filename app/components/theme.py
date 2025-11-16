"""
Theme and styling configuration
"""

# Color palette
COLORS = {
    "primary": "#1f77b4",
    "secondary": "#ff7f0e",
    "success": "#2ca02c",
    "warning": "#ffcc00",
    "error": "#d62728",
    "info": "#17a2b8",
    "light": "#f0f2f6",
    "dark": "#262730",
    "text": "#31333F",
    "text_light": "#808495",
}

# Custom CSS styles
CUSTOM_CSS = """
<style>
    /* Card styles */
    .custom-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }

    .success-card {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
    }

    .warning-card {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
    }

    .error-card {
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
    }

    /* Header styles */
    .section-header {
        font-size: 1.8rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
        color: #31333F;
    }

    .section-subtitle {
        font-size: 0.9rem;
        color: #808495;
        margin-bottom: 1rem;
    }

    /* Badge styles */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.5rem;
        border-radius: 0.25rem;
        font-size: 0.85rem;
        font-weight: 600;
        margin: 0 0.25rem;
    }

    .badge-success {
        background-color: #d4edda;
        color: #155724;
    }

    .badge-warning {
        background-color: #fff3cd;
        color: #856404;
    }

    .badge-error {
        background-color: #f8d7da;
        color: #721c24;
    }

    .badge-info {
        background-color: #d1ecf1;
        color: #0c5460;
    }

    /* Table styles */
    .dataframe {
        font-size: 0.9rem;
    }

    /* Button styles */
    .stButton > button {
        transition: all 0.3s ease;
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }

    /* Metric styles */
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
    }

    /* Compact spacing */
    .compact {
        margin: 0.25rem 0;
        padding: 0.25rem 0;
    }

    /* Status indicators */
    .status-running {
        color: #28a745;
        font-weight: bold;
    }

    .status-stopped {
        color: #dc3545;
        font-weight: bold;
    }

    .status-unknown {
        color: #6c757d;
        font-weight: bold;
    }

    /* Empty state */
    .empty-state {
        text-align: center;
        padding: 3rem 1rem;
        color: #808495;
    }

    .empty-state-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }

    /* Loading overlay */
    .loading-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        z-index: 9999;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* Tooltips */
    .tooltip {
        position: relative;
        display: inline-block;
        cursor: help;
    }

    /* Responsive adjustments */
    @media (max-width: 768px) {
        .section-header {
            font-size: 1.5rem;
        }

        .metric-container {
            padding: 0.5rem;
        }
    }
</style>
"""


def apply_custom_theme():
    """Apply custom theme to the Streamlit app"""
    import streamlit as st
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def get_status_icon(status):
    """Get icon for status"""
    status_icons = {
        "running": "✅",
        "stopped": "⏸️",
        "error": "❌",
        "warning": "⚠️",
        "unknown": "❓",
        "success": "✅",
    }
    return status_icons.get(status.lower(), "❓")


def get_status_color(status):
    """Get color for status"""
    status_colors = {
        "running": COLORS["success"],
        "stopped": COLORS["error"],
        "error": COLORS["error"],
        "warning": COLORS["warning"],
        "unknown": COLORS["text_light"],
        "success": COLORS["success"],
    }
    return status_colors.get(status.lower(), COLORS["text"])
