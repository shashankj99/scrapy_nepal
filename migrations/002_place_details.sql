BEGIN;

ALTER TABLE ingest.places
    ADD COLUMN details jsonb NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN ingest.places.details IS
    'Optional source-reported place metadata. Keys and values vary by source.';

COMMIT;
