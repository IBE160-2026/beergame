"""Model configs, budgets and prompt files from the command line (`python -m app.ai.cli`, AD-6).

Subcommands:
  config add FILE        store a model config from a JSON file and print `config <id>`. Exit 1
                         when the file breaks a rule (one `error <code> <field>: <message>` line
                         per field on stderr: a credential in the file, a prompt version with no
                         file, an Effort level without both time values, ...), 2 when the file
                         cannot be read or is not one JSON object.
  config edit ID         write a NEW row from config ID and print `config <new id>`; the source
                         row never changes. `--prompt <purpose>=<version>` (repeatable) adds a
                         purpose to the `prompts` map or moves it to another version;
                         `--from FILE` takes the whole content from a file instead (any
                         `--prompt` is then laid over that file's map).
  config list            one line per row, oldest first: id, name, model version, endpoint,
                         region and whether a Class session or a simulation run references it.
  config show ID         the row as JSON.
  budget set             create or change one budget row: `--evaluation <config id>` (needs
                         `--limit`) or `--session <Class session id>` (limit defaults to
                         AI_DEFAULT_SESSION_BUDGET_USD); `--reserve` defaults to
                         AI_BUDGET_RESERVE_USD. Prints the row. Exit 1 when refused.
  prompts check          check the prompt files against `prompts/hashes.json` and every prompt
                         version a stored config references: one `error <problem>` line on
                         stderr per locked version changed or removed, file not locked, or
                         referenced version missing; exit 1 when there is any (Story 2.3).
  prompts lock           record the hash of every prompt file not locked yet and print
                         `locked <purpose>/v<N>` per file; existing entries never change.
                         Exit 1, with the problems on stderr, when a locked version was
                         changed or removed.

No credential is read, stored or printed: a config names only the environment variable.

The example files in `backend/ai-configs/` carry placeholder prices, rate limits and Effort
levels until the prototype sets them (issues #8, #9).
"""

import argparse
import asyncio
import json
import sys
import uuid
from collections.abc import Coroutine, Sequence
from decimal import Decimal, InvalidOperation
from pathlib import Path

from sqlalchemy.exc import DBAPIError, OperationalError

from app.ai import budget, config, prompt_files
from app.platform import db
from app.platform.config import get_settings
from app.platform.logging import configure_logging


def _run[T](coroutine: Coroutine[object, object, T]) -> T:
    # psycopg's async mode cannot run on Windows' default Proactor loop.
    factory = asyncio.SelectorEventLoop if sys.platform == "win32" else asyncio.new_event_loop
    return asyncio.run(coroutine, loop_factory=factory)


def _error(code: str, field: str, message: str) -> None:
    print(f"error {code}{' ' + field if field else ''}: {message}", file=sys.stderr)


def _report_db(exc: DBAPIError) -> int:
    if isinstance(exc, OperationalError):
        _error("db_unavailable", "", "cannot reach the database")
    else:
        _error("db_error", "", type(getattr(exc, "orig", exc)).__name__)
    return 1


def _read_json(path: str, parser: argparse.ArgumentParser) -> dict[str, object]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))  # a BOM is allowed
    except OSError as exc:
        parser.error(f"cannot read {path}: {exc.strerror or exc}")
    except ValueError as exc:
        parser.error(f"{path} is not JSON: {exc}")
    if not isinstance(data, dict):
        parser.error(f"{path} must hold one JSON object")
    return data


def _parse(data: dict[str, object]) -> config.ModelConfigSpec | None:
    try:
        return config.parse(data)
    except config.ConfigInvalid as exc:
        for error in exc.errors:
            _error(error.code, error.field, error.message)
        return None


def _print_added(row: config.ModelConfig) -> None:
    print(f"config {row.id}")
    if row.derived_from is not None:
        print(f"from {row.derived_from}")
    for level in row.spec.effort_levels:
        if level.placeholder:
            print(
                f"note: effort level {level.name} holds placeholder values (issues #8, #9)",
                file=sys.stderr,
            )


async def _store(coroutine: Coroutine[object, object, config.ModelConfig]) -> int:
    try:
        row = await coroutine
    except config.ConfigNotFound as exc:
        _error(exc.code, "", exc.message)
        return 1
    except config.ConfigInvalid as exc:
        for error in exc.errors:
            _error(error.code, error.field, error.message)
        return 1
    except DBAPIError as exc:
        return _report_db(exc)
    finally:
        await db.dispose()
    _print_added(row)
    return 0


