import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any

# Modern color palette
COLORS = {
    # Primary colors
    "primary": "#6366F1",      # Indigo
    "secondary": "#8B5CF6",    # Purple
    "accent": "#EC4899",       # Pink
    
    # Status colors
    "success": "#10B981",      # Emerald
    "warning": "#F59E0B",      # Amber
    "error": "#EF4444",        # Red
    "info": "#3B82F6",         # Blue
    
    # Neutral colors
    "dark": "#1F2937",
    "medium": "#6B7280",
    "light": "#F3F4F6",
    "white": "#FFFFFF",
    
    # Population colors
    "ING": "#3B82F6",          # Blue
    "PREPA": "#F59E0B",        # Amber
    
    # Queue state colors
    "idle": "#10B981",
    "busy": "#EF4444",
    "waiting": "#F59E0B",
    
    # Gradient for heatmaps
    "gradient_start": "#6366F1",
    "gradient_end": "#EC4899",
}

# Color palettes for multi-series plots
PALETTE_CATEGORICAL = [
    "#6366F1", "#EC4899", "#10B981", "#F59E0B", 
    "#3B82F6", "#8B5CF6", "#14B8A6", "#F97316"
]

PALETTE_SEQUENTIAL = [
    "#E0E7FF", "#C7D2FE", "#A5B4FC", "#818CF8",
    "#6366F1", "#4F46E5", "#4338CA", "#3730A3"
]

# Figure sizes
FIGURE_SIZES = {
    "small": (8, 5),
    "medium": (10, 6),
    "large": (12, 8),
    "wide": (14, 6),
    "tall": (8, 10),
    "dashboard": (16, 10),
}


def set_theme(style: str = "default", context: str = "paper"):
    """
    Set the visualization theme.
    
    Args:
        style: "default", "dark", "presentation"
        context: "paper", "talk", "poster"
    """
    # Base seaborn style
    if style == "dark":
        sns.set_style("darkgrid")
        plt.rcParams["figure.facecolor"] = COLORS["dark"]
        plt.rcParams["axes.facecolor"] = "#111827"
        plt.rcParams["text.color"] = COLORS["white"]
        plt.rcParams["axes.labelcolor"] = COLORS["white"]
        plt.rcParams["xtick.color"] = COLORS["light"]
        plt.rcParams["ytick.color"] = COLORS["light"]
    else:
        sns.set_style("whitegrid")
        plt.rcParams["figure.facecolor"] = COLORS["white"]
        plt.rcParams["axes.facecolor"] = COLORS["white"]
        plt.rcParams["text.color"] = COLORS["dark"]
        plt.rcParams["axes.labelcolor"] = COLORS["dark"]
    
    # Context scaling
    sns.set_context(context)
    
    # Common settings
    plt.rcParams["font.family"] = "sans-serif"
    # Add DejaVu Sans for Linux compatibility
    plt.rcParams["font.sans-serif"] = ["Inter", "Helvetica", "Arial", "DejaVu Sans", "sans-serif"]
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.3
    plt.rcParams["legend.frameon"] = False
    plt.rcParams["figure.dpi"] = 100
    plt.rcParams["savefig.dpi"] = 150
    plt.rcParams["savefig.bbox"] = "tight"
    
    # Set default color cycle
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=PALETTE_CATEGORICAL)


def get_persona_style(persona: str) -> Dict[str, Any]:
    """
    Get visualization style for a specific persona view.
    
    Args:
        persona: "robert" (student), "valerie" (admin), "alex" (tech)
    
    Returns:
        Dictionary of style parameters
    """
    if persona.lower() == "robert":
        return {
            "focus_metrics": ["waiting_time", "sojourn_time", "rejection_rate"],
            "title_prefix": "📱 Vue Étudiant",
            "color": COLORS["info"],
            "highlight_threshold": {
                "waiting_time": 30,  # seconds
                "rejection_rate": 0.01,
            }
        }
    elif persona.lower() == "valerie":
        return {
            "focus_metrics": ["rejection_rate", "utilization", "cost"],
            "title_prefix": "📊 Vue Direction",
            "color": COLORS["secondary"],
            "highlight_threshold": {
                "sojourn_time": 120,  # 2 minutes
                "rejection_rate": 0.05,
            }
        }
    else:  # alex
        return {
            "focus_metrics": ["queue_length", "utilization", "bottleneck"],
            "title_prefix": "⚙️ Vue Technique",
            "color": COLORS["primary"],
            "highlight_threshold": {
                "queue_length": 100,
                "utilization": 0.95,
            }
        }


# Apply default theme on import
set_theme()
