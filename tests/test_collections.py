"""Test /collections endpoints."""


def test_collections(app):
    """Test /collections endpoint."""
    response = app.get("/collections")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert [
        "links",
        "numberMatched",
        "numberReturned",
        "collections",
    ] == list(body)
    assert body["numberMatched"] == 2
    assert body["numberReturned"] == 2

    ids = [x["id"] for x in body["collections"]]
    assert "noaa-emergency-response-copy" in ids
    assert "noaa-emergency-response" in ids

    response = app.get("/?f=html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Collections" in response.text


def test_collections_limit_offset(app):
    """Test /collections endpoint."""
    response = app.get("/collections", params={"limit": 1})
    body = response.json()
    assert body["numberMatched"] == 2
    assert body["numberReturned"] == 1
    rels = [x["rel"] for x in body["links"]]
    assert "next" in rels
    assert "prev" not in rels

    ncol = body["numberMatched"]

    response = app.get("/collections", params={"limit": 1, "offset": 1})
    body = response.json()
    assert body["numberMatched"] == ncol
    assert body["numberReturned"] == 1
    rels = [x["rel"] for x in body["links"]]
    assert "next" not in rels
    assert "prev" in rels


def test_collections_bbox(app):
    """Test /collections endpoint."""
    response = app.get("/collections", params={"bbox": "-180,-90,0,0"})
    body = response.json()
    assert body["numberMatched"] == 2

    response = app.get("/collections", params={"bbox": "1,1,180,90"})
    body = response.json()
    assert body["numberMatched"] == 1


def test_collections_datetime(app):
    """Test /collections endpoint."""
    response = app.get("/collections", params={"datetime": "../2005-02-01T00:00:00Z"})
    body = response.json()
    assert body["numberMatched"] == 2

    # one collection 2010
    response = app.get("/collections", params={"datetime": "2010-01-01T00:00:00Z/.."})
    body = response.json()
    print(body)
    assert body["numberMatched"] == 1

    # only one collection before 2004-05
    response = app.get("/collections", params={"datetime": "../2004-05-01T00:00:00Z"})
    body = response.json()
    assert body["numberMatched"] == 1

    # only one collection after 2004/05
    response = app.get("/collections", params={"datetime": "2004-05-01T00:00:00Z/.."})
    body = response.json()
    assert body["numberMatched"] == 1

    # only one collection between 2003 and 2004
    response = app.get(
        "/collections", params={"datetime": "2003-01-01T00:00:00Z/2004-01-01T00:00:00Z"}
    )
    body = response.json()
    assert body["numberMatched"] == 1


def test_collection(app):
    """Test /collections/{collectionId} endpoint."""
    response = app.get("/collections/noaa-emergency-response")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert body["id"] == "noaa-emergency-response"
    assert ["id", "title", "description", "links", "extent", "itemType", "crs"] == list(
        body
    )
    assert body["crs"] == ["http://www.opengis.net/def/crs/OGC/1.3/CRS84"]
    assert ["bbox", "crs"] == list(body["extent"]["spatial"])
    assert (
        body["extent"]["spatial"]["crs"]
        == "http://www.opengis.net/def/crs/OGC/1.3/CRS84"
    )
    assert body["extent"].get("temporal")

    response = app.get("/collections/noaa-emergency-response?f=html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Collection: noaa-emergency-response" in response.text

    # bad collection name
    response = app.get("/collections/noaa-emergency")
    assert response.status_code == 404
    assert response.headers["content-type"] == "application/json"
    body = response.json()
    assert body["detail"] == "Collection 'noaa-emergency' not found."


def test_collection_queryables(app):
    """Test /collections/{collectionId}/queryables endpoint."""
    response = app.get("/collections/noaa-emergency-response/queryables")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/schema+json"
    body = response.json()
    assert body["title"] == "noaa-emergency-response"
    assert body["type"] == "object"
    assert ["title", "properties", "type", "$schema", "$id"] == list(body)
    assert "id" in body["properties"]
    assert "datetime" in body["properties"]
    assert "geometry" in body["properties"]

    response = app.get(
        "/collections/noaa-emergency-response/queryables", params={"f": "schemajson"}
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/schema+json"

    response = app.get("/collections/noaa-emergency-response/queryables?f=html")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Queryables" in response.text
