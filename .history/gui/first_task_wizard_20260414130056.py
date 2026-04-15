"""First task wizard - guides users through their first run."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QRadioButton,
    QTextEdit,
    QButtonGroup,
    QStackedWidget,
    QWidget,
)
from PySide6.QtCore import Signal


@dataclass
class FirstTaskExample:
    """Example task for first run."""

    profile: str
    title: str
    description: str
    task_text: str


FIRST_TASK_EXAMPLES = {
    "flutter": [
        FirstTaskExample(
            profile="flutter",
            title="Análise e correção básica",
            description="Revisa o código, roda validações e corrige problemas simples.",
            task_text=(
                "Revise a tela inicial do aplicativo, rode flutter analyze e flutter test, "
                "corrija erros simples encontrados e gere um relatório final com o que foi alterado."
            ),
        ),
        FirstTaskExample(
            profile="flutter",
            title="Melhoria de documentação",
            description="Adiciona comentários e documentação básica.",
            task_text=(
                "Analise os arquivos principais do projeto, adicione comentários explicativos "
                "nas funções mais importantes e gere documentação básica do fluxo principal."
            ),
        ),
    ],
    "python": [
        FirstTaskExample(
            profile="python",
            title="Análise e correção básica",
            description="Revisa o código, roda testes e corrige problemas simples.",
            task_text=(
                "Revise o módulo principal do projeto, execute pytest e ruff check, "
                "corrija falhas simples encontradas e gere um relatório final com o que foi alterado."
            ),
        ),
        FirstTaskExample(
            profile="python",
            title="Melhoria de documentação",
            description="Adiciona docstrings e type hints.",
            task_text=(
                "Analise as funções principais do projeto, adicione docstrings descritivas "
                "e type hints básicos onde estiverem faltando."
            ),
        ),
    ],
    "generic": [
        FirstTaskExample(
            profile="generic",
            title="Análise exploratória",
            description="Analisa o projeto e identifica melhorias seguras.",
            task_text=(
                "Analise a estrutura do projeto, identifique melhorias seguras e de baixo risco, "
                "valide o ambiente e gere um relatório com sugestões organizadas por prioridade."
            ),
        ),
        FirstTaskExample(
            profile="generic",
            title="Organização de código",
            description="Organiza arquivos e melhora a estrutura.",
            task_text=(
                "Revise a organização dos arquivos do projeto, sugira melhorias na estrutura "
                "de pastas e gere um relatório com as mudanças recomendadas."
            ),
        ),
    ],
}


class ProfileSelectionPage(QWidget):
    """Page for selecting project profile."""

    profile_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_profile: Optional[str] = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("Que tipo de projeto você está usando?")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Escolha o perfil que melhor descreve seu projeto. "
            "Isso vai ajudar a sugerir uma tarefa inicial adequada."
        )
        subtitle.setProperty("muted", True)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self.button_group = QButtonGroup(self)
        self.button_group.buttonClicked.connect(self._on_profile_clicked)

        profiles = [
            ("flutter", "Flutter", "Apps Flutter/Dart com flutter analyze e flutter test"),
            ("python", "Python", "Projetos Python com pytest e ruff/flake8"),
            ("generic", "Generic", "Outros projetos sem validações específicas"),
        ]

        for profile, label, description in profiles:
            card = self._create_profile_card(profile, label, description)
            layout.addWidget(card)

        layout.addStretch()

    def _create_profile_card(self, profile: str, label: str, description: str) -> QFrame:
        card = QFrame()
        card.setProperty("card", True)
        card.setStyleSheet("""
            QFrame[card=true] {
                background-color: #161a22;
                border: 1px solid #2a2f3a;
                border-radius: 6px;
                padding: 12px;
            }
            QFrame[card=true]:hover {
                border-color: #4f8cff;
            }
        """)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)

        radio = QRadioButton()
        radio.setProperty("profile", profile)
        self.button_group.addButton(radio)
        card_layout.addWidget(radio)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title = QLabel(label)
        title.setStyleSheet("font-weight: 600; font-size: 14px;")
        text_layout.addWidget(title)

        desc = QLabel(description)
        desc.setProperty("muted", True)
        desc.setWordWrap(True)
        text_layout.addWidget(desc)

        card_layout.addLayout(text_layout, 1)

        return card

    def _on_profile_clicked(self, button):
        self._selected_profile = button.property("profile")
        self.profile_selected.emit(self._selected_profile)

    def get_selected_profile(self) -> Optional[str]:
        return self._selected_profile


class TaskSelectionPage(QWidget):
    """Page for selecting or writing a task."""

    task_ready = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._profile = "generic"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        self.title_label = QLabel("Escolha uma tarefa inicial")
        self.title_label.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(
            "Selecione um exemplo pronto ou escreva sua própria tarefa. "
            "Recomendamos começar com algo simples e seguro."
        )
        self.subtitle_label.setProperty("muted", True)
        self.subtitle_label.setWordWrap(True)
        layout.addWidget(self.subtitle_label)

        # Example cards container
        self.examples_container = QVBoxLayout()
        self.examples_container.setSpacing(8)
        layout.addLayout(self.examples_container)

        # Custom task option
        custom_frame = QFrame()
        custom_frame.setProperty("card", True)
        custom_layout = QVBoxLayout(custom_frame)
        custom_layout.setContentsMargins(12, 10, 12, 10)

        custom_header = QHBoxLayout()
        self.custom_radio = QRadioButton("Escrever minha própria tarefa")
        self.custom_radio.toggled.connect(self._on_custom_toggled)
        custom_header.addWidget(self.custom_radio)
        custom_layout.addLayout(custom_header)

        self.custom_edit = QTextEdit()
        self.custom_edit.setPlaceholderText(
            "Descreva o que você quer fazer...\n\n"
            "Dica: inclua o objetivo, o resultado esperado e restrições importantes."
        )
        self.custom_edit.setMaximumHeight(120)
        self.custom_edit.setEnabled(False)
        self.custom_edit.textChanged.connect(self._on_custom_text_changed)
        custom_layout.addWidget(self.custom_edit)

        layout.addWidget(custom_frame)

        # Tips
        tips_frame = QFrame()
        tips_layout = QVBoxLayout(tips_frame)
        tips_layout.setContentsMargins(0, 8, 0, 0)

        tips_title = QLabel("Dicas para a primeira tarefa:")
        tips_title.setStyleSheet("font-weight: 600; font-size: 12px;")
        tips_layout.addWidget(tips_title)

        tips_text = QLabel(
            "• Comece com algo pequeno e seguro\n"
            "• Evite exclusões ou migrações na primeira vez\n"
            "• Use tarefas de análise ou documentação primeiro\n"
            "• Deixe a validação automática ativada"
        )
        tips_text.setProperty("muted", True)
        tips_layout.addWidget(tips_text)

        layout.addWidget(tips_frame)
        layout.addStretch()

        self.example_radios: list[QRadioButton] = []
        self.button_group = QButtonGroup(self)
        self.button_group.addButton(self.custom_radio)

    def set_profile(self, profile: str):
        self._profile = profile
        self._rebuild_examples()

    def _rebuild_examples(self):
        # Clear existing
        for radio in self.example_radios:
            self.button_group.removeButton(radio)
        self.example_radios.clear()

        while self.examples_container.count():
            item = self.examples_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add examples for profile
        examples = FIRST_TASK_EXAMPLES.get(self._profile, FIRST_TASK_EXAMPLES["generic"])

        for i, example in enumerate(examples):
            card = self._create_example_card(example, i)
            self.examples_container.addWidget(card)

        # Select first by default
        if self.example_radios:
            self.example_radios[0].setChecked(True)
            self._emit_task()

    def _create_example_card(self, example: FirstTaskExample, index: int) -> QFrame:
        card = QFrame()
        card.setProperty("card", True)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)

        radio = QRadioButton()
        radio.setProperty("example_index", index)
        radio.toggled.connect(self._on_example_toggled)
        self.button_group.addButton(radio)
        self.example_radios.append(radio)
        card_layout.addWidget(radio)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)

        title = QLabel(example.title)
        title.setStyleSheet("font-weight: 600;")
        text_layout.addWidget(title)

        desc = QLabel(example.description)
        desc.setProperty("muted", True)
        desc.setWordWrap(True)
        text_layout.addWidget(desc)

        card_layout.addLayout(text_layout, 1)

        return card

    def _on_example_toggled(self, checked: bool):
        if checked:
            self.custom_edit.setEnabled(False)
            self._emit_task()

    def _on_custom_toggled(self, checked: bool):
        self.custom_edit.setEnabled(checked)
        if checked:
            self._emit_task()

    def _on_custom_text_changed(self):
        if self.custom_radio.isChecked():
            self._emit_task()

    def _emit_task(self):
        task = self.get_task_text()
        if task:
            self.task_ready.emit(task)

    def get_task_text(self) -> str:
        if self.custom_radio.isChecked():
            return self.custom_edit.toPlainText().strip()

        # Find selected example
        for radio in self.example_radios:
            if radio.isChecked():
                index = radio.property("example_index")
                examples = FIRST_TASK_EXAMPLES.get(self._profile, FIRST_TASK_EXAMPLES["generic"])
                if 0 <= index < len(examples):
                    return examples[index].task_text

        return ""


class ReviewPage(QWidget):
    """Page for reviewing the task before execution."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        title = QLabel("Revise antes de executar")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")
        layout.addWidget(title)

        subtitle = QLabel(
            "Confira os detalhes abaixo. Quando estiver pronto, clique em Executar."
        )
        subtitle.setProperty("muted", True)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Summary card
        card = QFrame()
        card.setProperty("card", True)
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)
        card_layout.setContentsMargins(16, 14, 16, 14)

        # Task
        task_header = QLabel("Tarefa")
        task_header.setStyleSheet("font-weight: 600; color: #6b7280; font-size: 11px;")
        card_layout.addWidget(task_header)

        self.task_label = QLabel()
        self.task_label.setWordWrap(True)
        self.task_label.setStyleSheet("font-size: 13px;")
        card_layout.addWidget(self.task_label)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #2a2f3a;")
        card_layout.addWidget(sep)

        # Details grid
        details = QHBoxLayout()
        details.setSpacing(24)

        # Left column
        left = QVBoxLayout()
        left.setSpacing(8)

        profile_header = QLabel("Perfil")
        profile_header.setStyleSheet("font-weight: 600; color: #6b7280; font-size: 11px;")
        left.addWidget(profile_header)
        self.profile_label = QLabel("flutter")
        left.addWidget(self.profile_label)

        mode_header = QLabel("Modo")
        mode_header.setStyleSheet("font-weight: 600; color: #6b7280; font-size: 11px;")
        left.addWidget(mode_header)
        self.mode_label = QLabel("Simples")
        left.addWidget(self.mode_label)

        details.addLayout(left)

        # Right column
        right = QVBoxLayout()
        right.setSpacing(8)

        validation_header = QLabel("Validação")
        validation_header.setStyleSheet("font-weight: 600; color: #6b7280; font-size: 11px;")
        right.addWidget(validation_header)
        self.validation_label = QLabel("Automática")
        self.validation_label.setStyleSheet("color: #22c55e;")
        right.addWidget(self.validation_label)

        iterations_header = QLabel("Iterações")
        iterations_header.setStyleSheet("font-weight: 600; color: #6b7280; font-size: 11px;")
        right.addWidget(iterations_header)
        self.iterations_label = QLabel("Até 3")
        right.addWidget(self.iterations_label)

        details.addLayout(right)
        details.addStretch()

        card_layout.addLayout(details)
        layout.addWidget(card)

        # What will happen
        info_card = QFrame()
        info_card.setProperty("card", True)
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(16, 14, 16, 14)

        info_title = QLabel("O que vai acontecer:")
        info_title.setStyleSheet("font-weight: 600;")
        info_layout.addWidget(info_title)

        steps = QLabel(
            "1. O planner vai analisar a tarefa e criar uma estratégia\n"
            "2. O executor vai aplicar as mudanças no código\n"
            "3. O reviewer vai conferir o resultado\n"
            "4. A validação vai rodar os testes do perfil\n"
            "5. Você poderá ver o relatório final"
        )
        steps.setProperty("muted", True)
        info_layout.addWidget(steps)

        layout.addWidget(info_card)
        layout.addStretch()

    def set_task(self, task: str):
        display = task[:300] + "..." if len(task) > 300 else task
        self.task_label.setText(display)

    def set_profile(self, profile: str):
        self.profile_label.setText(profile.capitalize())


