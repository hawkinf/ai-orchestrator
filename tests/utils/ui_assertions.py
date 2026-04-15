def assert_widget_ready(widget):
    assert widget is not None
    assert widget.isEnabled()