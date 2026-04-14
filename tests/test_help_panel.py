"""Tests for the embedded help panel."""

import pytest

pytest.importorskip("PySide6")


def test_help_panel_loads_sections(qapp):
    from gui.help_panel import HelpPanel

    panel = HelpPanel()
    panel.show()
    qapp.processEvents()

    assert panel.section_list.count() > 5
    assert "Visão Geral" in panel.content_browser.toPlainText()


def test_help_panel_search_filters_content(qapp):
    from gui.help_panel import HelpPanel

    panel = HelpPanel()
    panel.show()
    panel.search_input.setText("OpenAI")
    qapp.processEvents()

    visible_items = [
        panel.section_list.item(index).text()
        for index in range(panel.section_list.count())
        if not panel.section_list.item(index).isHidden()
    ]
    assert any("OpenAI" in item for item in visible_items)


def test_help_panel_has_system_insights_section(qapp):
    from gui.help_panel import HelpPanel

    panel = HelpPanel()
    panel.set_current_section("system_insights")

    assert "Insights do Sistema" in panel.content_browser.toPlainText()


def test_help_panel_has_recommended_actions_section(qapp):
    from gui.help_panel import HelpPanel

    panel = HelpPanel()
    panel.set_current_section("recommended_actions")

    assert "Ações Recomendadas" in panel.content_browser.toPlainText()
