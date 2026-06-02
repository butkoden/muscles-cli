from io import StringIO

from muscles import ActionDispatcher, ApplicationMeta, BaseStrategy, Context, StreamEvent, StreamResult
from muscles.cli import render_stream_result


class _EchoStrategy(BaseStrategy):
    def execute(self, *args, **kwargs):
        return kwargs


class _App(metaclass=ApplicationMeta):
    context = Context(_EchoStrategy)


def add_action(app, **options):
    handler = options.pop("handler")
    app.action(**options)(handler)


def test_cli_stream_text_output_uses_core_events():
    stream = StreamResult(
        source=[
            StreamEvent(type="progress", data={"step": 1}),
            StreamEvent(type="log", data={"message": "working"}),
            StreamEvent(type="result", data={"ok": True}),
        ]
    )
    stdout = StringIO()
    stderr = StringIO()

    result = render_stream_result(stream, stdout=stdout, stderr=stderr)

    assert result.exit_code == 0
    assert "progress: {'step': 1}" in stdout.getvalue()
    assert "log: {'message': 'working'}" in stdout.getvalue()
    assert "result: {'ok': True}" in stdout.getvalue()
    assert stderr.getvalue() == ""


def test_cli_stream_json_lines_output_is_machine_readable():
    stream = StreamResult(
        source=[
            StreamEvent(type="progress", data={"step": 1}, event_id="evt-1"),
            StreamEvent(type="result", data={"ok": True}),
        ]
    )
    stdout = StringIO()

    result = render_stream_result(stream, json_lines=True, stdout=stdout)

    assert result.exit_code == 0
    assert stdout.getvalue().splitlines() == [
        '{"event": "progress", "data": {"step": 1}, "id": "evt-1", "metadata": {}}',
        '{"event": "result", "data": {"ok": true}, "id": null, "metadata": {}}',
    ]


def test_cli_stream_error_returns_non_zero_exit_code():
    def source():
        yield StreamEvent(type="progress", data={"step": 1})
        raise RuntimeError("stream failed")

    stdout = StringIO()
    stderr = StringIO()

    result = render_stream_result(StreamResult(source=source()), stdout=stdout, stderr=stderr)

    assert result.exit_code == 1
    assert "progress" in stdout.getvalue()
    assert "stream_error" in stderr.getvalue()


def test_cli_non_stream_list_result_remains_regular_action_result():
    app = _App()
    add_action(app, name="bookings.list", transports=["cli"], handler=lambda payload, context: [{"id": 1}])

    result = ActionDispatcher(app).execute("bookings.list", {}, transport="cli")

    assert result.is_stream is False
    assert result.value == [{"id": 1}]
