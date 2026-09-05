"""No-op telemetry adapter for embedded Chroma usage."""

from chromadb.telemetry.product import ProductTelemetryClient, ProductTelemetryEvent
from overrides import override


class NoopProductTelemetry(ProductTelemetryClient):
    """Drops Chroma product telemetry events locally."""

    @override
    def capture(self, event: ProductTelemetryEvent) -> None:
        return None
