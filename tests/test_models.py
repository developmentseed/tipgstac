"""tipgstac test models."""


import pytest
from geojson_pydantic import Polygon
from pydantic import ValidationError

from tipgstac.models import CollectionsSearch, ItemsSearch


def test_items_search():
    """test items search."""
    p = Polygon.from_bounds(-10, -10, 10, 10)
    assert ItemsSearch(intersects=p)

    with pytest.raises(ValidationError):
        ItemsSearch(intersects=p, bbox=(-10, -10, 10, 10))

    assert ItemsSearch(bbox=(-10, -10, 10, 10))
    assert ItemsSearch(bbox=(-10, -10, 50, 10, 10, 100))

    with pytest.raises(ValidationError):
        ItemsSearch(bbox=(-10, -10, -20, 10))

    with pytest.raises(ValidationError):
        ItemsSearch(bbox=(-10, -10, 20, -20))

    with pytest.raises(ValidationError):
        ItemsSearch(bbox=(-10, -10, 100, 10, 10, 50))


def test_collections_search():
    """test collections search."""
    p = Polygon.from_bounds(-10, -10, 10, 10)
    assert CollectionsSearch(intersects=p)

    with pytest.raises(ValidationError):
        CollectionsSearch(intersects=p, bbox=(-10, -10, 10, 10))

    assert CollectionsSearch(bbox=(-10, -10, 10, 10))
    assert CollectionsSearch(bbox=(-10, -10, 50, 10, 10, 100))

    with pytest.raises(ValidationError):
        CollectionsSearch(bbox=(-10, -10, -20, 10))

    with pytest.raises(ValidationError):
        CollectionsSearch(bbox=(-10, -10, 20, -20))

    with pytest.raises(ValidationError):
        CollectionsSearch(bbox=(-10, -10, 100, 10, 10, 50))
