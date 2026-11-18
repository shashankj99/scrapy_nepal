"""Import configured place feeds into PostgreSQL."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Set
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias, TypedDict, cast
from uuid import uuid4

import tomllib

from crawler import MAX_BYTES, Fetcher, ImportFailure, public_url
from place_html import extract

if TYPE_CHECKING:
    from psycopg import Connection

    DbConnection: TypeAlias = Connection[tuple[Any, ...]]


class SourceConfig(TypedDict, total=False):
    fixture: str
    format: str
    url: str
    hosts: list[str]
    minimum_rows: int
    categories: dict[str, str]
    reuse: str


PlaceRows = dict[str, tuple[str, str, str, str]]

ROOT = Path(__file__).resolve().parent
FIELDS = ("id", "name", "category", "locality", "source_url")
MAX_ROWS = 10_000


def load_source(body: bytes, minimum_rows: int, hosts: Set[str]) -> PlaceRows:
    try:
        records = json.loads(body)
    except (ValueError, RecursionError):
        raise ImportFailure("invalid_json") from None
    return validate_records(records, minimum_rows, hosts)


def validate_records(records: object, minimum_rows: int, hosts: Set[str]) -> PlaceRows:
    if not isinstance(records, list) or not minimum_rows <= len(records) <= MAX_ROWS:
        raise ImportFailure("unexpected_record_count")
    rows: PlaceRows = {}
    rejected = 0
    for record in records:
        try:
            if not isinstance(record, dict):
                raise ImportFailure("invalid_record")
            fields: list[str] = []
            for field in FIELDS:
                value = record.get(field)
                limit = 2048 if field in {"id", "source_url"} else 300
                if (
                    not isinstance(value, str)
                    or not value.strip()
                    or len(value) > limit
                    or any(ord(char) < 32 or 0xD800 <= ord(char) <= 0xDFFF for char in value)
                ):
                    raise ImportFailure("invalid_record")
                fields.append(value.strip())
            key, name, category, locality, source_url = fields
            url = public_url(source_url)
            if key in rows or url.hostname is None or url.hostname not in hosts or url.query:
                raise ImportFailure("invalid_record")
            rows[key] = (name, category, locality, source_url)
        except ImportFailure:
            rejected += 1
    if rejected:
        raise ImportFailure("invalid_records", rejected)
    return rows


def collect(source: SourceConfig) -> PlaceRows:
    final_url = None
    hosts: Set[str]
    if "fixture" in source:
        if source.get("format", "json") != "json":
            raise ImportFailure("unknown_fixture_format")
        with (ROOT / source["fixture"]).open("rb") as fixture:
            body = fixture.read(MAX_BYTES + 1)
        hosts = {"example.com"}
    else:
        if "hosts" not in source or "url" not in source:
            raise ImportFailure("missing_source_endpoint")
        hosts = frozenset(source["hosts"])
        body, final_url = Fetcher(hosts).fetch(source["url"])
    if len(body) > MAX_BYTES:
        raise ImportFailure("source_too_large")
    minimum_rows = source.get("minimum_rows", 1)
    if not isinstance(minimum_rows, int) or not 1 <= minimum_rows <= MAX_ROWS:
        raise ImportFailure("invalid_minimum_rows")
    source_format = source.get("format", "json")
    if source_format == "json":
        return load_source(body, minimum_rows, hosts)
    if source_format == "place-jsonld" and final_url is not None:
        if "categories" not in source:
            raise ImportFailure("missing_source_categories")
        records = extract(body, final_url, source["categories"])
        return validate_records(records, minimum_rows, hosts)
    raise ImportFailure("unknown_source_format")


def connect() -> DbConnection:
    try:
        import psycopg
    except ImportError:
        raise ImportFailure("install_database_dependencies") from None
    required = ("PGHOST", "PGDATABASE", "PGUSER")
    if any(not os.environ.get(name) for name in required):
        raise ImportFailure("missing_database_configuration")
    host = os.environ["PGHOST"]
    if "," in host or (not host.startswith("/") and "/" in host):
        raise ImportFailure("invalid_database_host")
    return psycopg.connect(
        host=host,
        hostaddr="",
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        port=os.environ.get("PGPORT", "5432"),
        sslmode="verify-full",
        gssencmode="disable",
        connect_timeout=5,
        options="-c statement_timeout=30000 -c lock_timeout=5000 -c search_path=pg_catalog",
        autocommit=True,
    )


def save(conn: DbConnection, source_id: str, rows: PlaceRows) -> tuple[int, int, int]:
    existing = dict(
        (key, (name, category, locality, url))
        for key, name, category, locality, url in conn.execute(
            "SELECT external_id, name, category, locality, source_url "
            "FROM ingest.places WHERE source_id = %s",
            (source_id,),
        )
    )
    inserted = sum(key not in existing for key in rows)
    updated = sum(key in existing and existing[key] != values for key, values in rows.items())
    with conn.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO ingest.places (source_id, external_id, name, category, locality, source_url)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (source_id, external_id) DO UPDATE SET
                name = excluded.name,
                category = excluded.category,
                locality = excluded.locality,
                source_url = excluded.source_url,
                last_seen_at = now(),
                updated_at = CASE
                    WHEN (places.name, places.category, places.locality, places.source_url)
                         IS DISTINCT FROM
                         (excluded.name, excluded.category, excluded.locality, excluded.source_url)
                    THEN now() ELSE places.updated_at END
            """,
            [(source_id, key, *values) for key, values in rows.items()],
        )
    return inserted, updated, len(rows) - inserted - updated


