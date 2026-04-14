"""Run timeline widget with expandable details.

Displays a vertical timeline of events for a run with human-friendly
explanations and expandable details.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QScrollArea,
    QPushButton,
    QTextEdit,
    QSizePolicy,
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QColor

from orchestrator.run_timeline import (
    RunTimeline,
    RunTimelineEvent,
    TimelineEventStatus,
    TimelineEventType,
    TimelineEventDetail,
    TimelineBuilder,
)


# Status colors
STATUS_COLORS = {
    TimelineEventStatus.PENDING: "#6b7280",      # Gray
    TimelineEventStatus.IN_PROGRESS: "#3b82f6",  # Blue
    TimelineEventStatus.COMPLETED: "#22c55e",    # Green
    TimelineEventStatus.FAILED: "#ef4444",       # Red
    TimelineEventStatus.SKIPPED: "#9ca3af",      # Light gray
}

# Event type icons (using simple text symbols)
EVENT_ICONS = {
    TimelineEventType.PLANNING: "📋",
    TimelineEventType.EXECUTION: "⚙️",
    TimelineEventType.REVIEW: "🔍",
    TimelineEventType.VALIDATION: "✓",
    TimelineEventType.GIT: "📦",
    TimelineEventType.FINALIZATION: "🏁",
    TimelineEventType.CHECKPOINT: "⚠️",
    TimelineEventType.POLICY_DECISION: "📜",
    TimelineEventType.ERROR: "❌",
    TimelineEventType.ITERATION_START: "🔄",
}


class TimelineDetailWidget(QFrame):
    """Expandable detail section for a timeline event."""

    def __init__(self, detail: TimelineEventDetail, parent=None):
        super().__init__(parent)
        self.detail = detail
        self._expanded = False
        self._setup_ui()

    def _setup_ui(self):
        self.setProperty("detail", True)
        self.setStyleSheet("""
            QFrame[detail=true] {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)

        # Header (clickable to expand)
        header = QHBoxLayout()
        header.setSpacing(8)

        self.expand_btn = QPushButton("▶")
        self.expand_btn.setFixedSize(20, 20)
        self.expand_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #8b949e;
                font-size: 10px;
            }
            QPushButton:hover {
                color: #e6edf3;
            }
        """)
        self.expand_btn.clicked.connect(self._toggle_expand)
        header.addWidget(self.expand_btn)

        label = QLabel(self.detail.label)
        label.setStyleSheet("color: #8b949e; font-size: 12px; font-weight: 500;")
        header.addWidget(label)
        header.addStretch()

        layout.addLayout(header)

        # Content (hidden by default)
        self.content_widget = QTextEdit()
        self.content_widget.setReadOnly(True)
        self.content_widget.setPlainText(self.detail.content)
        self.content_widget.setVisible(False)
        self.content_widget.setMaximumHeight(200)
        self.content_widget.setStyleSheet("""
            QTextEdit {
                background-color: #0d1117;
                border: 1px solid #21262d;
                border-radius: 4px;
                color: #c9d1d9;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
                padding: 6px;
            }
        """)
        layout.addWidget(self.content_widget)

    def _toggle_expand(self):
        self._expanded = not self._expanded
        self.content_widget.setVisible(self._expanded)
        self.expand_btn.setText("▼" if self._expanded else "▶")


class TimelineEventWidget(QFrame):
    """Widget for a single timeline event."""

    clicked = Signal(str)  # event_type

    def __init__(self, timeline_event: RunTimelineEvent, is_last: bool = False, parent=None):
        super().__init__(parent)
        self.timeline_event = timeline_event
        self.is_last = is_last
        self._expanded = False
        self._setup_ui()

    def _setup_ui(self):
        self.setProperty("timeline-event", True)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Left column: timeline connector
        connector_widget = QWidget()
        connector_widget.setFixedWidth(40)
        connector_layout = QVBoxLayout(connector_widget)
        connector_layout.setContentsMargins(0, 0, 0, 0)
        connector_layout.setSpacing(0)

        # Status dot
        dot_container = QWidget()
        dot_container.setFixedSize(40, 24)
        dot_layout = QHBoxLayout(dot_container)
        dot_layout.setContentsMargins(0, 0, 0, 0)

        self.status_dot = QLabel("●")
        color = STATUS_COLORS.get(self.timeline_event.status, "#6b7280")
        self.status_dot.setStyleSheet(f"color: {color}; font-size: 14px;")
        self.status_dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dot_layout.addWidget(self.status_dot)

        connector_layout.addWidget(dot_container)

        # Vertical line (if not last)
        if not self.is_last:
            line = QFrame()
            line.setFixedWidth(2)
            line.setStyleSheet("background-color: #30363d;")
            line.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

            line_container = QWidget()
            line_layout = QHBoxLayout(line_container)
            line_layout.setContentsMargins(19, 0, 0, 0)
            line_layout.addWidget(line)
            line_layout.addStretch()

            connector_layout.addWidget(line_container, 1)
        else:
            connector_layout.addStretch()

        layout.addWidget(connector_widget)

        # Right column: event content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(8, 0, 0, 16)
        content_layout.setSpacing(4)

        # Event header
        header = QHBoxLayout()
        header.setSpacing(8)

        # Icon
        icon = EVENT_ICONS.get(self.timeline_event.event_type, "○")
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 14px;")
        header.addWidget(icon_label)

        # Title
        title = QLabel(self.timeline_event.title)
        title.setStyleSheet("color: #e6edf3; font-size: 14px; font-weight: 600;")
        header.addWidget(title)

        # Iteration badge
        if self.timeline_event.iteration_number > 0 and self.timeline_event.event_type != TimelineEventType.ITERATION_START:
            iter_badge = QLabel(f"#{self.timeline_event.iteration_number}")
            iter_badge.setStyleSheet("""
                background-color: #21262d;
                color: #8b949e;
                font-size: 10px;
                padding: 2px 6px;
                border-radius: 8px;
            """)
            header.addWidget(iter_badge)

        header.addStretch()

        # Duration badge
        if self.timeline_event.duration_seconds:
            mins = int(self.timeline_event.duration_seconds // 60)
            secs = int(self.timeline_event.duration_seconds % 60)
            duration_text = f"{mins}m {secs}s" if mins else f"{secs}s"
            duration_label = QLabel(duration_text)
            duration_label.setStyleSheet("color: #8b949e; font-size: 11px;")
            header.addWidget(duration_label)

        # Status badge
        status_text = {
            TimelineEventStatus.PENDING: "Pendente",
            TimelineEventStatus.IN_PROGRESS: "Em andamento",
            TimelineEventStatus.COMPLETED: "Concluído",
            TimelineEventStatus.FAILED: "Falhou",
            TimelineEventStatus.SKIPPED: "Pulado",
        }.get(self.timeline_event.status, "")

        if status_text:
            status_badge = QLabel(status_text)
            color = STATUS_COLORS.get(self.timeline_event.status, "#6b7280")
            status_badge.setStyleSheet(f"""
                background-color: {color}20;
                color: {color};
                font-size: 10px;
                padding: 2px 8px;
                border-radius: 8px;
            """)
            header.addWidget(status_badge)

        content_layout.addLayout(header)

        # Timestamp
        if self.timeline_event.timestamp:
            time_str = self.timeline_event.timestamp.strftime("%H:%M:%S")
            time_label = QLabel(time_str)
            time_label.setStyleSheet("color: #6b7280; font-size: 11px;")
            content_layout.addWidget(time_label)

        # Description
        if self.timeline_event.description:
            desc = QLabel(self.timeline_event.description)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #c9d1d9; font-size: 12px;")
            content_layout.addWidget(desc)

        # Human explanation (collapsed by default)
        if self.timeline_event.explanation:
            self.explanation_widget = QLabel(self.timeline_event.explanation)
            self.explanation_widget.setWordWrap(True)
            self.explanation_widget.setStyleSheet("""
                color: #8b949e;
                font-size: 11px;
                font-style: italic;
                padding: 8px;
                background-color: #161b22;
                border-radius: 4px;
            """)
            self.explanation_widget.setVisible(False)
            content_layout.addWidget(self.explanation_widget)

        # Toggle explanation button
        if self.timeline_event.explanation or self.timeline_event.details:
            toggle_btn = QPushButton("Mostrar detalhes")
            toggle_btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #58a6ff;
                    font-size: 11px;
                    text-align: left;
                    padding: 4px 0;
                }
                QPushButton:hover {
                    text-decoration: underline;
                }
            """)
            toggle_btn.clicked.connect(self._toggle_details)
            content_layout.addWidget(toggle_btn)
            self.toggle_btn = toggle_btn

        # Details container
        self.details_container = QWidget()
        details_layout = QVBoxLayout(self.details_container)
        details_layout.setContentsMargins(0, 8, 0, 0)
        details_layout.setSpacing(6)

        for detail in self.timeline_event.details:
            detail_widget = TimelineDetailWidget(detail)
            details_layout.addWidget(detail_widget)

        # Files affected
        if self.timeline_event.files_affected and not any(d.label == "Arquivos Modificados" for d in self.timeline_event.details):
            files_detail = TimelineEventDetail(
                label=f"Arquivos ({len(self.timeline_event.files_affected)})",
                content="\n".join(self.timeline_event.files_affected),
                detail_type="files"
            )
            details_layout.addWidget(TimelineDetailWidget(files_detail))

        # Commands run
        if self.timeline_event.commands_run and not any(d.label == "Comandos Executados" for d in self.timeline_event.details):
            cmds_detail = TimelineEventDetail(
                label=f"Comandos ({len(self.timeline_event.commands_run)})",
                content="\n".join(self.timeline_event.commands_run),
                detail_type="commands"
            )
            details_layout.addWidget(TimelineDetailWidget(cmds_detail))

        # Errors
        if self.timeline_event.errors:
            for i, error in enumerate(self.timeline_event.errors[:3]):  # Limit to 3
                error_detail = TimelineEventDetail(
                    label=f"Erro {i+1}" if len(self.timeline_event.errors) > 1 else "Erro",
                    content=error,
                    detail_type="logs"
                )
                details_layout.addWidget(TimelineDetailWidget(error_detail))

        self.details_container.setVisible(False)
        content_layout.addWidget(self.details_container)

        layout.addWidget(content_widget, 1)

    def _toggle_details(self):
        self._expanded = not self._expanded

        if hasattr(self, 'explanation_widget'):
            self.explanation_widget.setVisible(self._expanded)

        self.details_container.setVisible(self._expanded)

        if hasattr(self, 'toggle_btn'):
            self.toggle_btn.setText("Ocultar detalhes" if self._expanded else "Mostrar detalhes")


