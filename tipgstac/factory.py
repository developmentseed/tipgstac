"""Custom Factory.

PgSTAC uses `token: str` instead of `offset: int` which means we have to overwrite the /items endpoint.
"""

import json
import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional
from urllib.parse import unquote_plus

from ciso8601 import parse_rfc3339
from fastapi import Body, Depends, Path, Query
from fastapi.responses import ORJSONResponse
from geojson_pydantic.geometries import parse_geometry_obj
from pygeofilter.ast import AstType
from pygeofilter.backends.cql2_json import to_cql2
from starlette.datastructures import QueryParams
from starlette.requests import Request
from starlette.responses import StreamingResponse
from typing_extensions import Annotated

from tipg import factory, model
from tipg.dependencies import (
    ItemsOutputType,
    bbox_query,
    datetime_query,
    filter_query,
    ids_query,
    properties_query,
    sortby_query,
)
from tipg.errors import InvalidDatetime, NotFound
from tipg.resources.enums import MediaType
from tipg.resources.response import GeoJSONResponse, orjsonDumps
from tipg.settings import FeaturesSettings
from tipgstac.collections import CollectionList, PgSTACCollection, pgstac_search
from tipgstac.dependencies import (
    CollectionParams,
    CollectionsParams,
    PostSearchOutputType,
    collections_query,
)
from tipgstac.model import PgSTACSearch, PostItems

features_settings = FeaturesSettings()


