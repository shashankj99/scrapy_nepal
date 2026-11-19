"""Read named tourism-related OpenStreetMap objects from Overpass."""

import json
import math
from collections.abc import Mapping, Sequence
from typing import cast
from urllib.parse import urlencode

from crawler import ImportFailure

OSM_HOST = "www.openstreetmap.org"
TAGS = {
    "aeroway": "aerodrome",
    "tourism": "hotel|hostel|guest_house|motel|camp_site|alpine_hut|museum|gallery|attraction|viewpoint|zoo|picnic_site|information",
    "historic": "monument|memorial|archaeological_site|castle|ruins",
    "amenity": "restaurant|cafe|fast_food|bar|pub|biergarten|bus_station|taxi|place_of_worship|marketplace",
    "highway": "bus_stop",
    "leisure": "nature_reserve|park",
    "boundary": "national_park|protected_area",
    "natural": "peak|cave_entrance|water",
    "waterway": "waterfall",
    "sport": "free_flying|climbing|canoe",
}


def query_url(endpoint: str, bounds: Sequence[float]) -> str:
    if len(bounds) != 4 or not all(math.isfinite(value) for value in bounds):
        raise ImportFailure("invalid_osm_bounds")
    south, west, north, east = bounds
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise ImportFailure("invalid_osm_bounds")
    box = ",".join(map(str, bounds))
    clauses = "".join(
        f'nwr["{key}"~"^({values})$"]["name"]({box});' for key, values in TAGS.items()
    )
    query = f"[out:json][timeout:18];({clauses});out tags;"
    return f"{endpoint}?{urlencode({'data': query})}"


def extract_osm(body: bytes, locality: str) -> list[dict[str, object]]:
    try:
        payload: object = json.loads(body)
    except (ValueError, RecursionError):
        raise ImportFailure("invalid_osm_response") from None
    if not isinstance(payload, dict):
        raise ImportFailure("invalid_osm_response")
    document = cast(Mapping[object, object], payload)
    elements = document.get("elements")
    if document.get("remark") or not isinstance(elements, list):
        raise ImportFailure("incomplete_osm_response")

    records: list[dict[str, object]] = []
    for element in cast(Sequence[object], elements):
        if not isinstance(element, dict):
            raise ImportFailure("invalid_osm_element")
        entry = cast(Mapping[object, object], element)
        kind, identifier, raw_tags = entry.get("type"), entry.get("id"), entry.get("tags")
        if (
            not isinstance(kind, str) or kind not in {"node", "way", "relation"}
            or not isinstance(identifier, int) or isinstance(identifier, bool) or identifier <= 0
            or not isinstance(raw_tags, dict)
        ):
            raise ImportFailure("invalid_osm_element")
        tags = cast(Mapping[object, object], raw_tags)
        category = next(
            (
                value for key, allowed in TAGS.items()
                if isinstance(value := tags.get(key), str) and value in allowed.split("|")
            ),
            None,
        )
        if category is None:
            raise ImportFailure("unexpected_osm_category")
        name = tags.get("name:en") or tags.get("name")
        records.append({
            "id": f"{kind}/{identifier}",
            "name": name,
            "category": category,
            "locality": locality,
            "source_url": f"https://{OSM_HOST}/{kind}/{identifier}",
        })
    return records
