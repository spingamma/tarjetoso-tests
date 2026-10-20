#!/usr/bin/env python3
"""Genera el reporte diario copy-ready de las columnas QA de Jira Cloud."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from utils.jira_daily_review import (  # noqa: E402
    DEFAULT_COLUMNS,
    DEFAULT_TIMEZONE,
    JiraCloudClient,
    JiraConfigurationError,
    JiraRequestError,
    JiraSettings,
    atomic_write,
    normalize_issues,
    render_report,
    resolve_columns,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--env-file",
        default=str(REPO_ROOT / ".env.jira"),
        help="Archivo local de credenciales (default: .env.jira en tarjetoso-tests o raiz)",
    )
    parser.add_argument("--board-id", type=int, default=None)
    parser.add_argument(
        "--column",
        action="append",
        dest="columns",
        help="Columna a incluir; puede repetirse. Por defecto usa las dos columnas QA o JIRA_COLUMNS.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor", help="Valida autenticacion, board y columnas")
    update = subparsers.add_parser("update", help="Actualiza el reporte Markdown")
    update.add_argument(
        "--output",
        default=str(REPO_ROOT / "artifacts" / "jira" / "jira_qa_daily.md"),
    )
    update.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    return parser


def _load(args: argparse.Namespace) -> tuple[JiraCloudClient, list[dict]]:
    env_path = Path(args.env_file).expanduser().resolve()
    if not env_path.exists():
        fallback_path = REPO_ROOT.parent / ".env.jira"
        if fallback_path.exists():
            env_path = fallback_path
        else:
            raise JiraConfigurationError(
                f"No existe {env_path}. Copia .env.jira.example a .env.jira y completa el token."
            )
    load_dotenv(env_path, override=False)
    settings = JiraSettings.from_env(args.board_id)
    client = JiraCloudClient(settings)
    configuration = client.board_configuration()

    env_columns = [
        col.strip()
        for col in os.getenv("JIRA_COLUMNS", "").split(",")
        if col.strip()
    ]
    requested_columns = args.columns or env_columns or DEFAULT_COLUMNS
    columns = resolve_columns(configuration, requested_columns)
    return client, columns


def _doctor(args: argparse.Namespace) -> None:
    client, columns = _load(args)
    user = client.current_user()
    print(f"Conexion Jira: OK ({user.get('displayName', 'usuario visible')})")
    print(f"Board {client.settings.board_id}: OK")
    for column in columns:
        print(f"Columna: {column['name']} | estados={','.join(column['status_ids'])}")


def _update(args: argparse.Namespace) -> None:
    client, columns = _load(args)
    status_ids = [status for column in columns for status in column["status_ids"]]
    raw_issues = client.board_issues(status_ids)
    comments_by_key: dict[str, list[dict]] = {}
    for issue in raw_issues:
        key = str(issue.get("key", "")).strip()
        if key:
            comments_by_key[key] = client.issue_comments(key)

    issues = normalize_issues(
        raw_issues,
        columns,
        comments_by_key,
        client.settings.base_url,
    )
    report = render_report(
        issues=issues,
        resolved_columns=columns,
        board_id=client.settings.board_id,
        base_url=client.settings.base_url,
        timezone_name=args.timezone,
    )
    output = Path(args.output).expanduser().resolve()
    atomic_write(output, report)
    print(f"Reporte actualizado: {output}")
    print(f"Tickets exportados: {len(issues)}")


def main() -> int:
    args = _parser().parse_args()
    try:
        if args.command == "doctor":
            _doctor(args)
        else:
            _update(args)
        return 0
    except (JiraConfigurationError, JiraRequestError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