def _config_add(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    spec = _parse(_read_json(args.file, parser))
    if spec is None:
        return 1
    return _run(_store(config.add(spec)))


def _prompt(text: str) -> tuple[str, int]:
    try:
        return config.parse_prompt(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from None


def _config_edit(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if not args.prompt and args.source is None:
        parser.error("give --prompt or --from")
    spec = None
    if args.source is not None:
        spec = _parse(_read_json(args.source, parser))
        if spec is None:
            return 1
    return _run(_store(config.derive(args.config_id, prompts=dict(args.prompt), spec=spec)))


async def _list() -> int:
    try:
        rows = await config.list_all()
    except DBAPIError as exc:
        return _report_db(exc)
    finally:
        await db.dispose()
    for row in rows:
        spec = row.spec
        print(
            f"config {row.id} name={spec.name} model={spec.model_version} "
            f"endpoint={spec.endpoint} region={spec.region} "
            f"referenced={'yes' if row.referenced else 'no'}"
        )
    return 0


def _config_list(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    return _run(_list())


async def _show(config_id: str) -> int:
    try:
        row = await config.get(config_id)
    except DBAPIError as exc:
        return _report_db(exc)
    finally:
        await db.dispose()
    if row is None:
        _error("config_not_found", "", f"no model config {config_id}")
        return 1
    shown = {
        "id": str(row.id),
        **row.spec.model_dump(mode="json"),
        "derived_from": None if row.derived_from is None else str(row.derived_from),
        "referenced_at": None if row.referenced_at is None else row.referenced_at.isoformat(),
        "created_at": row.created_at.isoformat(),
    }
    print(json.dumps(shown, indent=2))
    return 0


def _config_show(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    return _run(_show(args.config_id))


def _usd(text: str) -> Decimal:
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise argparse.ArgumentTypeError(f"{text!r} is not a USD amount") from None
    if not value.is_finite() or value < 0:
        raise argparse.ArgumentTypeError(f"{text!r} is not a USD amount of at least 0")
    return value


def _id(text: str) -> uuid.UUID:
    try:
        return uuid.UUID(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not an id") from None


def _money(value: Decimal) -> str:
    return f"{value:f}"


async def _set_budget(
    scope: budget.BudgetScope, limit: Decimal | None, reserve: Decimal | None
) -> int:
    try:
        row = await budget.set_budget(scope, limit=limit, reserve=reserve)
    except budget.BudgetRefused as exc:
        _error(exc.code, "", exc.message)
        return 1
    except DBAPIError as exc:
        return _report_db(exc)
    finally:
        await db.dispose()
    exhausted = "-" if row.players_exhausted_at is None else row.players_exhausted_at.isoformat()
    print(
        f"budget {row.scope.kind} {row.scope.id} limit={_money(row.limit)} "
        f"reserve={_money(row.reserve)} spent={_money(row.spent)} "
        f"players_exhausted_at={exhausted}"
    )
    return 0


def _budget_set(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    if args.evaluation is not None:
        scope = budget.BudgetScope.evaluation(args.evaluation)
    else:
        scope = budget.BudgetScope.class_session(args.session)
    return _run(_set_budget(scope, args.limit, args.reserve))


async def _check_prompts() -> int:
    try:
        rows = await config.list_all()
    except DBAPIError as exc:
        return _report_db(exc)
    finally:
        await db.dispose()
    references = [
        (purpose, version) for row in rows for purpose, version in row.spec.prompts.items()
    ]
    problems = prompt_files.check(references)
    for problem in problems:
        print(f"error {problem}", file=sys.stderr)
    if problems:
        return 1
    print(f"prompts ok: {len(prompt_files.read_lock())} locked, {len(set(references))} referenced")
    return 0


def _prompts_check(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    return _run(_check_prompts())


def _prompts_lock(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    for name in prompt_files.lock():
        print(f"locked {name}")
    problems = prompt_files.check()  # locking never hides a changed or removed version
    for problem in problems:
        print(f"error {problem}", file=sys.stderr)
    return 1 if problems else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.ai.cli",
        description="Register model configs and budgets, check prompt files (AD-6).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    groups = parser.add_subparsers(dest="group", required=True)

    config_parser = groups.add_parser("config", help="model configs")
    config_commands = config_parser.add_subparsers(dest="command", required=True)
    add = config_commands.add_parser("add", help="store a model config from a JSON file")
    add.add_argument("file")
    add.set_defaults(handler=_config_add, command_parser=add)
    edit = config_commands.add_parser("edit", help="write a new row from an existing config")
    edit.add_argument("config_id")
    edit.add_argument(
        "--prompt",
        type=_prompt,
        action="append",
        default=[],
        metavar="PURPOSE=VERSION",
        help="add a purpose or move it to another prompt version (repeatable)",
    )
    edit.add_argument("--from", dest="source", metavar="FILE", help="take the content from FILE")
    edit.set_defaults(handler=_config_edit, command_parser=edit)
    listing = config_commands.add_parser("list", help="every config row, oldest first")
    listing.set_defaults(handler=_config_list, command_parser=listing)
    show = config_commands.add_parser("show", help="one config row as JSON")
    show.add_argument("config_id")
    show.set_defaults(handler=_config_show, command_parser=show)

    budget_parser = groups.add_parser("budget", help="budgets")
    budget_commands = budget_parser.add_subparsers(dest="command", required=True)
    set_ = budget_commands.add_parser("set", help="create or change a scope's budget row")
    scope = set_.add_mutually_exclusive_group(required=True)
    scope.add_argument("--evaluation", type=_id, metavar="CONFIG_ID")
    scope.add_argument("--session", type=_id, metavar="CLASS_SESSION_ID")
    set_.add_argument("--limit", type=_usd, metavar="USD")
    set_.add_argument("--reserve", type=_usd, metavar="USD")
    set_.set_defaults(handler=_budget_set, command_parser=set_)

    prompts_parser = groups.add_parser("prompts", help="prompt files and their hash lock")
    prompts_commands = prompts_parser.add_subparsers(dest="command", required=True)
    check = prompts_commands.add_parser("check", help="check prompt files and stored configs")
    check.set_defaults(handler=_prompts_check, command_parser=check)
    lock = prompts_commands.add_parser("lock", help="record hashes of new prompt files")
    lock.set_defaults(handler=_prompts_lock, command_parser=lock)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args, args.command_parser)


if __name__ == "__main__":
    configure_logging(get_settings().log_level, stream=sys.stderr)
    raise SystemExit(main())
