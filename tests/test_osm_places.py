import unittest
from typing import cast
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from crawler import ImportFailure
from osm_places import extract_osm, query_url
from scraper import SourceConfig, collect

SOURCE: SourceConfig = {
    "format": "osm-overpass",
    "url": "https://overpass.private.coffee/api/interpreter",
    "hosts": ["overpass.private.coffee"],
    "bounds": [28.13, 83.88, 28.30, 84.05],
    "locality": "Pokhara",
}


class OsmTests(unittest.TestCase):
    def test_configured_source_normalizes_map_listings(self) -> None:
        body = b'''{"elements":[
            {"type":"node","id":21,"tags":{"name":"Example Cafe","amenity":"cafe"}},
            {"type":"way","id":21,"tags":{"name":"Local name","name:en":"Example Museum","tourism":"museum"}}
        ]}'''
        with patch("scraper.Fetcher.fetch", return_value=(body, "https://overpass.private.coffee/")) as fetch:
            rows = collect(SOURCE)
        self.assertEqual(rows["node/21"], (
            "Example Cafe", "cafe", "Pokhara", "https://www.openstreetmap.org/node/21"
        ))
        self.assertEqual(rows["way/21"][0], "Example Museum")
        endpoint = urlsplit(cast(str, fetch.call_args.args[0]))
        self.assertEqual(endpoint.hostname, "overpass.private.coffee")
        self.assertIn('["highway"~"^(bus_stop)$"]', parse_qs(endpoint.query)["data"][0])

    def test_rejects_partial_overpass_result(self) -> None:
        with self.assertRaisesRegex(ImportFailure, "incomplete_osm_response"):
            extract_osm(b'{"remark":"timeout","elements":[]}', "Pokhara")

    def test_rejects_reversed_bounds(self) -> None:
        with self.assertRaisesRegex(ImportFailure, "invalid_osm_bounds"):
            query_url("https://example.com", [28, 84, 27, 85])
