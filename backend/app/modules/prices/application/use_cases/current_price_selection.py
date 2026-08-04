"""Selección de precios actuales dentro de la capa application."""

from app.modules.prices.domain.entities import Price


def select_current_prices(prices: list[Price]) -> list[Price]:
    """Selecciona el último precio disponible por producto fuente y sucursal.

    Regla de MVP:
    - se descartan precios no disponibles;
    - se agrupa por ``(product_source_id, branch_id)``;
    - se conserva el precio con mayor ``observed_at``;
    - ante empate de fecha, se conserva el menor importe.

    ``product_source_id`` ya referencia al producto normalizado, por eso esta
    clave evita duplicados históricos por producto, sucursal y producto fuente.
    """
    latest: dict[tuple[str, str], Price] = {}

    for price in prices:
        if not price.available:
            continue

        key = (str(price.product_source_id), str(price.branch_id))
        current = latest.get(key)
        if current is None:
            latest[key] = price
            continue

        if price.observed_at > current.observed_at:
            latest[key] = price
        elif price.observed_at == current.observed_at and price.amount < current.amount:
            latest[key] = price

    return sorted(
        latest.values(),
        key=lambda item: (
            item.observed_at,
            str(item.branch_id),
            str(item.product_source_id),
        ),
        reverse=True,
    )