def import_rows(conn: DbConnection, source_id: str, source: SourceConfig) -> dict[str, int | str]:
    lock_row = conn.execute(
        "SELECT pg_try_advisory_lock(hashtextextended(%s, 0))",
        (f"ingest:{source_id}",),
    ).fetchone()
    if lock_row is None:
        raise ImportFailure("lock_result_missing")
    if not lock_row[0]:
        raise ImportFailure("source_already_running")
    run_id = uuid4()
    with conn.transaction():
        conn.execute(
            "INSERT INTO ingest.sources (id, reuse) VALUES (%s, %s) "
            "ON CONFLICT (id) DO UPDATE SET reuse = excluded.reuse",
            (source_id, source.get("reuse", "Synthetic test data")),
        )
        conn.execute(
            "UPDATE ingest.crawl_runs SET status = 'failed', finished_at = now(), "
            "error_code = 'interrupted' WHERE source_id = %s AND status = 'running'",
            (source_id,),
        )
        conn.execute(
            "INSERT INTO ingest.crawl_runs (id, source_id, status) VALUES (%s, %s, 'running')",
            (run_id, source_id),
        )
    try:
        rows = collect(source)
        with conn.transaction():
            counts = save(conn, source_id, rows)
            conn.execute(
                "UPDATE ingest.crawl_runs SET status = 'succeeded', finished_at = now(), "
                "inserted = %s, updated = %s, unchanged = %s, rejected = 0 WHERE id = %s",
                (*counts, run_id),
            )
    except Exception as error:
        failure = error if isinstance(error, ImportFailure) else ImportFailure("import_failed")
        conn.execute(
            "UPDATE ingest.crawl_runs SET status = 'failed', finished_at = now(), "
            "error_code = %s, rejected = %s WHERE id = %s",
            (failure.code, failure.rejected, run_id),
        )
        raise failure from None
    inserted, updated, unchanged = counts
    return {
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "run_id": str(run_id),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="scraper")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sources")
    run = commands.add_parser("run")
    run.add_argument("source")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--allow-fixture-write", action="store_true", help="Use only with a test database")
    history = commands.add_parser("runs")
    history.add_argument("--source", required=True)
    args = parser.parse_args()
    try:
        settings = tomllib.loads((ROOT / "sources.toml").read_text(encoding="utf-8"))
        sources = cast(dict[str, SourceConfig], settings["sources"])
        if args.command == "sources":
            print(json.dumps({key: "fixture" if "fixture" in item else "https"
                              for key, item in sources.items()}))
            return 0
        if args.source not in sources:
            raise ImportFailure("unknown_source")
        source = sources[args.source]
        if args.command == "run":
            if "fixture" not in source and not source.get("reuse"):
                raise ImportFailure("missing_source_reuse_terms")
            if args.dry_run:
                print(json.dumps({"source": args.source, "valid": len(collect(source))}))
                return 0
            if "fixture" in source and not args.allow_fixture_write:
                raise ImportFailure("fixture_write_requires_explicit_flag")
        result: dict[str, int | str] | list[dict[str, Any]]
        with connect() as conn:
            if args.command == "run":
                result = import_rows(conn, args.source, source)
            else:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT id, status, started_at, finished_at, inserted, updated, "
                        "unchanged, rejected, error_code FROM ingest.crawl_runs "
                        "WHERE source_id = %s ORDER BY started_at DESC LIMIT 20",
                        (args.source,),
                    )
                    if cursor.description is None:
                        raise ImportFailure("run_history_missing")
                    columns = [column.name for column in cursor.description]
                    result = [dict(zip(columns, row, strict=True)) for row in cursor]
            print(json.dumps(result, default=str))
        return 0
    except ImportFailure as error:
        print(json.dumps({"error": error.code, "rejected": error.rejected}), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print('{"error":"interrupted"}', file=sys.stderr)
        return 130
    except Exception:
        # Driver and network exceptions may contain credential or source details.
        print('{"error":"operation_failed"}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
