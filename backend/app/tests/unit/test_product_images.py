import pytest

from app.modules.ingestion.application.product_images import normalize_image_url


@pytest.mark.parametrize("value", [None, "", 42, {}, "javascript:alert(1)", "data:image/png,x", "https://", "https://user:pass@shop.test/a", "https://shop.test/a b", "https://[invalid"])
def test_invalid_image_is_optional(value):
    assert normalize_image_url(value) is None


@pytest.mark.parametrize("value,expected", [
    (" /images/a.jpg ", "https://shop.test/images/a.jpg"),
    ("//cdn.test/a.jpg", "https://cdn.test/a.jpg"),
    ("https://cdn.test/a.jpg?v=2", "https://cdn.test/a.jpg?v=2"),
])
def test_image_links_resolve_against_product_page(value, expected):
    assert normalize_image_url(value, "https://shop.test/products/a") == expected