class FirstTaskWizard(QDialog):
    """Wizard for guiding the user through their first task."""

    task_submitted = Signal(str, str)  # task_text, profile
    navigate_to_dashboard = Signal()

    def __init__(self, project_path: Optional[Path] = None, parent=None):
        super().__init__(parent)
        self.project_path = project_path or Path.cwd()
        self._current_page = 0
        self._profile = "generic"
        self._task_text = ""
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Sua Primeira Tarefa")
        self.setMinimumSize(580, 520)

        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #161a22; border-bottom: 1px solid #2a2f3a;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(24, 16, 24, 16)

        title = QLabel("Primeira Tarefa Guiada")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        header_layout.addWidget(title)

        subtitle = QLabel("Vamos executar sua primeira tarefa juntos, passo a passo.")
        subtitle.setProperty("muted", True)
        header_layout.addWidget(subtitle)

        # Progress indicator
        self.progress_label = QLabel("Etapa 1 de 3")
        self.progress_label.setStyleSheet("color: #4f8cff; font-size: 12px;")
        header_layout.addWidget(self.progress_label)

        layout.addWidget(header)

        # Pages
        self.stack = QStackedWidget()

        self.profile_page = ProfileSelectionPage()
        self.profile_page.profile_selected.connect(self._on_profile_selected)
        self.stack.addWidget(self.profile_page)

        self.task_page = TaskSelectionPage()
        self.task_page.task_ready.connect(self._on_task_ready)
        self.stack.addWidget(self.task_page)

        self.review_page = ReviewPage()
        self.stack.addWidget(self.review_page)

        layout.addWidget(self.stack, 1)

        # Footer
        footer = QFrame()
        footer.setStyleSheet("background-color: #161a22; border-top: 1px solid #2a2f3a;")
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(24, 12, 24, 12)

        self.back_btn = QPushButton("Voltar")
        self.back_btn.setProperty("ghost", True)
        self.back_btn.clicked.connect(self._on_back)
        self.back_btn.setVisible(False)
        footer_layout.addWidget(self.back_btn)

        footer_layout.addStretch()

        self.skip_btn = QPushButton("Pular")
        self.skip_btn.setProperty("ghost", True)
        self.skip_btn.clicked.connect(self.reject)
        footer_layout.addWidget(self.skip_btn)

        self.next_btn = QPushButton("Próximo")
        self.next_btn.clicked.connect(self._on_next)
        footer_layout.addWidget(self.next_btn)

        layout.addWidget(footer)

    def _on_profile_selected(self, profile: str):
        self._profile = profile

    def _on_task_ready(self, task: str):
        self._task_text = task

    def _on_back(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._update_page()

    def _on_next(self):
        if self._current_page == 0:
            # Profile -> Task
            if not self._profile:
                self._profile = "generic"
            self.task_page.set_profile(self._profile)
            self._current_page = 1
            self._update_page()

        elif self._current_page == 1:
            # Task -> Review
            self._task_text = self.task_page.get_task_text()
            if not self._task_text:
                return
            self.review_page.set_task(self._task_text)
            self.review_page.set_profile(self._profile)
            self._current_page = 2
            self._update_page()

        elif self._current_page == 2:
            # Execute
            self.task_submitted.emit(self._task_text, self._profile)
            self.accept()

    def _update_page(self):
        self.stack.setCurrentIndex(self._current_page)
        self.progress_label.setText(f"Etapa {self._current_page + 1} de 3")
        self.back_btn.setVisible(self._current_page > 0)

        if self._current_page == 2:
            self.next_btn.setText("Executar")
            self.next_btn.setStyleSheet("background-color: #22c55e;")
        else:
            self.next_btn.setText("Próximo")
            self.next_btn.setStyleSheet("")

    def get_task_text(self) -> str:
        return self._task_text

    def get_profile(self) -> str:
        return self._profile


class FirstRunCompletionDialog(QDialog):
    """Dialog shown after first run completes."""

    open_dashboard = Signal()
    create_new_task = Signal()
    open_artifacts = Signal(str)  # run_id
    open_diagnostics = Signal()
    open_manual = Signal()

    def __init__(self, run_id: str, success: bool, summary: str, parent=None):
        super().__init__(parent)
        self.run_id = run_id
        self.success = success
        self.summary = summary
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("Primeira Tarefa Concluída")
        self.setMinimumSize(480, 380)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # Status icon/header
        if self.success:
            status_text = "Tarefa concluída com sucesso!"
            status_color = "#22c55e"
        else:
            status_text = "A tarefa encontrou problemas"
            status_color = "#f59e0b"

        status = QLabel(status_text)
        status.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {status_color};")
        layout.addWidget(status)

        # Summary
        summary_card = QFrame()
        summary_card.setProperty("card", True)
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(16, 14, 16, 14)

        summary_header = QLabel("O que aconteceu:" if self.success else "Diagnóstico rápido:")
        summary_header.setStyleSheet("font-weight: 600; color: #6b7280; font-size: 11px;")
        summary_layout.addWidget(summary_header)

        summary_text = QLabel(self.summary[:500] if self.summary else "Execução processada.")
        summary_text.setWordWrap(True)
        summary_layout.addWidget(summary_text)

        layout.addWidget(summary_card)

        # Next steps
        next_header = QLabel("Próximos passos:")
        next_header.setStyleSheet("font-weight: 600;")
        layout.addWidget(next_header)

        if self.success:
            next_text = (
                "• Veja os artefatos gerados para entender o que mudou\n"
                "• Crie uma nova tarefa para continuar explorando\n"
                "• Consulte o manual se tiver dúvidas"
            )
        else:
            next_text = (
                "• Abra o Diagnóstico para validar ambiente, executor e credenciais\n"
                "• Consulte os artefatos e logs para ver onde a execução parou\n"
                "• Ajuste a configuração ou a tarefa e tente novamente"
            )

        next_label = QLabel(next_text)
        next_label.setProperty("muted", True)
        layout.addWidget(next_label)

        layout.addStretch()

        # Actions
        actions = QHBoxLayout()
        actions.setSpacing(10)

        artifacts_btn = QPushButton("Ver Artefatos")
        artifacts_btn.setProperty("secondary", True)
        artifacts_btn.setObjectName("first_run_artifacts_button")
        artifacts_btn.clicked.connect(lambda: self.open_artifacts.emit(self.run_id))
        actions.addWidget(artifacts_btn)

        if not self.success:
            diagnostics_btn = QPushButton("Abrir Diagnóstico")
            diagnostics_btn.setProperty("secondary", True)
            diagnostics_btn.setObjectName("first_run_diagnostics_button")
            diagnostics_btn.clicked.connect(self.open_diagnostics.emit)
            actions.addWidget(diagnostics_btn)

        manual_btn = QPushButton("Abrir Manual")
        manual_btn.setProperty("ghost", True)
        manual_btn.setObjectName("first_run_manual_button")
        manual_btn.clicked.connect(self.open_manual.emit)
        actions.addWidget(manual_btn)

        actions.addStretch()

        new_task_btn = QPushButton("Nova Tarefa")
        new_task_btn.setObjectName("first_run_new_task_button")
        new_task_btn.clicked.connect(self._on_new_task)
        actions.addWidget(new_task_btn)

        dashboard_btn = QPushButton("Ir para Dashboard")
        dashboard_btn.setProperty("secondary", True)
        dashboard_btn.setObjectName("first_run_dashboard_button")
        dashboard_btn.clicked.connect(self._on_dashboard)
        actions.addWidget(dashboard_btn)

        layout.addLayout(actions)

    def _on_new_task(self):
        self.create_new_task.emit()
        self.accept()

    def _on_dashboard(self):
        self.open_dashboard.emit()
        self.accept()
