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
\i migrations/002_place_details.sql
\quit
```

Run these commands from the project directory so `psql` can find the migration files. The migrations grant the writer access to the ingestion tables and give the reader access to `ingest.places`. For a managed database, have your administrator provision the roles and run the same SQL files in order.

Create a private `.env` file in the project directory. If you already have one, edit it directly.

```sh
test -e .env || install -m 600 .env.example .env
chmod 600 .env
nano .env
```

Set `PGHOST`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD` using your own connection details. For passwords containing spaces or `#`, use single quotes. Escape literal backslashes and single quotes inside a single-quoted value. `PGHOST=/tmp` uses a local PostgreSQL Unix socket. For a remote database, use its DNS name and set `PGSSLROOTCERT` to the trusted CA file path. TCP connections use verified TLS by default. If a local PostgreSQL server has no TLS, set `PGHOST=localhost` and `PGSSLMODE=disable`. The CLI allows that setting only on loopback.

The CLI reads the project’s `.env` automatically for database commands. Existing environment variables take precedence. The file is ignored by Git. You can also leave `PGPASSWORD` blank and use your existing PostgreSQL password file or set `PGPASSFILE` to a protected file. For scheduled jobs, you can keep using environment variables or a password file provisioned through your secret store.

Check connectivity with `./venv/bin/python scraper.py runs --source demo`. An empty JSON array means the connection and run-history query worked and there are no demo runs yet.

## 3. Verify a database write

Run this against your **test database**. The explicit flag allows the synthetic demo record to be stored.

```sh
./venv/bin/python scraper.py run demo --allow-fixture-write
./venv/bin/python scraper.py run demo --allow-fixture-write
./venv/bin/python scraper.py runs --source demo
```

On a fresh database, the first run reports `inserted: 1`. The second reports `unchanged: 1`. The last command shows recent import attempts. Your other app can read `ingest.places` using the reader role.

## 4. Run a real source

The project comes with live OpenStreetMap sources for 13 destination areas. Run these commands from the project directory:

```sh
./venv/bin/python scraper.py sources
./venv/bin/python scraper.py run osm-kathmandu-valley --dry-run
./venv/bin/python scraper.py run osm-pokhara --dry-run
```

The CLI discovers mapped listings from the configured region on each run. Dry runs need internet access and work without PostgreSQL. Once PostgreSQL is configured and the dry run succeeds, import the source you want:

```sh
./venv/bin/python scraper.py run osm-kathmandu-valley
./venv/bin/python scraper.py runs --source osm-kathmandu-valley
```

Use the source ID listed by `sources` for other regions. Public Overpass is a shared service. Run refreshes infrequently and avoid launching multiple regions in parallel. If a dry run returns a source connection or HTTP error, the service may be busy. Wait before retrying.

Read the [tourist question inventory](TOURISM_COVERAGE.md) for data coverage and gaps. Display **© OpenStreetMap contributors** with a link to the [OSM license page](https://www.openstreetmap.org/copyright) wherever the consuming app uses the data. The data is available under the ODbL. Review its share-alike terms when distributing an adapted database.

For another approved JSON feed or single-page HTML directory with place JSON-LD, adapt the commented templates in [sources.toml](sources.toml). The [demo fixture](fixtures/places.json) shows the JSON input format. Sources requiring pagination or JavaScript rendering need a separate adapter. Schedule successful imports using absolute paths and a job deadline.

## Troubleshooting

| What you see | What to check |
|---|---|
| `install_database_dependencies` | Install `requirements.txt` using `./venv/bin/python -m pip`. |
| `missing_database_configuration` | Set `PGHOST`, `PGDATABASE`, and `PGUSER` in `.env` or in the environment running the CLI. |
| `database_server_has_no_tls` | For loopback only, use `PGSSLMODE=disable`. For remote PostgreSQL, configure TLS on the server. |
| `database_schema_missing` | Have the database administrator apply the migrations from step 2 to the database in `PGDATABASE`. |
| `database_connection_failed` or `operation_failed` | The CLI hides underlying error details. Check that PostgreSQL is running, the migrations ran in the target database, and the connection settings, password file, and remote CA are correct. |
| `unknown_source` | Run `sources` and use the ID listed there. |
| `unexpected_record_count` | Compare the source output with its configured `minimum_rows` and check that it still returns the expected data. |

Run the unit tests with `./venv/bin/python -m unittest discover -s tests -v`.

## Database behavior

`source_id` and `external_id` identify each place. The importer stores the name, category, locality, and public source URL. Successful runs refresh `last_seen_at`. The `updated_at` value changes when the record’s fields change. Records missing from a later batch retain their previous timestamps.

The CLI rejects invalid, duplicate, and unexpectedly small batches. A per-source lock prevents overlapping runs, and completed imports update the dataset and run status in one transaction. Failed imports preserve prior data. A subsequent import marks abandoned runs as interrupted.

Exit codes are 0 for success, 1 for an import or configuration error, 2 for invalid CLI syntax, and 130 for keyboard interruption.
