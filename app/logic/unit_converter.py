"""
Unit Conversion Engine for the Ingredient Inventory System.

Supports conversions within the same measurement family only:
    Liquid family:   ml <-> l
    Weight family:   g  <-> kg
    Discrete family: unidad | pieza | botella | lata  (no cross-unit conversion)

Cross-family conversions (e.g., ml -> g) are BLOCKED by design.
"""

from decimal import Decimal
from typing import Dict, FrozenSet, Set

# ─── Unit family definitions ──────────────────────────────────────────────────

UNIT_FAMILIES: Dict[str, FrozenSet[str]] = {
    "liquido":  frozenset({"ml", "l"}),
    "peso":     frozenset({"g", "kg"}),
    "discreto": frozenset({"unidad", "pieza", "botella", "lata"}),
}

# Reverse lookup: unit -> family name
UNIT_TO_FAMILY: Dict[str, str] = {}
for _family, _units in UNIT_FAMILIES.items():
    for _unit in _units:
        UNIT_TO_FAMILY[_unit] = _family

VALID_UNITS: Set[str] = set(UNIT_TO_FAMILY.keys())

# ─── Conversion factors (multiply source qty to get target qty) ───────────────
# Only within the same family. Discrete units have no cross-unit conversions.

_FACTORS: Dict[str, Dict[str, Decimal]] = {
    # Liquid
    "ml": {"ml": Decimal("1"),      "l": Decimal("0.001")},
    "l":  {"l":  Decimal("1"),      "ml": Decimal("1000")},
    # Weight
    "g":  {"g":  Decimal("1"),      "kg": Decimal("0.001")},
    "kg": {"kg": Decimal("1"),      "g":  Decimal("1000")},
    # Discrete — only same-to-same
    "unidad":  {"unidad":  Decimal("1")},
    "pieza":   {"pieza":   Decimal("1")},
    "botella": {"botella": Decimal("1")},
    "lata":    {"lata":    Decimal("1")},
}


class UnitConversionError(ValueError):
    """Raised when an impossible unit conversion is requested."""
    pass


def convert(cantidad: Decimal, unidad_origen: str, unidad_destino: str) -> Decimal:
    """
    Convert *cantidad* from *unidad_origen* to *unidad_destino*.

    Args:
        cantidad:        Quantity to convert (must be >= 0).
        unidad_origen:   Source unit (must be in VALID_UNITS).
        unidad_destino:  Target unit (must be in VALID_UNITS).

    Returns:
        Converted quantity as Decimal.

    Raises:
        UnitConversionError: If units are invalid or from different families.
    """
    # Validate units
    if unidad_origen not in VALID_UNITS:
        raise UnitConversionError(
            f"Unidad de origen inválida: '{unidad_origen}'. "
            f"Unidades válidas: {sorted(VALID_UNITS)}"
        )
    if unidad_destino not in VALID_UNITS:
        raise UnitConversionError(
            f"Unidad de destino inválida: '{unidad_destino}'. "
            f"Unidades válidas: {sorted(VALID_UNITS)}"
        )

    # Short-circuit: same unit
    if unidad_origen == unidad_destino:
        return Decimal(str(cantidad))

    # Check family compatibility
    familia_origen  = UNIT_TO_FAMILY[unidad_origen]
    familia_destino = UNIT_TO_FAMILY[unidad_destino]

    if familia_origen != familia_destino:
        raise UnitConversionError(
            f"Conversión imposible: '{unidad_origen}' pertenece a la familia "
            f"'{familia_origen}', pero '{unidad_destino}' pertenece a "
            f"'{familia_destino}'. Solo se permiten conversiones dentro de la "
            f"misma familia de unidades."
        )

    # Discrete family: no cross-unit conversion allowed (e.g., botella -> lata)
    if familia_origen == "discreto":
        raise UnitConversionError(
            f"Conversión imposible entre unidades discretas: "
            f"'{unidad_origen}' -> '{unidad_destino}'. "
            f"Las unidades discretas no son intercambiables."
        )

    factor = _FACTORS.get(unidad_origen, {}).get(unidad_destino)
    if factor is None:
        raise UnitConversionError(
            f"No existe factor de conversión de '{unidad_origen}' a '{unidad_destino}'."
        )

    return Decimal(str(cantidad)) * factor


def get_family(unidad: str) -> str:
    """Returns the family name for a unit, or raises UnitConversionError."""
    if unidad not in UNIT_TO_FAMILY:
        raise UnitConversionError(
            f"Unidad desconocida: '{unidad}'. Válidas: {sorted(VALID_UNITS)}"
        )
    return UNIT_TO_FAMILY[unidad]


def are_compatible(unidad_a: str, unidad_b: str) -> bool:
    """Returns True if both units belong to the same measurement family."""
    try:
        return get_family(unidad_a) == get_family(unidad_b)
    except UnitConversionError:
        return False
