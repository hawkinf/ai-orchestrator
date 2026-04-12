"""GUI styles and theme definitions."""

# Color palette
COLORS = {
    "primary": "#2563eb",
    "primary_hover": "#1d4ed8",
    "secondary": "#64748b",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "background": "#f8fafc",
    "surface": "#ffffff",
    "border": "#e2e8f0",
    "text": "#1e293b",
    "text_secondary": "#64748b",
    "text_muted": "#94a3b8",
}

# Status colors
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
}

# Main application stylesheet
MAIN_STYLESHEET = """
QMainWindow {
    background-color: #f8fafc;
}

QWidget {
    font-family: "Segoe UI", "SF Pro Display", system-ui, sans-serif;
    font-size: 13px;
    color: #1e293b;
}

/* Sidebar */
#sidebar {
    background-color: #1e293b;
    border: none;
}

#sidebar QPushButton {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    padding: 12px 16px;
    text-align: left;
    font-size: 13px;
    border-radius: 6px;
    margin: 2px 8px;
}

#sidebar QPushButton:hover {
    background-color: #334155;
    color: #f1f5f9;
}

#sidebar QPushButton:checked {
    background-color: #2563eb;
    color: #ffffff;
}

/* Content area */
#content_area {
    background-color: #f8fafc;
}

/* Cards */
.card {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 16px;
}

/* Headers */
QLabel#header {
    font-size: 20px;
    font-weight: 600;
    color: #1e293b;
    padding-bottom: 8px;
}

QLabel#subheader {
    font-size: 14px;
    color: #64748b;
}

/* Text inputs */
QLineEdit, QTextEdit, QPlainTextEdit {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
    color: #1e293b;
}

QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #2563eb;
    outline: none;
}

QLineEdit:disabled, QTextEdit:disabled {
    background-color: #f1f5f9;
    color: #94a3b8;
}

/* Combo boxes */
QComboBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px 12px;
    min-width: 120px;
}

QComboBox:hover {
    border-color: #cbd5e1;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox::down-arrow {
    width: 12px;
    height: 12px;
}

QComboBox QAbstractItemView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    selection-background-color: #eff6ff;
    selection-color: #1e293b;
}

/* Buttons */
QPushButton {
    background-color: #2563eb;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 10px 20px;
    font-weight: 500;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #1d4ed8;
}

QPushButton:pressed {
    background-color: #1e40af;
}

QPushButton:disabled {
    background-color: #94a3b8;
    color: #e2e8f0;
}

QPushButton#secondary {
    background-color: #f1f5f9;
    color: #475569;
    border: 1px solid #e2e8f0;
}

QPushButton#secondary:hover {
    background-color: #e2e8f0;
}

QPushButton#success {
    background-color: #22c55e;
}

QPushButton#success:hover {
    background-color: #16a34a;
}

QPushButton#danger {
    background-color: #ef4444;
}

QPushButton#danger:hover {
    background-color: #dc2626;
}

/* Check boxes */
QCheckBox {
    spacing: 8px;
    color: #1e293b;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #cbd5e1;
    border-radius: 4px;
    background-color: #ffffff;
}

QCheckBox::indicator:checked {
    background-color: #2563eb;
    border-color: #2563eb;
}

QCheckBox::indicator:hover {
    border-color: #2563eb;
}

/* Spin boxes */
QSpinBox {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 8px 12px;
}

/* Group boxes */
QGroupBox {
    font-weight: 600;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 16px;
    background-color: #ffffff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 8px;
    color: #475569;
}

/* Tables */
QTableWidget, QTableView {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    gridline-color: #f1f5f9;
    selection-background-color: #eff6ff;
    selection-color: #1e293b;
}

QTableWidget::item, QTableView::item {
    padding: 8px 12px;
    border-bottom: 1px solid #f1f5f9;
}

QHeaderView::section {
    background-color: #f8fafc;
    color: #64748b;
    font-weight: 600;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid #e2e8f0;
}

/* Tabs */
QTabWidget::pane {
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    background-color: #ffffff;
}

QTabBar::tab {
    background-color: transparent;
    color: #64748b;
    padding: 10px 20px;
    margin-right: 4px;
    border-bottom: 2px solid transparent;
}

QTabBar::tab:selected {
    color: #2563eb;
    border-bottom-color: #2563eb;
}

QTabBar::tab:hover:!selected {
    color: #1e293b;
}

/* Scroll bars */
QScrollBar:vertical {
    background-color: #f1f5f9;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background-color: #cbd5e1;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94a3b8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #f1f5f9;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background-color: #cbd5e1;
    border-radius: 5px;
    min-width: 30px;
}

/* Progress bar */
QProgressBar {
    background-color: #e2e8f0;
    border-radius: 4px;
    height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #2563eb;
    border-radius: 4px;
}

/* Splitter */
QSplitter::handle {
    background-color: #e2e8f0;
}

QSplitter::handle:horizontal {
    width: 2px;
}

QSplitter::handle:vertical {
    height: 2px;
}

/* Status bar */
QStatusBar {
    background-color: #f1f5f9;
    border-top: 1px solid #e2e8f0;
    color: #64748b;
    padding: 4px 12px;
}

/* Tooltips */
QToolTip {
    background-color: #1e293b;
    color: #f8fafc;
    border: none;
    border-radius: 4px;
    padding: 6px 10px;
}

/* Menu */
QMenu {
    background-color: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #eff6ff;
}

QMenu::separator {
    height: 1px;
    background-color: #e2e8f0;
    margin: 4px 8px;
}

/* Dialog */
QDialog {
    background-color: #ffffff;
}

/* Message box */
QMessageBox {
    background-color: #ffffff;
}

QMessageBox QLabel {
    color: #1e293b;
}
"""


def get_status_color(status: str) -> str:
    """Get color for a given status."""
    return STATUS_COLORS.get(status.lower(), COLORS["secondary"])


def get_status_style(status: str) -> str:
    """Get inline style for status badge."""
    color = get_status_color(status)
    return f"""
        background-color: {color}20;
        color: {color};
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 500;
        font-size: 11px;
    """