class RunTimelineWidget(QWidget):
    """Complete timeline widget for a run."""

    event_clicked = Signal(str)  # event_type

    def __init__(self, workspace_path: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.workspace_path = workspace_path
        self._timeline: Optional[RunTimeline] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #161b22;
                border-bottom: 1px solid #30363d;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        self.title_label = QLabel("Timeline da Run")
        self.title_label.setStyleSheet("color: #e6edf3; font-size: 15px; font-weight: 600;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")
        header_layout.addWidget(self.status_label)

        layout.addWidget(header)

        # Scroll area for events
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: #0d1117;
                border: none;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #0d1117;
            }
        """)

        self.events_container = QWidget()
        self.events_layout = QVBoxLayout(self.events_container)
        self.events_layout.setContentsMargins(16, 16, 16, 16)
        self.events_layout.setSpacing(0)
        self.events_layout.addStretch()

        scroll.setWidget(self.events_container)
        layout.addWidget(scroll, 1)

        # Empty state
        self.empty_label = QLabel("Selecione uma run para ver a timeline")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #6b7280; font-size: 13px; padding: 40px;")
        self.events_layout.insertWidget(0, self.empty_label)

    def set_workspace(self, workspace_path: Path):
        """Set the workspace path."""
        self.workspace_path = workspace_path

    def load_timeline(self, run_id: str):
        """Load and display timeline for a run."""
        if not self.workspace_path:
            return

        builder = TimelineBuilder(self.workspace_path)
        timeline = builder.build_timeline(run_id)

        if timeline:
            self.set_timeline(timeline)
        else:
            self.clear_timeline()

    def set_timeline(self, timeline: RunTimeline):
        """Set the timeline to display."""
        self._timeline = timeline
        self._rebuild_ui()

    def clear_timeline(self):
        """Clear the timeline display."""
        self._timeline = None
        self._rebuild_ui()

    def _rebuild_ui(self):
        """Rebuild the UI with current timeline."""
        # Clear existing events
        while self.events_layout.count() > 1:  # Keep stretch
            item = self.events_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self._timeline or not self._timeline.events:
            self.empty_label = QLabel("Nenhum evento na timeline")
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setStyleSheet("color: #6b7280; font-size: 13px; padding: 40px;")
            self.events_layout.insertWidget(0, self.empty_label)
            self.title_label.setText("Timeline da Run")
            self.status_label.setText("")
            return

        # Update header
        self.title_label.setText(f"Timeline: {self._timeline.run_id[:16]}...")

        # Status summary
        if self._timeline.is_complete:
            if self._timeline.has_errors:
                self.status_label.setText("❌ Finalizada com erros")
                self.status_label.setStyleSheet("color: #ef4444; font-size: 12px;")
            else:
                self.status_label.setText("✓ Finalizada com sucesso")
                self.status_label.setStyleSheet("color: #22c55e; font-size: 12px;")
        else:
            current = self._timeline.get_current_event()
            if current:
                self.status_label.setText(f"⏳ {current.title}...")
                self.status_label.setStyleSheet("color: #3b82f6; font-size: 12px;")
            else:
                self.status_label.setText("Em andamento...")
                self.status_label.setStyleSheet("color: #8b949e; font-size: 12px;")

        # Add event widgets
        events = self._timeline.events
        for i, event in enumerate(events):
            is_last = i == len(events) - 1
            event_widget = TimelineEventWidget(event, is_last=is_last)
            event_widget.clicked.connect(self.event_clicked.emit)
            self.events_layout.insertWidget(i, event_widget)

    def refresh(self):
        """Refresh the current timeline."""
        if self._timeline:
            self.load_timeline(self._timeline.run_id)
