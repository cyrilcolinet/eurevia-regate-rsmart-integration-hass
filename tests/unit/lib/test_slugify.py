"""Tests for slugify helper."""

from eurevia_regate_rsmart.lib.slugify import slugify_snake


def test_slugify_snake_normalizes_accents():
    assert slugify_snake("Séjour") == "sejour"


def test_slugify_snake_collapses_separators():
    assert slugify_snake("Chambre  du  Poux") == "chambre_du_poux"
