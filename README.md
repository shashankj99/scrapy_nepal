# Scraper CLI

Run the scraper from a terminal. It loads places from a configured source, validates the records, and can write them to PostgreSQL for your other app.

## 1. Run the demo now

Open a terminal and run:

```sh
cd /Users/shashankjha/workspace/freelancing/scrapy_nepal
./venv/bin/python scraper.py sources
./venv/bin/python scraper.py run demo --dry-run
```

The commands use the existing virtual environment directly. The second command should print:

```json
{"source": "demo", "valid": 1}
```

The demo reads one synthetic place from `fixtures/places.json`. It needs no database, credentials, network connection, or third-party Python packages. If you’re setting up a fresh checkout, use Python 3.11 or newer and run `python3 -m venv venv` first.

## 2. Set up PostgreSQL for writes

You need a running PostgreSQL instance, the `psql` client, and an admin or migration connection. If you already have a database for testing, use its name in place of `scraper_dev`.

Install the database driver in the project environment:

```sh
./venv/bin/python -m pip install -r requirements.txt
```

For a fresh local PostgreSQL instance, connect as an administrator to the maintenance database with `psql -d postgres`. Use your normal admin connection settings if your server requires them. At the `psql` prompt, run the following once. Skip any database or role creation that your administrator has already performed.

```sql
CREATE DATABASE scraper_dev;
CREATE ROLE scraper_writer LOGIN;
CREATE ROLE scraper_reader LOGIN;
\password scraper_writer
\password scraper_reader
\connect scraper_dev
\set ON_ERROR_STOP on
\i migrations/001_initial.sql
\i migrations/grants.sql
\quit
```

Run these commands from the project directory so `psql` can find the migration files. The migrations grant the writer access to the ingestion tables and give the reader access to `ingest.places`. For a managed database, have your administrator provision the roles and run the same two SQL files in order.

Set the connection details in your shell. This example uses a local PostgreSQL Unix socket. Replace `/tmp` if your server puts its socket elsewhere.

```sh
export PGHOST=/tmp
export PGPORT=5432
export PGDATABASE=scraper_dev
export PGUSER=scraper_writer
```

If your server requires password authentication, create a password file outside the repository, restrict it to mode `0600`, and set `PGPASSFILE` to its path. Enter the real password in the file using an editor or provision it through your secret store. The file format is `host:port:database:user:password`. Use the same connection details as above. For a remote database, set `PGHOST` to the server’s DNS name and `PGSSLROOTCERT` to the trusted CA file. The CLI verifies the remote certificate and hostname. Keep credentials out of shell commands, project files, and logs.

## 3. Verify a database write

Run this against your **test database**. The explicit flag allows the synthetic demo record to be stored.

```sh
./venv/bin/python scraper.py run demo --allow-fixture-write
./venv/bin/python scraper.py run demo --allow-fixture-write
./venv/bin/python scraper.py runs --source demo
```

On a fresh database, the first run reports `inserted: 1`. The second reports `unchanged: 1`. The last command shows recent import attempts. Your other app can read `ingest.places` using the reader role.

## 4. Run a real source

Only `demo` ships enabled. To import real data, uncomment and adapt one of the examples in [sources.toml](sources.toml). Replace the example URL and host, set a credible minimum row count, and record the applicable access and reuse terms.

- **JSON feed** uses an array with the fields shown in [the demo fixture](fixtures/places.json). Each item needs a stable ID.
- **HTML directory** uses `format = "place-jsonld"` and a mapping from Schema.org types to categories. The built-in parser reads a single page with object, array, or top-level `@graph` JSON-LD. Other markup, pagination, and JavaScript-rendered sources require an adapter.

For a source configured under `[sources.directory]`, run:

```sh
./venv/bin/python scraper.py sources
./venv/bin/python scraper.py run directory --dry-run
./venv/bin/python scraper.py run directory
./venv/bin/python scraper.py runs --source directory
```

Only run the write command after the dry run returns the expected count. The crawler uses HTTPS, honors crawler rules, throttles requests, and checks redirect destinations. Schedule the same write command with absolute paths if you later use cron. Set a job deadline and capture the exit status.

## Troubleshooting

| What you see | What to check |
|---|---|
| `install_database_dependencies` | Install `requirements.txt` using `./venv/bin/python -m pip`. |
| `missing_database_configuration` | Set `PGHOST`, `PGDATABASE`, and `PGUSER` in the terminal running the CLI. |
| `operation_failed` | The CLI hides underlying error details. Check that PostgreSQL is running, the migrations ran in the target database, and the connection settings, password file, and remote CA are correct. |
| `unknown_source` | Run `sources` and use the ID listed there. |
| `unexpected_record_count` | Compare the source output with its configured `minimum_rows` and check that it still returns the expected data. |

Run the unit tests with `./venv/bin/python -m unittest discover -s tests -v`.

## Database behavior

`source_id` and `external_id` identify each place. The importer stores the name, category, locality, and public source URL. Successful runs refresh `last_seen_at`. The `updated_at` value changes when the record’s fields change. Records missing from a later batch retain their previous timestamps.

The CLI rejects invalid, duplicate, and unexpectedly small batches. A per-source lock prevents overlapping runs, and completed imports update the dataset and run status in one transaction. Failed imports preserve prior data. A subsequent import marks abandoned runs as interrupted.

Exit codes are 0 for success, 1 for an import or configuration error, 2 for invalid CLI syntax, and 130 for keyboard interruption.
