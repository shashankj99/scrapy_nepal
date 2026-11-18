"""Extract Schema.org place records from an approved directory's HTML."""

import json
from collections.abc import Iterator, Mapping
from html.parser import HTMLParser
from urllib.parse import urljoin

from crawler import ImportFailure


class PlaceMarkup(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.reading = False
        self.blocks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self.reading = True
            self.blocks.append("")

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.reading = False

    def handle_data(self, data: str) -> None:
        if self.reading:
            self.blocks[-1] += data


def nodes(document: object) -> Iterator[object]:
    if isinstance(document, list):
        yield from document
    elif isinstance(document, dict):
        graph = document.get("@graph")
        if isinstance(graph, list):
            yield from graph
        else:
            yield document


def extract(body: bytes, page: str, categories: Mapping[str, str]) -> list[dict[str, object]]:
    parser = PlaceMarkup()
    try:
        parser.feed(body.decode("utf-8"))
        parser.close()
        documents = [json.loads(block) for block in parser.blocks]
    except (ValueError, RecursionError):
        raise ImportFailure("invalid_place_markup") from None
    records: list[dict[str, object]] = []
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
