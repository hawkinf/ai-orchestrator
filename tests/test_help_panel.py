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
