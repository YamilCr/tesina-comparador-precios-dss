from uuid import uuid4

from app.modules.catalog.domain.entities import Product
from app.modules.ingestion.infrastructure.etl import ProductIdentityCandidate, ProductIdentityMatcher
from app.modules.ingestion.application.category_evidence import category_from_payload


def test_ambiguous_exact_candidates_require_review():
    candidates = [ProductIdentityCandidate(Product(uuid4(), "Arroz Gallo 500 g"), "Gallo") for _ in range(2)]
    decision = ProductIdentityMatcher().assess(name="Arroz Gallo 500 g", presentation=None, brand="Gallo", candidates=candidates)
    assert decision.status == "review_required"
    assert len(decision.candidate_ids) == 2


def test_structural_conflict_is_not_a_review_candidate():
    candidates = [ProductIdentityCandidate(Product(uuid4(), "Arroz Gallo 1000 g"), "Gallo")]
    decision = ProductIdentityMatcher().assess(name="Arroz Gallo 500 g", presentation=None, brand="Gallo", candidates=candidates)
    assert decision.status == "no_match"


def test_verified_scons_presentation_matches():
    candidates = [ProductIdentityCandidate(Product(uuid4(), "Scons 9 de Oro 200 g"), "9 de Oro")]
    decision = ProductIdentityMatcher().assess(name="Sconcitos 9 de Oro 200 g", presentation=None, brand="9 de Oro", candidates=candidates)
    assert decision.status == "matched"
    assert decision.match.product.id == candidates[0].product.id


def test_categories_use_only_unambiguous_explicit_paths():
    assert category_from_payload({"categories": ["/Almacen/Arroz/", "/Almacen/"]}) == "Arroz"
    assert category_from_payload({"categories": ["/Almacen/", "/Promociones/"]}) is None
    assert category_from_payload({"name": "Arroz Gallo"}) is None


def test_verified_sconcitos_alias_preserves_other_variants_and_packs():
    from app.modules.ingestion.infrastructure.etl import product_matching_key
    expected = product_matching_key("Sconcitos 9 De Oro 200g")
    assert product_matching_key("bizcochos 9 de oro sconcitos 200grs") == expected
    assert product_matching_key("SCONS 9 DE ORO 200 GR") == expected
    for name in ["Scons 9 de Oro 200 g pack x2", "Scons 9 de Oro 500 g",
                 "Bizcochos 9 de Oro salvado 200 g", "Scons Otra Marca 200 g"]:
        assert product_matching_key(name) != expected
