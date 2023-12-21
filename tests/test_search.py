"""Test /search endpoints."""

import json
from urllib.parse import quote_plus


def test_search(app):
    """Test /search endpoint."""
    response = app.get("/search")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["description"] == "{}"
    assert body["links"]
    assert body["numberMatched"] == 40
    assert body["numberReturned"] == 10
    assert ["self", "next"] == [link["rel"] for link in body["links"]]

    response = app.post("/search")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["description"] == "{}"
    assert body["links"]
    assert body["numberMatched"] == 40
    assert body["numberReturned"] == 10
    assert ["self", "next"] == [link["rel"] for link in body["links"]]

    response = app.get("/search?f=html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    response = app.get("/search", params={"limit": 1})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["numberMatched"] == 40
    assert body["numberReturned"] == 1

    response = app.post("/search", json={"limit": 1})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["numberMatched"] == 40
    assert body["numberReturned"] == 1

    response = app.get("/search", params={"collections": "noaa-emergency-response"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["description"] == '{"collections": "noaa-emergency-response"}'
    assert body["links"]
    assert body["numberMatched"] == 20
    assert body["numberReturned"] == 10

    response = app.post("/search", json={"collections": ["noaa-emergency-response"]})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["description"] == '{"collections":["noaa-emergency-response"]}'
    assert body["links"]
    assert body["numberMatched"] == 20
    assert body["numberReturned"] == 10

    response = app.get(
        "/search",
        params={"collections": "noaa-emergency-response,noaa-emergency-response-copy"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert (
        body["description"]
        == '{"collections": "noaa-emergency-response,noaa-emergency-response-copy"}'
    )
    assert body["links"]
    assert body["numberMatched"] == 40
    assert body["numberReturned"] == 10

    response = app.post(
        "/search",
        json={
            "collections": ["noaa-emergency-response", "noaa-emergency-response-copy"]
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert (
        body["description"]
        == '{"collections":["noaa-emergency-response","noaa-emergency-response-copy"]}'
    )
    assert body["links"]
    assert body["numberMatched"] == 40
    assert body["numberReturned"] == 10

    response = app.get("/search", params={"collections": "something"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["description"] == '{"collections": "something"}'
    assert body["links"]
    assert body["numberMatched"] == 0
    assert body["numberReturned"] == 0

    response = app.post("/search", json={"collections": ["something"]})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["description"] == '{"collections":["something"]}'
    assert body["links"]
    assert body["numberMatched"] == 0
    assert body["numberReturned"] == 0

    # response = app.get("/search", params={"collections": "noaa-emergency-response", "token": "noaa-emergency-response:20200307aC0853130w360900"})
    # assert response.status_code == 200
    # assert response.headers["content-type"] == "application/geo+json"
    # body = response.json()
    # assert body["type"] == "FeatureCollection"
    # assert body["description"] == '{"collections": "noaa-emergency-response", "token": "noaa-emergency-response:20200307aC0853130w360900"}'
    # assert body["links"]
    # assert body["numberMatched"] == 20
    # assert body["numberReturned"] == 10
    # assert ["self", "next", "prev"] == [link["rel"] for link in body["links"]]
    # assert body["features"][0]["id"] == "20200307aC0853600w361200"
    # assert body["features"][0]["collection"] == "noaa-emergency-response"

    response = app.get(
        "/search",
        params={
            "bbox": "-85.63646803008008,36.03577147693936,-85.33716039442996,36.268784367466466"
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 10
    assert body["numberMatched"] == 40
    assert body["numberReturned"] == 10

    response = app.post(
        "/search",
        json={
            "bbox": [
                -85.63646803008008,
                36.03577147693936,
                -85.33716039442996,
                36.268784367466466,
            ]
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 10
    assert body["numberMatched"] == 40
    assert body["numberReturned"] == 10

    response = app.get(
        "/search",
        params={"ids": "20200307aC0853600w361200,20200307aC0853430w361200"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 2
    assert body["numberMatched"] == 2
    assert body["numberReturned"] == 2

    response = app.post(
        "/search",
        json={"ids": ["20200307aC0853600w361200", "20200307aC0853430w361200"]},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 2
    assert body["numberMatched"] == 2
    assert body["numberReturned"] == 2

    response = app.get(
        "/search",
        params={"datetime": "2020-03-07T00:00:00Z"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 10
    assert body["numberMatched"] == 10
    assert body["numberReturned"] == 10

    response = app.post(
        "/search",
        json={"datetime": "2020-03-07T00:00:00Z"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 10
    assert body["numberMatched"] == 10
    assert body["numberReturned"] == 10

    response = app.get("/search", params={"datetime": "2020-03-07T12:00:00Z/.."})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 10
    assert body["numberMatched"] == 20
    assert body["numberReturned"] == 10
    assert body["features"][0]["collection"] == "noaa-emergency-response-copy"

    response = app.post("/search", json={"datetime": "2020-03-07T12:00:00Z/.."})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 10
    assert body["numberMatched"] == 20
    assert body["numberReturned"] == 10
    assert body["features"][0]["collection"] == "noaa-emergency-response-copy"

    response = app.get(
        "/search",
        params={"datetime": "../2020-03-06T12:00:00Z"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 10
    assert body["numberMatched"] == 10
    assert body["numberReturned"] == 10
    assert body["features"][0]["collection"] == "noaa-emergency-response"

    response = app.post(
        "/search",
        json={"datetime": "../2020-03-06T12:00:00Z"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 10
    assert body["numberMatched"] == 10
    assert body["numberReturned"] == 10
    assert body["features"][0]["collection"] == "noaa-emergency-response"


def test_search_properties(app):
    """Test /search endpoint with properties options."""
    response = app.get("/search", params={"properties": "properties.name"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert ["name"] == list(body["features"][0]["properties"])

    response = app.post("/search", json={"fields": {"include": ["properties.name"]}})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert ["name"] == list(body["features"][0]["properties"])

    # no properties
    response = app.get("/search?properties=")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    # NOTE: in tipg we return `properties={}`
    assert "properties" not in body["features"][0]

    response = app.post("/search", json={"fields": {"exclude": ["properties.name"]}})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert "name" not in body["features"][0]["properties"]


def test_search_filter_cql_properties(app):
    """Test /items endpoint with cql filter options."""
    filter_query = {
        "op": "=",
        "args": [{"property": "name"}, "20200307aC0853130w360900"],
    }
    response = app.get(
        f"/search?filter-lang=cql2-json&filter={json.dumps(filter_query)}"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 2
    assert body["numberMatched"] == 2
    assert body["numberReturned"] == 2
    assert body["features"][0]["collection"] == "noaa-emergency-response-copy"
    assert body["features"][0]["properties"]["name"] == "20200307aC0853130w360900"
    assert body["features"][1]["collection"] == "noaa-emergency-response"
    assert body["features"][1]["properties"]["name"] == "20200307aC0853130w360900"

    filter_query = {
        "op": "=",
        "args": [{"property": "name"}, "20200307aC0853130w360900"],
    }
    response = app.post(
        "/search", json={"filter-lang": "cql2-json", "filter": filter_query}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 2
    assert body["numberMatched"] == 2
    assert body["numberReturned"] == 2
    assert body["features"][0]["collection"] == "noaa-emergency-response-copy"
    assert body["features"][0]["properties"]["name"] == "20200307aC0853130w360900"
    assert body["features"][1]["collection"] == "noaa-emergency-response"
    assert body["features"][1]["properties"]["name"] == "20200307aC0853130w360900"

    response = app.get(
        "/search?filter-lang=cql2-text&filter=name='20200307aC0853130w360900'"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 2
    assert body["numberMatched"] == 2
    assert body["numberReturned"] == 2
    assert body["features"][0]["collection"] == "noaa-emergency-response-copy"
    assert body["features"][0]["properties"]["name"] == "20200307aC0853130w360900"
    assert body["features"][1]["collection"] == "noaa-emergency-response"
    assert body["features"][1]["properties"]["name"] == "20200307aC0853130w360900"


def test_search_sortby(app):
    """Test /search endpoint with sortby options."""
    response = app.get("/search", params={"limit": 1, "sortby": "datetime"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["features"][0]["properties"]["datetime"] == "2020-03-06T00:00:00Z"
    assert body["numberMatched"] == 40

    response = app.post(
        "/search",
        json={"limit": 1, "sortby": {"field": "datetime", "direction": "asc"}},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["features"][0]["properties"]["datetime"] == "2020-03-06T00:00:00Z"
    assert body["numberMatched"] == 40

    response = app.get("/search", params={"limit": 1, "sortby": "+datetime"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["features"][0]["properties"]["datetime"] == "2020-03-06T00:00:00Z"
    assert body["numberMatched"] == 40

    response = app.get("/search", params={"limit": 1, "sortby": "-datetime"})
    assert response.status_code == 200
    body = response.json()
    assert body["features"][0]["properties"]["datetime"] == "2020-03-08T00:00:00Z"
    assert body["numberMatched"] == 40

    response = app.post(
        "/search",
        json={"limit": 1, "sortby": {"field": "datetime", "direction": "desc"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["features"][0]["properties"]["datetime"] == "2020-03-08T00:00:00Z"
    assert body["numberMatched"] == 40

    response = app.get("/search", params={"limit": 1, "sortby": "datetime,event"})
    assert response.status_code == 200
    body = response.json()
    assert body["features"][0]["properties"]["datetime"] == "2020-03-06T00:00:00Z"

    response = app.post(
        "/search",
        json={
            "limit": 1,
            "sortby": [
                {"field": "datetime", "direction": "asc"},
                {"field": "event", "direction": "asc"},
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["features"][0]["properties"]["datetime"] == "2020-03-06T00:00:00Z"

    # Invalid column name
    response = app.get("/search", params={"limit": 1, "sortby": "something"})
    assert response.status_code == 200
    body = response.json()
    assert body["numberMatched"] == 40

    response = app.post(
        "/search",
        json={"limit": 1, "sortby": {"field": "something", "direction": "asc"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["numberMatched"] == 40


def test_search_query(app):
    """Test /search endpoint query."""
    response = app.get(
        "/search",
        params={
            "query": quote_plus(
                json.dumps({"name": {"eq": "20200307aC0852830w361200"}})
            )
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["links"]
    assert body["numberMatched"] == 2
    assert body["numberReturned"] == 2

    response = app.post(
        "/search",
        json={"query": {"name": {"eq": "20200307aC0852830w361200"}}},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["links"]
    assert body["numberMatched"] == 2
    assert body["numberReturned"] == 2

    response = app.get(
        "/search",
        params={
            "query": quote_plus(json.dumps({"event": {"eq": "Nashville Tornado"}}))
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["links"]
    assert body["numberMatched"] == 40
    assert body["numberReturned"] == 10

    response = app.post(
        "/search",
        json={"query": {"event": {"eq": "Nashville Tornado"}}},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["links"]
    assert body["numberMatched"] == 40
    assert body["numberReturned"] == 10
