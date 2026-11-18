import io
import json
from contextlib import redirect_stderr, redirect_stdout
import unittest
from unittest.mock import patch

import crawler
from place_html import extract
import scraper


class ImportTests(unittest.TestCase):
    def test_demo_dry_run_never_connects(self):
        out = io.StringIO()
        with (
            patch.object(scraper.sys, "argv", ["scraper", "run", "demo", "--dry-run"]),
            patch.object(scraper, "connect") as connect,
            redirect_stdout(out),
        ):
            self.assertEqual(scraper.main(), 0)
        connect.assert_not_called()
        self.assertEqual(json.loads(out.getvalue())["valid"], 1)

    def test_driver_errors_never_print_secrets(self):
        out = io.StringIO()
        with (
            patch.object(scraper.sys, "argv", ["scraper", "runs", "--source", "demo"]),
            patch.object(scraper, "connect", side_effect=RuntimeError("password=secret")),
            redirect_stderr(out),
        ):
            self.assertEqual(scraper.main(), 1)
        self.assertEqual(json.loads(out.getvalue())["error"], "operation_failed")

    def test_duplicate_invalidates_batch(self):
        row = {"id": "1", "name": "Pub", "category": "pub", "locality": "Thamel",
               "source_url": "https://example.com/pub"}
        with self.assertRaisesRegex(crawler.ImportFailure, "invalid_records"):
            scraper.validate_records([row, row], 1, {"example.com"})

    def test_html_extracts_place(self):
        body = b'''<script type="application/ld+json">
          {"@type":"BarOrPub","name":"A pub","url":"/pub",
           "address":{"addressLocality":"Thamel"}}</script>'''
        rows = extract(body, "https://example.com/places", {"BarOrPub": "pub"})
        self.assertEqual(len(scraper.validate_records(rows, 1, {"example.com"})), 1)

    def test_crawler_blocks_private_dns_result(self):
        with patch.object(crawler.socket, "getaddrinfo", return_value=[(
            0, 0, 0, "", ("127.0.0.1", 443)
        )]):
            with self.assertRaisesRegex(crawler.ImportFailure, "nonpublic_destination"):
                crawler.resolve("example.com")

    def test_crawler_checks_redirect_target_before_requesting(self):
        fetcher = crawler.Fetcher({"example.com"})
        with (
            patch.object(fetcher, "check_robots"),
            patch.object(fetcher, "request", return_value=(
                302, "https://other.example/path", b""
            )) as request,
        ):
            with self.assertRaisesRegex(crawler.ImportFailure, "unapproved_host"):
                fetcher.fetch("https://example.com/start")
        self.assertEqual(request.call_count, 1)

    def test_short_import_is_rejected(self):
        with self.assertRaisesRegex(crawler.ImportFailure, "unexpected_record_count"):
            scraper.validate_records([], 1, {"example.com"})
