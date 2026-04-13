"""GUI styles and theme definitions - Modern Dark Theme."""

# =============================================================================
# COLOR PALETTE - Modern Dark Theme
# =============================================================================
# Based on a refined dark palette optimized for long coding sessions
# Emphasis on reduced eye strain and clear visual hierarchy

COLORS = {
    # Core backgrounds (from darkest to lightest)
    "bg_base": "#0f1115",          # Main app background
    "bg_surface": "#161a22",       # Cards, panels
    "bg_elevated": "#1c212b",      # Elevated surfaces, modals
    "bg_hover": "#242a36",         # Hover states
    "bg_active": "#2d3442",        # Active/selected states

    # Text colors (high to low emphasis)
    "text_primary": "#e6edf3",     # Primary text, headings
    "text_secondary": "#9da7b3",   # Secondary text, labels
    "text_tertiary": "#6b7280",    # Muted text, hints
    "text_disabled": "#4b5563",    # Disabled text

    # Borders (subtle)
    "border": "#2a2f3a",           # Default borders
    "border_hover": "#3d4451",     # Hover borders
    "border_focus": "#4f8cff",     # Focus rings

    # Brand / Primary
    "primary": "#4f8cff",          # Primary actions
    "primary_hover": "#6ba1ff",    # Primary hover
    "primary_pressed": "#3d7aed",  # Primary pressed
    "primary_muted": "#1e3a5f",    # Primary backgrounds

    # Status colors
    "success": "#22c55e",
    "success_muted": "#14532d",
    "warning": "#f59e0b",
    "warning_muted": "#78350f",
    "error": "#ef4444",
    "error_muted": "#7f1d1d",
    "info": "#3b82f6",
    "info_muted": "#1e3a5f",

    # Special
    "sidebar_bg": "#0d1117",
    "scrollbar": "#3d4451",
    "scrollbar_hover": "#4f5563",
}

# Status colors for different run states
STATUS_COLORS = {
    "pending": "#f59e0b",
    "planning": "#3b82f6",
    "executing": "#3b82f6",
    "reviewing": "#8b5cf6",
    "validating": "#06b6d4",
    "committing": "#10b981",
    "completed": "#22c55e",
    "failed": "#ef4444",
    "cancelled": "#6b7280",
    "checkpoint": "#f59e0b",
    "running": "#3b82f6",
    "executando": "#3b82f6",
    "concluido": "#22c55e",
    "falhou": "#ef4444",
    "iniciando": "#3b82f6",
}

