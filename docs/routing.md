# CLI Routing

The CLI runtime treats console commands as a route tree. A group is an internal
node and a command is usually a terminal node.

## Nested Groups

```python
from muscles import cli


@cli.group()
def bookings(*args):
    """Booking commands."""
    return True


@bookings.command(command_name="list")
def list_bookings(*args):
    return "list"


@bookings.command(command_name="remove")
def remove_booking(*args):
    return f"remove {args[0]}"
```

Calls:

```bash
python -m app.cli bookings list
python -m app.cli bookings remove 1
```

An application may also normalize slash notation before calling the framework:

```bash
python -m app.cli bookings/remove 1
```

The framework receives that as `bookings`, `remove`, `1`.

## Performance

Groups maintain a command index by command name. Execution and help rendering
look up the next child directly instead of scanning the whole child list for
every argument.

## Handler Return Values

A group handler can return a real result when the group itself is the requested
command. If it returns `True` while more arguments remain, the CLI continues to
the child route.

This keeps parent groups useful for help/default actions without blocking nested
commands.
