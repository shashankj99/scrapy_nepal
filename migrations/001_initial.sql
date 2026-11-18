BEGIN;

CREATE SCHEMA ingest;

CREATE TABLE ingest.sources (
    id text PRIMARY KEY,
    reuse text NOT NULL
);

CREATE TABLE ingest.crawl_runs (
    id uuid PRIMARY KEY,
    source_id text NOT NULL REFERENCES ingest.sources(id),
    status text NOT NULL CHECK (status IN ('running', 'succeeded', 'failed')),
    started_at timestamptz NOT NULL DEFAULT now(),
    finished_at timestamptz,
    inserted integer,
    updated integer,
    unchanged integer,
    rejected integer,
    error_code text
);

CREATE INDEX crawl_runs_source_started_idx
    ON ingest.crawl_runs (source_id, started_at DESC);

CREATE TABLE ingest.places (
    source_id text NOT NULL REFERENCES ingest.sources(id),
    external_id text NOT NULL,
    name text NOT NULL,
    category text NOT NULL,
    locality text NOT NULL,
    source_url text NOT NULL,
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (source_id, external_id)
);

COMMIT;
