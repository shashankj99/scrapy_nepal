"""Extract Schema.org place records from an approved directory's HTML."""

from html.parser import HTMLParser
import json
from urllib.parse import urljoin

from crawler import ImportFailure


class PlaceMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reading = False
        self.blocks = []

    def handle_starttag(self, tag, attrs):
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self.reading = True
            self.blocks.append("")

    def handle_endtag(self, tag):
        if tag == "script":
            self.reading = False

    def handle_data(self, data):
        if self.reading:
            self.blocks[-1] += data


def nodes(document):
    if isinstance(document, list):
        yield from document
    elif isinstance(document, dict):
        graph = document.get("@graph")
        if isinstance(graph, list):
            yield from graph
        else:
            yield document


def extract(body, page, categories):
    parser = PlaceMarkup()
    try:
        parser.feed(body.decode("utf-8"))
        parser.close()
        documents = [json.loads(block) for block in parser.blocks]
    except (ValueError, RecursionError):
        raise ImportFailure("invalid_place_markup") from None
    records = []
    for document in documents:
        for node in nodes(document):
            if not isinstance(node, dict):
                continue
            types = node.get("@type")
            if isinstance(types, str):
                types = [types]
            if not isinstance(types, list):
                continue
            category = next(
                (categories[kind] for kind in types if isinstance(kind, str) and kind in categories),
                None,
            )
            if category is None:
                continue
            url = node.get("url")
            if isinstance(url, str) and url:
                try:
                    url = urljoin(page, url)
                except ValueError:
                    raise ImportFailure("invalid_place_markup") from None
            address = node.get("address")
            records.append({
                "id": url,
                "name": node.get("name"),
                "category": category,
                "locality": address.get("addressLocality") if isinstance(address, dict) else None,
                "source_url": url,
            })
    return records
