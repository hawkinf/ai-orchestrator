"""Smoke tests for onboarding wizard."""

import pytest

pytest.importorskip("PySide6")


def test_onboarding_builds_settings(qapp, tmp_path):
    from gui.onboarding_wizard import OnboardingWizard

    wizard = OnboardingWizard(tmp_path)
    wizard.show()
    qapp.processEvents()

    wizard.project_page.project_edit.setText(str(tmp_path))
    wizard.project_page.profile_combo.setCurrentText("python")
    wizard.executor_page.command_edit.setText("claude")
    wizard.workspace_page.workspace_edit.setText(str(tmp_path / "workspace"))

    settings = wizard.build_settings()

    assert settings.project_path == str(tmp_path)
    assert settings.active_profile == "python"


def test_onboarding_destination_switches(qapp, tmp_path):
    from gui.onboarding_wizard import OnboardingWizard

    wizard = OnboardingWizard(tmp_path)
    wizard.show()
    qapp.processEvents()

    # Default should be first_task (recommended)
    assert wizard.selected_destination() == "first_task"

    # Switch to diagnostics
    wizard.finish_page.diagnostics_radio.setChecked(True)
    qapp.processEvents()

    assert wizard.selected_destination() == "diagnostics"


def test_onboarding_can_route_to_demo(qapp, tmp_path):
    from gui.onboarding_wizard import OnboardingWizard

    wizard = OnboardingWizard(tmp_path)
    wizard.show()
    qapp.processEvents()

    wizard.finish_page.demo_radio.setChecked(True)
    qapp.processEvents()

    assert wizard.selected_destination() == "demo"
