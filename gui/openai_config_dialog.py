"""Compact dialog for missing OpenAI configuration."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class OpenAIConfigRequiredDialog(QDialog):
    """Compact dialog guiding the user to configure the OpenAI API key."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """Build the dialog UI."""
        self.setWindowTitle("Configuração da OpenAI necessária")
        self.setModal(True)
        self.setMinimumWidth(420)
        self.setMaximumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("A chave da OpenAI não está configurada.")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        title.setWordWrap(True)
        layout.addWidget(title)

        subtitle = QLabel("Configure a chave em Ambiente/Config ou crie um arquivo `.env` na raiz do projeto.")
        subtitle.setProperty("subheading", True)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.instructions_frame = QFrame()
        self.instructions_frame.setProperty("card", True)
        self.instructions_frame.hide()

        instructions_layout = QVBoxLayout(self.instructions_frame)
        instructions_layout.setContentsMargins(14, 12, 14, 12)
        instructions_layout.setSpacing(8)

        steps = QLabel(
            "Como configurar:\n"
            "1. Abra Configurações > Ambiente.\n"
            "2. Informe a chave no campo OpenAI API Key.\n"
            "3. Clique em Salvar no .env.\n\n"
            "Alternativa:\n"
            "Crie um arquivo `.env` com:\n"
            "OPENAI_API_KEY=sk-sua-chave"
        )
        steps.setWordWrap(True)
        instructions_layout.addWidget(steps)

        note = QLabel("Detalhes técnicos completos continuam disponíveis nos logs da aplicação.")
        note.setProperty("muted", True)
        note.setWordWrap(True)
        instructions_layout.addWidget(note)

        layout.addWidget(self.instructions_frame)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)

        self.open_settings_btn = QPushButton("Abrir Configurações")
        self.open_settings_btn.clicked.connect(self.accept)
        button_row.addWidget(self.open_settings_btn)

        self.instructions_btn = QPushButton("Ver instruções")
        self.instructions_btn.setProperty("secondary", True)
        self.instructions_btn.setCheckable(True)
        self.instructions_btn.toggled.connect(self._toggle_instructions)
        button_row.addWidget(self.instructions_btn)

        button_row.addStretch()

        self.close_btn = QPushButton("Fechar")
        self.close_btn.setProperty("ghost", True)
        self.close_btn.clicked.connect(self.reject)
        button_row.addWidget(self.close_btn)

        layout.addLayout(button_row)

    def _toggle_instructions(self, checked: bool):
        """Show or hide the instructions area."""
        self.instructions_frame.setVisible(checked)
        self.instructions_btn.setText("Ocultar instruções" if checked else "Ver instruções")
