"""Tests for the interactive in-app demo."""

import pytest

pytest.importorskip("PySide6")


def test_demo_scenarios_include_success_failure_and_checkpoint():
    from orchestrator.demo_run_builder import build_demo_scenarios

    scenarios = build_demo_scenarios()

    assert {"success", "failure", "checkpoint"} <= set(scenarios)
    assert "login" in scenarios["success"].task_text.lower()
    assert scenarios["failure"].outcome == "failure"
    assert scenarios["checkpoint"].outcome == "checkpoint"


def test_demo_controller_can_start_and_advance(qapp):
    from gui.main_window import MainWindow
    from gui.demo_controller import DemoController

    window = MainWindow(config=None, paths=None)
    window.show()
    qapp.processEvents()

    controller = DemoController(window)
    controller.start()
    qapp.processEvents()

    assert controller.current_step() is not None
    assert controller.overlay.isVisible()
    assert controller.current_step().key == "intro"

    controller.next_step()
    qapp.processEvents()
    assert controller.current_step().key == "command_center"

    controller.previous_step()
    qapp.processEvents()
    assert controller.current_step().key == "intro"

    controller.stop()
    qapp.processEvents()
    assert controller.current_step() is None
    assert not controller.overlay.isVisible()
    window.close()


def test_demo_controller_reaches_failure_and_checkpoint_steps(qapp):
    from gui.main_window import MainWindow
    from gui.demo_controller import DemoController

    window = MainWindow(config=None, paths=None)
    window.show()
    qapp.processEvents()

    controller = DemoController(window)
    controller.start()
    qapp.processEvents()

    while controller.current_step() and controller.current_step().key != "failure_run":
        controller.next_step()
        qapp.processEvents()

    assert controller.current_step() is not None
    assert controller.current_step().key == "failure_run"
    assert window.stack.currentWidget() is window.run_panel

    controller.stop()
    window.close()
