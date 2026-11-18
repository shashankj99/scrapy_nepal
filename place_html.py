"""Extract Schema.org place records from an approved directory's HTML."""

import json
from collections.abc import Iterator, Mapping, Sequence
from html.parser import HTMLParser
from typing import cast
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
        yield from cast(Sequence[object], document)
    elif isinstance(document, dict):
        graph = cast(Mapping[object, object], document).get("@graph")
        if isinstance(graph, list):
            yield from cast(Sequence[object], graph)
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
            data = cast(Mapping[object, object], node)
            raw_types = data.get("@type")
            if isinstance(raw_types, str):
                types: Sequence[object] = [raw_types]
            elif isinstance(raw_types, list):
                types = cast(Sequence[object], raw_types)
            else:
                continue
            category = next(
                (categories[kind] for kind in types if isinstance(kind, str) and kind in categories),
                None,
            )
            if category is None:
                continue
            url = data.get("url")
            if isinstance(url, str) and url:
                try:
                    url = urljoin(page, url)
                except ValueError:
                    raise ImportFailure("invalid_place_markup") from None
            address = data.get("address")
            locality = (
                cast(Mapping[object, object], address).get("addressLocality")
                if isinstance(address, dict) else None
            )
            records.append({
                "id": url,
                "name": data.get("name"),
                "category": category,
                "locality": locality,
                "source_url": url,
            })
    return records
