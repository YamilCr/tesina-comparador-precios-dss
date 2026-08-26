"""Services that prepare extracted records before they are loaded."""

from .price_cleaner import clean_price
from .product_identity_matcher import (
    ProductIdentityCandidate,
    ProductIdentityMatch,
    ProductIdentityMatcher,
)
from .product_normalizer import (
    NormalizedProduct,
    PackageQuantity,
    ProductIdentity,
    build_product_identity,
    catalog_quantity_fields,
    extract_package_quantity,
    normalize_gtin,
    normalized_brand_key,
    normalize_product,
    normalized_token_set,
    product_matching_key,
)
from .validation_rules import validate_scraped_product

__all__ = [
    "NormalizedProduct",
    "PackageQuantity",
    "ProductIdentity",
    "ProductIdentityCandidate",
    "ProductIdentityMatch",
    "ProductIdentityMatcher",
    "build_product_identity",
    "catalog_quantity_fields",
    "clean_price",
    "extract_package_quantity",
    "normalize_gtin",
    "normalized_brand_key",
    "normalize_product",
    "normalized_token_set",
    "product_matching_key",
    "validate_scraped_product",
]
