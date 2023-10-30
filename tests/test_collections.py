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

    # response = app.get("/collections", params={"bbox": "-180,81,180,87"})
    # body = response.json()
    # assert body["numberMatched"] < ncol  # some collections are not within the bbox
    # ids = [x["id"] for x in body["collections"]]
    # assert "public.nongeo_data" not in ids
    # assert "public.canada" not in ids

    # response = app.get("/collections", params={"datetime": "../2022-12-31T23:59:59Z"})
    # body = response.json()
    # assert body["numberMatched"] == 4
    # ids = [x["id"] for x in body["collections"]]
    # assert sorted(
    #     [
    #         "public.my_data",
    #         "public.my_data_alt",
    #         "public.my_data_geo",
    #         "public.nongeo_data",
    #     ]
    # ) == sorted(ids)

    # response = app.get("/collections", params={"datetime": "2022-12-31T23:59:59Z/.."})
    # body = response.json()
    # assert body["numberMatched"] == 0

    # response = app.get("/collections", params={"datetime": "2003-12-31T23:59:59Z/.."})
    # body = response.json()
    # assert body["numberMatched"] == 4
    # ids = [x["id"] for x in body["collections"]]
    # assert sorted(
    #     [
    #         "public.my_data",
    #         "public.my_data_alt",
    #         "public.my_data_geo",
    #         "public.nongeo_data",
    #     ]
    # ) == sorted(ids)

    # response = app.get("/collections", params={"datetime": "2004-12-31T23:59:59Z/.."})
    # body = response.json()
    # assert body["numberMatched"] == 3
    # ids = [x["id"] for x in body["collections"]]
    # assert sorted(
    #     ["public.my_data", "public.my_data_alt", "public.my_data_geo"]
    # ) == sorted(ids)

    # response = app.get(
    #     "/collections", params={"datetime": "2004-01-01T00:00:00Z/2004-12-31T23:59:59Z"}
    # )
    # body = response.json()
    # assert body["numberMatched"] == 1
    # ids = [x["id"] for x in body["collections"]]
    # assert ["public.nongeo_data"] == ids


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
