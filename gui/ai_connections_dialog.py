"""Conexões IA — single place to connect/configure ChatGPT/OpenAI and Claude.

The dialog never touches ``.env`` or runs ``subprocess`` directly: every
read/write/test goes through :class:`~orchestrator.ai_connection_service.AIConnectionService`,
and the (potentially slow) connectivity probes run on worker threads so the
window never freezes.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from orchestrator.ai_connection_service import AIConnectionService
from orchestrator.claude_detector import ClaudeStatus
from orchestrator.env_config_service import OpenAIKeyState

from .claude_test_worker import ClaudeTestManager

_OK = "#22c55e"
_WARN = "#f59e0b"
_ERR = "#ef4444"
_MUTED = "#6b7280"
_INFO = "#3b82f6"


class _OpenAITestSignals(QObject):
    finished = Signal(dict)
    error = Signal(str)


class _OpenAITestRunnable(QRunnable):
    """Run an OpenAI connectivity probe off the UI thread."""

    def __init__(self, service: AIConnectionService, api_key: Optional[str]):
        super().__init__()
        self._service = service
        self._api_key = api_key
        self.signals = _OpenAITestSignals()

    def run(self):
        try:
            if self._api_key:
                result = self._service.test_openai_key(self._api_key, skip_network=False)
            else:
                result = self._service.test_openai(skip_network=False)
            self.signals.finished.emit(result.to_dict())
        except Exception as exc:  # pragma: no cover - defensive
            import re

            self.signals.error.emit(re.sub(r"sk-[a-zA-Z0-9]{20,}", "sk-***", str(exc)))


class AIConnectionsDialog(QDialog):
    """Modal to connect/configure ChatGPT/OpenAI and Claude without editing files."""

    # Emitted whenever the OpenAI key or the Claude command changes.
    configuration_changed = Signal()
    # Emitted with the new command string when the Claude command is saved.
    claude_command_changed = Signal(str)

    def __init__(
        self,
        service: AIConnectionService,
        claude_command: str = "claude",
        initial_section: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self._service = service
        self._claude_command = claude_command or "claude"
        self._thread_pool = QThreadPool.globalInstance()
        self._claude_test_manager = ClaudeTestManager()
        self._openai_busy = False

        self.setWindowTitle("Conexões IA")
        self.setModal(True)
        self.setMinimumSize(640, 620)

        self._setup_ui()
        self.refresh_openai_status()
        self.refresh_claude_status()

        if initial_section == "claude":
            self.claude_command_edit.setFocus()
        else:
            self.api_key_input.setFocus()

    # ----------------------------------------------------------------- build
    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)

        header = QLabel("Conectar IA")
        header.setStyleSheet("font-size: 17px; font-weight: 600;")
        root.addWidget(header)

        subtitle = QLabel(
            "Configure o ChatGPT/OpenAI e o Claude sem editar arquivos manualmente."
        )
        subtitle.setStyleSheet(f"color: {_MUTED}; font-size: 12px;")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(14)
        content_layout.setContentsMargins(0, 0, 0, 0)

        content_layout.addWidget(self._build_openai_section())
        content_layout.addWidget(self._build_claude_section())
        content_layout.addWidget(self._build_diagnostics_section())
        content_layout.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("Fechar")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        root.addLayout(footer)

    def _build_openai_section(self) -> QGroupBox:
        group = QGroupBox("ChatGPT / OpenAI")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:"))
        self.openai_status_badge = QLabel("Verificando...")
        self._set_badge(self.openai_status_badge, "Verificando...", _MUTED)
        status_row.addWidget(self.openai_status_badge)
        status_row.addStretch()
        layout.addLayout(status_row)

        self.openai_note_label = QLabel("")
        self.openai_note_label.setWordWrap(True)
        self.openai_note_label.setStyleSheet(f"color: {_MUTED}; font-size: 11px;")
        layout.addWidget(self.openai_note_label)

        self.openai_system_warning = QLabel("")
        self.openai_system_warning.setWordWrap(True)
        self.openai_system_warning.setStyleSheet(f"color: {_WARN}; font-size: 11px;")
        self.openai_system_warning.hide()
        layout.addWidget(self.openai_system_warning)

        input_row = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Cole aqui sua OPENAI_API_KEY (sk-...)")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        input_row.addWidget(self.api_key_input)

        self.show_key_btn = QPushButton("Mostrar")
        self.show_key_btn.setCheckable(True)
        self.show_key_btn.setFixedWidth(80)
        self.show_key_btn.toggled.connect(self._toggle_key_visibility)
        input_row.addWidget(self.show_key_btn)
        layout.addLayout(input_row)

        btn_row = QHBoxLayout()
        self.save_key_btn = QPushButton("Salvar chave")
        self.save_key_btn.clicked.connect(self._on_save_openai_key)
        btn_row.addWidget(self.save_key_btn)

        self.test_openai_btn = QPushButton("Testar OpenAI")
        self.test_openai_btn.clicked.connect(self._on_test_openai)
        btn_row.addWidget(self.test_openai_btn)

        self.clear_key_btn = QPushButton("Limpar/Remover chave")
        self.clear_key_btn.setProperty("secondary", True)
        self.clear_key_btn.clicked.connect(self._on_remove_openai_key)
        btn_row.addWidget(self.clear_key_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.openai_result_label = QLabel("")
        self.openai_result_label.setWordWrap(True)
        self.openai_result_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.openai_result_label)

        return group

    def _build_claude_section(self) -> QGroupBox:
        group = QGroupBox("Claude")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:"))
        self.claude_status_badge = QLabel("Verificando...")
        self._set_badge(self.claude_status_badge, "Verificando...", _MUTED)
        status_row.addWidget(self.claude_status_badge)
        status_row.addStretch()
        layout.addLayout(status_row)

        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Caminho detectado:"))
        self.claude_path_label = QLabel("-")
        self.claude_path_label.setStyleSheet(f"color: {_MUTED}; font-family: monospace; font-size: 11px;")
        self.claude_path_label.setWordWrap(True)
        path_row.addWidget(self.claude_path_label, 1)
        layout.addLayout(path_row)

        cmd_row = QHBoxLayout()
        cmd_row.addWidget(QLabel("Comando Claude:"))
        self.claude_command_edit = QLineEdit()
        self.claude_command_edit.setPlaceholderText("claude")
        self.claude_command_edit.setText(self._claude_command)
        cmd_row.addWidget(self.claude_command_edit, 1)

        self.browse_claude_btn = QPushButton("Procurar executável")
        self.browse_claude_btn.clicked.connect(self._on_browse_claude)
        cmd_row.addWidget(self.browse_claude_btn)
        layout.addLayout(cmd_row)

        btn_row = QHBoxLayout()
        self.save_claude_btn = QPushButton("Salvar comando")
        self.save_claude_btn.clicked.connect(self._on_save_claude_command)
        btn_row.addWidget(self.save_claude_btn)

        self.test_claude_btn = QPushButton("Testar Claude")
        self.test_claude_btn.clicked.connect(self._on_test_claude)
        btn_row.addWidget(self.test_claude_btn)

        self.claude_login_btn = QPushButton("Abrir login do Claude")
        self.claude_login_btn.setProperty("secondary", True)
        self.claude_login_btn.clicked.connect(self._on_open_claude_login)
        btn_row.addWidget(self.claude_login_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.claude_result_label = QLabel("")
        self.claude_result_label.setWordWrap(True)
        self.claude_result_label.setStyleSheet("font-size: 12px;")
        layout.addWidget(self.claude_result_label)

        self.claude_install_hint = QLabel(self._service.claude_install_instructions())
        self.claude_install_hint.setWordWrap(True)
        self.claude_install_hint.setStyleSheet(
            f"color: {_MUTED}; font-size: 11px; font-family: monospace;"
        )
        self.claude_install_hint.hide()
        layout.addWidget(self.claude_install_hint)

        return group

    def _build_diagnostics_section(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.diagnostics_btn = QPushButton("Mostrar diagnóstico técnico")
        self.diagnostics_btn.setProperty("ghost", True)
        self.diagnostics_btn.setCheckable(True)
        self.diagnostics_btn.toggled.connect(self._toggle_diagnostics)
        layout.addWidget(self.diagnostics_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        self.diagnostics_text = QTextEdit()
        self.diagnostics_text.setReadOnly(True)
        self.diagnostics_text.setMaximumHeight(140)
        self.diagnostics_text.setStyleSheet(
            "background-color: #0f1115; font-family: monospace; font-size: 11px; color: #c9d1d9;"
        )
        self.diagnostics_text.setPlaceholderText("Execute um teste para ver os detalhes técnicos...")
        self.diagnostics_text.hide()
        layout.addWidget(self.diagnostics_text)

        return container

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _set_badge(label: QLabel, text: str, color: str):
        label.setText(text)
        label.setStyleSheet(
            f"background-color: {color}; color: white; padding: 2px 8px; "
            "border-radius: 4px; font-weight: 600; font-size: 11px;"
        )

    def _toggle_key_visibility(self, show: bool):
        self.api_key_input.setEchoMode(
            QLineEdit.EchoMode.Normal if show else QLineEdit.EchoMode.Password
        )
        self.show_key_btn.setText("Ocultar" if show else "Mostrar")

    def _toggle_diagnostics(self, checked: bool):
        self.diagnostics_text.setVisible(checked)
        self.diagnostics_btn.setText(
            "Ocultar diagnóstico técnico" if checked else "Mostrar diagnóstico técnico"
        )

    def _append_diagnostics(self, title: str, details: list[str]):
        if not details:
            return
        block = f"== {title} ==\n" + "\n".join(details) + "\n"
        existing = self.diagnostics_text.toPlainText()
        self.diagnostics_text.setPlainText((existing + "\n" + block).strip() if existing else block)

    # ----------------------------------------------------------- OpenAI logic
    def refresh_openai_status(self):
        """Re-read the OpenAI key state and update the section (no restart needed)."""
        status = self._service.openai_status()
        self.openai_note_label.setText(status.note)

        if status.state == OpenAIKeyState.NOT_CONFIGURED:
            self._set_badge(self.openai_status_badge, "Não configurado", _ERR)
        else:
            preview = f" ({status.masked_value})" if status.masked_value else ""
            self._set_badge(self.openai_status_badge, f"Chave encontrada{preview}", _OK)

        if status.in_system:
            self.openai_system_warning.setText(
                "Atenção: já existe uma OPENAI_API_KEY no ambiente do sistema. "
                + status.note
            )
            self.openai_system_warning.show()
        else:
            self.openai_system_warning.hide()

    def _on_save_openai_key(self):
        key = self.api_key_input.text().strip()
        if not key:
            self._show_openai_result("Digite uma chave para salvar.", _WARN)
            return
        if not key.startswith("sk-"):
            reply = QMessageBox.question(
                self,
                "Formato da chave",
                "A chave não começa com 'sk-'. Chaves da OpenAI normalmente começam com 'sk-'.\n\n"
                "Deseja salvar mesmo assim?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        result = self._service.save_openai_key(key)
        self._append_diagnostics("OpenAI — salvar chave", result.details)
        if result.success:
            self.api_key_input.clear()
            self.show_key_btn.setChecked(False)
            self._show_openai_result(
                f"{result.message} (valor: {result.masked_value})", _OK
            )
            self.refresh_openai_status()
            self.configuration_changed.emit()
        else:
            self._show_openai_result(result.message, _ERR)

    def _on_remove_openai_key(self):
        reply = QMessageBox.question(
            self,
            "Remover chave",
            "Remover a OPENAI_API_KEY do arquivo .env do projeto?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        result = self._service.remove_openai_key()
        self._append_diagnostics("OpenAI — remover chave", result.details)
        self.api_key_input.clear()
        self._show_openai_result(result.message, _OK if result.success else _ERR)
        self.refresh_openai_status()
        if result.success:
            self.configuration_changed.emit()

    def _on_test_openai(self):
        if self._openai_busy:
            return
        typed_key = self.api_key_input.text().strip()
        self._openai_busy = True
        self.test_openai_btn.setEnabled(False)
        self.test_openai_btn.setText("Testando...")
        self._show_openai_result("Testando conexão com a OpenAI...", _INFO)

        runnable = _OpenAITestRunnable(self._service, typed_key or None)
        runnable.signals.finished.connect(self._on_openai_test_finished)
        runnable.signals.error.connect(self._on_openai_test_error)
        self._thread_pool.start(runnable)

    def _on_openai_test_finished(self, result: dict):
        self._openai_busy = False
        self.test_openai_btn.setEnabled(True)
        self.test_openai_btn.setText("Testar OpenAI")
        self._append_diagnostics("OpenAI — teste de conexão", result.get("details", []))

        message = result.get("message", "")
        if result.get("success"):
            self._show_openai_result(f"Conexão OK. {message}", _OK)
        else:
            stage = result.get("stage", "")
            lowered = (message + " " + stage).lower()
            if "autentica" in lowered or "auth" in lowered or "invalid" in lowered:
                self._show_openai_result(f"Erro de autenticação. {message}", _ERR)
            elif "rede" in lowered or "network" in lowered or "timeout" in lowered or "conex" in lowered:
                self._show_openai_result(f"Erro de rede. {message}", _ERR)
            else:
                self._show_openai_result(f"Falha no teste. {message}", _ERR)
        self.refresh_openai_status()
        self.configuration_changed.emit()

    def _on_openai_test_error(self, error_msg: str):
        self._openai_busy = False
        self.test_openai_btn.setEnabled(True)
        self.test_openai_btn.setText("Testar OpenAI")
        self._show_openai_result(f"Erro inesperado no teste: {error_msg}", _ERR)

    def _show_openai_result(self, text: str, color: str):
        self.openai_result_label.setText(text)
        self.openai_result_label.setStyleSheet(f"color: {color}; font-size: 12px;")

    # ----------------------------------------------------------- Claude logic
    def refresh_claude_status(self):
        """Lightweight (no subprocess) refresh of the detected Claude path."""
        command = self.claude_command_edit.text().strip() or "claude"
        self._service.set_claude_command(command)
        result = self._service.detect_claude(command)
        self.claude_path_label.setText(result.resolved_path or "Não encontrado")
        if result.found:
            self._set_badge(self.claude_status_badge, "Claude encontrado", _WARN)
            self.claude_install_hint.hide()
        else:
            self._set_badge(self.claude_status_badge, "Claude não encontrado", _ERR)
            self.claude_install_hint.show()

    def _on_browse_claude(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Selecionar executável do Claude",
            str(Path.home()),
        )
        if path:
            self.claude_command_edit.setText(path)
            self.refresh_claude_status()

    def _on_save_claude_command(self):
        command = self.claude_command_edit.text().strip() or "claude"
        self.claude_command_edit.setText(command)
        self._claude_command = command
        self._service.set_claude_command(command)
        self.refresh_claude_status()
        self._show_claude_result(f"Comando Claude salvo: {command}", _OK)
        self.claude_command_changed.emit(command)
        self.configuration_changed.emit()

    def _on_test_claude(self):
        command = self.claude_command_edit.text().strip() or "claude"
        if self._claude_test_manager.is_running:
            return
        self.test_claude_btn.setEnabled(False)
        self.test_claude_btn.setText("Testando...")
        self._show_claude_result("Testando o Claude...", _INFO)
        started = self._claude_test_manager.run_test(
            command=command,
            project_root=self._service.project_root,
            timeout=15,
            on_finished=self._on_claude_test_finished,
            on_error=self._on_claude_test_error,
        )
        if not started:
            self.test_claude_btn.setEnabled(True)
            self.test_claude_btn.setText("Testar Claude")

    def _on_claude_test_finished(self, result: dict):
        self.test_claude_btn.setEnabled(True)
        self.test_claude_btn.setText("Testar Claude")
        self._append_diagnostics("Claude — teste", result.get("details", []))
        self.claude_path_label.setText(result.get("resolved_path") or "Não encontrado")

        status = result.get("status")
        message = result.get("message", "")
        if status == ClaudeStatus.RESPONDS_OK.value:
            self._set_badge(self.claude_status_badge, "Claude responde OK", _OK)
            self.claude_install_hint.hide()
            self._show_claude_result(message, _OK)
        elif status == ClaudeStatus.LOGIN_PENDING.value:
            self._set_badge(self.claude_status_badge, "Login pendente", _WARN)
            self.claude_install_hint.hide()
            self._show_claude_result(
                message + " Use 'Abrir login do Claude' para concluir o login.", _WARN
            )
        elif status == ClaudeStatus.NOT_FOUND.value:
            self._set_badge(self.claude_status_badge, "Claude não encontrado", _ERR)
            self.claude_install_hint.show()
            self._show_claude_result(message, _ERR)
        else:
            self._set_badge(self.claude_status_badge, "Erro ao executar", _ERR)
            self._show_claude_result(message, _ERR)
        self.configuration_changed.emit()

    def _on_claude_test_error(self, error_msg: str):
        self.test_claude_btn.setEnabled(True)
        self.test_claude_btn.setText("Testar Claude")
        self._show_claude_result(f"Erro inesperado no teste: {error_msg}", _ERR)

    def _on_open_claude_login(self):
        """Open a terminal running ``claude`` so the user can log in (non-blocking)."""
        command = self.claude_command_edit.text().strip() or "claude"
        launched = False
        try:
            if sys.platform == "darwin":
                subprocess.Popen(
                    ["osascript", "-e", f'tell application "Terminal" to do script "{command}"',
                     "-e", 'tell application "Terminal" to activate']
                )
                launched = True
            elif sys.platform == "win32":
                subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", command])
                launched = True
            else:
                for term in ("x-terminal-emulator", "gnome-terminal", "konsole", "xterm"):
                    import shutil as _shutil

                    if _shutil.which(term):
                        subprocess.Popen([term, "-e", command])
                        launched = True
                        break
        except OSError:
            launched = False

        if launched:
            self._show_claude_result(
                "Terminal aberto. Conclua o login do Claude na janela do terminal.", _INFO
            )
        else:
            QMessageBox.information(
                self,
                "Login do Claude",
                "Para fazer login, abra um terminal e execute:\n\n"
                f"  {command}\n\n"
                "Siga as instruções exibidas para autenticar o Claude Code.",
            )

    def _show_claude_result(self, text: str, color: str):
        self.claude_result_label.setText(text)
        self.claude_result_label.setStyleSheet(f"color: {color}; font-size: 12px;")
