"""Test /items and /item endpoints."""

import json
from urllib.parse import quote_plus


def test_items(app):
    """Test /items endpoint."""
    response = app.get("/collections/noaa-emergency-response/items")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["id"] == "noaa-emergency-response"
    assert body["title"] == "noaa-emergency-response"
    assert body["links"]
    assert body["numberMatched"] == 20
    assert body["numberReturned"] == 10
    assert ["collection", "self", "next"] == [link["rel"] for link in body["links"]]

    response = app.get("/collections/noaa-emergency-response/items?f=html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Collection Items: noaa-emergency-response" in response.text


def test_items_limit_and_offset(app):
    """Test /items endpoint with limit and offset options."""
    response = app.get("/collections/noaa-emergency-response/items?limit=1")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 1
    assert body["numberMatched"] == 20
    assert body["numberReturned"] == 1

    response = app.get(
        "/collections/noaa-emergency-response/items",
        params={
            "limit": 1,
            "offset": "noaa-emergency-response:20200307aC0853600w361200",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 1
    assert body["numberMatched"] == 20
    assert body["numberReturned"] == 1
    assert ["collection", "self", "next", "prev"] == [
        link["rel"] for link in body["links"]
    ]

    # bad token
    response = app.get("/collections/noaa-emergency-response/items?offset=-1")
    assert response.status_code == 404

    # bad token
    response = app.get(
        "/collections/noaa-emergency-response/items?offset=somethingwhichisnotatoken"
    )
    assert response.status_code == 404


def test_items_bbox(app):
    """Test /items endpoint with bbox options."""
    response = app.get(
        "/collections/noaa-emergency-response/items?bbox=-85.63646803008008,36.03577147693936,-85.33716039442996,36.268784367466466"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 10
    assert body["numberMatched"] == 20
    assert body["numberReturned"] == 10

    response = app.get(
        "/collections/noaa-emergency-response/items?bbox=-200,34.488448,-85.429688,41.112469"
    )
    assert response.status_code == 422

    response = app.get(
        "/collections/noaa-emergency-response/items?bbox=-94.702148,91,-85.429688,41.112469"
    )
    assert response.status_code == 422

    response = app.get(
        "/collections/noaa-emergency-response/items?bbox=-200,34.488448,0,-85.429688,41.112469,0"
    )
    assert response.status_code == 422

    response = app.get(
        "/collections/noaa-emergency-response/items?bbox=-94.702148,91,0,-85.429688,41.112469,0"
    )
    assert response.status_code == 422

    # more than 6 coordinates
    response = app.get("/collections/noaa-emergency-response/items?bbox=0,1,2,3,4,5,6")
    assert response.status_code == 422


def test_items_ids(app):
    """Test /items endpoint with ids options."""
    response = app.get(
        "/collections/noaa-emergency-response/items?ids=20200307aC0853600w361200"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 1
    assert body["numberMatched"] == 1
    assert body["numberReturned"] == 1
    assert body["features"][0]["id"] == "20200307aC0853600w361200"

    response = app.get(
        "/collections/noaa-emergency-response/items?ids=20200307aC0853600w361200,20200307aC0853430w361030"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 2
    assert body["numberMatched"] == 2
    assert body["numberReturned"] == 2
    assert body["features"][0]["id"] == "20200307aC0853600w361200"
    assert body["features"][1]["id"] == "20200307aC0853430w361030"


def test_items_filter_cql_properties(app):
    """Test /items endpoint with cql filter options."""
    filter_query = {
        "op": "=",
        "args": [{"property": "name"}, "20200307aC0853130w360900"],
    }
    response = app.get(
        f"/collections/noaa-emergency-response/items?filter-lang=cql2-json&filter={json.dumps(filter_query)}"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 1
    assert body["numberMatched"] == 1
    assert body["numberReturned"] == 1
    assert body["features"][0]["properties"]["name"] == "20200307aC0853130w360900"

    response = app.get(
        "/collections/noaa-emergency-response/items?filter-lang=cql2-text&filter=name='20200307aC0852830w361200'"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert len(body["features"]) == 1
    assert body["numberMatched"] == 1
    assert body["numberReturned"] == 1
    assert body["features"][0]["id"] == "20200307aC0852830w361200"
    assert body["features"][0]["properties"]["name"] == "20200307aC0852830w361200"


# The properties= options isn't working with PgSTAC
# def test_items_properties(app):
#     """Test /items endpoint with properties options."""
#     # NOTE: This should work!!! maybe a pgstac bug
#     # response = app.get("/collections/noaa-emergency-response/items?properties=name")
#     # assert response.status_code == 200
#     # assert response.headers["content-type"] == "application/geo+json"
#     # body = response.json()
#     # assert ["name"] == list(body["features"][0]["properties"])

#     # no properties
#     # response = app.get("/collections/noaa-emergency-response/items?properties=")
#     # assert response.status_code == 200
#     # assert response.headers["content-type"] == "application/geo+json"
#     # body = response.json()
#     # # NOTE: in tipg we return `properties={}`
#     # assert not list(body["features"][0]["properties"])


def test_items_datetime(app):
    """Test /items endpoint datetime."""
    response = app.get(
        "/collections/noaa-emergency-response/items?datetime=2020-03-07T00:00:00Z"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["id"] == "noaa-emergency-response"
    assert body["links"]
    assert body["numberMatched"] == 10
    assert body["numberReturned"] == 10

    # no items for 2004-10-10T10:23:54
    response = app.get(
        "/collections/noaa-emergency-response/items?datetime=2020-03-08T00:00:00Z"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["numberMatched"] == 0
    assert body["numberReturned"] == 0

    # Closed Interval
    response = app.get(
        "/collections/noaa-emergency-response/items?datetime=2020-03-07T00:00:00Z/2020-03-08T00:00:00Z"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["numberMatched"] == 10
    assert body["numberReturned"] == 10

    # Open end-Interval (2004-10-20T10:23:54Z or later)
    response = app.get(
        "/collections/noaa-emergency-response/items?datetime=2020-03-07T00:00:00Z/.."
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["numberMatched"] == 10
    assert body["numberReturned"] == 10

    response = app.get(
        "/collections/noaa-emergency-response/items?datetime=2020-03-07T00:00:00Z/"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["numberMatched"] == 10
    assert body["numberReturned"] == 10

    # Open start-Interval (2020-03-06T00:00:00Z or earlier)
    response = app.get(
        "/collections/noaa-emergency-response/items?datetime=../2020-03-06T00:00:00Z"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["numberMatched"] == 10
    assert body["numberReturned"] == 10

    response = app.get(
        "/collections/noaa-emergency-response/items?datetime=/2020-03-06T00:00:00Z"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["numberMatched"] == 10
    assert body["numberReturned"] == 10

    # bad interval (no valid datetime)
    response = app.get("/collections/noaa-emergency-response/items?datetime=../..")
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/json"

    # bad interval (d1 < d2)
    response = app.get(
        "/collections/noaa-emergency-response/items?datetime=2004-10-21T10:23:54Z/2004-10-20T10:23:54Z"
    )
    assert response.status_code == 422
    assert response.headers["content-type"] == "application/json"


def test_items_query(app):
    """Test /items endpoint query."""
    response = app.get(
        "/collections/noaa-emergency-response/items",
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
    assert body["id"] == "noaa-emergency-response"
    assert body["links"]
    assert body["numberMatched"] == 1
    assert body["numberReturned"] == 1

    response = app.get(
        "/collections/noaa-emergency-response/items",
        params={
            "query": quote_plus(json.dumps({"event": {"eq": "Nashville Tornado"}}))
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "FeatureCollection"
    assert body["id"] == "noaa-emergency-response"
    assert body["links"]
    assert body["numberMatched"] == 20
    assert body["numberReturned"] == 10


def test_output_response_type(app):
    """Make sure /items returns wanted output response type."""
    # CSV output
    response = app.get("/collections/noaa-emergency-response/items?f=csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    body = response.text.splitlines()
    assert len(body) == 11
    assert set(body[0].split(",")) == set(
        "event,datetime,collectionId,name,geometry,itemId".split(",")
    )

    # we only accept csv
    response = app.get(
        "/collections/noaa-emergency-response/items", headers={"accept": "text/csv"}
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

    # we accept csv or json (CSV should be returned)
    response = app.get(
        "/collections/noaa-emergency-response/items",
        headers={"accept": "text/csv;q=1.0, application/json;q=0.4"},
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]

    # the first preference is geo+json
    response = app.get(
        "/collections/noaa-emergency-response/items",
        headers={"accept": "application/geo+json, text/csv;q=0.1"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"

    # geojsonseq output
    response = app.get("/collections/noaa-emergency-response/items?f=geojsonseq")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json-seq"
    body = response.text.splitlines()
    assert len(body) == 10
    assert json.loads(body[0])["type"] == "Feature"

    response = app.get(
        "/collections/noaa-emergency-response/items",
        headers={"accept": "application/geo+json-seq"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json-seq"
    body = response.text.splitlines()
    assert len(body) == 10
    assert json.loads(body[0])["type"] == "Feature"

    # json output
    response = app.get("/collections/noaa-emergency-response/items?f=json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert len(body) == 10
    feat = body[0]
    assert {"datetime", "geometry", "collectionId", "itemId", "event", "name"} == set(
        feat.keys()
    )

    response = app.get(
        "/collections/noaa-emergency-response/items",
        headers={"accept": "application/json"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert len(body) == 10

    # ndjson output
    response = app.get("/collections/noaa-emergency-response/items?f=ndjson")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/ndjson"
    body = response.text.splitlines()
    assert len(body) == 10
    feat = json.loads(body[0])
    assert {"name", "event", "datetime", "itemId", "collectionId", "geometry"} == set(
        feat.keys()
    )

    response = app.get(
        "/collections/noaa-emergency-response/items",
        headers={"accept": "application/ndjson"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/ndjson"
    body = response.text.splitlines()
    assert len(body) == 10


def test_items_sortby(app):
    """Test /items endpoint with sortby options."""
    response = app.get(
        "/collections/noaa-emergency-response/items?limit=1&sortby=datetime"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["features"][0]["properties"]["datetime"] == "2020-03-06T00:00:00Z"
    assert body["numberMatched"] == 20

    response = app.get(
        "/collections/noaa-emergency-response/items?limit=1&sortby=+datetime"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["features"][0]["properties"]["datetime"] == "2020-03-06T00:00:00Z"
    assert body["numberMatched"] == 20

    response = app.get(
        "/collections/noaa-emergency-response/items?limit=1&sortby=-datetime"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["features"][0]["properties"]["datetime"] == "2020-03-07T00:00:00Z"
    assert body["numberMatched"] == 20

    response = app.get(
        "/collections/noaa-emergency-response/items?limit=1&sortby=datetime,event"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["features"][0]["properties"]["datetime"] == "2020-03-06T00:00:00Z"

    # Invalid column name
    response = app.get(
        "/collections/noaa-emergency-response/items?limit=1&sortby=something"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["numberMatched"] == 20


def test_item(app):
    """Test /items/{item id} endpoint."""
    response = app.get(
        "/collections/noaa-emergency-response/items/20200307aC0853130w360900"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/geo+json"
    body = response.json()
    assert body["type"] == "Feature"
    assert body["id"] == "20200307aC0853130w360900"
    assert body["links"]

    response = app.get(
        "/collections/noaa-emergency-response/items/20200307aC0853130w360900?f=html"
    )
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Collection Item: 20200307aC0853130w360900" in response.text

    # json output
    response = app.get(
        "/collections/noaa-emergency-response/items/20200307aC0853130w360900?f=json"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    # not found
    response = app.get("/collections/noaa-emergency-response/items/yoooooooooo")
    assert response.status_code == 404
