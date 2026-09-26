from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.catalog.domain.entities import Product
from app.modules.decision.domain.services.substitution_policy import (
    compatible,
    known_brand_aliases,
    similar_product,
)


def product(name, **kwargs):
    return Product(id=uuid4(), normalized_name=name, **kwargs)


@pytest.mark.parametrize(
    "left,right",
    [
        ("Arroz largo fino Uno 1 kg", "Arroz largo fino Dos 1000 g"),
        ("Leche entera Uno 1 L", "Leche entera Dos 1000 ml"),
        ("Arroz Uno x 1 kg pack x2", "Arroz Dos 1000 g 2 un"),
        ("Arroz Uno 500 g pack x2", "Arroz Dos 500 g x 2"),
    ],
)
def test_allows_other_brand_and_equivalent_presentation(left, right):
    assert compatible(product(left), product(right), "Uno", "Dos")


@pytest.mark.parametrize(
    "name",
    [
        "Arroz integral Dos 1 kg",
        "Arroz largo fino Dos 500 g",
        "Arroz largo fino Dos 1 L",
        "Arroz largo fino Dos 1 kg pack x2",
        "Arroz largo fino Dos",
        "Arroz largo fino Dos 1 kg pack",
        "Arroz largo fino sin gluten Dos 1 kg",
        "Arroz largo fino Dos 1 kg x2 x3",
    ],
)
def test_rejects_type_variant_quantity_pack_or_ambiguous_attributes(name):
    assert not compatible(product("Arroz largo fino Uno 1 kg"), product(name), "Uno", "Dos")


def test_preserves_declared_restrictions_and_categories():
    left = product("Leche entera 1 L", category_id=uuid4(), description="Sin lactosa")
    right = product("Leche entera 1 L", category_id=None)
    assert not compatible(left, right)
    assert compatible(left, replace(right, description="Sin lactosa"))
    assert not compatible(left, replace(right, description="Sin lactosa", category_id=uuid4()))
    assert not compatible(left, replace(right, active=False))


def test_fields_must_agree_with_name_and_descriptor_is_required():
    left = product("Arroz Uno 1 kg", unit_measure="g", net_content=Decimal("500"))
    assert not compatible(left, product("Arroz Dos 500 g"), "Uno", "Dos")
    assert not compatible(product("Uno 1 L"), product("Dos 1 L"), "Uno", "Dos")


@pytest.mark.parametrize(
    "left,right",
    [
        ("Bizcocho dulce Uno 200 g", "Bizcochos dulces Dos 200 g"),
        ("Bizcocho original Uno 200 g", "Bizcochos originales Dos 200 g"),
        ("Arroz Parboilizado Bolsa Gallo x 1 Kg.", "Arroz Parbolizado Bolsa Dos Hermanos x 1 Kg."),
        ("Galletitas c/chips Uno 120 g", "Galletitas con chips Dos 120 g"),
        ("Galletitas s/azucar Uno 120 g", "Galletitas sin azucar Dos 120 g"),
        ("Arroz integral Uno 1kgs", "Arroz integral Dos 1000 g"),
    ],
)
def test_limited_wording_differences_keep_structural_constraints(left, right):
    left_brand, right_brand = ("Gallo", "Dos Hermanos") if "Bolsa" in left else ("Uno", "Dos")
    a, b = product(left), product(right)
    assert compatible(a, b, left_brand, right_brand)
    assert compatible(b, a, right_brand, left_brand)


def test_explicit_brand_spelling_without_guessing_missing_brands():
    original = product("Arroz Luchetti Integral X1kg")
    replacement = product("Arroz Integral 1 Kg Dos Hermanos")
    assert compatible(original, replacement, "Lucchetti", "Dos Hermanos")
    assert not compatible(original, replacement, None, "Dos Hermanos")


def test_product_and_type_matching_recovers_missing_brand_metadata():
    original = product("ARROZ ALA LARGO 1 KG", unit_measure="KG", net_content=Decimal("1"))
    replacement = product("Arroz Dos Hermanos Largo Fino 00000 1000grs")
    aliases = known_brand_aliases(["Molinos Ala", "Dos Hermanos"])

    assert compatible(original, replacement, None, "Dos Hermanos", known_brands=aliases)
    assert compatible(replacement, original, "Dos Hermanos", None, known_brands=aliases)
    assert not compatible(original, replacement, None, "Dos Hermanos")


@pytest.mark.parametrize(
    "name",
    [
        "Arroz Dos Hermanos Integral 1 Kg",
        "Arroz Dos Hermanos Parboil 1 Kg",
        "Arroz Dos Hermanos Largo Fino 00000 500 g",
        "Arroz Dos Hermanos Largo Fino 00000 1 Kg pack x2",
        "Arroz Dos Hermanos Largo Fino 00000 Sin Gluten 1 Kg",
        "Alfajor de Arroz Largo Dos Hermanos 1 Kg",
    ],
)
def test_generalized_rice_type_keeps_variant_and_presentation_boundaries(name):
    original = product("ARROZ ALA LARGO 1 KG")
    replacement = product(name)
    aliases = known_brand_aliases(["Molinos Ala", "Dos Hermanos"])

    assert not compatible(original, replacement, None, "Dos Hermanos", known_brands=aliases)


@pytest.mark.parametrize(
    "left,right",
    [
        ("Galletitas sin azucar 120 g", "Galletitas con azucar 120 g"),
        ("Leche descremada 1 L", "Leche entera 1 L"),
        ("Leche 1.5% grasa 1 L", "Leche 5.1% grasa 1 L"),
        ("Arroz largo fino 1 kg", "Arroz integral 1 kg"),
        ("Arroz parboil 1 kg", "Arroz parboilizado 1 kg"),
        ("Galletitas sin gluten 120 g", "Galletitas 120 g"),
        ("Arroz parboilizado bolsa 1 kg", "Arroz parbolizado 1 kg"),
        ("Galletita dulce 120 g", "Galletitas dulces 200 g"),
        ("Galletita dulce 120 g", "Galletitas dulces 120 g pack x2"),
        ("Arroz parboilizado 1 kg", "Arroz parbolizado 1 L"),
        ("Galletitas azucaradas 120 g", "Galletitas azucarados 120 g"),
    ],
)
def test_wording_tolerance_does_not_erase_meaning(left, right):
    assert not compatible(product(left), product(right))


@pytest.mark.parametrize(
    "original,replacement",
    [
        ("Arroz Ala Largo 1 kg", "Arroz Dos Hermanos Integral 500 g"),
        ("Leche entera 1 L", "Leche descremada 500 ml pack x2"),
        ("Galletitas dulces 120 g", "Galletita salada 350 g"),
    ],
)
def test_similar_products_allow_presentation_and_variant_changes(original, replacement):
    assert similar_product(product(original), product(replacement), "Ala", "Dos Hermanos")


def test_similar_products_still_require_a_real_family_and_chain_safe_category():
    category = uuid4()
    assert not similar_product(product("Arroz largo 1 kg"), product("Fideos largos 1 kg"))
    assert not similar_product(product("Arroz largo 1 kg"), product("Alfajor de arroz 1 kg"))
    assert not similar_product(
        product("Leche entera 1 L", category_id=category),
        product("Leche descremada 500 ml", category_id=uuid4()),
    )
