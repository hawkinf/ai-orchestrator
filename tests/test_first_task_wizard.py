"""Tests for first task wizard."""

import pytest

pytest.importorskip("PySide6")


def test_first_task_wizard_creates_with_project_path(qapp, tmp_path):
    from gui.first_task_wizard import FirstTaskWizard

    wizard = FirstTaskWizard(tmp_path)
    wizard.show()
    qapp.processEvents()

    assert wizard.project_path == tmp_path
    assert wizard.windowTitle() == "Sua Primeira Tarefa"


def test_profile_selection_page_emits_signal(qapp, tmp_path):
    from gui.first_task_wizard import ProfileSelectionPage

    page = ProfileSelectionPage()
    page.show()
    qapp.processEvents()

    received_profiles = []
    page.profile_selected.connect(lambda p: received_profiles.append(p))

    # Find and click a profile radio button
    for button in page.button_group.buttons():
        if button.property("profile") == "flutter":
            button.click()
            break

    qapp.processEvents()

    assert "flutter" in received_profiles


def test_task_selection_page_sets_profile(qapp):
    from gui.first_task_wizard import TaskSelectionPage

    page = TaskSelectionPage()
    page.show()
    qapp.processEvents()

    page.set_profile("python")

    # Should have example radios after setting profile
    assert len(page.example_radios) > 0


def test_task_selection_page_returns_example_task(qapp):
    from gui.first_task_wizard import TaskSelectionPage, FIRST_TASK_EXAMPLES

    page = TaskSelectionPage()
    page.show()
    page.set_profile("flutter")
    qapp.processEvents()

    # First example should be selected by default
    task = page.get_task_text()

    # Should match the first flutter example
    expected = FIRST_TASK_EXAMPLES["flutter"][0].task_text
    assert task == expected


def test_task_selection_page_custom_task(qapp):
    from gui.first_task_wizard import TaskSelectionPage

    page = TaskSelectionPage()
    page.show()
    page.set_profile("generic")
    qapp.processEvents()

    # Select custom radio
    page.custom_radio.setChecked(True)
    qapp.processEvents()

    # Enter custom text
    custom_text = "My custom task description"
    page.custom_edit.setPlainText(custom_text)
    qapp.processEvents()

    assert page.get_task_text() == custom_text


def test_review_page_displays_task(qapp):
    from gui.first_task_wizard import ReviewPage

    page = ReviewPage()
    page.show()
    qapp.processEvents()

    test_task = "Test task description for review"
    page.set_task(test_task)

    assert test_task in page.task_label.text()


def test_review_page_displays_profile(qapp):
    from gui.first_task_wizard import ReviewPage

    page = ReviewPage()
    page.show()
    qapp.processEvents()

    page.set_profile("python")

    assert "Python" in page.profile_label.text()


def test_first_task_wizard_navigation(qapp, tmp_path):
    from gui.first_task_wizard import FirstTaskWizard

    wizard = FirstTaskWizard(tmp_path)
    wizard.show()
    qapp.processEvents()

    # Should start at page 0
    assert wizard._current_page == 0

    # Go to next page
    wizard._on_next()
    qapp.processEvents()

    assert wizard._current_page == 1


def test_first_task_wizard_emits_task_submitted(qapp, tmp_path):
    from gui.first_task_wizard import FirstTaskWizard

    wizard = FirstTaskWizard(tmp_path)
    wizard.show()
    qapp.processEvents()

    received_tasks = []

    def on_submitted(task, profile):
        received_tasks.append((task, profile))

    wizard.task_submitted.connect(on_submitted)

    # Navigate through pages - select profile on profile page
    for button in wizard.profile_page.button_group.buttons():
        if button.property("profile") == "generic":
            button.click()
            break
    qapp.processEvents()

    wizard._on_next()  # Profile -> Task
    qapp.processEvents()

    # Select custom task option and enter text
    wizard.task_page.custom_radio.setChecked(True)
    qapp.processEvents()
    wizard.task_page.custom_edit.setPlainText("Test task")
    qapp.processEvents()

    wizard._on_next()  # Task -> Review
    qapp.processEvents()

    wizard._on_next()  # Execute
    qapp.processEvents()

    assert len(received_tasks) == 1
    assert received_tasks[0] == ("Test task", "generic")


def test_first_run_completion_dialog_shows_success(qapp):
    from gui.first_task_wizard import FirstRunCompletionDialog

    dialog = FirstRunCompletionDialog(
        run_id="test-run-123",
        success=True,
        summary="Task completed successfully"
    )
    dialog.show()
    qapp.processEvents()

    assert "sucesso" in dialog.windowTitle().lower() or dialog.success


def test_first_run_completion_dialog_shows_failure(qapp):
    from gui.first_task_wizard import FirstRunCompletionDialog

    dialog = FirstRunCompletionDialog(
        run_id="test-run-123",
        success=False,
        summary="Task failed with error"
    )
    dialog.show()
    qapp.processEvents()

    assert not dialog.success


def test_first_task_examples_exist_for_all_profiles():
    from gui.first_task_wizard import FIRST_TASK_EXAMPLES

    expected_profiles = ["flutter", "python", "generic"]

    for profile in expected_profiles:
        assert profile in FIRST_TASK_EXAMPLES
        assert len(FIRST_TASK_EXAMPLES[profile]) >= 1

        for example in FIRST_TASK_EXAMPLES[profile]:
            assert example.profile == profile
            assert len(example.title) > 0
            assert len(example.description) > 0
            assert len(example.task_text) > 0


def test_first_task_example_dataclass():
    from gui.first_task_wizard import FirstTaskExample

    example = FirstTaskExample(
        profile="test",
        title="Test Title",
        description="Test Description",
        task_text="Test task text"
    )

    assert example.profile == "test"
    assert example.title == "Test Title"
    assert example.description == "Test Description"
    assert example.task_text == "Test task text"