@dataclass
class OGCFeaturesFactory(factory.OGCFeaturesFactory):
    """Override /items and /item endpoints."""

    collection_dependency: Callable[..., PgSTACCollection] = CollectionParams
    collections_dependency: Callable[..., CollectionList] = CollectionsParams

    def register_routes(self):
        """Register endpoints."""
        super().register_routes()
        self._searches_routes()

    def links(self, request: Request) -> List[model.Link]:
        """add more links."""
        return [
            *super().links(request),
            model.Link(
                title="Search (GET)",
                href=self.url_for(
                    request,
                    "search_get",
                ),
                type=MediaType.geojson,
                rel="data",
            ),
        ]

    def _items_route(self):  # noqa: C901
        @self.router.get(
            "/collections/{collectionId}/items",
            response_class=GeoJSONResponse,
            responses={
                200: {
                    "content": {
                        MediaType.geojson.value: {},
                        MediaType.html.value: {},
                        MediaType.csv.value: {},
                        MediaType.json.value: {},
                        MediaType.geojsonseq.value: {},
                        MediaType.ndjson.value: {},
                    },
                    "model": model.Items,
                },
            },
            tags=["OGC Features API"],
        )
        async def items(  # noqa: C901
            request: Request,
            collection: Annotated[
                PgSTACCollection, Depends(self.collection_dependency)
            ],
            ids_filter: Annotated[Optional[List[str]], Depends(ids_query)],
            bbox_filter: Annotated[Optional[List[float]], Depends(bbox_query)],
            datetime_filter: Annotated[Optional[List[str]], Depends(datetime_query)],
            properties: Annotated[Optional[List[str]], Depends(properties_query)],
            cql_filter: Annotated[Optional[AstType], Depends(filter_query)],
            sortby: Annotated[Optional[str], Depends(sortby_query)],
            query: Annotated[
                Optional[str],
                Query(
                    description="Additional filtering based on the properties of Item objects."
                ),
            ] = None,
            limit: Annotated[
                int,
                Query(
                    ge=0,
                    le=features_settings.max_features_per_query,
                    description="Limits the number of features in the response.",
                ),
            ] = features_settings.default_features_limit,
            offset: Annotated[
                Optional[str],
                Query(
                    description="Starts the response at an specific item.",
                ),
            ] = None,
            output_type: Annotated[
                Optional[MediaType], Depends(ItemsOutputType)
            ] = None,
        ):
            output_type = output_type or MediaType.geojson

            item_list = await collection.features(
                request.app.state.pool,
                ids_filter=ids_filter,
                bbox_filter=bbox_filter,
                datetime_filter=datetime_filter,
                cql_filter=cql_filter,
                sortby=sortby,
                properties=properties,
                limit=limit,
                token=offset,
                query=query,
            )

            if output_type in (
                MediaType.csv,
                MediaType.json,
                MediaType.ndjson,
            ):
                if any(
                    [f.get("geometry", None) is not None for f in item_list["items"]]
                ):
                    rows = (
                        {
                            "collectionId": collection.id,
                            "itemId": f.get("id"),
                            **f.get("properties", {}),
                            "geometry": parse_geometry_obj(f["geometry"]).wkt
                            if f.get("geometry", None)
                            else None,
                        }
                        for f in item_list["items"]
                    )
                else:
                    rows = (
                        {
                            "collectionId": collection.id,
                            "itemId": f.get("id"),
                            **f.get("properties", {}),
                        }
                        for f in item_list["items"]
                    )

                # CSV Response
                if output_type == MediaType.csv:
                    return StreamingResponse(
                        factory.create_csv_rows(rows),
                        media_type=MediaType.csv,
                        headers={
                            "Content-Disposition": "attachment;filename=items.csv"
                        },
                    )

                # JSON Response
                if output_type == MediaType.json:
                    return ORJSONResponse(list(rows))

                # NDJSON Response
                if output_type == MediaType.ndjson:
                    return StreamingResponse(
                        (orjsonDumps(row) + b"\n" for row in rows),
                        media_type=MediaType.ndjson,
                        headers={
                            "Content-Disposition": "attachment;filename=items.ndjson"
                        },
                    )

            qs = "?" + str(request.query_params) if request.query_params else ""
            links: List[Dict] = [
                {
                    "title": "Collection",
                    "href": self.url_for(
                        request, "collection", collectionId=collection.id
                    ),
                    "rel": "collection",
                    "type": "application/json",
                },
                {
                    "title": "Items",
                    "href": self.url_for(request, "items", collectionId=collection.id)
                    + qs,
                    "rel": "self",
                    "type": "application/geo+json",
                },
            ]

            if next_token := item_list["next"]:
                query_params = QueryParams(
                    {**request.query_params, "offset": next_token}
                )
                url = (
                    self.url_for(request, "items", collectionId=collection.id)
                    + f"?{query_params}"
                )
                links.append(
                    {
                        "href": url,
                        "rel": "next",
                        "type": "application/geo+json",
                        "title": "Next page",
                    },
                )

            if item_list["prev"] is not None:
                prev_token = item_list["prev"]
                qp = dict(request.query_params)
                qp.pop("offset")
                query_params = QueryParams({**qp, "offset": prev_token})
                url = self.url_for(request, "items", collectionId=collection.id)
                if query_params:
                    url += f"?{query_params}"

                links.append(
                    {
                        "href": url,
                        "rel": "prev",
                        "type": "application/geo+json",
                        "title": "Previous page",
                    },
                )

            data = {
                "type": "FeatureCollection",
                "id": collection.id,
                "title": collection.title or collection.id,
                "description": collection.description
                or collection.title
                or collection.id,
                "numberMatched": item_list["matched"],
                "numberReturned": len(item_list["items"]),
                "links": links,
                "features": [
                    {
                        **feature,  # type: ignore
                        "links": [
                            {
                                "title": "Collection",
                                "href": self.url_for(
                                    request,
                                    "collection",
                                    collectionId=collection.id,
                                ),
                                "rel": "collection",
                                "type": "application/json",
                            },
                            {
                                "title": "Item",
                                "href": self.url_for(
                                    request,
                                    "item",
                                    collectionId=collection.id,
                                    itemId=feature.get("id"),
                                ),
                                "rel": "item",
                                "type": "application/geo+json",
                            },
                        ],
                    }
                    for feature in item_list["items"]
                ],
            }

            # HTML Response
            if output_type == MediaType.html:
                return self._create_html_response(
                    request, orjsonDumps(data).decode(), template_name="items"
                )

            # GeoJSONSeq Response
            elif output_type == MediaType.geojsonseq:
                return StreamingResponse(
                    (orjsonDumps(f) + b"\n" for f in data["features"]),  # type: ignore
                    media_type=MediaType.geojsonseq,
                    headers={
                        "Content-Disposition": "attachment;filename=items.geojson"
                    },
                )

            # Default to GeoJSON Response
            return GeoJSONResponse(data)

    def _item_route(self):
        @self.router.get(
            "/collections/{collectionId}/items/{itemId}",
            response_class=GeoJSONResponse,
            responses={
                200: {
                    "content": {
                        MediaType.geojson.value: {},
                        MediaType.html.value: {},
                        MediaType.csv.value: {},
                        MediaType.json.value: {},
                        MediaType.geojsonseq.value: {},
                        MediaType.ndjson.value: {},
                    },
                    "model": model.Item,
                },
            },
            tags=["OGC Features API"],
        )
        async def item(
            request: Request,
            collection: Annotated[
                PgSTACCollection, Depends(self.collection_dependency)
            ],
            itemId: Annotated[str, Path(description="Item identifier")],
            properties: Optional[List[str]] = Depends(properties_query),
            output_type: Annotated[
                Optional[MediaType], Depends(ItemsOutputType)
            ] = None,
        ):
            output_type = output_type or MediaType.geojson
            item_list = await collection.features(
                pool=request.app.state.pool,
                ids_filter=[itemId],
                properties=properties,
            )

            if not item_list["items"]:
                raise NotFound(
                    f"Item {itemId} in Collection {collection.id} does not exist."
                )

            feature = item_list["items"][0]

            if output_type in (
                MediaType.csv,
                MediaType.json,
                MediaType.ndjson,
            ):
                row = {
                    "collectionId": collection.id,
                    "itemId": feature.get("id"),
                    **feature.get("properties", {}),
                }
                if feature.get("geometry") is not None:
                    row["geometry"] = (parse_geometry_obj(feature["geometry"]).wkt,)

                rows = iter([row])

                # CSV Response
                if output_type == MediaType.csv:
                    return StreamingResponse(
                        factory.create_csv_rows(rows),
                        media_type=MediaType.csv,
                        headers={
                            "Content-Disposition": "attachment;filename=items.csv"
                        },
                    )

                # JSON Response
                if output_type == MediaType.json:
                    return ORJSONResponse(rows.__next__())

                # NDJSON Response
                if output_type == MediaType.ndjson:
                    return StreamingResponse(
                        (orjsonDumps(row) + b"\n" for row in rows),
                        media_type=MediaType.ndjson,
                        headers={
                            "Content-Disposition": "attachment;filename=items.ndjson"
                        },
                    )

            data = {
                **feature,  # type: ignore
                "links": [
                    {
                        "href": self.url_for(
                            request, "collection", collectionId=collection.id
                        ),
                        "rel": "collection",
                        "type": "application/json",
                    },
                    {
                        "href": self.url_for(
                            request,
                            "item",
                            collectionId=collection.id,
                            itemId=itemId,
                        ),
                        "rel": "self",
                        "type": "application/geo+json",
                    },
                ],
            }

            # HTML Response
            if output_type == MediaType.html:
                return self._create_html_response(
                    request,
                    orjsonDumps(data).decode(),
                    template_name="item",
                )

            # Default to GeoJSON Response
            return GeoJSONResponse(data)

    def _searches_routes(self):  # noqa: C901
        @self.router.get(
            "/search",
            response_class=GeoJSONResponse,
            responses={
                200: {
                    "content": {
                        MediaType.geojson.value: {},
                        MediaType.html.value: {},
                        MediaType.csv.value: {},
                        MediaType.json.value: {},
                        MediaType.geojsonseq.value: {},
                        MediaType.ndjson.value: {},
                    },
                    "model": model.Items,
                },
            },
            tags=["OGC Features API"],
        )
        async def search_get(  # noqa: C901
            request: Request,
            collections_filter: Annotated[
                Optional[List[str]], Depends(collections_query)
            ],
            ids_filter: Annotated[Optional[List[str]], Depends(ids_query)],
            bbox_filter: Annotated[Optional[List[float]], Depends(bbox_query)],
            datetime_filter: Annotated[Optional[List[str]], Depends(datetime_query)],
            properties: Annotated[Optional[List[str]], Depends(properties_query)],
            cql_filter: Annotated[Optional[AstType], Depends(filter_query)],
            sortby: Annotated[Optional[str], Depends(sortby_query)],
            query: Annotated[
                Optional[str],
                Query(
                    description="Additional filtering based on the properties of Item objects."
                ),
            ] = None,
            limit: Annotated[
                int,
                Query(
                    ge=0,
                    le=features_settings.max_features_per_query,
                    description="Limits the number of features in the response.",
                ),
            ] = features_settings.default_features_limit,
            offset: Annotated[
                Optional[str],
                Query(
                    description="Starts the response at an specific item.",
                ),
            ] = None,
            output_type: Annotated[
                Optional[MediaType], Depends(ItemsOutputType)
            ] = None,
        ):
            """PgSTAC GET Search endpoint."""
            output_type = output_type or MediaType.geojson

            if datetime_filter:
                if len(datetime_filter) == 2:
                    start = (
                        parse_rfc3339(datetime_filter[0])
                        if datetime_filter[0] not in ["..", ""]
                        else None
                    )
                    end = (
                        parse_rfc3339(datetime_filter[1])
                        if datetime_filter[1] not in ["..", ""]
                        else None
                    )

                    if start is None and end is None:
                        raise InvalidDatetime(
                            "Double open-ended datetime intervals are not allowed."
                        )

                    if start is not None and end is not None and start > end:
                        raise InvalidDatetime(
                            "Start datetime cannot be before end datetime."
                        )

                datetime_filter = "/".join(datetime_filter)  # type: ignore

            base_args = {
                "collections": collections_filter,
                "ids": ids_filter,
                "bbox": bbox_filter,
                "limit": limit or features_settings.default_features_limit,
                "token": offset,
                "query": json.loads(unquote_plus(query)) if query else query,
            }

            if cql_filter:
                base_args["filter"] = json.loads(to_cql2(cql_filter))
                base_args["filter-lang"] = "cql2-json"

            if datetime_filter:
                base_args["datetime"] = datetime_filter

            if sortby:
                sort_param = []
                for s in sortby.strip().split(","):
                    if part := re.match("^(?P<direction>[+-]?)(?P<prop>.*)$", s):
                        parts = part.groupdict()
                        direction = parts["direction"]
                        prop = parts["prop"].strip()
                        sort_param.append(
                            {
                                "field": prop,
                                "direction": "desc" if direction == "-" else "asc",
                            }
                        )

                base_args["sortby"] = sort_param

            if properties:
                base_args["fields"] = {"include": set(properties)}

            clean = {}
            for k, v in base_args.items():
                if v is not None and v != []:
                    clean[k] = v

            search = PgSTACSearch.model_validate(clean)

            item_list = await pgstac_search(request.app.state.pool, search=search)

            if output_type in (
                MediaType.csv,
                MediaType.json,
                MediaType.ndjson,
            ):
                rows = (
                    {
                        k: v
                        for k, v in {
                            "collectionId": f.get("collection"),
                            "itemId": f.get("id"),
                            **f.get("properties", {}),
                            "geometry": parse_geometry_obj(f["geometry"]).wkt
                            if f.get("geometry")
                            else None,
                        }.items()
                        if v is not None
                    }
                    for f in item_list["items"]
                )

                # CSV Response
                if output_type == MediaType.csv:
                    return StreamingResponse(
                        factory.create_csv_rows(rows),
                        media_type=MediaType.csv,
                        headers={
                            "Content-Disposition": "attachment;filename=items.csv"
                        },
                    )

                # JSON Response
                if output_type == MediaType.json:
                    return ORJSONResponse(list(rows))

                # NDJSON Response
                if output_type == MediaType.ndjson:
                    return StreamingResponse(
                        (orjsonDumps(row) + b"\n" for row in rows),
                        media_type=MediaType.ndjson,
                        headers={
                            "Content-Disposition": "attachment;filename=items.ndjson"
                        },
                    )

            qs = "?" + str(request.query_params) if request.query_params else ""
            links: List[Dict] = [
                {
                    "title": "Search",
                    "href": self.url_for(request, "search_get") + qs,
                    "rel": "self",
                    "type": "application/geo+json",
                },
            ]
            if next_token := item_list["next"]:
                query_params = QueryParams(
                    {**request.query_params, "offset": next_token}
                )
                url = self.url_for(request, "search_get") + f"?{query_params}"
                links.append(
                    {
                        "href": url,
                        "rel": "next",
                        "type": "application/geo+json",
                        "title": "Next page",
                    },
                )

            if item_list["prev"] is not None:
                prev_token = item_list["prev"]
                qp = dict(request.query_params)
                qp.pop("offset")
                query_params = QueryParams({**qp, "offset": prev_token})
                url = self.url_for(request, "search_get")
                if query_params:
                    url += f"?{query_params}"

                links.append(
                    {
                        "href": url,
                        "rel": "prev",
                        "type": "application/geo+json",
                        "title": "Previous page",
                    },
                )

            data = {
                "type": "FeatureCollection",
                "description": json.dumps({**request.query_params}),
                "numberMatched": item_list["matched"],
                "numberReturned": len(item_list["items"]),
                "links": links,
                "features": [
                    {
                        **feature,  # type: ignore
                        "links": [
                            {
                                "title": "Collection",
                                "href": self.url_for(
                                    request,
                                    "collection",
                                    collectionId=feature["collection"],
                                ),
                                "rel": "collection",
                                "type": "application/json",
                            },
                            {
                                "title": "Item",
                                "href": self.url_for(
                                    request,
                                    "item",
                                    collectionId=feature["collection"],
                                    itemId=feature["id"],
                                ),
                                "rel": "item",
                                "type": "application/geo+json",
                            },
                        ],
                    }
                    for feature in item_list["items"]
                ],
            }

            # HTML Response
            if output_type == MediaType.html:
                return self._create_html_response(
                    request, orjsonDumps(data).decode(), template_name="search"
                )

            # GeoJSONSeq Response
            elif output_type == MediaType.geojsonseq:
                return StreamingResponse(
                    (orjsonDumps(f) + b"\n" for f in data["features"]),  # type: ignore
                    media_type=MediaType.geojsonseq,
                    headers={
                        "Content-Disposition": "attachment;filename=search.geojson"
                    },
                )

            # Default to GeoJSON Response
            return GeoJSONResponse(data)

        @self.router.post(
            "/search",
            response_class=GeoJSONResponse,
            responses={
                200: {
                    "content": {
                        MediaType.geojson.value: {},
                        MediaType.html.value: {},
                        MediaType.csv.value: {},
                        MediaType.json.value: {},
                        MediaType.geojsonseq.value: {},
                        MediaType.ndjson.value: {},
                    },
                    "model": PostItems,
                },
            },
            tags=["OGC Features API"],
        )
        async def search_post(  # noqa: C901
            request: Request,
            search: Annotated[
                Optional[PgSTACSearch],
                Body(description="PgSTAC Search."),
            ] = None,
            output_type: Annotated[
                Optional[MediaType], Depends(PostSearchOutputType)
            ] = None,
        ):
            """PgSTAC POST Search endpoint."""
            output_type = output_type or MediaType.geojson

            search = search or PgSTACSearch()
            item_list = await pgstac_search(request.app.state.pool, search=search)

            if output_type in (
                MediaType.csv,
                MediaType.json,
                MediaType.ndjson,
            ):
                rows = (
                    {
                        k: v
                        for k, v in {
                            "collectionId": f.get("collection"),
                            "itemId": f.get("id"),
                            **f.get("properties", {}),
                            "geometry": parse_geometry_obj(f["geometry"]).wkt
                            if f.get("geometry")
                            else None,
                        }.items()
                        if v is not None
                    }
                    for f in item_list["items"]
                )

                # CSV Response
                if output_type == MediaType.csv:
                    return StreamingResponse(
                        factory.create_csv_rows(rows),
                        media_type=MediaType.csv,
                        headers={
                            "Content-Disposition": "attachment;filename=items.csv"
                        },
                    )

                # JSON Response
                if output_type == MediaType.json:
                    return ORJSONResponse(list(rows))

                # NDJSON Response
                if output_type == MediaType.ndjson:
                    return StreamingResponse(
                        (orjsonDumps(row) + b"\n" for row in rows),
                        media_type=MediaType.ndjson,
                        headers={
                            "Content-Disposition": "attachment;filename=items.ndjson"
                        },
                    )

            qs = f"?{request.query_params}" if request.query_params else ""
            links: List[Dict] = [
                {
                    "title": "Search",
                    "href": self.url_for(request, "search_get") + qs,
                    "rel": "self",
                    "type": "application/geo+json",
                    "body": search.model_dump(exclude_unset=True, exclude_none=True),
                },
            ]
            if next_token := item_list["next"]:
                url = self.url_for(request, "search_post") + qs
                body = search.model_dump(exclude_unset=True, exclude_none=True)
                body["token"] = next_token
                links.append(
                    {
                        "href": url,
                        "rel": "next",
                        "type": "application/geo+json",
                        "title": "Next page",
                        "body": body,
                    },
                )

            if item_list["prev"] is not None:
                url = self.url_for(request, "search_post") + qs
                body = search.model_dump(exclude_unset=True, exclude_none=True)
                body["token"] = item_list["prev"]
                links.append(
                    {
                        "href": url,
                        "rel": "prev",
                        "type": "application/geo+json",
                        "title": "Previous page",
                        "body": body,
                    },
                )

            data = {
                "type": "FeatureCollection",
                "description": search.model_dump_json(
                    exclude_unset=True, exclude_none=True
                ),
                "numberMatched": item_list["matched"],
                "numberReturned": len(item_list["items"]),
                "links": links,
                "features": [
                    {
                        **feature,  # type: ignore
                        "links": [
                            {
                                "title": "Collection",
                                "href": self.url_for(
                                    request,
                                    "collection",
                                    collectionId=feature["collection"],
                                ),
                                "rel": "collection",
                                "type": "application/json",
                            },
                            {
                                "title": "Item",
                                "href": self.url_for(
                                    request,
                                    "item",
                                    collectionId=feature["collection"],
                                    itemId=feature["id"],
                                ),
                                "rel": "item",
                                "type": "application/geo+json",
                            },
                        ],
                    }
                    for feature in item_list["items"]
                ],
            }

            # HTML Response
            if output_type == MediaType.html:
                return self._create_html_response(
                    request, orjsonDumps(data).decode(), template_name="search"
                )

            # GeoJSONSeq Response
            elif output_type == MediaType.geojsonseq:
                return StreamingResponse(
                    (orjsonDumps(f) + b"\n" for f in data["features"]),  # type: ignore
                    media_type=MediaType.geojsonseq,
                    headers={
                        "Content-Disposition": "attachment;filename=search.geojson"
                    },
                )

            # Default to GeoJSON Response
            return GeoJSONResponse(data)
