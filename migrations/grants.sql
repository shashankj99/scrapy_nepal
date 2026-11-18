-- Create scraper_writer and scraper_reader separately as LOGIN roles using
-- your database administrator's credential provisioning workflow.
BEGIN;
REVOKE ALL ON SCHEMA ingest FROM PUBLIC;
GRANT USAGE ON SCHEMA ingest TO scraper_writer, scraper_reader;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA ingest TO scraper_writer;
GRANT SELECT ON ingest.places TO scraper_reader;
COMMIT;
