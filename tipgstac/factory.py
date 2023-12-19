"""Custom Factory.

PgSTAC uses `token: str` instead of `offset: int` which means we have to overwrite the /items endpoint.
"""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

from fastapi import Depends, Path, Query
from fastapi.responses import ORJSONResponse
from pygeofilter.ast import AstType
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
from tipg.errors import NoPrimaryKey, NotFound
from tipg.resources.enums import MediaType
from tipg.resources.response import GeoJSONResponse, orjsonDumps
from tipg.settings import FeaturesSettings
from tipgstac.collections import CollectionList, PgSTACCollection
from tipgstac.dependencies import CollectionParams, CollectionsParams

features_settings = FeaturesSettings()


@dataclass
class OGCFeaturesFactory(factory.OGCFeaturesFactory):
    """Override /items and /item endpoints."""

    collection_dependency: Callable[..., PgSTACCollection] = CollectionParams
    collections_dependency: Callable[..., CollectionList] = CollectionsParams

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
            bbox_only: Annotated[
                Optional[bool],
                Query(
                    description="Only return the bounding box of the feature.",
                    alias="bbox-only",
                ),
            ] = None,
            simplify: Annotated[
                Optional[float],
                Query(
                    description="Simplify the output geometry to given threshold in decimal degrees.",
                ),
            ] = None,
            output_type: Annotated[
                Optional[MediaType], Depends(ItemsOutputType)
            ] = None,
        ):
            output_type = output_type or MediaType.geojson
            geom_as_wkt = output_type not in [
                MediaType.geojson,
                MediaType.geojsonseq,
                MediaType.html,
            ]

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
                bbox_only=bbox_only,
                simplify=simplify,
                geom_as_wkt=geom_as_wkt,
                query=query,
            )

            if output_type in (
                MediaType.csv,
                MediaType.json,
                MediaType.ndjson,
            ):
                rows = (
                    {
                        k: v
                        for k, v in {
                            "collectionId": collection.id,
                            "itemId": f.get("id"),
                            **f.get("properties", {}),
                            "geometry": f.get("geometry", None),
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
            bbox_only: Annotated[
                Optional[bool],
                Query(
                    description="Only return the bounding box of the feature.",
                    alias="bbox-only",
                ),
            ] = None,
            simplify: Annotated[
                Optional[float],
                Query(
                    description="Simplify the output geometry to given threshold in decimal degrees.",
                ),
            ] = None,
            properties: Optional[List[str]] = Depends(properties_query),
            output_type: Annotated[
                Optional[MediaType], Depends(ItemsOutputType)
            ] = None,
        ):
            if collection.id_column is None:
                raise NoPrimaryKey("No primary key is set on this table")

            output_type = output_type or MediaType.geojson
            geom_as_wkt = output_type not in [
                MediaType.geojson,
                MediaType.geojsonseq,
                MediaType.html,
            ]

            item_list = await collection.features(
                pool=request.app.state.pool,
                bbox_only=bbox_only,
                simplify=simplify,
                ids_filter=[itemId],
                properties=properties,
                geom_as_wkt=geom_as_wkt,
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
                    row["geometry"] = (feature["geometry"],)
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
