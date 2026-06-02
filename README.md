# Muscles CLI

`muscles-cli` is the console runtime for Muscles. It uses the same application
shape as the HTTP runtimes: an `ApplicationMeta` class owns a `Context`, and the
context delegates execution to `CliStrategy`.

## Installation

Canonical ecosystem install matrix is documented in core:
[Muscles installation matrix](https://github.com/butkoden/muscles/blob/master/docs/installation.md).

## Project Scaffolding

Use canonical command `muscles new`:

```bash
muscles new demo --runtime asgi
muscles new demo --runtime wsgi
muscles new demo --runtime cli
```

Notes:

- `muscular new` is not a canonical command.
- Existing non-empty directory is rejected unless `--force` is used.

## AI Workflow Commands

```bash
muscles capabilities --json
muscles inspect --json --app app.application:App
muscles routes --app app.application:App
muscles schemas --app app.application:App
muscles rules --app app.application:App
muscles cli --app app.application:App
muscles generate page Home --with-tests
muscles doctor --json
muscles test --doctor
```

## Quick Start

```python
from muscles import ApplicationMeta, Context, cli
from muscles.cli import CliStrategy


class App(metaclass=ApplicationMeta):
    context = Context(CliStrategy, transport="cli")

    def run(self, *args):
        return self.context.execute(*args, shutup=True)


@cli.group()
def bookings(*args):
    """Booking commands."""
    return True


@bookings.command(command_name="remove")
def remove_booking(*args):
    booking_id = args[0]
    return f"removed {booking_id}"


app = App()
assert app.run("bookings", "remove", "1") == "removed 1"
```

## Routing Model

Groups and commands form a tree. That makes CLI routing close to HTTP routing:

- `bookings remove 1` is a nested route with an argument;
- `bookings/list` can be normalized by an application before calling the CLI;
- groups can have handlers, but returning `True` lets execution continue to a
  child command.

More detail: [docs/routing.md](docs/routing.md).

## Core Stream Output

English: CLI progress output uses core `StreamEvent` items from
`StreamResult`. `render_stream_result()` can print human-readable progress/log
and result lines, or machine-readable JSON lines. The CLI layer only owns
presentation and exit code mapping; stream semantics stay in `muscles.core`.

Русский: CLI progress output использует core `StreamEvent` из `StreamResult`.
`render_stream_result()` может печатать human-readable progress/log/result
строки или machine-readable JSON lines. CLI слой отвечает только за presentation
и exit code mapping; stream semantics остаётся в `muscles.core`.

## Arguments

Use `@cli.argument()` for named arguments and `@cli.flag()` for boolean flags.
Required prompted arguments use `input()` or `getpass.getpass()` when hidden.

For nested commands, define options on the parent group object:

```python
@cli.group(command_name="bookings")
def bookings(*args):
    return True

@bookings.command(command_name="list")
@bookings.argument("--limit", nargs=1, default="25")
def bookings_list(*args, limit):
    return limit
```

Canonical invocations for benchmark/automation scripts:

```bash
bookings list --limit 10
bookings list --limit=10
```

## Development

Run tests with the core package on `PYTHONPATH`:

```bash
PYTHONPATH=../muscles/src:src python -m pytest -q
```
