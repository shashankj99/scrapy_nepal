# Scraper CLI

A scheduled or manually run importer that updates a places dataset in PostgreSQL. It supports an approved HTTPS JSON feed and an HTML directory exposing Schema.org place data in JSON-LD. The bundled demo uses a synthetic record. Configure and validate a real source before scheduling imports.

## Run locally

Use Python 3.11 or later. From this directory, activate your virtual environment and run:

```sh
python -m pip install -r requirements.txt
python scraper.py sources
python scraper.py run demo --dry-run
python -m unittest discover -s tests -v
```

Source listing and dry runs work with the Python standard library. Psycopg is required for database commands. Dry-run output reports counts without echoing source content.

## Configure PostgreSQL

1. Provision a dedicated database and two login roles named `scraper_writer` and `scraper_reader` using your database administrator's credential workflow. Use a separate schema owner or migration role to apply `migrations/001_initial.sql`, then `migrations/grants.sql`. The grants cover the tables in this migration.
2. Configure `PGHOST`, `PGDATABASE`, `PGUSER`, and optionally `PGPORT`. For remote PostgreSQL, set `PGSSLROOTCERT` to the CA certificate trusted for the database. Remote connections verify the server hostname and certificate.
3. Use a PostgreSQL password file with permissions `0600`. If it is outside libpq's default location, set `PGPASSFILE` to its path. For scheduled runs, have the deployment secret store mount or provision the file. Give the consuming app its own reader credentials.
4. To test using a disposable database, run `python scraper.py run demo --allow-fixture-write` twice, then run `python scraper.py runs --source demo`. Expect one insert on the first run and one unchanged record on the second.

Keep credentials out of command arguments, source TOML, CI output, and version control. Use a restricted host and network for the scraper, especially when it can also reach a private database. The `ingest.places` table is the read contract for the other app.

## Configure a live source

Add an entry to [sources.toml](sources.toml) with its URL, approved hosts, minimum expected row count, and an access and reuse reference. For JSON, the remote document must be an array in the fixture's format. For HTML, use `format = "place-jsonld"` and map Schema.org types to your dataset's categories. The built-in HTML extractor reads one directory page with object, array, or top-level `@graph` JSON-LD. HTML without that markup needs a source-specific parser.

Choose a stable ID and a credible minimum row count after inspecting the source. The live fetcher uses HTTPS, checks crawler rules, throttles requests, and revalidates redirect destinations. It connects to the approved public address returned by DNS and verifies TLS against the source hostname. If a source needs pagination or a JavaScript renderer, add and verify that source adapter before enabling writes.

Run `python scraper.py run <source> --dry-run` first. For repeated imports, schedule `python scraper.py run <source>` with cron or an equivalent runner. Set a job-level deadline and capture its exit status. Cron should use absolute paths to the project and interpreter.

## Database fields and import behavior

| Field | Meaning |
|---|---|
| `source_id` and `external_id` | Together identify a record from a particular source. HTML extraction uses the canonical entry URL as its ID. |
| `name`, `category`, `locality` | Required text fields. The locality is the source's place or neighborhood label. |
| `source_url` | Public HTTPS reference on an approved host. Query strings are rejected for stored URLs. |
| `last_seen_at` | When the record was last included in a successful import. |
| `updated_at` | When the importer first stored the record or changed its fields. |

The importer rejects invalid, duplicate, or unexpectedly small batches. It writes valid rows and the successful run status in one transaction. A per-source advisory lock prevents overlapping writes. Prior data remains readable after failure. Missing rows retain their last-seen timestamp so the consuming app can decide when they become stale. A process that exits unexpectedly leaves a running entry, which the next import marks as interrupted.

Exit codes are 0 for success, 1 for an import or configuration error, 2 for invalid CLI syntax, and 130 for keyboard interruption.