# =============================================================================
# MAIN STYLESHEET - Modern Dark
# =============================================================================
MAIN_STYLESHEET = """
/* =========================================================================
   GLOBAL RESET & BASE
   ========================================================================= */
* {
    margin: 0;
    padding: 0;
}

QMainWindow, QWidget {
    background-color: #0f1115;
    color: #e6edf3;
    font-family: "Segoe UI", "Inter", -apple-system, system-ui, sans-serif;
    font-size: 13px;
    font-weight: 400;
}

QMainWindow {
    background-color: #0f1115;
}

/* =========================================================================
   SIDEBAR
   ========================================================================= */
#sidebar {
    background-color: #0d1117;
    border: none;
    border-right: 1px solid #2a2f3a;
}

#sidebar QLabel {
    background: transparent;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #9da7b3;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
    margin: 1px 6px;
}

#sidebar QPushButton:hover {
    background-color: #1c212b;
    color: #e6edf3;
}

#sidebar QPushButton:checked {
    background-color: #4f8cff;
    color: #ffffff;
}

#sidebar QPushButton:checked:hover {
    background-color: #6ba1ff;
}

/* =========================================================================
   CONTENT AREA
   ========================================================================= */
#content_area {
    background-color: #0f1115;
}

/* =========================================================================
   TYPOGRAPHY
   ========================================================================= */
QLabel {
    color: #e6edf3;
    background: transparent;
}

QLabel#header, QLabel[heading="true"] {
    font-size: 18px;
    font-weight: 600;
    color: #e6edf3;
    padding: 0;
    margin: 0;
}

QLabel#subheader, QLabel[subheading="true"] {
    font-size: 13px;
    font-weight: 400;
    color: #9da7b3;
}

QLabel[muted="true"] {
    color: #6b7280;
}

/* =========================================================================
   BUTTONS
   ========================================================================= */
QPushButton {
    background-color: #4f8cff;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 7px 14px;
    font-weight: 500;
    font-size: 13px;
    min-height: 18px;
}

QPushButton:hover {
    background-color: #6ba1ff;
}

QPushButton:pressed {
    background-color: #3d7aed;
}

QPushButton:disabled {
    background-color: #2d3442;
    color: #4b5563;
}

/* Secondary button */
QPushButton#secondary,
QPushButton[secondary="true"] {
    background-color: transparent;
    color: #e6edf3;
    border: 1px solid #2a2f3a;
}

QPushButton#secondary:hover,
QPushButton[secondary="true"]:hover {
    background-color: #1c212b;
    border-color: #3d4451;
}

/* Ghost button */
QPushButton#ghost,
QPushButton[ghost="true"] {
    background-color: transparent;
    color: #9da7b3;
    border: none;
    padding: 6px 12px;
}

QPushButton#ghost:hover,
QPushButton[ghost="true"]:hover {
    background-color: #1c212b;
    color: #e6edf3;
}

/* Success button */
QPushButton#success,
QPushButton[success="true"] {
    background-color: #22c55e;
}

QPushButton#success:hover,
QPushButton[success="true"]:hover {
    background-color: #16a34a;
}

/* Danger button */
QPushButton#danger,
QPushButton[danger="true"] {
    background-color: #ef4444;
}

QPushButton#danger:hover,
QPushButton[danger="true"]:hover {
    background-color: #dc2626;
}

/* Small button */
QPushButton[size="small"] {
    padding: 4px 10px;
    font-size: 12px;
    min-height: 16px;
}

/* =========================================================================
   TEXT INPUTS
   ========================================================================= */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #161a22;
    border: 1px solid #2a2f3a;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
    color: #e6edf3;
    selection-background-color: #4f8cff;
    selection-color: #ffffff;
}

QLineEdit:hover, QTextEdit:hover, QPlainTextEdit:hover {
    border-color: #3d4451;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #4f8cff;
    outline: none;
}

QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {
    background-color: #0f1115;
    color: #4b5563;
    border-color: #1c212b;
}

QLineEdit::placeholder {
    color: #6b7280;
}

/* =========================================================================
   COMBO BOXES
   ========================================================================= */
QComboBox {
    background-color: #161a22;
    border: 1px solid #2a2f3a;
    border-radius: 6px;
    padding: 7px 10px;
    padding-right: 28px;
    color: #e6edf3;
    min-width: 100px;
}

QComboBox:hover {
    border-color: #3d4451;
}

QComboBox:focus {
    border-color: #4f8cff;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
    background: transparent;
}

QComboBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #9da7b3;
    margin-right: 8px;
}

QComboBox QAbstractItemView {
    background-color: #1c212b;
    color: #e6edf3;
    border: 1px solid #2a2f3a;
    border-radius: 6px;
    padding: 4px;
    selection-background-color: #4f8cff;
    selection-color: #ffffff;
    outline: none;
}

QComboBox QAbstractItemView::item {
    padding: 8px 12px;
    border-radius: 4px;
}

QComboBox QAbstractItemView::item:hover {
    background-color: #242a36;
}

/* =========================================================================
   CHECKBOXES & RADIO BUTTONS
   ========================================================================= */
QCheckBox, QRadioButton {
    spacing: 8px;
    color: #e6edf3;
    background: transparent;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3d4451;
    border-radius: 4px;
    background-color: #161a22;
}

QCheckBox::indicator:hover {
    border-color: #4f8cff;
}

QCheckBox::indicator:checked {
    background-color: #4f8cff;
    border-color: #4f8cff;
}

QRadioButton::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #3d4451;
    border-radius: 8px;
    background-color: #161a22;
}

QRadioButton::indicator:hover {
    border-color: #4f8cff;
}

QRadioButton::indicator:checked {
    background-color: #4f8cff;
    border-color: #4f8cff;
}

/* =========================================================================
   SPIN BOXES
   ========================================================================= */
QSpinBox, QDoubleSpinBox {
    background-color: #161a22;
    border: 1px solid #2a2f3a;
    border-radius: 6px;
    padding: 5px 8px;
    color: #e6edf3;
}

QSpinBox:hover, QDoubleSpinBox:hover {
    border-color: #3d4451;
}

QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #4f8cff;
}

QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    background: transparent;
    border: none;
    width: 16px;
}

/* =========================================================================
   GROUP BOXES
   ========================================================================= */
QGroupBox {
    font-weight: 500;
    font-size: 13px;
    color: #e6edf3;
    border: 1px solid #2a2f3a;
    border-radius: 8px;
    margin-top: 14px;
    padding: 14px 10px 10px 10px;
    background-color: #161a22;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: 0;
    padding: 0 6px;
    background-color: #161a22;
    color: #9da7b3;
}

/* =========================================================================
   TABLES
   ========================================================================= */
QTableWidget, QTableView {
    background-color: #161a22;
    alternate-background-color: #1c212b;
    border: 1px solid #2a2f3a;
    border-radius: 8px;
    gridline-color: #2a2f3a;
    selection-background-color: #1e3a5f;
    selection-color: #e6edf3;
    outline: none;
}

QTableWidget::item, QTableView::item {
    padding: 10px 12px;
    border: none;
}

QTableWidget::item:selected, QTableView::item:selected {
    background-color: #1e3a5f;
}

QTableWidget::item:hover, QTableView::item:hover {
    background-color: #1c212b;
}

QHeaderView {
    background-color: transparent;
}

QHeaderView::section {
    background-color: #0f1115;
    color: #9da7b3;
    font-weight: 600;
    font-size: 12px;
    padding: 10px 12px;
    border: none;
    border-bottom: 1px solid #2a2f3a;
}

QHeaderView::section:hover {
    color: #e6edf3;
}

/* =========================================================================
   LISTS
   ========================================================================= */
QListWidget, QListView {
    background-color: #161a22;
    border: 1px solid #2a2f3a;
    border-radius: 8px;
    outline: none;
    padding: 4px;
}

QListWidget::item, QListView::item {
    padding: 10px 12px;
    border-radius: 6px;
    margin: 2px 4px;
    color: #e6edf3;
}

QListWidget::item:hover, QListView::item:hover {
    background-color: #1c212b;
}

QListWidget::item:selected, QListView::item:selected {
    background-color: #1e3a5f;
}

/* =========================================================================
   TREE VIEW
   ========================================================================= */
QTreeWidget, QTreeView {
    background-color: #161a22;
    border: 1px solid #2a2f3a;
    border-radius: 8px;
    outline: none;
}

QTreeWidget::item, QTreeView::item {
    padding: 6px 8px;
    color: #e6edf3;
}

QTreeWidget::item:hover, QTreeView::item:hover {
    background-color: #1c212b;
}

QTreeWidget::item:selected, QTreeView::item:selected {
    background-color: #1e3a5f;
}

/* =========================================================================
   TABS
   ========================================================================= */
QTabWidget::pane {
    background-color: #161a22;
    border: 1px solid #2a2f3a;
    border-radius: 8px;
    border-top-left-radius: 0;
    margin-top: -1px;
}

QTabBar {
    background: transparent;
}

QTabBar::tab {
    background-color: transparent;
    color: #9da7b3;
    padding: 10px 16px;
    margin-right: 2px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 500;
}

QTabBar::tab:hover {
    color: #e6edf3;
}

QTabBar::tab:selected {
    color: #4f8cff;
    border-bottom-color: #4f8cff;
}

/* =========================================================================
   SCROLL BARS
   ========================================================================= */
QScrollBar:vertical {
    background-color: transparent;
    width: 10px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #3d4451;
    border-radius: 5px;
    min-height: 30px;
    margin: 2px;
}

QScrollBar::handle:vertical:hover {
    background-color: #4f5563;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}

QScrollBar:horizontal {
    background-color: transparent;
    height: 10px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #3d4451;
    border-radius: 5px;
    min-width: 30px;
    margin: 2px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4f5563;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
    background: transparent;
}

/* =========================================================================
   PROGRESS BAR
   ========================================================================= */
QProgressBar {
    background-color: #2a2f3a;
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}

QProgressBar::chunk {
    background-color: #4f8cff;
    border-radius: 4px;
}

/* =========================================================================
   SLIDERS
   ========================================================================= */
QSlider::groove:horizontal {
    background-color: #2a2f3a;
    height: 4px;
    border-radius: 2px;
}

QSlider::handle:horizontal {
    background-color: #4f8cff;
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background-color: #6ba1ff;
}

/* =========================================================================
   SPLITTER
   ========================================================================= */
QSplitter::handle {
    background-color: #2a2f3a;
}

QSplitter::handle:horizontal {
    width: 1px;
}

QSplitter::handle:vertical {
    height: 1px;
}

QSplitter::handle:hover {
    background-color: #4f8cff;
}

/* =========================================================================
   STATUS BAR
   ========================================================================= */
QStatusBar {
    background-color: #0d1117;
    border-top: 1px solid #2a2f3a;
    color: #9da7b3;
    padding: 2px 8px;
    font-size: 12px;
}

QStatusBar QLabel {
    background: transparent;
}

/* =========================================================================
   TOOLTIPS
   ========================================================================= */
QToolTip {
    background-color: #1c212b;
    color: #e6edf3;
    border: 1px solid #2a2f3a;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}

/* =========================================================================
   MENUS
   ========================================================================= */
QMenu {
    background-color: #1c212b;
    border: 1px solid #2a2f3a;
    border-radius: 8px;
    padding: 6px;
}

QMenu::item {
    padding: 8px 24px 8px 12px;
    border-radius: 4px;
    color: #e6edf3;
}

QMenu::item:selected {
    background-color: #242a36;
}

QMenu::item:disabled {
    color: #4b5563;
}

QMenu::separator {
    height: 1px;
    background-color: #2a2f3a;
    margin: 6px 8px;
}

/* =========================================================================
   DIALOGS & MESSAGE BOXES
   ========================================================================= */
QDialog {
    background-color: #161a22;
}

QMessageBox {
    background-color: #161a22;
}

QMessageBox QLabel {
    color: #e6edf3;
}

/* =========================================================================
   FRAMES & CARDS
   ========================================================================= */
QFrame {
    background: transparent;
    border: none;
}

QFrame[card="true"],
QFrame#card,
.card {
    background-color: #161a22;
    border: 1px solid #2a2f3a;
    border-radius: 8px;
}

#task_action_bar {
    background-color: #0d1117;
    border-top: 1px solid #2a2f3a;
}

QFrame[card="true"]:hover,
QFrame#card:hover {
    border-color: #3d4451;
}

/* =========================================================================
   BADGES
   ========================================================================= */
QLabel[badge="success"] {
    background-color: #14532d;
    color: #22c55e;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel[badge="warning"] {
    background-color: #78350f;
    color: #f59e0b;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel[badge="error"] {
    background-color: #7f1d1d;
    color: #ef4444;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel[badge="info"] {
    background-color: #1e3a5f;
    color: #3b82f6;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel[badge="neutral"] {
    background-color: #2d3442;
    color: #9da7b3;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

/* =========================================================================
   SPECIAL COMPONENTS
   ========================================================================= */

/* Empty state */
#empty_state {
    color: #6b7280;
}

/* Section headers */
QLabel[section="true"] {
    color: #9da7b3;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 8px 0 4px 0;
}

/* Dividers */
QFrame[divider="true"] {
    background-color: #2a2f3a;
    max-height: 1px;
    min-height: 1px;
}

/* =========================================================================
   NOTIFICATION BANNER
   ========================================================================= */
#checkpoint_notification {
    background-color: #78350f;
    border: 1px solid #f59e0b;
    border-radius: 6px;
    padding: 10px 14px;
}

#checkpoint_notification QLabel {
    color: #fef3c7;
}

#checkpoint_notification QPushButton {
    background-color: #f59e0b;
    color: #78350f;
    font-weight: 600;
    padding: 6px 12px;
}

#checkpoint_notification QPushButton:hover {
    background-color: #fbbf24;
}
"""


def get_status_color(status: str) -> str:
    """Get color for a given status."""
    return STATUS_COLORS.get(status.lower(), COLORS["text_secondary"])


def get_status_style(status: str) -> str:
    """Get inline style for status badge."""
    color = get_status_color(status)
    bg_alpha = "30"  # 30% opacity
    return f"""
        background-color: {color}{bg_alpha};
        color: {color};
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 11px;
    """


def get_badge_style(variant: str = "neutral") -> str:
    """Get style for a badge variant."""
    variants = {
        "success": (COLORS["success_muted"], COLORS["success"]),
        "warning": (COLORS["warning_muted"], COLORS["warning"]),
        "error": (COLORS["error_muted"], COLORS["error"]),
        "info": (COLORS["info_muted"], COLORS["info"]),
        "neutral": (COLORS["bg_active"], COLORS["text_secondary"]),
    }
    bg, fg = variants.get(variant, variants["neutral"])
    return f"""
        background-color: {bg};
        color: {fg};
        padding: 3px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 11px;
    """
