"""Pure generic helpers for the Eurevia reGATE integration."""

from .conversion import as_bool, as_float, as_int
from .slugify import slugify_snake

__all__ = [
    "as_bool",
    "as_float",
    "as_int",
    "slugify_snake",
]
