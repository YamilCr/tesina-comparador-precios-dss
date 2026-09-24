from dataclasses import replace
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.catalog.domain.entities import Product
from app.modules.decision.domain.services.substitution_policy import compatible


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
