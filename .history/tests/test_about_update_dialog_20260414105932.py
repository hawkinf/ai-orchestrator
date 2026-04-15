"""Widget tests for About and Update dialogs."""

import pytest

from orchestrator.updater import ReleaseInfo, UpdateResult, UpdateStatus
from orchestrator.version import ReleaseChannel, Version, VersionInfo
from gui.about_dialog import AboutDialog
from gui.update_dialog import UpdateDialog


@pytest.mark.usefixtures("qapp")
class TestAboutDialog:
    """Tests for the about dialog."""

    def test_about_dialog_renders_version_info(self):
        info = VersionInfo(
            version=Version(0, 2, 0),
            channel=ReleaseChannel.STABLE,
            build_date="2026-04-14T10:00:00",
            app_name="AI Orchestrator",
        )

        dialog = AboutDialog(
            version_info=info,
            release_url="https://github.com/hawkinf/ai-orchestrator/releases",
            changelog_markdown="## v0.2.0\n- Release polish",
            auto_check_updates=True,
            update_channel="stable",
        )

        assert dialog.windowTitle()
        assert dialog.auto_check_checkbox.isChecked() is True
        assert "0.2.0" in dialog.changelog_browser.toPlainText()


@pytest.mark.usefixtures("qapp")
class TestUpdateDialog:
    """Tests for the update dialog."""

    def test_update_dialog_enables_update_when_release_available(self):
        dialog = UpdateDialog(
            current_version="0.2.0",
            release_url="https://github.com/hawkinf/ai-orchestrator/releases",
            auto_check_updates=True,
        )
        release = ReleaseInfo(
            tag_name="v0.3.0",
            name="v0.3.0",
            body="- Nova release\n- Melhorias de distribuição",
            published_at="2026-04-14T12:00:00Z",
            prerelease=False,
            draft=False,
            html_url="https://github.com/hawkinf/ai-orchestrator/releases/tag/v0.3.0",
        )
        result = UpdateResult(
            status=UpdateStatus.UPDATE_AVAILABLE,
            current_version="0.2.0",
            latest_version="0.3.0",
            release_info=release,
        )

        dialog.present_result(result)

        assert dialog.update_button.isEnabled() is True
        assert "0.3.0" in dialog.latest_version_label.text()
        assert "Melhorias de distribuição" in dialog.changelog_browser.toPlainText()

    def test_update_dialog_shows_up_to_date_state(self):
        dialog = UpdateDialog(
            current_version="0.2.0",
            release_url="https://github.com/hawkinf/ai-orchestrator/releases",
            auto_check_updates=False,
        )
        result = UpdateResult(
            status=UpdateStatus.UP_TO_DATE,
            current_version="0.2.0",
            latest_version="0.2.0",
        )

        dialog.present_result(result)

        assert dialog.update_button.isEnabled() is False
        assert "mais recente" in dialog.summary_label.text().lower()